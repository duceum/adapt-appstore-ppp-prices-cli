# 批量更新 App Store PPP 价格，覆盖 175+ 个国家 —— 基于购买力平价（PPP）的应用内购买与订阅区域定价

![PyPI](https://img.shields.io/pypi/v/appstore-ppp-prices)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-141%20passing-brightgreen)

**appstore-ppp-prices** 是一个免费开源的命令行工具，按**购买力平价（PPP）**批量更新 **175+ 个国家**的 App Store 应用内购买（IAP）与订阅价格。它读取基于人均 GDP 的系数，可选地用 GPT 针对你的应用类型微调，然后通过 **App Store Connect API** 直接写入价格——一条命令，取代在各个区域里点上一下午。

你的 API 密钥不会离开本机，每次执行都可以先预览再改动。

> **其他语言：** [English](README.md) · [Русский](README.ru.md) · [Português](README.pt.md) · [Español](README.es.md)

```
uv tool install appstore-ppp-prices
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

典型场景：提升新兴市场（印度、巴西、印度尼西亚）的 App Store 收入；为 iOS 游戏和订阅制应用做区域价格本地化；批量调价而无需手动处理 175 个区域；以及由 Claude Code 这类 AI 代理来驱动调价。

## 为什么苹果的自动定价会少赚钱

当你设定美国区价格后，App Store Connect 会为你生成其余 174 个店面——但它做的是**价格拉平**。它按当前汇率换算你的价格并调整当地税费，于是印度的订阅用户支付的**美元金额**和瑞士用户几乎相同。

汇率不等于购买力。App Store 各区域之间的收入中位数相差二十倍以上，因此全球拉平的价格在新兴市场过高——直接压低转化率——而在少数最富裕的国家又低于用户本愿意支付的水平。

PPP 定价让每个区域的价格贴合当地实际的支付能力。

## 你的价格会变成什么样

以下是 `--dry-run` 对一项 **5.99 美元周订阅**的真实输出，使用默认系数：

| 国家/地区 | 分组 | 系数 | PPP 价格 | 苹果拉平价格 |
|---|---|---|---|---|
| 美国 | 基准 | 1.00 | $5.99 | $5.99 |
| 瑞士 | premium | 1.12 | $6.69 | ≈ $5.99 |
| 德国 | high income | 0.92 | $5.49 | ≈ $5.99 |
| 日本 | upper middle | 0.75 | $4.49 | ≈ $5.99 |
| 波兰 | upper middle | 0.75 | $4.49 | ≈ $5.99 |
| 巴西 | lower middle | 0.55 | $3.29 | ≈ $5.99 |
| 墨西哥 | lower middle | 0.55 | $3.29 | ≈ $5.99 |
| 土耳其 | lower middle | 0.55 | $3.29 | ≈ $5.99 |
| 印度 | emerging | 0.38 | $2.29 | ≈ $5.99 |
| 印度尼西亚 | emerging | 0.38 | $2.29 | ≈ $5.99 |
| 尼日利亚 | emerging | 0.38 | $2.29 | ≈ $5.99 |
| 埃及 | emerging | 0.38 | $2.29 | ≈ $5.99 |

每个目标价都会对齐到苹果实际存在的最接近价格档位，所以这些价格 App Store Connect 一定接受。

## 它做什么

1. 用你自己的 `.p8` 密钥连接 App Store Connect API
2. 拉取你的应用内购买、订阅及其当前美国区价格
3. 依据人均 GDP 计算每个国家的目标价
4. *（可选）*让 GPT 按你的应用类型微调系数——益智游戏和 AI 工具的价格弹性完全不同
5. 把每个目标价对齐到最接近的苹果价格档位
6. 批量应用；加上 `--dry-run` 则只打印表格、不做任何改动

## 为 AI 代理而设计

多数区域定价工具是网页面板或 Mac 应用。这个工具是一条命令加一组确定性参数，因此代理可以端到端地完成整件事：

- **没有图形界面，不需要浏览器自动化。** 没有要点的按钮，没有要截的屏。
- **`--dry-run` 打印可读表格**，代理可以在应用任何改动之前核对数字。
- **没有交互式提问。** 每个决定都是一个参数。
- **纯文本错误信息和真实退出码**，失败的执行不会被误认为成功。
- **在 CI 里运行**和在笔记本上运行完全一样。

实际使用中可以把整件事交出去：

> *"先预览我周订阅的 PPP 价格，然后在除俄罗斯和白俄罗斯以外的所有地区应用。"*

其实就是这两条命令：

```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

## 你的 API 密钥不会离开本机

拥有定价权限的 App Store Connect 密钥可以改变你的客户实际支付的金额。托管型定价服务需要你把这把密钥上传到它们的服务器。

这个工具在本地运行。`.p8` 文件留在你的配置目录里，JWT 在你的机器上签名，请求直接从你的机器发往苹果。不需要注册账号，中间没有服务器，事后除了密钥本身也没有别的东西需要撤销。

## 对比

| | appstore-ppp-prices | 托管定价服务 | 手动操作 App Store Connect |
|---|---|---|---|
| API 密钥存放在哪里 | 你的机器上 | 上传给第三方 | — |
| 费用 | 免费，MIT | 订阅制 | 免费 |
| 批量更新 175+ 个区域 | 一条命令 | 支持 | 一次一个区域 |
| 应用前预览 | `--dry-run` | 视产品而定 | 不支持 |
| 可脚本化、可在 CI 运行 | 支持 | 很少 | 不支持 |
| 可由 AI 代理驱动 | 支持 | 不支持 | 不支持 |
| IAP **与**订阅 | 都支持 | 视产品而定 | 都支持 |
| 按应用类型微调系数 | GPT 辅助 | 不支持 | — |
| 计划调价、保留老订阅用户价格 | 支持 | 视产品而定 | 支持 |

## 前置条件

- 拥有定价权限的 **App Store Connect** 账号
- （可选）用于 AI 分析的 **OpenAI** API 密钥
- **Python 3.10** 或更高版本——如果用 `uv` 安装则不需要，它自带 Python

## 分步安装

### 第 1 步：安装工具

最简单的方式是 [uv](https://docs.astral.sh/uv/)，它自带 Python，你不需要事先装：

```
uv tool install appstore-ppp-prices
```

还没有 uv？先安装：`curl -LsSf https://astral.sh/uv/install.sh | sh`（macOS、Linux）或 `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`（Windows）。

已经有 Python 3.10+？下面两条也可以：

```
pipx install appstore-ppp-prices
pip install appstore-ppp-prices
```

安装后会得到同一个工具的两个命令名：`appstore-ppp-prices` 和更短的 `ppp-pricing`。本文档后面统一使用短的那个。

验证：
```
ppp-pricing --version
```

想完全不安装先试一下：`uvx appstore-ppp-prices --help`

<details>
<summary>从源码运行</summary>

```
git clone https://github.com/duceum/appstore-ppp-pricing-agent-skill.git
cd appstore-ppp-pricing-agent-skill
pip install -e .
```

</details>

### 第 2 步：创建 App Store Connect API 密钥

1. 打开 https://appstoreconnect.apple.com/access/integrations/api
2. 点击 **"Generate API Key"**
3. 名称：任意（例如 `ppp-pricing`）
4. 权限：**Admin** 或 **App Manager**
5. 点击 **"Generate"**
6. **复制 Key ID**（10 个字符，例如 `A1B2C3D4E5`）
7. **复制 Issuer ID**（页面顶部显示的 UUID）
8. **下载 .p8 文件**——这是你的私钥，只能下载一次！

把 `.p8` 文件放到配置目录：
```
mkdir -p ~/.config/ppp-pricing
mv ~/Downloads/AuthKey_*.p8 ~/.config/ppp-pricing/
```

### 第 3 步：（可选）获取 OpenAI API 密钥

AI 分析会针对你具体的应用类型调整系数。不用它也完全可以，工具会使用基于 GDP 的默认系数。

1. 打开 https://platform.openai.com/api-keys
2. 创建密钥并复制（以 `sk-` 开头）

### 第 4 步：创建 .env 配置文件

在密钥旁边创建 `.env` 文件，路径为 `~/.config/ppp-pricing/.env`（注意文件名开头的点）：

```
nano ~/.config/ppp-pricing/.env
```

填入你的值：
```
ASC_KEY_ID=你的_key_id
ASC_ISSUER_ID=你的_issuer_id
ASC_PRIVATE_KEY_PATH=AuthKey_XXXX.p8
OPENAI_API_KEY=sk-你的密钥
```

换成你自己的值。`ASC_PRIVATE_KEY_PATH` 是下载的 `.p8` 文件名——只写文件名时，会在 `.env` 同目录下查找。

想把配置放在别处？用 `--config /路径/到/目录` 指定，或设置 `PPP_PRICING_CONFIG`，也可以直接在含有 `.env` 的目录里运行。

### 第 5 步：验证安装

用你的 App ID（App Store Connect 里的 9 位数字）运行：
```
ppp-pricing --app-id 123456789
```

如果配置正确，你会看到应用下所有 IAP 和订阅的列表。

## 使用方法

### 列出所有产品
```
ppp-pricing --app-id 123456789
```

### 预览价格（不实际应用）
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

按国家显示计算出的价格表。App Store 中不会有任何改动。

### 应用价格
```
ppp-pricing --app-id 123456789 --iap com.app.weekly
```

**警告**：这条命令会真正修改 App Store Connect 中的价格！

### 参数

| 参数 | 说明 |
|------|------|
| `--dry-run` | 只预览，不应用 |
| `--no-ai` | 关闭 AI 分析 |
| `--us-price 5.99` | 覆盖美国区价格 |
| `--coeff emerging=0.70` | 手动指定某个分组的系数 |
| `--exclude RUS,BLR` | 排除国家（逗号分隔） |
| `--preserved` | 为现有订阅用户保留原价（仅订阅） |
| `--start-date 2026-08-01` | 新价格生效日期（仅订阅；默认为两天后） |
| `--config ~/keys/` | 指定存放 .env 和 .p8 的目录 |
| `--clear-cache` | 清除 AI 分析缓存并退出 |
| `--version` | 显示版本号 |

### 示例

带 AI 分析的预览：
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run
```

不使用 AI 的预览：
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --dry-run --no-ai
```

应用价格，排除俄罗斯和白俄罗斯：
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --exclude RUS,BLR
```

覆盖新兴市场的系数：
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --coeff emerging=0.50 --dry-run
```

只对新订阅用户涨价，从下个月开始：
```
ppp-pricing --app-id 123456789 --iap com.app.weekly --preserved --start-date 2026-09-01
```

清除 AI 分析缓存：
```
ppp-pricing --clear-cache
```

## 国家分组

按人均 GDP 把国家分成 6 组：

| 分组 | 示例国家 | 典型系数 |
|------|----------|----------|
| Premium | 卢森堡、瑞士、挪威 | 1.05 - 1.15 |
| USA | 美国（基准价） | 1.00 |
| High Income | 德国、英国、加拿大、澳大利亚 | 0.80 - 0.95 |
| Upper Middle | 波兰、西班牙、意大利、日本 | 0.60 - 0.75 |
| Lower Middle | 巴西、中国、墨西哥 | 0.45 - 0.60 |
| Emerging | 印度、越南、乌克兰 | 0.35 - 0.50 |

175+ 个国家的人均 GDP 与默认系数的完整清单在 [`appstore_ppp_prices/countries.csv`](appstore_ppp_prices/countries.csv)——不认同某个分组就直接改。

## 常见问题

**这会改变现有订阅用户的价格吗？**
默认会——调价对所有人生效。加上 `--preserved` 可以让现有订阅用户保持原价，新价格只对之后新增的订阅生效。仅适用于订阅；一次性内购没有这个概念。

**能在改动之前看到会发生什么吗？**
`--dry-run` 就是干这个的。它会打印全部 174 个目标价的完整表格，不写入任何内容。

**应用内购买和订阅都支持吗？**
都支持。两者使用不同的 App Store Connect 接口，工具会自动选择正确的那个。

**我的 App Store Connect API 密钥会去哪里？**
哪里都不去。它留在你的配置目录，JWT 在本地签名，请求直接发往苹果。

**系数是怎么算出来的？**
每个国家按人均 GDP 归入六个收入档之一，每个档位相对美国价格有一个默认乘数。提供 OpenAI 密钥后，GPT 会根据你的应用类别和价格弹性调整这些乘数——休闲游戏能承受的折扣力度，远大于每次请求都产生服务器成本的 AI 工具。最低系数为 0.35，同时保证 $0.99 / $0.49 的价格下限，并保持你各个产品之间的价格比例不变。

**能在 CI 或 AI 代理里运行吗？**
可以。没有交互式提问，参数确定，退出码真实。见[为 AI 代理而设计](#为-ai-代理而设计)。

**支持 Google Play 吗？**
目前不支持，仅支持 App Store。

**能预约调价时间吗？**
订阅可以：`--start-date YYYY-MM-DD`。默认是两天之后。

**如果我不认同某个国家的分档怎么办？**
用 `--coeff emerging=0.50` 整体覆盖某个分组，用 `--exclude` 排除国家，或者直接编辑 `countries.csv`。

## 故障排查

| 问题 | 解决办法 |
|------|----------|
| `Error: Missing App Store Connect credentials` | 检查 `.env`——三个变量（ASC_KEY_ID、ASC_ISSUER_ID、ASC_PRIVATE_KEY_PATH）都必须设置 |
| `Error: Private key not found` | 确认 `.p8` 与 `.env` 在同一目录，且 `.env` 里的文件名一致 |
| `Error: Could not fetch US price` | 确认该产品在 App Store Connect 中设置了美国区价格 |
| `command not found: appstore-ppp-prices` | 重新安装 `uv tool install appstore-ppp-prices`，或打开新终端让 `PATH` 生效 |
| `Error: No USD price points available` | 该产品没有可用的价格档位，请检查 App Store Connect 中的设置 |

## 运行测试

```
pip install pytest
pytest
```

## 许可证

MIT —— 见 [LICENSE](LICENSE)。
