# CLAUDE.md — Project Context for AI Agents

## What This Project Does

CLI tool that automates regional pricing for App Store in-app purchases and subscriptions. Calculates optimal prices for 175+ countries based on GDP per capita and optionally uses GPT to adjust coefficients per app type.

## Tech Stack

- Python 3.10+
- httpx — HTTP client for App Store Connect API
- PyJWT — JWT token generation for API auth
- openai — GPT integration for pricing analysis
- python-dotenv — .env config loading

## Architecture

```
src/
  cli.py          — Entry point, argument parsing, orchestration
  appstore.py     — App Store Connect API client (JWT auth, products, prices)
  pipeline.py     — Core workflow: find product → AI analysis → calculate → resolve → apply
  pricing.py      — Pure pricing logic: coefficients × US price → target prices
  countries.py    — Country data loader from CSV (GDP, categories, coefficients)
  ai_analyzer.py  — OpenAI integration, caching, cache clearing, prompt template
  display.py      — Terminal output formatting, dry-run tables

countries.csv     — 175+ countries with GDP per capita and default coefficients
.env              — Secrets (not committed)
.env.example      — Template for .env
```

## Key Patterns

- **Business logic is pure**: `pricing.py` has no I/O, no side effects
- **API client is stateful**: `AppStoreConnectClient` manages JWT token lifecycle with thread-safe locking
- **Context manager**: `AppStoreConnectClient` supports `with client:` pattern
- **Concurrent API calls**: `ThreadPoolExecutor` for equalizations and subscription price setting
- **AI caching**: Results cached in `.ai_cache/` by SHA-256 hash of app name; `--clear-cache` removes all cached results
- **IAP vs Subscription**: Different API endpoints and flows — IAPs use single atomic request, subscriptions need per-territory POST + pending price cleanup

## How to Run

```bash
pip install -e .
pytest                    # unit tests (114 tests)
pytest tests/integration  # integration tests (need real API keys)
adapt-prices-bot --app-id ID --iap PRODUCT_ID --dry-run
adapt-prices-bot --app-id ID --iap PRODUCT_ID --preserved --start-date 2026-08-01  # subscriptions only
adapt-prices-bot --clear-cache            # clear AI analysis cache
```

## Environment Variables

Required:
- `ASC_KEY_ID` — App Store Connect API Key ID
- `ASC_ISSUER_ID` — App Store Connect Issuer ID
- `ASC_PRIVATE_KEY_PATH` — Path to .p8 private key file

Optional:
- `OPENAI_API_KEY` — Enables AI pricing analysis (GPT-5.2)
- `ASC_REQUEST_TIMEOUT` — API timeout in seconds (default: 30)

## Important Notes

- **GPT model is `gpt-5.2`** — this is correct, do not change it
- **USA is always excluded** from country list (it's the base price)
- **Minimum coefficient is 0.35** (enforced in prompt, not in code)
- **Minimum prices**: $0.99 for premium/usa/high_income, $0.49 for others
- **Subscription price changes hit existing subscribers by default** (`preserveCurrentPrice=False`); pass `--preserved` to grandfather them. `--start-date` schedules the change (default: today+2). Both flags are subscriptions-only — CLI exits with an error for one-time IAPs.
- **Country categories**: premium, usa, high_income, upper_middle, lower_middle, emerging
- Tests mock `_load_cache` to avoid cache interference between test runs

## Error Handling Strategy

- API errors: specific httpx exceptions (HTTPStatusError, TimeoutException, ConnectError)
- CSV parsing: skip corrupt rows with warning
- AI responses: validate JSON structure, check coefficient types
- Pipeline: continue on partial failures (e.g., some equalizations fail), exit if all fail

## Files to Read for Each Task

| Task | Files |
|------|-------|
| Pricing logic | `src/pricing.py`, `src/countries.py` |
| API integration | `src/appstore.py` |
| AI analysis | `src/ai_analyzer.py` |
| CLI / orchestration | `src/cli.py`, `src/pipeline.py` |
| Output formatting | `src/display.py` |
| Country data | `countries.csv`, `src/countries.py` |
