# Больше выручки в App Store с региональными ценами — автоматическая PPP-локализация цен для 175+ стран

> **[English version (README.md)](README.md)**

**appstore-ppp-prices** — автоматическая региональная ценовая оптимизация для App Store: локализует цены на встроенные покупки (IAP) и подписки в 175+ странах по паритету покупательной способности (PPP) на основе ВВП на душу населения, с опциональным AI-анализом, через App Store Connect API.

## Что делает этот инструмент

1. Подключается к App Store Connect API
2. Получает текущие цены на ваш продукт (IAP или подписку)
3. Рассчитывает оптимальные цены для каждой страны на основе покупательной способности
4. (Опционально) Использует GPT для подбора коэффициентов под тип приложения
5. Применяет рассчитанные цены через API

## Требования

- Аккаунт **App Store Connect** с правами на управление ценами
- (Опционально) API-ключ **OpenAI** для AI-анализа
- **Python 3.10** или новее — не нужен, если ставить через `uv`: он приносит свой

## Пошаговая установка

### Шаг 1: Установить программу

Проще всего через [uv](https://docs.astral.sh/uv/) — свой Python для этого не нужен, uv принесёт собственный:

```
uv tool install appstore-ppp-prices
```

Нет uv? Сначала поставьте его: `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS, Linux) или `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows).

Если Python 3.10+ уже стоит, подойдёт любая из этих команд:

```
pipx install appstore-ppp-prices
pip install appstore-ppp-prices
```

Ставятся сразу два имени одной и той же программы: `appstore-ppp-prices` и короткое `ppp-pricing`. Дальше в README используется короткое.

Проверьте:
```
ppp-pricing --help
```

Попробовать вообще без установки: `uvx appstore-ppp-prices --help`

<details>
<summary>Запуск из исходников</summary>

```
git clone https://github.com/duceum/appstore-ppp-pricing-agent-skill.git
cd appstore-ppp-pricing-agent-skill
pip install -e .
```

</details>

### Шаг 2: Создать API-ключ App Store Connect

1. Откройте https://appstoreconnect.apple.com/access/integrations/api
2. Нажмите **"Generate API Key"** (или "Ключи" -> "Создать ключ API")
3. Имя: любое (например, `ppp-pricing`)
4. Права доступа: **Admin** или **App Manager**
5. Нажмите **"Generate"**
6. **Скопируйте Key ID** (10 символов, например `A1B2C3D4E5`)
7. **Скопируйте Issuer ID** (UUID, виден вверху страницы)
8. **Скачайте .p8 файл** — это приватный ключ. Скачать можно только один раз!

Положите `.p8` файл в папку настроек:
```
mkdir -p ~/.config/ppp-pricing
mv ~/Downloads/AuthKey_*.p8 ~/.config/ppp-pricing/
```

### Шаг 3: (Опционально) Получить OpenAI API Key

Если хотите использовать AI-анализ для более точных коэффициентов:

1. Откройте https://platform.openai.com/api-keys
2. Нажмите **"Create new secret key"**
3. Скопируйте ключ (начинается с `sk-...`)

### Шаг 4: Создать файл настроек .env

Создайте файл `.env` рядом с ключом, по пути `~/.config/ppp-pricing/.env` (точка в начале имени обязательна):

```
nano ~/.config/ppp-pricing/.env
```

Заполните своими значениями:
```
ASC_KEY_ID=ваш_key_id
ASC_ISSUER_ID=ваш_issuer_id
ASC_PRIVATE_KEY_PATH=AuthKey_XXXX.p8
OPENAI_API_KEY=sk-ваш-ключ
```

Замените значения на свои. `ASC_PRIVATE_KEY_PATH` — имя скачанного `.p8` файла; если указано просто имя, файл ищется рядом с `.env`.

Хотите держать настройки в другом месте? Укажите его через `--config /путь/к/папке`, задайте переменную `PPP_PRICING_CONFIG` или просто запускайте программу из папки, где лежит `.env`.

### Шаг 5: Проверить установку

Запустите команду со своим App ID (9-значный номер из App Store Connect):
```
ppp-pricing --app-id 123456789
```

Если всё настроено верно, вы увидите список всех IAP и подписок вашего приложения.

## Использование

### Посмотреть все продукты приложения
```
ppp-pricing --app-id 123456789
```

### Предварительный просмотр цен (без применения)
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Покажет таблицу рассчитанных цен для каждой страны. Ничего не изменится в App Store.

### Применить цены
```
ppp-pricing --app-id 123456789 --iap com.app.weekly
```

**Внимание**: эта команда реально изменит цены в App Store Connect!

### Дополнительные опции

| Опция | Описание |
|-------|----------|
| `--dry-run` | Только показать цены, не применять |
| `--no-ai` | Не использовать AI-анализ |
| `--us-price 5.99` | Переопределить цену в США |
| `--coeff emerging=0.70` | Вручную задать коэффициент для категории |
| `--exclude RUS,BLR` | Исключить страны (через запятую) |
| `--preserved` | Сохранить текущую цену действующим подписчикам (только подписки) |
| `--start-date 2026-08-01` | Дата вступления новых цен в силу (только подписки; по умолчанию через 2 дня) |
| `--config ~/keys/` | Указать папку с .env и .p8 файлом |
| `--clear-cache` | Удалить весь кеш AI-анализа и выйти |

### Примеры

Посмотреть цены с AI-анализом:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Посмотреть цены без AI:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run --no-ai
```

Применить цены, исключив Россию и Беларусь:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

Переопределить коэффициент для развивающихся стран:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --coeff emerging=0.50 --dry-run
```

Очистить кеш AI-анализа:
```
ppp-pricing --clear-cache
```

## Категории стран

Страны разделены на 6 категорий по ВВП на душу населения:

| Категория | Примеры стран | Типичный коэффициент |
|-----------|--------------|---------------------|
| Premium | Люксембург, Швейцария, Норвегия | 1.05 - 1.15 |
| USA | США (базовая цена) | 1.00 |
| High Income | Германия, Великобритания, Канада | 0.80 - 0.95 |
| Upper Middle | Польша, Испания, Италия | 0.60 - 0.75 |
| Lower Middle | Бразилия, Китай, Мексика | 0.45 - 0.60 |
| Emerging | Индия, Вьетнам, Украина | 0.35 - 0.50 |

## Устранение проблем

| Проблема | Решение |
|----------|---------|
| `Error: Missing App Store Connect credentials` | Проверьте файл `.env` — все 3 переменные (ASC_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY_PATH) должны быть заполнены |
| `Error: Private key not found` | Проверьте, что `.p8` лежит рядом с `.env` и имя в `.env` совпадает |
| `Error: Could not fetch US price` | Убедитесь, что у продукта установлена цена в США в App Store Connect |
| `command not found: appstore-ppp-prices` | Переустановите: `uv tool install appstore-ppp-prices`, либо откройте новый терминал, чтобы подхватился `PATH` |
| `Error: No USD price points available` | У продукта нет доступных ценовых уровней. Проверьте настройки в App Store Connect |

## Запуск тестов

```
pip install pytest
pytest
```
