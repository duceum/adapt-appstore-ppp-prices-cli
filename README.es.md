# Actualización masiva de precios PPP en la App Store en 175+ países — precios regionales por paridad de poder adquisitivo para suscripciones y compras dentro de la app

![PyPI](https://img.shields.io/pypi/v/appstore-ppp-prices)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-141%20passing-brightgreen)

**appstore-ppp-prices** es una herramienta de línea de comandos gratuita y de código abierto que actualiza de forma masiva los precios de compras dentro de la app (IAP) y suscripciones de la App Store en **175+ países** según la **paridad de poder adquisitivo (PPA, PPP)**. Lee coeficientes basados en el PIB per cápita, opcionalmente los ajusta con GPT según el tipo de tu app, y escribe los precios directamente a través de la **App Store Connect API** — un comando en lugar de una tarde entera haciendo clic por territorios.

Tu clave de API nunca sale de tu máquina, y cada ejecución se puede previsualizar antes de cambiar nada.

> **Otros idiomas:** [English](README.md) · [Русский](README.ru.md) · [Português](README.pt.md) · [中文](README.zh.md)

```
uv tool install appstore-ppp-prices
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Casos de uso habituales: aumentar los ingresos de la App Store en mercados emergentes (India, Brasil, Indonesia), localización regional de precios para juegos de iOS y apps de suscripción, cambios de precio masivos sin recorrer 175 territorios a mano, y reajuste de precios dirigido por un agente de IA como Claude Code.

## Por qué los precios automáticos de Apple dejan dinero sobre la mesa

Cuando fijas un precio para Estados Unidos, App Store Connect genera las otras 174 tiendas por ti — pero las **iguala**. Convierte tu precio al tipo de cambio actual y ajusta el impuesto local, así que un suscriptor en India paga aproximadamente lo mismo **en dólares** que uno en Suiza.

El tipo de cambio no es poder adquisitivo. El salario mediano varía más de 20× entre los territorios de la App Store, de modo que un precio igualado globalmente resulta a la vez demasiado alto en los mercados emergentes — donde hunde la conversión — y, en algunos de los más ricos, más bajo de lo que los clientes pagarían sin pestañear.

El precio por PPA sitúa cada territorio en relación con lo que allí realmente se pueden permitir.

## En qué se convierten tus precios

Salida real de `--dry-run` para una **suscripción semanal de 5,99 USD**, con los coeficientes por defecto:

| País | Categoría | Coeficiente | Precio PPA | Precio igualado de Apple |
|---|---|---|---|---|
| Estados Unidos | base | 1,00 | $5.99 | $5.99 |
| Suiza | premium | 1,12 | $6.69 | ≈ $5.99 |
| Alemania | high income | 0,92 | $5.49 | ≈ $5.99 |
| Japón | upper middle | 0,75 | $4.49 | ≈ $5.99 |
| Polonia | upper middle | 0,75 | $4.49 | ≈ $5.99 |
| Brasil | lower middle | 0,55 | $3.29 | ≈ $5.99 |
| México | lower middle | 0,55 | $3.29 | ≈ $5.99 |
| Turquía | lower middle | 0,55 | $3.29 | ≈ $5.99 |
| India | emerging | 0,38 | $2.29 | ≈ $5.99 |
| Indonesia | emerging | 0,38 | $2.29 | ≈ $5.99 |
| Nigeria | emerging | 0,38 | $2.29 | ≈ $5.99 |
| Egipto | emerging | 0,38 | $2.29 | ≈ $5.99 |

Cada objetivo se ajusta al tramo de precio real más cercano de Apple, así que son precios que App Store Connect acepta de verdad.

## Qué hace

1. Se conecta a la App Store Connect API con tu propia clave `.p8`
2. Obtiene tus compras dentro de la app, suscripciones y sus precios actuales en EE. UU.
3. Calcula un precio objetivo por país a partir del PIB per cápita
4. *(Opcional)* Pide a GPT que ajuste los coeficientes al tipo de tu app — un juego de puzles y una herramienta de IA tienen elasticidades de precio muy distintas
5. Resuelve cada objetivo al tramo de precio más cercano de Apple
6. Lo aplica todo de forma masiva, o imprime una tabla y no cambia nada con `--dry-run`

## Pensado para agentes de IA

Casi todas las herramientas de precios regionales son un panel web o una app de Mac. Esta es un solo comando con flags deterministas, lo que permite a un agente llevar la tarea de principio a fin:

- **Sin interfaz gráfica ni automatización del navegador.** Nada que pulsar, nada que capturar en pantalla.
- **`--dry-run` imprime una tabla legible**, para que el agente compruebe las cifras antes de aplicar nada.
- **Sin preguntas interactivas.** Cada decisión es una flag.
- **Errores en texto plano y códigos de salida reales**, de modo que una ejecución fallida es inequívoca.
- **Funciona en CI** igual que en un portátil.

En la práctica puedes delegar la tarea entera:

> *«Previsualiza los precios PPA de mi suscripción semanal y luego aplícalos en todas partes menos Rusia y Bielorrusia.»*

que son solo estos dos comandos:

```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

### Skills listas para usar

Las instrucciones listas para los principales agentes de código están en [`agent-skills/`](agent-skills/):

| Agente | Archivo | Dónde instalarlo |
|---|---|---|
| Claude Code | `SKILL.md` | `~/.claude/skills/appstore-ppp-pricing/` |
| Cursor | regla `.mdc` | `.cursor/rules/` |
| Codex, Copilot, Aider, Jules, VS Code, Devin | `AGENTS.md` | raíz del repositorio |

Le enseñan al agente lo que `--help` no cuenta: aplicar es irreversible y exige un `--dry-run` confirmado antes, y un cambio de precio de suscripción afecta a los suscriptores **actuales** salvo que se pase `--preserved`. Los comandos de instalación están en [agent-skills/README.md](agent-skills/README.md).

## Tu clave de API nunca sale de tu máquina

Una clave de App Store Connect con permisos de precios puede cambiar cuánto pagan tus clientes. Los servicios de precios alojados en la nube te piden subir esa clave a sus servidores.

Esta herramienta se ejecuta en local. El archivo `.p8` se queda en tu directorio de configuración, el JWT se firma en tu máquina y las peticiones van directas de tu máquina a Apple. No hay cuenta que crear, no hay servidor en medio, y después no queda nada que revocar salvo la propia clave.

## Comparativa

| | appstore-ppp-prices | Servicios de precios en la nube | App Store Connect a mano |
|---|---|---|---|
| Dónde vive tu clave de API | en tu máquina | subida a un tercero | — |
| Coste | gratis, MIT | suscripción | gratis |
| Actualizar 175+ territorios en masa | un comando | sí | de uno en uno |
| Previsualizar antes de aplicar | `--dry-run` | según el caso | no |
| Automatizable, funciona en CI | sí | rara vez | no |
| Manejable por un agente de IA | sí | no | no |
| IAP **y** suscripciones | ambos | según el caso | ambos |
| Coeficientes ajustados al tipo de app | con GPT | no | — |
| Programar cambios, respetar el precio de los suscriptores actuales | sí | según el caso | sí |

## Requisitos

- Cuenta de **App Store Connect** con permisos para gestionar precios
- (Opcional) clave de API de **OpenAI** para el análisis con IA
- **Python 3.10** o superior — no hace falta si instalas con `uv`, que trae el suyo

## Instalación paso a paso

### Paso 1: Instalar la herramienta

Lo más fácil es [uv](https://docs.astral.sh/uv/), que no necesita un Python tuyo — trae el propio:

```
uv tool install appstore-ppp-prices
```

¿Todavía sin uv? Instálalo primero con `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS, Linux) o `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows).

¿Ya tienes Python 3.10+? Cualquiera de estos también sirve:

```
pipx install appstore-ppp-prices
pip install appstore-ppp-prices
```

¿Estás en Mac y prefieres Homebrew?

```
brew tap duceum/tap
brew trust duceum/tap
brew install duceum/tap/appstore-ppp-prices
```

`brew trust` es Homebrew 6 preguntando si aceptas ejecutar código de fórmula de un tap de terceros. La instalación tarda unos minutos: Homebrew compila las dependencias de Python desde el código fuente, y tres de ellas llevan extensiones nativas. `uv` usa wheels precompilados y termina en segundos.

Esto instala dos nombres para la misma herramienta: `appstore-ppp-prices` y el más corto `ppp-pricing`. El resto de este README usa el corto.

Comprueba:
```
ppp-pricing --version
```

Para probarla sin instalar nada: `uvx appstore-ppp-prices --help`

<details>
<summary>Ejecutar desde el código fuente</summary>

```
git clone https://github.com/duceum/appstore-ppp-pricing-agent-skill.git
cd appstore-ppp-pricing-agent-skill
pip install -e .
```

</details>

### Paso 2: Crear una clave de API de App Store Connect

1. Entra en https://appstoreconnect.apple.com/access/integrations/api
2. Pulsa **"Generate API Key"**
3. Nombre: el que quieras (por ejemplo, `ppp-pricing`)
4. Acceso: **Admin** o **App Manager**
5. Pulsa **"Generate"**
6. **Copia el Key ID** (10 caracteres, p. ej. `A1B2C3D4E5`)
7. **Copia el Issuer ID** (el UUID que aparece arriba en la página)
8. **Descarga el archivo .p8** — es tu clave privada. ¡Solo se puede descargar una vez!

Coloca el archivo `.p8` en tu carpeta de configuración:
```
mkdir -p ~/.config/ppp-pricing
mv ~/Downloads/AuthKey_*.p8 ~/.config/ppp-pricing/
```

### Paso 3: (Opcional) Conseguir una clave de OpenAI

El análisis con IA ajusta los coeficientes al tipo concreto de tu app. Sin él, la herramienta usa los valores por defecto basados en el PIB, que funcionan perfectamente.

1. Entra en https://platform.openai.com/api-keys
2. Crea una clave y cópiala (empieza por `sk-`)

### Paso 4: Crear el archivo de configuración .env

Crea un archivo `.env` junto a la clave, en `~/.config/ppp-pricing/.env` (ojo al punto al principio del nombre):

```
nano ~/.config/ppp-pricing/.env
```

Rellena con tus valores:
```
ASC_KEY_ID=tu_key_id
ASC_ISSUER_ID=tu_issuer_id
ASC_PRIVATE_KEY_PATH=AuthKey_XXXX.p8
OPENAI_API_KEY=sk-tu-clave
```

Sustituye por tus valores reales. `ASC_PRIVATE_KEY_PATH` es el nombre del archivo `.p8` descargado — un nombre a secas se resuelve junto al `.env`.

¿Prefieres tener la configuración en otro sitio? Apúntala con `--config /ruta/a/carpeta`, define `PPP_PRICING_CONFIG`, o simplemente ejecuta la herramienta desde un directorio que tenga un `.env`.

### Paso 5: Verificar la instalación

Ejecuta el comando con tu App ID (número de 9 dígitos de App Store Connect):
```
ppp-pricing --app-id 123456789
```

Si todo está bien configurado, verás la lista de todos los IAP y suscripciones de tu app.

## Uso

### Listar todos los productos
```
ppp-pricing --app-id 123456789
```

### Previsualizar precios (sin aplicar)
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Muestra una tabla con los precios calculados por país. No cambia nada en la App Store.

### Aplicar precios
```
ppp-pricing --app-id 123456789 --iap com.app.weekly
```

**Aviso**: este comando cambia de verdad los precios en App Store Connect.

### Opciones

| Opción | Descripción |
|--------|-------------|
| `--dry-run` | Previsualizar sin aplicar |
| `--no-ai` | Desactivar el análisis con IA |
| `--us-price 5.99` | Sobrescribir el precio de EE. UU. |
| `--coeff emerging=0.70` | Fijar manualmente el coeficiente de una categoría |
| `--exclude RUS,BLR` | Excluir países (separados por comas) |
| `--preserved` | Mantener el precio actual a los suscriptores existentes (solo suscripciones) |
| `--start-date 2026-08-01` | Fecha de entrada en vigor de los nuevos precios (solo suscripciones; por defecto, dentro de 2 días) |
| `--config ~/keys/` | Indicar la carpeta con el .env y la clave .p8 |
| `--clear-cache` | Borrar la caché del análisis con IA y salir |
| `--version` | Mostrar la versión |

### Ejemplos

Previsualizar con análisis de IA:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Previsualizar sin IA:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run --no-ai
```

Aplicar precios excluyendo Rusia y Bielorrusia:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

Sobrescribir el coeficiente de mercados emergentes:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --coeff emerging=0.50 --dry-run
```

Subir el precio solo a los nuevos suscriptores, a partir del mes que viene:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --preserved --start-date 2026-09-01
```

Borrar la caché del análisis con IA:
```
ppp-pricing --clear-cache
```

## Categorías de países

Los países se reparten en 6 categorías según el PIB per cápita:

| Categoría | Países de ejemplo | Coeficiente típico |
|-----------|-------------------|--------------------|
| Premium | Luxemburgo, Suiza, Noruega | 1,05 - 1,15 |
| USA | Estados Unidos (precio base) | 1,00 |
| High Income | Alemania, Reino Unido, Canadá, Australia | 0,80 - 0,95 |
| Upper Middle | Polonia, España, Italia, Japón | 0,60 - 0,75 |
| Lower Middle | Brasil, China, México | 0,45 - 0,60 |
| Emerging | India, Vietnam, Ucrania | 0,35 - 0,50 |

La lista completa de 175+ países con su PIB per cápita y coeficientes por defecto está en [`appstore_ppp_prices/countries.csv`](appstore_ppp_prices/countries.csv) — edítala si no estás de acuerdo con alguna clasificación.

## Preguntas frecuentes

**¿Esto cambia el precio a los suscriptores que ya tengo?**
Por defecto sí — un cambio de precio se aplica a todos. Usa `--preserved` para dejar a los suscriptores actuales con su precio antiguo y aplicar el nuevo solo a las altas posteriores. Solo para suscripciones; las compras únicas no tienen ese concepto.

**¿Puedo ver qué va a pasar antes de que cambie nada?**
Para eso está `--dry-run`. Imprime la tabla completa de los 174 precios objetivo y no escribe nada.

**¿Funciona con compras dentro de la app y con suscripciones?**
Con ambas. Usan endpoints distintos de App Store Connect y la herramienta elige el correcto por su cuenta.

**¿Adónde va mi clave de App Store Connect API?**
A ninguna parte. Se queda en tu directorio de configuración, el JWT se firma en local y las peticiones van directas a Apple.

**¿Cómo se calculan los coeficientes?**
Cada país entra en uno de seis tramos de renta según el PIB per cápita, y cada tramo tiene un multiplicador por defecto respecto al precio de EE. UU. Con una clave de OpenAI, GPT ajusta esos multiplicadores a la categoría de tu app y a su elasticidad de precio — un juego casual admite descuentos mucho más agresivos que una herramienta de IA con coste de servidor por petición. El coeficiente mínimo es 0,35, se respetan los suelos de 0,99 $ / 0,49 $ y se preservan las proporciones entre tus productos.

**¿Puedo ejecutarla desde CI o desde un agente de IA?**
Sí. Sin preguntas interactivas, flags deterministas, códigos de salida reales. Ver [Pensado para agentes de IA](#pensado-para-agentes-de-ia).

**¿Admite Google Play?**
Hoy no. Esta herramienta es solo para la App Store.

**¿Puedo programar un cambio de precio?**
Sí, para suscripciones: `--start-date AAAA-MM-DD`. Por defecto, dos días más adelante.

**¿Y si no estoy de acuerdo con el tramo de un país?**
Sobrescribe la categoría entera con `--coeff emerging=0.50`, excluye países con `--exclude`, o edita `countries.csv` directamente.

## Solución de problemas

| Problema | Solución |
|----------|----------|
| `Error: Missing App Store Connect credentials` | Revisa tu `.env` — las 3 variables (ASC_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY_PATH) deben estar definidas |
| `Error: Private key not found` | Asegúrate de que el `.p8` está junto a tu `.env` y de que el nombre en `.env` coincide |
| `Error: Could not fetch US price` | Comprueba que el producto tiene precio para EE. UU. en App Store Connect |
| `command not found: appstore-ppp-prices` | Reinstala con `uv tool install appstore-ppp-prices`, o abre un terminal nuevo para que se recoja el `PATH` |
| `Error: No USD price points available` | El producto no tiene tramos de precio disponibles. Revisa la configuración en App Store Connect |

## Ejecutar los tests

```
pip install pytest
pytest
```

## Licencia

MIT — ver [LICENSE](LICENSE).
