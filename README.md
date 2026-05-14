![Murphy Agent](assets/murphy.svg)

# YourTreeHole

[![English](https://img.shields.io/badge/English-README-315B46?style=for-the-badge)](README.en.md)

YourTreeHole 是一个学习用的 AI 树洞项目。

它不是任务型 agent，也不是宠物养成应用。这个项目想探索的是：当用户把 AI 当作树洞时，AI 如何在很长时间里持续记住用户说过的话、状态、偏好和重要经历。

## 项目目标

普通聊天模型经常受上下文长度限制影响，聊久了就会忘记之前说过的事。YourTreeHole 的目标是做一个更单纯的树洞：

- 认真听用户说话。
- 把原始对话保存在本地。
- 从对话里整理出长期记忆。
- 在新会话开始时，能自然想起之前提到过的重要事情。
- 让用户可以在网页端查看、补充、删除自己的记忆。

这个项目目前并不是成熟产品，不过欢迎大家提出任何遇到的问题。

## 示例

重新开启对话时，Murphy 可以根据之前的记忆主动问起近况。

![主动问候示例](assets/examples/proactive-greeting.png)

日常聊天时，它更像一个安静的树洞，而不是任务型 agent。

![聊天示例](assets/examples/chat-example.png)

## 现在支持什么

- **Web 对话界面**：主要入口是网页端，而不是 CLI。
- **原始日记**：每轮对话会保存到本地 `data/journal.md`。
- **长期记忆**：重要信息会整理到 `data/memories.md`。
- **用户画像**：稳定信息会沉淀到 `data/user_profile.md`。
- **相关召回**：回复前会召回最近和相关的长期记忆。
- **主动问候**：启动时可以根据未闭环事件自然问起近况。
- **自定义人格**：首次使用时可以定义树洞的性格，设定保存在本地。
- **网页端记忆管理**：可以在侧边栏查看、手动添加、删除长期记忆。

## 快速开始

```bash
git clone https://github.com/Chenypovo/YourTreeHole.git
cd YourTreeHole
pip install -e ".[dev]"
cp .env.example .env
```

编辑 `.env`，填入你的 OpenAI-compatible API 配置：

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4.1-mini
```

启动 Web 版本：

```bash
python app.py
```

然后打开：

```text
http://127.0.0.1:7860/
```

## 配置

非敏感配置放在 `config/settings.toml`：

```toml
[llm]
# base_url = "https://api.z.ai/api/coding/paas/v4"
# model = "glm-5.1"

[persona]
path = "persona.md"

[memory]
data_dir = "./data"
enable_gating = true
profile_update_interval = 5
```

API key 不要写进 `config/settings.toml`。key 应该放在本地 `.env` 里。

## 本地数据

所有对话数据默认保存在本地 `data/` 目录：

```text
data/
├── journal.md        # 原始对话日记
├── memories.md       # 长期记忆
├── user_profile.md   # 用户画像
└── persona.md        # 用户自定义树洞性格
```

这些文件是用户自己的私密数据，不应该提交到仓库。

## 架构

```text
Web UI
  -> FastAPI
  -> Agent
  -> ContextManager
     -> persona
     -> user_profile.md
     -> relevant memories
     -> recent conversation
  -> LLMClient
  -> FileMemory
     -> journal.md
     -> memories.md
```

核心思路是：`journal.md` 保存原始事实，`memories.md` 保存长期记忆，`user_profile.md` 保存阶段性画像。画像和记忆都可以更新，但原始日记是更可靠的 source of truth。

## 关于 CLI

早期版本里有 CLI 命令，但现在的主要方向是 Web 端树洞。记忆查看、手动添加、删除、重置会话、人格设置这类操作会优先放到网页端。

## 项目状态

这是一个个人学习项目。当前重点是把长期记忆、用户画像、上下文召回和本地数据管理做清楚，再继续完善 Web 体验和记忆质量。
