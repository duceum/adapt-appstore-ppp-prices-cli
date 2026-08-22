---
name: appstore-ppp-pricing
description: Bulk-sets App Store in-app purchase and subscription prices across 175+ countries by purchasing power parity, using the appstore-ppp-prices CLI. Use whenever the user wants to localize, bulk-update, lower, raise or review regional App Store pricing — "set regional prices", "PPP pricing", "make my app cheaper in India", "update prices in every country", "localize subscription prices", "my app is too expensive in Brazil". Covers previewing before applying, protecting existing subscribers, and scheduling changes.
license: MIT
---

# App Store PPP pricing

Sets per-country App Store prices from a US base price, scaled by purchasing power.
The tool is a local CLI — the App Store Connect key stays on the user's machine.

## Before anything else

Check the tool is installed:

```bash
ppp-pricing --version
```

Not installed → `uv tool install appstore-ppp-prices` (or `pipx install appstore-ppp-prices`).

## First-run setup

If any command reports `Missing App Store Connect credentials`, walk the user through
this. It is the usual blocker and it is a one-time cost.

The tool needs an App Store Connect API key with pricing permissions. Only the user can
create one — it is behind their Apple account:

1. Open https://appstoreconnect.apple.com/access/integrations/api
2. **Generate API Key**, access level **Admin** or **App Manager**
3. Copy the **Key ID** (10 characters) and the **Issuer ID** (the UUID at the top)
4. Download the `.p8` file — Apple allows this exactly once

Then prepare the config directory for them:

```bash
mkdir -p ~/.config/ppp-pricing
```

Ask the user to move the downloaded key there themselves and to fill in the values:

```bash
mv ~/Downloads/AuthKey_XXXXXXXXXX.p8 ~/.config/ppp-pricing/
```

You may create `~/.config/ppp-pricing/.env` as a template with empty values for
`ASC_KEY_ID`, `ASC_ISSUER_ID` and `ASC_PRIVATE_KEY_PATH` (plus optional
`LLM_API_KEY`), and explain what goes in each. `ASC_PRIVATE_KEY_PATH` is just the
`.p8` filename — it resolves next to the `.env`.

Do not ask the user to paste key material into the chat, do not read the `.p8` back,
and do not echo the contents of `.env`. The user fills in the values; you never see them.

Confirm setup worked by listing products, which is read-only:

```bash
ppp-pricing --app-id 123456789
```

Alternative config locations, if the user wants one: `--config /path/to/dir`, the
`PPP_PRICING_CONFIG` environment variable, or a `.env` in the working directory.

## The one rule that matters

**Never run an apply without showing the user a dry run first and getting an explicit
yes.** This command changes what real customers are charged, in up to 174 territories,
and there is no undo. A price change is visible to users and, for subscriptions, can
trigger churn and Apple's own price-consent flows.

The sequence is always:

1. list products → 2. dry run → 3. show the table → 4. wait for confirmation → 5. apply

Do not collapse these steps, even when the user says "just do it". Run the dry run,
show what will change, then apply.

## 1. Find the product

The user rarely knows the product ID. List them:

```bash
ppp-pricing --app-id 123456789
```

Prints every IAP and subscription with its US price, tagged `[IAP]` or `[SUB]`. The
app ID is the 9-digit number from App Store Connect. Pick the product with the user
if more than one plausibly matches.

## 2. Preview

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Writes nothing. Prints all 174 target prices with the coefficient used and the Apple
price tier each one snapped to.

The table is long. Summarise it for the user rather than pasting all of it: the base
US price, and roughly a dozen representative countries across the tiers — a premium
market, a high-income one, a couple of upper-middle, and several emerging. Say
explicitly how much the price drops in the biggest emerging markets, because that is
the decision the user is actually making.

## 3. Apply

Only after the user confirms:

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly
```

## Subscriptions need two extra decisions

Ask about both before applying to a `[SUB]` product. Neither applies to one-time IAPs —
passing them for an IAP is an error.

**Existing subscribers.** By default the new price applies to *everyone*, including
people already subscribed. That is often not what the user wants: a price cut is fine,
but a price rise on existing subscribers causes churn and requires consent in some
territories. `--preserved` keeps current subscribers at their old price and applies the
new one only to new sign-ups.

**When it takes effect.** Defaults to two days out. `--start-date YYYY-MM-DD` schedules
it further ahead — useful when the user wants to announce a change first.

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly --preserved --start-date 2026-09-01
```

## Adjusting the result

| The user says | Use |
|---|---|
| "too cheap in emerging markets" | `--coeff emerging=0.50` — one category at a time, repeatable |
| "don't touch Russia" | `--exclude RUS,BLR` — ISO 3166-1 alpha-3, comma-separated |
| "price it from $7.99 instead" | `--us-price 7.99` — also sets the new US price on apply |
| "skip the AI part" | `--no-ai` |
| "the AI analysis is stale" | `--clear-cache`, then re-run |

Category names: `premium`, `high_income`, `upper_middle`, `lower_middle`, `emerging`.
There is no `usa` coefficient — the US is the base and is always 1.00.

## What the numbers mean

Each country sits in one of six tiers by GDP per capita, and each tier has a multiplier
against the US price. With an `LLM_API_KEY` set, GPT adjusts those multipliers for
the app's category and price elasticity — a casual game tolerates far deeper discounts
than an AI tool that pays server cost per request. Without the key the GDP defaults are
used, which are perfectly reasonable; do not treat the AI step as required.

Two floors are enforced and worth mentioning if the user is surprised by a price:
minimum coefficient 0.35, and minimum prices of $0.99 for premium/high-income tiers and
$0.49 elsewhere. When the cheapest product would fall below its floor, every product in
the app is scaled up together so the ratios between them stay intact.

Targets are always snapped to a real Apple price tier, so the printed price and the
final price can differ by a cent or two.

## When something fails

| Output | Meaning |
|---|---|
| `Missing App Store Connect credentials` | No `.env` found — the error lists where it looked |
| `Private key not found` | `.p8` is not beside the `.env`, or the name in `.env` differs |
| `Could not fetch US price` | The product has no US price set in App Store Connect |
| `No USD price points available` | The product has no price tiers — check it in App Store Connect |
| `--preserved and --start-date apply only to subscriptions` | The product is a one-time IAP |
| `There is no resource of type 'apps'` | Wrong app ID |

Partial failures on apply are reported per territory and are not fatal — the run
continues. Report which territories failed rather than claiming the whole run succeeded.

## Installing this skill somewhere else

When the user asks how to set this up on another machine, for a teammate, or in a
different agent, the files live in
[the repository](https://github.com/duceum/appstore-ppp-pricing-agent-skill/tree/main/agent-skills).

Claude Code — user-wide, or drop `.claude/skills/` in place of `~/.claude/skills/` for
one project only:

```bash
curl -fsSL https://raw.githubusercontent.com/duceum/appstore-ppp-pricing-agent-skill/main/agent-skills/claude-code/appstore-ppp-pricing/SKILL.md \
  --create-dirs -o ~/.claude/skills/appstore-ppp-pricing/SKILL.md
```

Cursor:

```bash
curl -fsSL https://raw.githubusercontent.com/duceum/appstore-ppp-pricing-agent-skill/main/agent-skills/cursor/appstore-ppp-pricing.mdc \
  --create-dirs -o .cursor/rules/appstore-ppp-pricing.mdc
```

Codex — and also GitHub Copilot, Aider, Jules, VS Code and Devin, which all read
`AGENTS.md`. Append rather than overwrite:

```bash
curl -fsSL https://raw.githubusercontent.com/duceum/appstore-ppp-pricing-agent-skill/main/agent-skills/codex/AGENTS.md \
  >> AGENTS.md
```

The CLI itself still has to be installed on each machine: `uv tool install appstore-ppp-prices`.

## Do not

- Apply without a confirmed dry run.
- Read, echo or copy the `.p8` key or the contents of `.env`.
- Guess an app ID or product ID — list them and confirm.
- Edit `countries.csv` inside the installed package to change one country; use
  `--coeff` or `--exclude`.
