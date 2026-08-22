# Bulk App Store PPP Price Updates for 175+ Countries — Regional Pricing for IAP and Subscriptions

![PyPI](https://img.shields.io/pypi/v/appstore-ppp-prices)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-141%20passing-brightgreen)

**appstore-ppp-prices** is a free, open-source CLI that bulk-updates App Store in-app purchase and subscription prices across **175+ countries** by **purchasing power parity (PPP)**. It reads GDP-per-capita coefficients, optionally tunes them with GPT for your app type, and writes the prices straight through the **App Store Connect API** — one command instead of an afternoon of clicking through territories.

Your API key never leaves your machine, and every run can be previewed before anything changes.

> **Other languages:** [Русский](README.ru.md) · [Português](README.pt.md) · [Español](README.es.md) · [中文](README.zh.md)

```
uv tool install appstore-ppp-prices
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Typical use cases: raising App Store revenue in emerging markets (India, Brazil, Indonesia), regional price localization for iOS games and subscription apps, bulk price changes without clicking through 175 territories by hand, and repricing driven by an AI agent such as Claude Code.

## Why Apple's Automatic Pricing Leaves Money on the Table

When you set a US price, App Store Connect generates the other 174 storefronts for you — but it *equalizes* them. It converts your price at the current exchange rate and adjusts for local tax, so a subscriber in India pays roughly the same **in dollars** as one in Switzerland.

Exchange rates are not purchasing power. The median monthly wage differs by more than 20× across App Store territories, so a globally equalized price is simultaneously too high in emerging markets — where it suppresses conversion — and, in a few of the richest ones, lower than customers would happily pay.

PPP pricing sets each territory relative to what people there can actually afford.

## What Your Prices Become

Real output from `--dry-run` for a **$5.99 weekly subscription**, using the default coefficients:

| Country | Category | Coefficient | PPP price | Apple's equalized price |
|---|---|---|---|---|
| United States | base | 1.00 | $5.99 | $5.99 |
| Switzerland | premium | 1.12 | $6.69 | ≈ $5.99 |
| Germany | high income | 0.92 | $5.49 | ≈ $5.99 |
| Japan | upper middle | 0.75 | $4.49 | ≈ $5.99 |
| Poland | upper middle | 0.75 | $4.49 | ≈ $5.99 |
| Brazil | lower middle | 0.55 | $3.29 | ≈ $5.99 |
| Mexico | lower middle | 0.55 | $3.29 | ≈ $5.99 |
| Turkey | lower middle | 0.55 | $3.29 | ≈ $5.99 |
| India | emerging | 0.38 | $2.29 | ≈ $5.99 |
| Indonesia | emerging | 0.38 | $2.29 | ≈ $5.99 |
| Nigeria | emerging | 0.38 | $2.29 | ≈ $5.99 |
| Egypt | emerging | 0.38 | $2.29 | ≈ $5.99 |

Every target is snapped to the nearest real Apple price tier, so the prices are ones App Store Connect will actually accept.

## What It Does

1. Connects to the App Store Connect API with your own `.p8` key
2. Fetches your current in-app purchases, subscriptions and their US prices
3. Calculates a target price per country from GDP per capita
4. *(Optional)* Asks GPT to tune the coefficients for your app type — a puzzle game and an AI tool have very different price elasticity
5. Resolves each target to the nearest Apple price tier
6. Applies everything in bulk, or prints a table and changes nothing with `--dry-run`

## Built for AI Agents

Most regional-pricing tools are a web dashboard or a Mac app. This one is a single command with deterministic flags, which means an agent can drive it end to end:

- **No GUI, no browser automation.** Nothing to click, nothing to screenshot.
- **`--dry-run` prints a readable table** so the agent can check the numbers before anything is applied.
- **No interactive prompts.** Every decision is a flag.
- **Plain-text errors and real exit codes**, so a failed run is unambiguous.
- **Runs in CI** the same way it runs on a laptop.

In practice you can hand the whole task over:

> *"Preview PPP prices for my weekly subscription, then apply them everywhere except Russia and Belarus."*

which is just these two commands:

```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

### Ready-made skills

Drop-in instructions for the main coding agents live in [`agent-skills/`](agent-skills/):

| Agent | File | Install into |
|---|---|---|
| Claude Code | `SKILL.md` | `~/.claude/skills/appstore-ppp-pricing/` |
| Cursor | `.mdc` rule | `.cursor/rules/` |
| Codex, Copilot, Aider, Jules, VS Code, Devin | `AGENTS.md` | repository root |

They teach the agent the two things `--help` cannot: that applying is irreversible and needs a confirmed `--dry-run` first, and that a subscription price change hits **existing** subscribers unless `--preserved` is passed. Install commands are in [agent-skills/README.md](agent-skills/README.md).

## Your API Key Never Leaves Your Machine

An App Store Connect key with pricing permissions can change what your customers are charged. Hosted pricing services need you to upload that key to their servers.

This tool runs locally. The `.p8` file stays in your config directory, the JWT is signed on your machine, and requests go straight from your machine to Apple. There is no account to create, no server in the middle, and nothing to revoke afterwards but the key itself.

## How It Compares

| | appstore-ppp-prices | Hosted pricing services | App Store Connect by hand |
|---|---|---|---|
| Where your API key lives | your machine | uploaded to a third party | — |
| Cost | free, MIT | subscription | free |
| Bulk update 175+ territories | one command | yes | one territory at a time |
| Preview before applying | `--dry-run` | varies | no |
| Scriptable, runs in CI | yes | rarely | no |
| Drivable by an AI agent | yes | no | no |
| IAP **and** subscriptions | both | varies | both |
| Coefficients tuned per app type | GPT-assisted | no | — |
| Schedule changes, grandfather existing subscribers | yes | varies | yes |

## Requirements

- **App Store Connect** account with pricing permissions
- (Optional) **OpenAI** API key for AI analysis
- **Python 3.10** or newer — not needed if you install with `uv`, which brings its own

## Step-by-Step Setup

### Step 1: Install the Tool

The easiest way is [uv](https://docs.astral.sh/uv/), which needs no Python of your own — it brings its own:

```
uv tool install appstore-ppp-prices
```

No uv yet? Install it first with `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS, Linux) or `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows).

Already have Python 3.10+? Either of these works too:

```
pipx install appstore-ppp-prices
pip install appstore-ppp-prices
```

On a Mac and would rather use Homebrew?

```
brew tap duceum/tap
brew trust duceum/tap
brew install duceum/tap/appstore-ppp-prices
```

`brew trust` is Homebrew 6 asking whether you accept formula code from a third-party tap. Expect the install to take a few minutes: Homebrew builds Python dependencies from source, and three of them carry native extensions. `uv` uses prebuilt wheels and finishes in seconds.

This installs two names for the same tool: `appstore-ppp-prices` and the shorter `ppp-pricing`. The rest of this README uses the short one.

Verify:
```
ppp-pricing --version
```

To try it without installing anything at all: `uvx appstore-ppp-prices --help`

<details>
<summary>Running from source instead</summary>

```
git clone https://github.com/duceum/appstore-ppp-pricing-agent-skill.git
cd appstore-ppp-pricing-agent-skill
pip install -e .
```

</details>

### Step 2: Create an App Store Connect API Key

1. Go to https://appstoreconnect.apple.com/access/integrations/api
2. Click **"Generate API Key"**
3. Name: anything (e.g. `ppp-pricing`)
4. Access: **Admin** or **App Manager**
5. Click **"Generate"**
6. **Copy the Key ID** (10 characters, e.g. `A1B2C3D4E5`)
7. **Copy the Issuer ID** (UUID shown at the top of the page)
8. **Download the .p8 file** — this is your private key. You can only download it once!

Put the `.p8` file in your config folder:
```
mkdir -p ~/.config/ppp-pricing
mv ~/Downloads/AuthKey_*.p8 ~/.config/ppp-pricing/
```

### Step 3: (Optional) Get an OpenAI API Key

AI analysis adjusts the coefficients for your specific app type. Without it, the tool uses the GDP-based defaults, which are perfectly usable.

1. Go to https://platform.openai.com/api-keys
2. Create a key and copy it (starts with `sk-`)

<details>
<summary>Using a provider other than OpenAI</summary>

The request is a plain OpenAI-format chat completion, so anything that speaks that
format works — OpenRouter, Groq, Together, Fireworks, DeepSeek, or a local Ollama,
LM Studio or vLLM. Point it somewhere else with two variables in your `.env`:

```
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.3-70b-instruct
```

`LLM_API_KEY` (or `OPENAI_API_KEY`) then holds that provider's key. A local model needs no key at all,
but the variable still has to be set to something. `LLM_REQUEST_TIMEOUT` (seconds,
default 120) helps with slow local models.

</details>

### Step 4: Create the .env Config File

Create a `.env` file next to the key, at `~/.config/ppp-pricing/.env` (note the dot at the beginning of the file name):

```
nano ~/.config/ppp-pricing/.env
```

Fill in your values:
```
ASC_KEY_ID=your_key_id
ASC_ISSUER_ID=your_issuer_id
ASC_PRIVATE_KEY_PATH=AuthKey_XXXX.p8
LLM_API_KEY=sk-your-key
```

Replace with your actual values. `ASC_PRIVATE_KEY_PATH` is the name of the downloaded `.p8` file — a bare name is resolved next to the `.env`.

Prefer to keep the config elsewhere? Point at it with `--config /path/to/dir`, set `PPP_PRICING_CONFIG`, or just run the tool from a directory that has a `.env` in it.

### Step 5: Verify the Installation

Run the command with your App ID (9-digit number from App Store Connect):
```
ppp-pricing --app-id 123456789
```

If everything is configured correctly, you'll see a list of all IAPs and subscriptions for your app.

## Usage

### List all products
```
ppp-pricing --app-id 123456789
```

### Preview prices (without applying)
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Shows a table of calculated prices per country. Nothing changes in App Store.

### Apply prices
```
ppp-pricing --app-id 123456789 --iap com.app.weekly
```

**Warning**: this command will actually change prices in App Store Connect!

### Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview prices without applying |
| `--no-ai` | Disable AI analysis |
| `--us-price 5.99` | Override the US price |
| `--coeff emerging=0.70` | Manually set a coefficient for a category |
| `--exclude RUS,BLR` | Exclude countries (comma-separated) |
| `--preserved` | Keep the current price for existing subscribers (subscriptions only) |
| `--start-date 2026-08-01` | Date the new prices take effect (subscriptions only; default: 2 days from now) |
| `--config ~/keys/` | Specify directory with .env and .p8 key |
| `--clear-cache` | Delete all cached AI analysis results and exit |
| `--version` | Print the version |

### Examples

Preview prices with AI analysis:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Preview prices without AI:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run --no-ai
```

Apply prices, excluding Russia and Belarus:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

Override the coefficient for emerging markets:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --coeff emerging=0.50 --dry-run
```

Raise prices for new subscribers only, starting next month:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --preserved --start-date 2026-09-01
```

Clear cached AI analysis results:
```
ppp-pricing --clear-cache
```

## Country Categories

Countries are divided into 6 categories by GDP per capita:

| Category | Example Countries | Typical Coefficient |
|----------|-------------------|---------------------|
| Premium | Luxembourg, Switzerland, Norway | 1.05 - 1.15 |
| USA | United States (base price) | 1.00 |
| High Income | Germany, UK, Canada, Australia | 0.80 - 0.95 |
| Upper Middle | Poland, Spain, Italy, Japan | 0.60 - 0.75 |
| Lower Middle | Brazil, China, Mexico | 0.45 - 0.60 |
| Emerging | India, Vietnam, Ukraine | 0.35 - 0.50 |

The full list of 175+ countries with their GDP per capita and default coefficients lives in [`appstore_ppp_prices/countries.csv`](appstore_ppp_prices/countries.csv) — edit it if you disagree with a placement.

## FAQ

**Does this change prices for existing subscribers?**
By default, yes — a price change applies to everyone. Pass `--preserved` to grandfather current subscribers at their existing price and apply the new one only to new sign-ups. Subscriptions only; one-time in-app purchases have no such concept.

**Can I see what will happen before anything changes?**
That is what `--dry-run` is for. It prints the full table of 174 target prices and writes nothing.

**Does it handle both in-app purchases and subscriptions?**
Both. They use different App Store Connect endpoints, and the tool picks the right one automatically.

**Where does my App Store Connect API key go?**
Nowhere. It stays in your config directory, the JWT is signed locally, and requests go straight to Apple.

**How are the coefficients calculated?**
Each country is placed in one of six income tiers by GDP per capita, and each tier has a default multiplier relative to the US price. With an OpenAI key, GPT adjusts those multipliers for your app's category and price elasticity — a casual game tolerates much deeper discounts than an AI tool with per-request server costs. Minimum coefficient is 0.35, and price floors of $0.99 / $0.49 are enforced with ratios between your products preserved.

**Can I run it from CI or from an AI agent?**
Yes. No interactive prompts, deterministic flags, real exit codes. See [Built for AI Agents](#built-for-ai-agents).

**Does it support Google Play?**
Not today. This tool is App Store only.

**Can I schedule a price change?**
Yes, for subscriptions: `--start-date YYYY-MM-DD`. The default is two days out.

**What if I disagree with a country's tier?**
Override a whole category with `--coeff emerging=0.50`, exclude countries with `--exclude`, or edit `countries.csv` directly.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Error: Missing App Store Connect credentials` | Check your `.env` file — all 3 variables (ASC_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY_PATH) must be set |
| `Error: Private key not found` | Make sure the `.p8` file sits next to your `.env` and the name in `.env` matches |
| `Error: Could not fetch US price` | Ensure the product has a US price set in App Store Connect |
| `command not found: appstore-ppp-prices` | Reinstall with `uv tool install appstore-ppp-prices`, or open a new terminal so `PATH` is picked up |
| `Error: No USD price points available` | The product has no available price tiers. Check settings in App Store Connect |

## Running Tests

```
pip install pytest
pytest
```

## License

MIT — see [LICENSE](LICENSE).
