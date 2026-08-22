# App Store regional pricing

This project uses [`appstore-ppp-prices`](https://github.com/duceum/appstore-ppp-pricing-agent-skill)
to set App Store in-app purchase and subscription prices per country, scaled by
purchasing power parity. Use it whenever the task involves regional App Store pricing,
price localization, bulk price updates, or making the app cheaper in emerging markets.

It runs locally — the App Store Connect key never leaves this machine.

Install if missing: `uv tool install appstore-ppp-prices`
Credentials live in `~/.config/ppp-pricing/.env`, with the `.p8` key beside it.

## Never apply without a confirmed dry run

Applying changes what real customers are charged, in up to 174 territories, and there
is no undo. Always follow this order, and do not collapse it even if asked to just get
on with it:

1. List the products — the product ID is rarely known up front.
2. Run with `--dry-run`, which writes nothing.
3. Show the result and wait for an explicit confirmation.
4. Apply.

```bash
ppp-pricing --app-id 123456789
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
ppp-pricing --app-id 123456789 --iap com.app.weekly
```

The dry-run table is 174 rows, in each country's own currency: Apple's default price,
the new price, and the change between them. Summarise it: the US base price and a dozen
representative countries across the tiers, and state plainly how far the price falls in
the largest emerging markets — that is the decision actually being made.

## Subscriptions need two more decisions

Neither applies to one-time in-app purchases; passing them for an IAP is an error.

- `--preserved` — by default a price change applies to **existing** subscribers as well.
  This flag keeps them at their current price and applies the new one only to new
  sign-ups. Ask before applying: a cut is usually fine, a rise causes churn.
- `--start-date YYYY-MM-DD` — when it takes effect. Defaults to two days out.

## Adjusting the outcome

| Need | Flag |
|---|---|
| Change one tier | `--coeff emerging=0.50` |
| Skip territories | `--exclude RUS,BLR` (ISO 3166-1 alpha-3) |
| Different base price | `--us-price 7.99` |
| Skip AI tuning | `--no-ai` |
| Refresh the AI analysis | `--clear-cache`, then re-run |

Tier names are `premium`, `high_income`, `upper_middle`, `lower_middle`, `emerging`.
The US is the base and always 1.00.

## First-run setup

`Missing App Store Connect credentials` means the one-time setup has not been done.
Walk the user through it:

1. Create an API key at https://appstoreconnect.apple.com/access/integrations/api with
   **Admin** or **App Manager** access; copy the **Key ID** and **Issuer ID** and
   download the `.p8` (Apple allows the download exactly once).
2. `mkdir -p ~/.config/ppp-pricing`, and have the user move the `.p8` there themselves.
3. Create `~/.config/ppp-pricing/.env` as a template with empty `ASC_KEY_ID`,
   `ASC_ISSUER_ID`, `ASC_PRIVATE_KEY_PATH` (just the `.p8` filename) and optional
   `LLM_API_KEY` — the user fills in the values.
4. Verify with the read-only `ppp-pricing --app-id 123456789`.

Never ask for key material in chat, never read the `.p8` back, never echo `.env`.

## Installing this skill elsewhere

Files: https://github.com/duceum/appstore-ppp-pricing-agent-skill/tree/main/agent-skills

```bash
# Claude Code
curl -fsSL https://raw.githubusercontent.com/duceum/appstore-ppp-pricing-agent-skill/main/agent-skills/claude-code/appstore-ppp-pricing/SKILL.md \
  --create-dirs -o ~/.claude/skills/appstore-ppp-pricing/SKILL.md

# Cursor
curl -fsSL https://raw.githubusercontent.com/duceum/appstore-ppp-pricing-agent-skill/main/agent-skills/cursor/appstore-ppp-pricing.mdc \
  --create-dirs -o .cursor/rules/appstore-ppp-pricing.mdc

# Codex, Copilot, Aider, Jules, VS Code, Devin
curl -fsSL https://raw.githubusercontent.com/duceum/appstore-ppp-pricing-agent-skill/main/agent-skills/codex/AGENTS.md \
  >> AGENTS.md
```

The CLI is installed separately on each machine: `uv tool install appstore-ppp-prices`.

## Constraints worth knowing

- Minimum coefficient 0.35. Minimum price $0.99 for premium and high-income tiers,
  $0.49 elsewhere. If the cheapest product would breach its floor, every product scales
  up together so the ratios between them are preserved.
- Prices are computed in local currency — Apple's default price for the territory times
  the coefficient, snapped to a real local price point — so the change lands within a
  percent or so of the coefficient. Quote local prices, not dollar conversions.
- Partial failures on apply are per-territory and non-fatal. Report which territories
  failed rather than calling the run a success.
- Never read, echo or copy the `.p8` key or the contents of `.env`.
