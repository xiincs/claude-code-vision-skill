# Claude Code Vision Skill

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
| OpenAI | gpt-4o | `OPENAI_API_KEY` |
| Claude (Anthropic) | claude-sonnet-5 | `ANTHROPIC_API_KEY` |

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

1. **选择 provider**：doubao / qwen / openai / anthropic（可多选）
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
export OPENAI_API_KEY="your_key"      # OpenAI
export ANTHROPIC_API_KEY="your_key"   # Claude

# 可选
export VISION_PROVIDER=qwen           # 默认 provider
export VISION_MODEL=qwen-vl-max       # 覆盖模型
```

## 使用方式

```bash
python ~/.claude/skills/vision/vision.py "screenshot.png" "描述这张图"
python ~/.claude/skills/vision/vision.py --provider qwen "ui.png" "分析布局问题"
python ~/.claude/skills/vision/vision.py --provider anthropic "ui.png" "分析布局问题"
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
