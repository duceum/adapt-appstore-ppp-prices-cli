# Grow App Store Revenue with Regional Pricing — Automatic PPP Price Localization for 175+ Countries

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-127%20passing-brightgreen)

**Adapt Prices Bot** localizes App Store in-app purchase and subscription prices across **175+ countries** by **purchasing power parity (PPP)**: GDP-per-capita coefficients, optional AI tuning for your app type, and price tiers applied directly through the **App Store Connect API** — one command instead of hours in the App Store Connect UI.

> **[Документация на русском (README.ru.md)](README.ru.md)**

Typical use cases: raising App Store revenue in emerging markets (India, Brazil, Indonesia), price localization for iOS games and subscription apps, bulk price changes without clicking through 175 territories by hand.

## What It Does

1. Connects to the App Store Connect API
2. Fetches current product prices (IAP or subscription)
3. Calculates optimal prices per country based on purchasing power
4. (Optional) Uses GPT to fine-tune coefficients for your app type
5. Applies calculated prices via the API

## Requirements

- **Python 3.10** or newer
- **App Store Connect** account with pricing permissions
- (Optional) **OpenAI** API key for AI analysis

## Step-by-Step Setup

### Step 1: Install Python

If Python is not installed yet:

- **macOS**: open Terminal and run:
  ```
  brew install python
  ```
  No Homebrew? Download Python from https://www.python.org/downloads/

- **Windows**: download the installer from https://www.python.org/downloads/ and check **"Add Python to PATH"** during installation

Verify:
```
python3 --version
```
Should show `Python 3.10` or higher.

### Step 2: Download the Project

Download and unzip the project folder (or `git clone` if you know how).

Open a terminal and navigate to the project folder:
```
cd path/to/Adapt-bot
```

### Step 3: Install Dependencies

```
pip install -e .
```

This installs all required libraries automatically.

### Step 4: Create an App Store Connect API Key

1. Go to https://appstoreconnect.apple.com/access/integrations/api
2. Click **"Generate API Key"**
3. Name: anything (e.g. `adapt-bot`)
4. Access: **Admin** or **App Manager**
5. Click **"Generate"**
6. **Copy the Key ID** (10 characters, e.g. `A1B2C3D4E5`)
7. **Copy the Issuer ID** (UUID shown at the top of the page)
8. **Download the .p8 file** — this is your private key. You can only download it once!

Place the `.p8` file in the project folder.

### Step 5: (Optional) Get an OpenAI API Key

If you want AI-driven coefficient analysis for better pricing:

1. Go to https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Copy the key (starts with `sk-...`)

### Step 6: Create the .env Config File

Create a `.env` file in the project folder (note the dot at the beginning).

You can copy the template:
```
cp .env.example .env
```

Open `.env` in any text editor and fill in your values:
```
ASC_KEY_ID=your_key_id
ASC_ISSUER_ID=your_issuer_id
ASC_PRIVATE_KEY_PATH=AuthKey_XXXX.p8
OPENAI_API_KEY=sk-your-key
```

Replace with your actual values. `ASC_PRIVATE_KEY_PATH` is the name of the downloaded `.p8` file.

### Step 7: Verify the Installation

Run the command with your App ID (9-digit number from App Store Connect):
```
adapt-prices-bot --app-id 123456789
```

If everything is configured correctly, you'll see a list of all IAPs and subscriptions for your app.

## Usage

### List all products
```
adapt-prices-bot --app-id 123456789
```

### Preview prices (without applying)
```
adapt-prices-bot --app-id 123456789 --iap com.app.weekly --dry-run
```

Shows a table of calculated prices per country. Nothing changes in App Store.

### Apply prices
```
adapt-prices-bot --app-id 123456789 --iap com.app.weekly
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

### Examples

Preview prices with AI analysis:
```
adapt-prices-bot --app-id 123456789 --iap com.app.weekly --dry-run
```

Preview prices without AI:
```
adapt-prices-bot --app-id 123456789 --iap com.app.weekly --dry-run --no-ai
```

Apply prices, excluding Russia and Belarus:
```
adapt-prices-bot --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

Override the coefficient for emerging markets:
```
adapt-prices-bot --app-id 123456789 --iap com.app.weekly --coeff emerging=0.50 --dry-run
```

Clear cached AI analysis results:
```
adapt-prices-bot --clear-cache
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

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Error: Missing App Store Connect credentials` | Check your `.env` file — all 3 variables (ASC_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY_PATH) must be set |
| `Error: Private key not found` | Make sure the `.p8` file is in the project folder and the name in `.env` matches |
| `Error: Could not fetch US price` | Ensure the product has a US price set in App Store Connect |
| `command not found: adapt-prices-bot` | Run `pip install -e .` again |
| `Error: No USD price points available` | The product has no available price tiers. Check settings in App Store Connect |

## Running Tests

```
pip install pytest
pytest
```
