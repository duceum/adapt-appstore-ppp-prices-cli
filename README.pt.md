# Preços PPP na App Store por país — CLI gratuita que atualiza em massa preços de IAP e assinaturas em 175+ países por poder de compra, com skills para agentes de IA

[![PyPI](https://img.shields.io/pypi/v/appstore-ppp-prices)](https://pypi.org/project/appstore-ppp-prices/)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-173%20passing-brightgreen)

- **Fácil de instalar** — uma linha no macOS, Windows ou Linux. Não precisa ter Python.
- **Feito para agentes de IA** — Claude Code, Codex ou Cursor instalam, configuram e rodam por você.
- **Seguro por padrão** — `--dry-run` imprime os 174 preços antes de qualquer um ser aplicado.
- **Sua chave de API nunca sai da sua máquina** — sem conta, sem upload, sem servidor no meio.
- **175+ territórios em um comando** — compras no app e assinaturas.
- **Faixas de preço reais da Apple** — cada preço sai na moeda local e é aceito pela App Store Connect.
- **Gratuito e de código aberto (MIT)** — nenhuma assinatura para precificar suas assinaturas.

**appstore-ppp-prices** é uma ferramenta de linha de comando gratuita e de código aberto que traz **preços PPP** — paridade de poder de compra — para a **App Store**. Ela atualiza em massa os preços de compras no app (IAP) e assinaturas em **175+ países**: lê coeficientes baseados no PIB per capita, opcionalmente os ajusta com GPT para o tipo do seu app, e grava os preços diretamente pela **App Store Connect API**. Um comando em vez de uma tarde inteira clicando por territórios.

> **Outros idiomas:** [English](README.md) · [Русский](README.ru.md) · [Español](README.es.md) · [中文](README.zh.md)

## Instale com o seu agente de IA

Cole isto no **Claude Code**, **Codex**, **Cursor** ou qualquer outro agente de código. Ele lê a página, instala a ferramenta do jeito que servir para a sua máquina e conduz você pela configuração única da App Store Connect:

```text
Instale para mim o appstore-ppp-prices: https://github.com/duceum/appstore-ppp-pricing-agent-skill
Leia a página, escolha a instalação que serve para a minha máquina e instale também a skill de agente desse repositório.
```

Prefere fazer na mão? São duas linhas — os detalhes estão em [macOS](#macos) · [Windows](#windows) · [Linux](#linux):

```bash
uv tool install appstore-ppp-prices
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Casos de uso típicos: aumentar a receita da App Store em mercados emergentes (Índia, Brasil, Indonésia), localização regional de preços para jogos iOS e apps de assinatura, mudanças de preço em massa sem passar por 175 territórios na mão, e reprecificação conduzida por um agente de IA como o Claude Code.

## Por que o preço automático da Apple deixa dinheiro na mesa

Quando você define um preço nos EUA, a App Store Connect gera as outras 174 vitrines para você — mas ela **equaliza**. Converte o preço pela taxa de câmbio atual e ajusta o imposto local, então um assinante na Índia paga aproximadamente o mesmo **em dólares** que um na Suíça.

Taxa de câmbio não é poder de compra. O salário mediano varia mais de 20× entre os territórios da App Store, então um preço globalmente equalizado é ao mesmo tempo alto demais nos mercados emergentes — onde sufoca a conversão — e, em alguns dos mais ricos, menor do que os clientes pagariam sem reclamar.

O preço por PPP posiciona cada território de acordo com o que as pessoas de lá realmente podem pagar.

## Como ficam os seus preços

Saída real do `--dry-run` para uma **assinatura semanal de $5.99** com os coeficientes padrão. Cada preço é uma faixa de preço real da Apple, na moeda do país, ao lado do que a App Store Connect cobra lá por padrão:

| País | Categoria | Coeficiente | Padrão da Apple | Preço PPP | Variação |
|---|---|---|---|---|---|
| Estados Unidos | base | 1,00 | $5.99 | **$5.99** | — |
| Suíça | premium | 1,10 | CHF 5,00 | **CHF 5,50** | +10% |
| Noruega | premium | 1,10 | NOK 79 | **NOK 87** | +10% |
| Alemanha | high income | 0,90 | € 6,99 | **€ 6,29** | −10% |
| Reino Unido | high income | 0,90 | £5.99 | **£5.39** | −10% |
| Japão | upper middle | 0,75 | ¥ 1.000 | **¥ 750** | −25% |
| Polônia | upper middle | 0,75 | 29,99 zł | **22,49 zł** | −25% |
| Brasil | lower middle | 0,50 | R$ 39,90 | **R$ 19,90** | −50% |
| México | lower middle | 0,50 | MX$ 129 | **MX$ 64** | −50% |
| Turquia | lower middle | 0,50 | ₺ 299,99 | **₺ 149,99** | −50% |
| Índia | emerging | 0,40 | ₹ 599 | **₹ 239** | −60% |
| Indonésia | emerging | 0,40 | Rp 99.000 | **Rp 39.500** | −60% |
| Nigéria | emerging | 0,40 | ₦ 9.900 | **₦ 3.950** | −60% |
| Egito | emerging | 0,40 | E£ 299,99 | **E£ 119,99** | −60% |

Cada país se moveu exatamente pelo coeficiente que recebeu, no próprio dinheiro: a Índia paga ₹ 239 em vez de ₹ 599, e a Suíça paga CHF 5,50 em vez de CHF 5,00, porque o cliente suíço aguenta mais do que um preço equalizado globalmente supõe.

**Por que os preços são calculados na moeda local.** A ferramenta pergunta à Apple quanto ela cobra em cada território pelo seu preço dos EUA, multiplica *esse* valor pelo coeficiente do país e escolhe um ponto da grade de preços do próprio território — que é fina: o franco suíço anda de 0,10 em 0,10, a coroa norueguesa de uma em uma. Quando o alvo cai entre dois pontos, o arredondamento se afasta do preço base: para cima num país mais caro que os EUA, para baixo num mais barato.

A mesma conta feita em dólares — escolher uma faixa em USD e deixar a equalização da Apple traduzir — distorce silenciosamente cada linha, porque a equalização só alcança um subconjunto grosseiro de cada grade. Todo preço de $6.39 a $6.99 vira CHF 6,00, e tanto $5.99 quanto $6.59 viram NOK 79. Um coeficiente de +10% chegaria como +20% na Suíça e como nada na Noruega.

## O que a ferramenta faz

1. Conecta-se à App Store Connect API com a sua própria chave `.p8`
2. Busca suas compras no app, assinaturas e os preços atuais nos EUA
3. Calcula um preço-alvo por país a partir do PIB per capita
4. *(Opcional)* Pede ao GPT para ajustar os coeficientes ao tipo do seu app — um jogo de puzzle e uma ferramenta de IA têm elasticidade de preço muito diferentes
5. Converte cada alvo numa faixa de preço local real: o preço da própria Apple naquele território, multiplicado pelo coeficiente
6. Aplica tudo em massa, ou imprime uma tabela e não muda nada com `--dry-run`

## Feito para agentes de IA

A maioria das ferramentas de preço regional é um painel web ou um app de Mac. Esta é um único comando com flags determinísticas, o que permite a um agente conduzir tudo do início ao fim:

- **Sem interface gráfica, sem automação de navegador.** Nada para clicar, nada para capturar em tela.
- **`--dry-run` imprime uma tabela legível**, para o agente conferir os números antes de aplicar qualquer coisa.
- **Sem perguntas interativas.** Toda decisão é uma flag.
- **Erros em texto puro e códigos de saída reais**, então uma execução que falhou é inequívoca.
- **Roda em CI** do mesmo jeito que roda num laptop.

Na prática dá para delegar a tarefa inteira:

> *"Pré-visualize os preços PPP da minha assinatura semanal e depois aplique em todos os lugares, menos Rússia e Belarus."*

que são apenas estes dois comandos:

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

### Skills prontas

Instruções prontas para os principais agentes de código estão em [`agent-skills/`](agent-skills/):

| Agente | Arquivo da skill | Onde instalar |
|---|---|---|
| Claude Code | [`SKILL.md`](agent-skills/claude-code/appstore-ppp-pricing/SKILL.md) | `~/.claude/skills/appstore-ppp-pricing/` |
| Cursor | [`appstore-ppp-pricing.mdc`](agent-skills/cursor/appstore-ppp-pricing.mdc) | `.cursor/rules/` |
| Codex, Copilot, Aider, Jules, VS Code, Devin | [`AGENTS.md`](agent-skills/codex/AGENTS.md) | raiz do repositório |

Elas ensinam ao agente o que o `--help` não diz: aplicar é irreversível e exige um `--dry-run` confirmado antes, e uma mudança de preço de assinatura atinge os assinantes **atuais** a menos que se passe `--preserved`. Comandos de instalação em [agent-skills/README.md](agent-skills/README.md).

## Sua chave de API nunca sai da sua máquina

Uma chave da App Store Connect com permissão de preços pode alterar quanto seus clientes pagam. Serviços de precificação hospedados exigem que você envie essa chave para os servidores deles.

Esta ferramenta roda localmente. O arquivo `.p8` fica no seu diretório de configuração, o JWT é assinado na sua máquina e as requisições vão direto da sua máquina para a Apple. Não há conta para criar, não há servidor no meio, e não sobra nada para revogar depois além da própria chave.

## Comparação

| | appstore-ppp-prices | Serviços de preço hospedados | App Store Connect na mão |
|---|---|---|---|
| Onde fica sua chave de API | na sua máquina | enviada a terceiros | — |
| Custo | gratuito, MIT | assinatura | gratuito |
| Atualizar 175+ territórios em massa | um comando | sim | um território por vez |
| Pré-visualizar antes de aplicar | `--dry-run` | varia | não |
| Automatizável, roda em CI | sim | raramente | não |
| Operável por agente de IA | sim | não | não |
| IAP **e** assinaturas | ambos | varia | ambos |
| Coeficientes ajustados ao tipo do app | com GPT | não | — |
| Agendar mudanças, manter preço de assinantes atuais | sim | varia | sim |

## Requisitos

- Conta **App Store Connect** com permissão para gerenciar preços
- (Opcional) chave de API da **OpenAI** para a análise por IA
- **Python 3.10** ou mais novo — dispensável se você instalar com `uv`, que traz o próprio

## Instalação

Escolha o seu sistema operacional. Todos os caminhos instalam os mesmos dois comandos: `appstore-ppp-prices` e o mais curto `ppp-pricing`. O resto deste README usa o curto.

### macOS

O jeito mais fácil é o [uv](https://docs.astral.sh/uv/), que não precisa de um Python seu — ele traz o dele:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install appstore-ppp-prices
ppp-pricing --version
```

Prefere Homebrew?

```bash
brew tap duceum/tap
brew trust duceum/tap
brew install duceum/tap/appstore-ppp-prices
```

`brew trust` é o Homebrew 6 perguntando se você aceita executar código de fórmula de um tap de terceiros. A instalação leva alguns minutos: o Homebrew compila as dependências Python a partir do código-fonte, e três delas têm extensões nativas. O `uv` usa wheels prontos e termina em segundos.

Já tem Python 3.10+? `pipx install appstore-ppp-prices` ou `pip install appstore-ppp-prices` também funcionam.

Sua configuração vai ficar em `~/.config/ppp-pricing/`.

### Windows

No **PowerShell**:

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install appstore-ppp-prices
```

Feche o terminal e abra um novo para o `PATH` ser lido, depois confira:

```powershell
ppp-pricing --version
```

Já tem Python 3.10+? `pip install appstore-ppp-prices` também funciona.

Sua configuração vai ficar em `C:\Users\<você>\.config\ppp-pricing\` — crie a pasta com:

```powershell
mkdir "$HOME\.config\ppp-pricing"
```

### Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install appstore-ppp-prices
ppp-pricing --version
```

`pipx install appstore-ppp-prices` e `pip install --user appstore-ppp-prices` funcionam igualmente bem se você já tem Python 3.10+.

Sua configuração vai ficar em `~/.config/ppp-pricing/` (ou em `$XDG_CONFIG_HOME/ppp-pricing/`, se você definir essa variável).

### Sem instalar nada

```bash
uvx appstore-ppp-prices --help
```

<details>
<summary>Rodando a partir do código-fonte</summary>

```bash
git clone https://github.com/duceum/appstore-ppp-pricing-agent-skill.git
cd appstore-ppp-pricing-agent-skill
pip install -e .
```

</details>

## Configuração

### Passo 1: Criar uma chave de API da App Store Connect

1. Acesse https://appstoreconnect.apple.com/access/integrations/api
2. Clique em **"Generate API Key"**
3. Nome: qualquer um (por exemplo, `ppp-pricing`)
4. Acesso: **Admin** ou **App Manager**
5. Clique em **"Generate"**
6. **Copie o Key ID** (10 caracteres, ex.: `A1B2C3D4E5`)
7. **Copie o Issuer ID** (UUID mostrado no topo da página)
8. **Baixe o arquivo .p8** — esta é a sua chave privada. Só dá para baixar uma vez!

Coloque o arquivo `.p8` na sua pasta de configuração — macOS e Linux:

```bash
mkdir -p ~/.config/ppp-pricing
mv ~/Downloads/AuthKey_*.p8 ~/.config/ppp-pricing/
```

Windows (PowerShell):

```powershell
mkdir "$HOME\.config\ppp-pricing"
Move-Item "$HOME\Downloads\AuthKey_*.p8" "$HOME\.config\ppp-pricing\"
```

### Passo 2: (Opcional) Obter uma chave da OpenAI

A análise por IA ajusta os coeficientes ao tipo específico do seu app. Sem ela, a ferramenta usa os padrões baseados no PIB, que são perfeitamente utilizáveis.

1. Acesse https://platform.openai.com/api-keys
2. Crie uma chave e copie (começa com `sk-`)

<details>
<summary>Usando outro provedor que não a OpenAI</summary>

A requisição é um chat completion no formato da OpenAI, então funciona com qualquer
coisa que fale esse formato — OpenRouter, Groq, Together, Fireworks, DeepSeek, ou um
Ollama, LM Studio ou vLLM local. Aponte para outro lugar com duas variáveis no `.env`:

```text
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.3-70b-instruct
```

`LLM_API_KEY` (ou `OPENAI_API_KEY`) passa a guardar a chave desse provedor. Um modelo local não precisa de
chave nenhuma, mas a variável ainda tem que estar preenchida com algo.
`LLM_REQUEST_TIMEOUT` (segundos, padrão 120) ajuda com modelos locais lentos.

</details>

### Passo 3: Criar o arquivo de configuração .env

Crie um arquivo `.env` ao lado da chave — note o ponto no começo do nome:

```bash
nano ~/.config/ppp-pricing/.env
```

No Windows: `notepad "$HOME\.config\ppp-pricing\.env"`

Preencha com seus valores:

```text
ASC_KEY_ID=seu_key_id
ASC_ISSUER_ID=seu_issuer_id
ASC_PRIVATE_KEY_PATH=AuthKey_XXXX.p8
LLM_API_KEY=sk-sua-chave
LLM_MODEL=gpt-5.2
```

`ASC_PRIVATE_KEY_PATH` é o nome do arquivo `.p8` baixado — um nome simples é resolvido ao lado do `.env`.

Prefere manter a configuração em outro lugar? Aponte com `--config /caminho/para/pasta`, defina `PPP_PRICING_CONFIG`, ou simplesmente rode a ferramenta a partir de um diretório que tenha um `.env`.

### Passo 4: Verificar a instalação

Rode o comando com o seu App ID (número de 9 dígitos da App Store Connect):

```bash
ppp-pricing --app-id 123456789
```

Se estiver tudo certo, você verá a lista de todos os IAPs e assinaturas do seu app.

## Uso

### Listar todos os produtos

```bash
ppp-pricing --app-id 123456789
```

### Pré-visualizar preços (sem aplicar)

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Mostra uma tabela dos preços calculados por país. Nada muda na App Store.

### Aplicar preços

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly
```

**Atenção**: este comando muda de verdade os preços na App Store Connect!

### Opções

| Opção | Descrição |
|-------|-----------|
| `--dry-run` | Pré-visualizar sem aplicar |
| `--no-ai` | Desativar a análise por IA |
| `--us-price 5.99` | Sobrescrever o preço dos EUA |
| `--coeff emerging=0.70` | Definir manualmente o coeficiente de uma categoria |
| `--exclude RUS,BLR` | Excluir países (separados por vírgula) |
| `--preserved` | Manter o preço atual para assinantes existentes (somente assinaturas) |
| `--start-date 2026-08-01` | Data em que os novos preços entram em vigor (somente assinaturas; padrão: daqui a 2 dias) |
| `--config ~/keys/` | Indicar a pasta com o .env e a chave .p8 |
| `--clear-cache` | Apagar o cache da análise por IA e sair |
| `--version` | Mostrar a versão |

### Exemplos

Pré-visualizar com análise por IA:

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Pré-visualizar sem IA:

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run --no-ai
```

Aplicar preços, excluindo Rússia e Belarus:

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

Sobrescrever o coeficiente dos mercados emergentes:

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly --coeff emerging=0.50 --dry-run
```

Aumentar o preço só para novos assinantes, a partir do mês que vem:

```bash
ppp-pricing --app-id 123456789 --iap com.app.weekly --preserved --start-date 2026-09-01
```

Limpar o cache da análise por IA:

```bash
ppp-pricing --clear-cache
```

## Categorias de países

Os países são divididos em 6 categorias pelo PIB per capita:

| Categoria | Países de exemplo | Coeficiente padrão |
|-----------|-------------------|--------------------|
| Premium | Luxemburgo, Suíça, Noruega | 1,10 |
| USA | Estados Unidos (preço base) | 1,00 |
| High Income | Alemanha, Reino Unido, Canadá, Austrália | 0,90 |
| Upper Middle | Polônia, Espanha, Itália, Japão | 0,75 |
| Lower Middle | Brasil, China, México | 0,50 |
| Emerging | Índia, Vietnã, Ucrânia | 0,40 |

A análise por IA move esses valores para cima ou para baixo conforme o tipo do app; `--coeff` sobrescreve de vez. A lista completa dos 175+ países com PIB per capita e coeficientes padrão está em [`appstore_ppp_prices/countries.csv`](appstore_ppp_prices/countries.csv) — edite se discordar de alguma classificação.

## Perguntas frequentes

**Isso muda o preço para assinantes que já tenho?**
Por padrão sim — uma mudança de preço vale para todos. Use `--preserved` para manter os assinantes atuais no preço antigo e aplicar o novo só a quem assinar depois. Somente para assinaturas; compras avulsas não têm esse conceito.

**Dá para ver o que vai acontecer antes de mudar alguma coisa?**
É exatamente para isso que existe o `--dry-run`. Ele imprime a tabela completa dos 174 preços-alvo e não grava nada.

**Funciona com compras no app e com assinaturas?**
Com os dois. Eles usam endpoints diferentes da App Store Connect, e a ferramenta escolhe o certo sozinha.

**Para onde vai a minha chave da App Store Connect API?**
Para lugar nenhum. Ela fica no seu diretório de configuração, o JWT é assinado localmente e as requisições vão direto para a Apple.

**Como os coeficientes são calculados?**
Cada país entra em uma de seis faixas de renda pelo PIB per capita, e cada faixa tem um multiplicador padrão relativo ao preço dos EUA. Com uma chave da OpenAI, o GPT ajusta esses multiplicadores à categoria do seu app e à elasticidade de preço — um jogo casual tolera descontos muito mais agressivos que uma ferramenta de IA com custo de servidor por requisição. O coeficiente mínimo é 0,35, os pisos de US$ 0,99 / US$ 0,49 são respeitados e as proporções entre os seus produtos são preservadas.

**E se o meu preço-alvo cair entre duas faixas de preço da Apple?**
Ele arredonda na direção da mudança, na moeda local: para cima quando o país é mais caro que os EUA, para baixo quando é mais barato. Coincidências exatas são usadas como estão.

**Dá para rodar em CI ou a partir de um agente de IA?**
Dá. Sem perguntas interativas, flags determinísticas, códigos de saída reais. Veja [Feito para agentes de IA](#feito-para-agentes-de-ia).

**Tem suporte a Google Play?**
Hoje não. Esta ferramenta é só App Store.

**Dá para agendar uma mudança de preço?**
Dá, para assinaturas: `--start-date AAAA-MM-DD`. O padrão são dois dias à frente.

**E se eu discordar da faixa de algum país?**
Sobrescreva a categoria inteira com `--coeff emerging=0.50`, exclua países com `--exclude`, ou edite o `countries.csv` direto.

## Solução de problemas

| Problema | Solução |
|----------|---------|
| `Error: Missing App Store Connect credentials` | Confira o `.env` — as 3 variáveis (ASC_KEY_ID, ASC_ISSUER_ID, ASC_PRIVATE_KEY_PATH) precisam estar definidas |
| `Error: Private key not found` | Verifique se o `.p8` está ao lado do `.env` e se o nome no `.env` bate |
| `Error: Could not fetch US price` | Garanta que o produto tem preço definido para os EUA na App Store Connect |
| `command not found: appstore-ppp-prices` | Reinstale com `uv tool install appstore-ppp-prices`, ou abra um terminal novo para o `PATH` ser lido |
| `Error: No USD price points available` | O produto não tem faixas de preço disponíveis. Confira as configurações na App Store Connect |

## Rodando os testes

```bash
pip install pytest
pytest
```

## Quem fez isto

Sou o **Aleksandr Belousov**, desenvolvedor iOS indie. Criei esta ferramenta para reprecificar meus próprios apps em 175 territórios sem gastar uma tarde na App Store Connect, e abri o código porque todo indie esbarra na mesma parede.

Site: [belousov.one](https://belousov.one) · X/Twitter: [@duceum](https://x.com/duceum) · GitHub: [@duceum](https://github.com/duceum)

Achou um bug ou discorda da faixa de algum país? [Abra uma issue](https://github.com/duceum/appstore-ppp-pricing-agent-skill/issues).

## Licença

MIT — veja [LICENSE](LICENSE).
