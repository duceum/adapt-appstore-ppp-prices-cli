# Atualização em massa de preços PPP na App Store em 175+ países — preços regionais por paridade de poder de compra para assinaturas e compras no app

![PyPI](https://img.shields.io/pypi/v/appstore-ppp-prices)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-164%20passing-brightgreen)

**appstore-ppp-prices** é uma ferramenta de linha de comando gratuita e de código aberto que atualiza em massa os preços de compras no app (IAP) e assinaturas da App Store em **175+ países** usando **paridade de poder de compra (PPP)**. Ela lê coeficientes baseados no PIB per capita, opcionalmente os ajusta com GPT para o tipo do seu app, e grava os preços diretamente pela **App Store Connect API** — um comando em vez de uma tarde inteira clicando por territórios.

Sua chave de API nunca sai da sua máquina, e toda execução pode ser pré-visualizada antes de qualquer mudança.

> **Outros idiomas:** [English](README.md) · [Русский](README.ru.md) · [Español](README.es.md) · [中文](README.zh.md)

```
uv tool install appstore-ppp-prices
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Casos de uso típicos: aumentar a receita da App Store em mercados emergentes (Índia, Brasil, Indonésia), localização regional de preços para jogos iOS e apps de assinatura, mudanças de preço em massa sem passar por 175 territórios na mão, e reprecificação conduzida por um agente de IA como o Claude Code.

## Por que o preço automático da Apple deixa dinheiro na mesa

Quando você define um preço nos EUA, a App Store Connect gera as outras 174 vitrines para você — mas ela as **equaliza**. Converte o preço pela taxa de câmbio atual e ajusta o imposto local, então um assinante na Índia paga aproximadamente o mesmo **em dólares** que um na Suíça.

Taxa de câmbio não é poder de compra. O salário mediano varia mais de 20× entre os territórios da App Store, então um preço globalmente equalizado é ao mesmo tempo alto demais nos mercados emergentes — onde sufoca a conversão — e, em alguns dos mais ricos, menor do que os clientes pagariam sem reclamar.

O preço por PPP posiciona cada território de acordo com o que as pessoas de lá realmente podem pagar.

## Como ficam os seus preços

Saída real do `--dry-run` para uma **assinatura semanal de US$ 5,99**, com os coeficientes padrão:

| País | Categoria | Coeficiente | Preço PPP | Preço equalizado da Apple |
|---|---|---|---|---|
| Estados Unidos | base | 1,00 | $5.99 | $5.99 |
| Suíça | premium | 1,12 | $6.69 | ≈ $5.99 |
| Alemanha | high income | 0,92 | $5.49 | ≈ $5.99 |
| Japão | upper middle | 0,75 | $4.49 | ≈ $5.99 |
| Polônia | upper middle | 0,75 | $4.49 | ≈ $5.99 |
| Brasil | lower middle | 0,55 | $3.29 | ≈ $5.99 |
| México | lower middle | 0,55 | $3.29 | ≈ $5.99 |
| Turquia | lower middle | 0,55 | $3.29 | ≈ $5.99 |
| Índia | emerging | 0,38 | $2.29 | ≈ $5.99 |
| Indonésia | emerging | 0,38 | $2.29 | ≈ $5.99 |
| Nigéria | emerging | 0,38 | $2.29 | ≈ $5.99 |
| Egito | emerging | 0,38 | $2.29 | ≈ $5.99 |

Cada alvo é ajustado para a faixa de preço real mais próxima da Apple, então são preços que a App Store Connect aceita de fato.

## O que a ferramenta faz

1. Conecta-se à App Store Connect API com a sua própria chave `.p8`
2. Busca suas compras no app, assinaturas e os preços atuais nos EUA
3. Calcula um preço-alvo por país a partir do PIB per capita
4. *(Opcional)* Pede ao GPT para ajustar os coeficientes ao tipo do seu app — um jogo de puzzle e uma ferramenta de IA têm elasticidade de preço muito diferentes
5. Resolve cada alvo para a faixa de preço mais próxima da Apple
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

```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

### Skills prontas

Instruções prontas para os principais agentes de código estão em [`agent-skills/`](agent-skills/):

| Agente | Arquivo | Onde instalar |
|---|---|---|
| Claude Code | `SKILL.md` | `~/.claude/skills/appstore-ppp-pricing/` |
| Cursor | regra `.mdc` | `.cursor/rules/` |
| Codex, Copilot, Aider, Jules, VS Code, Devin | `AGENTS.md` | raiz do repositório |

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

## Instalação passo a passo

### Passo 1: Instalar a ferramenta

O jeito mais fácil é o [uv](https://docs.astral.sh/uv/), que não precisa de um Python seu — ele traz o dele:

```
uv tool install appstore-ppp-prices
```

Ainda não tem uv? Instale primeiro com `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS, Linux) ou `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows).

Já tem Python 3.10+? Qualquer um destes também funciona:

```
pipx install appstore-ppp-prices
pip install appstore-ppp-prices
```

Está no Mac e prefere Homebrew?

```
brew tap duceum/tap
brew trust duceum/tap
brew install duceum/tap/appstore-ppp-prices
```

`brew trust` é o Homebrew 6 perguntando se você aceita executar código de fórmula de um tap de terceiros. A instalação leva alguns minutos: o Homebrew compila as dependências Python a partir do código-fonte, e três delas têm extensões nativas. O `uv` usa wheels prontos e termina em segundos.

Isso instala dois nomes para a mesma ferramenta: `appstore-ppp-prices` e o mais curto `ppp-pricing`. O resto deste README usa o curto.

Verifique:
```
ppp-pricing --version
```

Para experimentar sem instalar nada: `uvx appstore-ppp-prices --help`

<details>
<summary>Rodando a partir do código-fonte</summary>

```
git clone https://github.com/duceum/appstore-ppp-pricing-agent-skill.git
cd appstore-ppp-pricing-agent-skill
pip install -e .
```

</details>

### Passo 2: Criar uma chave de API da App Store Connect

1. Acesse https://appstoreconnect.apple.com/access/integrations/api
2. Clique em **"Generate API Key"**
3. Nome: qualquer um (por exemplo, `ppp-pricing`)
4. Acesso: **Admin** ou **App Manager**
5. Clique em **"Generate"**
6. **Copie o Key ID** (10 caracteres, ex.: `A1B2C3D4E5`)
7. **Copie o Issuer ID** (UUID mostrado no topo da página)
8. **Baixe o arquivo .p8** — esta é a sua chave privada. Só dá para baixar uma vez!

Coloque o arquivo `.p8` na sua pasta de configuração:
```
mkdir -p ~/.config/ppp-pricing
mv ~/Downloads/AuthKey_*.p8 ~/.config/ppp-pricing/
```

### Passo 3: (Opcional) Obter uma chave da OpenAI

A análise por IA ajusta os coeficientes ao tipo específico do seu app. Sem ela, a ferramenta usa os padrões baseados no PIB, que são perfeitamente utilizáveis.

1. Acesse https://platform.openai.com/api-keys
2. Crie uma chave e copie (começa com `sk-`)

<details>
<summary>Usando outro provedor que não a OpenAI</summary>

A requisição é um chat completion no formato da OpenAI, então funciona com qualquer
coisa que fale esse formato — OpenRouter, Groq, Together, Fireworks, DeepSeek, ou um
Ollama, LM Studio ou vLLM local. Aponte para outro lugar com duas variáveis no `.env`:

```
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.3-70b-instruct
```

`LLM_API_KEY` (ou `OPENAI_API_KEY`) passa a guardar a chave desse provedor. Um modelo local não precisa de
chave nenhuma, mas a variável ainda tem que estar preenchida com algo.
`LLM_REQUEST_TIMEOUT` (segundos, padrão 120) ajuda com modelos locais lentos.

</details>

### Passo 4: Criar o arquivo de configuração .env

Crie um arquivo `.env` ao lado da chave, em `~/.config/ppp-pricing/.env` (note o ponto no começo do nome):

```
nano ~/.config/ppp-pricing/.env
```

Preencha com seus valores:
```
ASC_KEY_ID=seu_key_id
ASC_ISSUER_ID=seu_issuer_id
ASC_PRIVATE_KEY_PATH=AuthKey_XXXX.p8
LLM_API_KEY=sk-sua-chave
LLM_MODEL=gpt-5.2
```

Substitua pelos valores reais. `ASC_PRIVATE_KEY_PATH` é o nome do arquivo `.p8` baixado — um nome simples é resolvido ao lado do `.env`.

Prefere manter a configuração em outro lugar? Aponte com `--config /caminho/para/pasta`, defina `PPP_PRICING_CONFIG`, ou simplesmente rode a ferramenta a partir de um diretório que tenha um `.env`.

### Passo 5: Verificar a instalação

Rode o comando com o seu App ID (número de 9 dígitos da App Store Connect):
```
ppp-pricing --app-id 123456789
```

Se estiver tudo certo, você verá a lista de todos os IAPs e assinaturas do seu app.

## Uso

### Listar todos os produtos
```
ppp-pricing --app-id 123456789
```

### Pré-visualizar preços (sem aplicar)
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Mostra uma tabela dos preços calculados por país. Nada muda na App Store.

### Aplicar preços
```
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
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

Pré-visualizar sem IA:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run --no-ai
```

Aplicar preços, excluindo Rússia e Belarus:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

Sobrescrever o coeficiente dos mercados emergentes:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --coeff emerging=0.50 --dry-run
```

Aumentar o preço só para novos assinantes, a partir do mês que vem:
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --preserved --start-date 2026-09-01
```

Limpar o cache da análise por IA:
```
ppp-pricing --clear-cache
```

## Categorias de países

Os países são divididos em 6 categorias pelo PIB per capita:

| Categoria | Países de exemplo | Coeficiente típico |
|-----------|-------------------|--------------------|
| Premium | Luxemburgo, Suíça, Noruega | 1,05 - 1,15 |
| USA | Estados Unidos (preço base) | 1,00 |
| High Income | Alemanha, Reino Unido, Canadá, Austrália | 0,80 - 0,95 |
| Upper Middle | Polônia, Espanha, Itália, Japão | 0,60 - 0,75 |
| Lower Middle | Brasil, China, México | 0,45 - 0,60 |
| Emerging | Índia, Vietnã, Ucrânia | 0,35 - 0,50 |

A lista completa dos 175+ países com PIB per capita e coeficientes padrão está em [`appstore_ppp_prices/countries.csv`](appstore_ppp_prices/countries.csv) — edite se discordar de alguma classificação.

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

```
pip install pytest
pytest
```

## Licença

MIT — veja [LICENSE](LICENSE).
