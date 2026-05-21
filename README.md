# Claude Code Vision Skill

为 Claude Code 提供多模态视觉能力，支持多种视觉模型分析截图、UI、图表。

专为使用 DeepSeek 等无多模态能力的模型作为 Claude Code 底座的用户设计。

本 skill 搭配 browser-harness skill 使用，驱动前端页面布局检查。

## 支持的模型

| Provider | 模型 | API Key 环境变量 |
|----------|------|-----------------|
| 豆包 (Doubao) | doubao-seed-2-0-pro-260215 | `DOUBAO_API_KEY` |
| 通义千问 (Qwen) | qwen-vl-max | `DASHSCOPE_API_KEY` |
| OpenAI | gpt-4o | `OPENAI_API_KEY` |

## 快速安装

```bash
# 安装到用户目录
python install.py

# 安装到指定项目
python install.py --project /path/to/project

# 预览（不实际写入）
python install.py --dry-run
```

## 环境变量

```bash
# 必选：至少设置一个 API Key
export DOUBAO_API_KEY="your_key"      # 豆包
export DASHSCOPE_API_KEY="your_key"   # 通义千问
export OPENAI_API_KEY="your_key"      # OpenAI

# 可选：全局配置
export VISION_PROVIDER=qwen           # 默认 provider
export VISION_MODEL=qwen-vl-max       # 全局模型覆盖
export VISION_TEMPERATURE=0           # 创造性 0-1，默认 0
export VISION_MAX_TOKENS=4096         # 最大输出 token

# 可选：provider 专属模型覆盖
export DOUBAO_MODEL=doubao-seed-2-0-pro-260215
export QWEN_MODEL=qwen-vl-max
export OPENAI_MODEL=gpt-4o

# 可选：自定义 API 端点
export DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
export DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export OPENAI_BASE_URL=https://api.openai.com/v1
```

## 使用方式

```bash
# 自动检测 provider
python ~/.claude/skills/vision/vision.py "screenshot.png" "描述这张图"

# 指定 provider
python ~/.claude/skills/vision/vision.py --provider qwen "ui.png" "分析布局问题"

# 短选项
python ~/.claude/skills/vision/vision.py -p openai "diagram.png" "解释架构"
```

## 目录结构

```
vision/              # skill 目录
├── SKILL.md         # skill 定义（Claude Code 读取）
└── vision.py        # 多 provider 视觉脚本

install.py           # 安装脚本
CLAUDE.md            # UI 检查流程模板（合并到你的 ~/.claude/CLAUDE.md）
README.md            # 本文件
```
