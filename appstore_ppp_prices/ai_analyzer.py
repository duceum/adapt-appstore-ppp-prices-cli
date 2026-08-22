from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass

from openai import OpenAI

from appstore_ppp_prices.paths import user_cache_dir

log = logging.getLogger(__name__)

CACHE_DIR = user_cache_dir()


@dataclass
class AIResult:
    """Full result from AI pricing analysis."""
    app_type: str
    elasticity: str
    reasoning: str
    coefficients: dict[str, float]

SYSTEM_MESSAGE = "You are an expert in mobile app pricing strategy, revenue optimization, and global market analysis. Return only valid JSON."

USER_PROMPT_TEMPLATE = """Analyze this mobile application and recommend pricing coefficients that MAXIMIZE TOTAL REVENUE across all markets.

App Information:
- Name: {app_name}
- App Store Category: {category}
- Subtitle: {subtitle}
- Current In-App Purchases: {iap_list}

Your goal: find the coefficients (price multipliers relative to the US price) for each country tier that produce the HIGHEST overall revenue. This means balancing:
- Higher prices in markets that will pay them (low elasticity segments)
- Lower prices in markets where a price drop significantly increases conversion and volume

Steps:

1. App Type Classification:
   - Is this a game, utility, AI tool, productivity app, or other?
   - Who is the target audience?

2. Price Elasticity Assessment:
   - How sensitive is demand to price changes for THIS specific app type?
   - Games: HIGH elasticity — lower prices in developing markets drive much more volume
   - AI/productivity tools: LOW elasticity — users pay for value, uniform pricing loses less volume
   - Consider competitor pricing in the same category

3. Revenue-Maximizing Coefficients by Country Category:
   For each tier, recommend the multiplier (relative to US price) that maximizes revenue:
   - Revenue = Price × Conversions. A lower coefficient loses per-user revenue but may gain enough extra users to increase total revenue.
   - Premium (Luxembourg, Switzerland, Ireland, Singapore, Norway): these users have high willingness to pay
   - USA: always 1.00 (base price)
   - High Income (Germany, UK, Canada, Australia): slight discount may increase volume
   - Upper Middle (Poland, Japan, Spain, Italy): meaningful discount, balance volume vs. margin
   - Lower Middle (Russia, Brazil, China, Mexico): significant discount to capture large user bases
   - Emerging (India, Vietnam, Ukraine): aggressive discount, but not below 35% of US price

Key constraints:
- iPhone owners in lower-income countries are NOT the poorest — they already own premium devices
- Minimum coefficient: 0.35 (35% of US price) — going lower rarely increases total revenue
- For high-elasticity apps (games): aggressive regional discounts increase total revenue
- For low-elasticity apps (AI tools, pro tools): keep pricing more uniform — discounts don't drive enough extra volume to compensate
- For AI/ML apps: every user generates significant server-side costs (inference, API calls, GPU compute). These costs are FIXED per request regardless of what the user pays — a user paying 40% of US price costs exactly the same to serve as a full-price user. Server costs typically consume 30-50% of revenue, meaning aggressive discounts quickly make users unprofitable. The price floor for AI apps must be much higher than for games or content apps where marginal cost per user is near zero. When setting coefficients for AI apps, ensure that even the lowest-tier markets still generate enough revenue per user to cover operational costs with a healthy margin

Return your analysis as JSON with this structure:
{{
  "app_type": "game|utility|ai_tool|productivity|other",
  "elasticity": "high|medium|low",
  "elasticity_score": 0.3-0.7,
  "reasoning": "brief explanation of your revenue optimization strategy",
  "coefficients": {{
    "premium": 1.10,
    "usa": 1.00,
    "high_income": 0.90,
    "upper_middle": 0.7,
    "lower_middle": 0.50,
    "emerging": 0.40
  }}
}}

IMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting."""


def clear_cache() -> int:
    """Delete all cached AI analysis results. Returns number of files removed."""
    if not CACHE_DIR.exists():
        return 0
    removed = 0
    for f in CACHE_DIR.iterdir():
        if f.suffix == ".json":
            f.unlink()
            removed += 1
    try:
        CACHE_DIR.rmdir()
    except OSError:
        pass
    return removed


def _cache_key(app_name: str) -> str:
    raw = json.dumps({"app": app_name}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_cache(app_name: str) -> AIResult | None:
    key = _cache_key(app_name)
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return AIResult(**data)
    except Exception:
        return None


def _save_cache(app_name: str, result: AIResult) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = _cache_key(app_name)
        path = CACHE_DIR / f"{key}.json"
        path.write_text(json.dumps(asdict(result), indent=2))
    except OSError as e:
        log.warning("Failed to save AI cache: %s", e)


def analyze_app(
    api_key: str,
    app_name: str,
    products: list[dict],
    category: str = "",
    subtitle: str = "",
) -> AIResult | None:
    """Call AI to get pricing coefficients. Returns cached result if available."""
    cached = _load_cache(app_name)
    if cached:
        log.info("Using cached AI analysis")
        return cached

    iap_list = ", ".join(f"{p['name']} (${p['us_price']:.2f})" for p in products)
    prompt = USER_PROMPT_TEMPLATE.format(
        app_name=app_name,
        category=category or "N/A",
        subtitle=subtitle or "N/A",
        iap_list=iap_list or "N/A",
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-5.2",
            temperature=0.3,
            max_completion_tokens=2000,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": prompt},
            ],
        )
        if not response.choices:
            log.warning("AI analysis returned empty choices")
            return None
        text = response.choices[0].message.content.strip()
        # Strip markdown code blocks if model wraps JSON
        if text.startswith("```"):
            parts = text.split("\n", 1)
            text = parts[1].rsplit("```", 1)[0].strip() if len(parts) > 1 else ""
        data = json.loads(text)
    except (json.JSONDecodeError, AttributeError) as e:
        log.warning("AI response parsing failed: %s", e)
        return None
    except Exception as e:
        log.warning("AI API call failed: %s: %s", type(e).__name__, e)
        return None

    try:
        coefficients = data["coefficients"]
        coeff_map = {
            cat: round(float(v), 3)
            for cat, v in coefficients.items()
            if cat != "usa"
        }
        result = AIResult(
            app_type=data.get("app_type", "unknown"),
            elasticity=data.get("elasticity", "unknown"),
            reasoning=data.get("reasoning", ""),
            coefficients=coeff_map,
        )
        _save_cache(app_name, result)
        return result
    except (KeyError, TypeError, ValueError) as e:
        log.warning("Failed to parse AI response: %s", e)
        return None
