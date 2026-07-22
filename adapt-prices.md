# Adapt Prices — Feature Specification

## Overview

Automated regional pricing of in-app purchases based on GDP per capita with AI analysis.
Takes US prices as base, calculates optimal prices for 175+ countries, snaps to valid store tiers.

## How It Works

### Flow

1. **Input**: App URL or ID → fetch app info and IAPs with US prices
2. **AI Analysis** (optional): GPT-4 classifies app type and recommends coefficients per country category
3. **Price Calculation**: US price × country coefficient → target price
4. **Tier Snapping**: Apple — snap to nearest fixed tier (68 tiers). Google — round to cents
5. **Ratio Preservation**: If cheapest IAP hits minimum price, scale ALL IAPs proportionally
6. **Output**: Regional prices for all countries, exportable as CSV/JSON

### Country Categories (by GDP per capita)

| Category | GDP Range | Coefficient | Examples |
|---|---|---|---|
| Premium | >$90k | 1.05–1.15 | Luxembourg, Switzerland, Singapore |
| USA | $90k | 1.00 | United States (base) |
| High Income | $50k–$90k | 0.85–0.95 | Germany, UK, Canada, Australia |
| Upper Middle | $25k–$50k | 0.60–0.75 | Japan, Spain, Poland, South Korea |
| Lower Middle | $10k–$25k | 0.45–0.55 | Russia, China, Brazil, Mexico |
| Emerging | <$10k | 0.35–0.45 | India, Vietnam, Ukraine, Indonesia |

### Price Calculation Logic

```
coefficient = AI_coefficient or default_for_category
target_price = us_price × coefficient

# Minimum price protection (preserves ratios)
if cheapest_iap × coefficient < country_minimum:
    scale_factor = country_minimum / (cheapest_iap × coefficient)
    coefficient = coefficient × scale_factor
    # All IAPs use this adjusted coefficient

# Store-specific rounding
apple_price = find_nearest_tier(target_price)  # 68 fixed tiers: $0.29–$999.99
google_price = round(target_price, 2)          # any price allowed
```

### Minimum Prices (USD equivalent)

- Developed markets (US, GB, DE, FR, JP, CN): $0.99
- Developing markets (RU, IN, BR, MX, TR, ID, VN, UA, PK, PH, EG, NG): $0.49
- Default for unlisted: $0.49

### Apple Price Tiers (68 tiers, USD)

```
0.29, 0.49, 0.99, 1.49, 1.99, 2.49, 2.99, 3.49, 3.99, 4.49,
4.99, 5.49, 5.99, 6.49, 6.99, 7.49, 7.99, 8.49, 8.99, 9.49,
9.99, 10.99, 11.99, 12.99, 13.99, 14.99, 15.99, 16.99, 17.99,
18.99, 19.99, 20.99, 21.99, 22.99, 23.99, 24.99, 27.99, 29.99,
32.99, 34.99, 37.99, 39.99, 44.99, 49.99, 54.99, 59.99, 64.99,
69.99, 74.99, 79.99, 84.99, 89.99, 94.99, 99.99, 109.99, 119.99,
129.99, 139.99, 149.99, 159.99, 169.99, 179.99, 189.99, 199.99,
249.99, 299.99, 349.99, 399.99, 449.99, 499.99, 599.99, 699.99,
799.99, 899.99, 999.99
```

## AI Analysis Prompt

### System Message

```
You are an expert in mobile app pricing strategy and global market analysis. Return only valid JSON.
```

### User Prompt

```
Analyze this mobile application and recommend pricing coefficients for different markets.

App Information:
- Name: {app_name}
- Description: {description}
- Category: {category}
- Developer: {developer}
- Current In-App Purchases: {iap_list}

Based on this information, determine:

1. App Type Classification:
   - Is this a game, utility, AI tool, productivity app, or other?
   - Who is the target audience?

2. Price Elasticity Assessment:
   - How sensitive is demand to price changes?
   - Games typically have HIGH elasticity (users are price-sensitive)
   - AI/productivity tools typically have LOW elasticity (users pay for value)

3. Pricing Coefficients by Country Category:
   Recommend multipliers (relative to US price) for each tier:
   - Premium (Luxembourg, Switzerland, Ireland, Singapore, Norway): coefficient range
   - USA: always 1.00 (base price)
   - High Income (Germany, UK, Canada, Australia): coefficient range (typically 0.85-0.95)
   - Upper Middle (Poland, Japan, Spain, Italy): coefficient range
   - Lower Middle (Russia, Brazil, China, Mexico): coefficient range
   - Emerging (India, Vietnam, Ukraine): coefficient range

Important considerations:
- iPhone owners in lower-income countries are NOT the poorest people in those countries
- Don't set prices too low - minimum 35% of US price
- Consider purchasing power parity, not just raw GDP
- Games can have more aggressive regional pricing than professional tools
- For AI apps, prices should be more uniform globally (lower elasticity)
- For games, bigger price differences between regions are acceptable

Return your analysis as JSON with this structure:
{
  "app_type": "game|utility|ai_tool|productivity|other",
  "elasticity": "high|medium|low",
  "elasticity_score": 0.3-0.7,
  "reasoning": "brief explanation of your pricing strategy",
  "coefficients": {
    "premium": {"min": 1.05, "max": 1.15},
    "usa": {"min": 1.00, "max": 1.00},
    "high_income": {"min": 0.85, "max": 0.95},
    "upper_middle": {"min": 0.60, "max": 0.75},
    "lower_middle": {"min": 0.45, "max": 0.55},
    "emerging": {"min": 0.35, "max": 0.45}
  }
}

IMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting.
```

### AI Parameters

- Model: GPT-4 (configurable)
- Temperature: 0.3
- Max tokens: 1000
- Fallback: default coefficients if AI fails

### Expected Response

```json
{
  "app_type": "game",
  "elasticity": "high",
  "elasticity_score": 0.6,
  "reasoning": "Casual game with wide audience, high price sensitivity in emerging markets",
  "coefficients": {
    "premium": {"min": 1.05, "max": 1.15},
    "usa": {"min": 1.00, "max": 1.00},
    "high_income": {"min": 0.85, "max": 0.95},
    "upper_middle": {"min": 0.55, "max": 0.70},
    "lower_middle": {"min": 0.40, "max": 0.50},
    "emerging": {"min": 0.30, "max": 0.40}
  }
}
```

## Data Files

- `countries.csv` — 175+ countries with GDP, categories, default coefficients
- Source: IMF World Economic Outlook 2025 estimates

## Key Design Decisions

1. **US price is always the base** (coefficient 1.0)
2. **Preserve value ratios** — if one IAP is 2× another in US, same ratio everywhere
3. **Minimum price floor** — never go below $0.49 (emerging) or $0.99 (developed)
4. **Apple tiers are fixed** — snap to nearest, no custom prices allowed
5. **Google allows any price** — just round to cents
6. **AI is optional** — works with default coefficients, AI refines them
7. **iPhone ≠ poorest** — owners in poor countries have higher purchasing power than average
