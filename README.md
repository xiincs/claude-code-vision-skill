# Claude Code Vision Skill

[![GitHub stars](https://img.shields.io/github/stars/xiincs/claude-code-vision-skill)](https://github.com/xiincs/claude-code-vision-skill/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/xiincs/claude-code-vision-skill)](https://github.com/xiincs/claude-code-vision-skill/forks)
[![GitHub last commit](https://img.shields.io/github/last-commit/xiincs/claude-code-vision-skill)](https://github.com/xiincs/claude-code-vision-skill/commits)

为 Claude Code 提供多模态视觉能力，支持多种视觉模型分析截图、UI、图表。

专为使用 DeepSeek 等无多模态能力的模型作为 Claude Code 底座的用户设计。

## 截图直贴，所见即所析
遇到 UI 报错、设计稿或数据图表？**直接 alt + v 截图粘贴到 Claude Code 对话中，自动调用视觉模型分析**。无需记住任何命令，像聊天一样自然。

## 串联工具链，自动 UI 审查
配合 **browser-harness** 等工具，可实现**自动截图 → AI 视觉分析 → 生成审查报告 → 修正页面**的完整闭环。前端页面渲染后自动截图，由视觉模型检查布局、样式和交互问题。

## 支持的模型

| Provider | 模型 | API Key 环境变量 |
|----------|------|-----------------|
| 豆包 (Doubao) | doubao-seed-2-0-pro-260215 | `DOUBAO_API_KEY` |
| 通义千问 (Qwen) | qwen-vl-max | `DASHSCOPE_API_KEY` |
| DeepSeek | deepseek-v4-flash-vision-exp | `DEEPSEEK_API_KEY` |
| OpenAI | gpt-4o | `OPENAI_API_KEY` |
| Claude (Anthropic) | claude-sonnet-5 | `ANTHROPIC_API_KEY` |
| **任意自定义 provider** | 任意 | `{NAME}_API_KEY` |

不在上面内置厂商里的 `--provider` 名字，会按同一套命名约定动态解析：设置
`{NAME}_API_KEY` / `{NAME}_BASE_URL` / `{NAME}_MODEL`（`{NAME}_PROTOCOL` 可选，
默认 `openai`，需要 Anthropic Messages API 形状时设为 `anthropic`），无需改一行代码即可接入任意 OpenAI 兼容端点（vLLM、Ollama、LiteLLM、OpenRouter、Azure OpenAI、自建代理等）。详见 [vision/SKILL.md](vision/SKILL.md#any-custom-provider)。

## 安装依赖

需要 Python 3.10+。

```bash
pip install -r requirements.txt
```

`anthropic` 包仅在使用 `--provider anthropic` 时才会被导入，其他 provider 不受影响。

---

## Claude Code 安装流程（给 Claude Code 看的指令）

> **When the user asks you to install this skill, follow these steps IN ORDER. Do NOT skip any step.**

### Step 1 — 询问用户

使用 AskUserQuestion 询问以下信息：

1. **选择 provider**：doubao / qwen / deepseek / openai / anthropic / 自定义（可多选；自定义需额外要 base URL、model，可选 protocol）
2. **API Key**：每个 provider 的 API key
3. **默认 provider**（多选时）：选哪个作为默认

### Step 2 — 运行安装脚本

```bash
python install.py \
  --api-key qwen:sk-xxx \
  --default-provider qwen \
  --merge-claude
```

`--api-key` 可重复，`--merge-claude` **必须带上**。

如果用户选了自定义 provider，额外带上 `--base-url` / `--model`（`--protocol` 可选，默认 openai）：

```bash
python install.py \
  --api-key myapi:sk-xxx \
  --base-url myapi:https://host/v1 \
  --model myapi:my-vision-model \
  --default-provider myapi \
  --merge-claude
```

### Step 3 — 合并 CLAUDE.md（如果 install.py 未自动完成）

如果未使用 `--merge-claude`，则手动合并：

1. 读取项目根目录的 `CLAUDE.md`
2. 检查 `~/.claude/CLAUDE.md` 是否已有 `<!-- === VISION_SKILL_START === -->` 标记
3. 如果有标记 → 替换标记之间的内容
4. 如果没有标记 → 追加到文件末尾（带标记）
5. **此步骤不可跳过**

### Step 4 — 验证安装

```bash
python ~/.claude/skills/vision/vision.py --help
```

---

## 手动安装

```bash
# 交互式安装（你自己操作时）
python install.py

# 预览
python install.py --dry-run
```

## 手动配置环境变量

```bash
# 至少设置一个
export DOUBAO_API_KEY="your_key"      # 豆包
export DASHSCOPE_API_KEY="your_key"   # 通义千问
export DEEPSEEK_API_KEY="your_key"    # DeepSeek
export OPENAI_API_KEY="your_key"      # OpenAI
export ANTHROPIC_API_KEY="your_key"   # Claude

# 可选
export VISION_PROVIDER=qwen           # 默认 provider
export VISION_MODEL=qwen-vl-max       # 覆盖模型
```

自定义 provider（不在内置列表之列）按 `{NAME}_*` 命名约定注册，无需改代码：

```bash
export MYAPI_API_KEY="your_key"
export MYAPI_BASE_URL="https://your-endpoint.example.com/v1"
export MYAPI_MODEL="your-vision-model"
export MYAPI_PROTOCOL="openai"        # 可选，openai(默认) 或 anthropic
```

## 免费供应商速查

不想为豆包/Qwen/OpenAI/Claude 任何一个申请付费 key？下面这些渠道提供免费视觉模型，注册即可用，按上面"自定义 provider"的三个环境变量接入即可。**额度随时可能调整，使用前请自行到官网核实**，此表仅供起步参考：

| 渠道 | 免费视觉模型 | 大致额度 | 备注 |
|---|---|---|---|
| 智谱 (bigmodel.cn) | `glm-4v-flash` | 新用户注册赠 2000万 token | openai 协议兼容；`glm-4.6v-flash` 等具体型号请以 [docs.bigmodel.cn](https://docs.bigmodel.cn) 当前列表为准 |
| DashScope（阿里云百炼） | `qwen-vl-max` / `qwen-vl-plus` 等 | 新人额度合计超7000万 token，单模型约100万、90天有效 | 即你已内置的 `qwen` provider，无需额外接入 |
| Groq | `meta-llama/llama-4-scout-17b-16e-instruct`（原生多模态，Preview 阶段） | 约 30 RPM，日请求上限各来源数字不一致（1000~14400） | 免信用卡；国内需代理访问 |
| Google AI Studio | `gemini-2.5-flash` / `flash-lite` | 约 10–15 RPM，日请求配额官方近期多次下调 | 需代理访问；配额波动频繁，以 [AI Studio 项目页](https://aistudio.google.com) 实时数据为准 |

接入示例（以智谱为例）：

```bash
export ZHIPU_API_KEY="your_key"
export ZHIPU_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
export ZHIPU_MODEL="glm-4v-flash"
```

```bash
python ~/.claude/skills/vision/vision.py --provider zhipu "screenshot.png" "描述这张图"
```

## 模型切换路由（VISION_ROUTING）

通过 CC Switch 等代理在 DeepSeek 之类纯文本模型和原生多模态模型之间切换时，Claude Code
**无法感知真实连接的是哪个模型**——代理把请求伪装成 Anthropic API 协议转发，这层转换对
Claude Code 不可见。路由判断按以下优先级依次进行：

1. **内置纯文本模型黑名单**（当前覆盖 Qwen3-Coder、Devstral，以及 DeepSeek、GLM-4.5/4.6、
   GLM-5.x、Kimi K2 的纯文本版本）：`ANTHROPIC_MODEL` 命中时始终强制 `external`，优先级最高，
   即使下面几条都指向别的结果也不例外。黑名单用正则匹配，因为个别厂商的多模态版本和纯文本版本
   共享同一前缀（例如 GLM 的 `glm-4.6` vs `glm-4.6v`、Kimi 的 `kimi-k2-thinking` vs
   `kimi-k2.6`、DeepSeek 的 `deepseek-v4-flash` vs `deepseek-v4-flash-vision-exp`），正则排除
   了这些多模态变体，避免误伤。黑名单只会让判断更保守（多调用），不会让它更激进（漏检）——未
   命中的新模型永远不会被静默推断成 `native`。
2. **显式 `VISION_ROUTING`**：设置了就按你说的来（`native` 或 `external`），优先于下面的自动判断。
3. **未设置 `ANTHROPIC_BASE_URL`，或指向官方 `api.anthropic.com`** → 自动判定为 `native`。
   这不是猜测：Anthropic 官方 API 不提供纯文本模型，只要没有代理把这个地址改写指向别处，
   后端就一定是原生多模态的，结构上可以确定，不需要用户手动声明。
4. **`ANTHROPIC_BASE_URL` 指向其他地址、且以上都不适用** → `external`。这才是真正"身份不可
   验证"的情况（CC Switch 之类代理在中间转发，模型名字不可信），保持默认安全。

安装时会自动注册一个 Claude Code `SessionStart` hook，**每次会话开始都会用当前环境变量重新判断一次路由**，
不需要切换厂商后重跑 `install.py`，也不需要任何手动开关。判断逻辑集中在 `vision.py` 一处
（`resolve_routing()`），CLAUDE.md 和 SKILL.md 都不感知具体路径或黑名单细节。

```bash
export VISION_ROUTING=native     # 强制原生（即使检测不到官方 base URL）
export VISION_ROUTING=external   # 强制外部（即使检测到官方 base URL，比如做对比测试）
```

## 使用方式

```bash
python ~/.claude/skills/vision/vision.py "screenshot.png" "描述这张图"
python ~/.claude/skills/vision/vision.py --provider qwen "ui.png" "分析布局问题"
python ~/.claude/skills/vision/vision.py --provider anthropic "ui.png" "分析布局问题"
python ~/.claude/skills/vision/vision.py --provider myapi "ui.png" "分析布局问题"
```

## 项目结构

```
vision/                # skill 目录
├── SKILL.md           # skill 定义
└── vision.py          # 多 provider 视觉脚本

tests/                 # pytest 测试套件
install.py             # 安装脚本
CLAUDE.md              # UI 检查流程模板（合并到 ~/.claude/CLAUDE.md）
README.md              # 本文件
requirements.txt       # 运行依赖
requirements-dev.txt   # 测试依赖
```

## Star History

<a href="https://www.star-history.com/?repos=xiincs%2Fclaude-code-vision-skill&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=xiincs/claude-code-vision-skill&type=date&theme=dark&legend=top-left&sealed_token=eXbr1XfowjfcMc_xueZDQ-cLVar5C-FIiIZ7-hRYxgA2zqFG7StIWgxTlgW6FsRts5EPqX3kNAnPkum4pAcVspqv7wJZCVwKO1oLpLJi0WRLCEXzc5LJ5w" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=xiincs/claude-code-vision-skill&type=date&legend=top-left&sealed_token=eXbr1XfowjfcMc_xueZDQ-cLVar5C-FIiIZ7-hRYxgA2zqFG7StIWgxTlgW6FsRts5EPqX3kNAnPkum4pAcVspqv7wJZCVwKO1oLpLJi0WRLCEXzc5LJ5w" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=xiincs/claude-code-vision-skill&type=date&legend=top-left&sealed_token=eXbr1XfowjfcMc_xueZDQ-cLVar5C-FIiIZ7-hRYxgA2zqFG7StIWgxTlgW6FsRts5EPqX3kNAnPkum4pAcVspqv7wJZCVwKO1oLpLJi0WRLCEXzc5LJ5w" />
 </picture>
</a>
