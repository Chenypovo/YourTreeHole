# MURPHY

[![English](https://img.shields.io/badge/English-README-315B46?style=for-the-badge)](README.en.md)

Murphy 是一个学习用的 AI 树洞项目，它不是为了帮用户执行任务，而是为了探索一件更具体的事：当用户把 AI 当作树洞时，AI 怎么在很长时间里持续记住用户说过的话、状态、偏好和重要经历。

## 项目目标

普通聊天模型经常受上下文长度限制影响，聊久了就会忘记之前说过的事。Murphy 的目标是做一个更单纯的树洞：

- 认真听用户说话。
- 把原始对话保存在本地。
- 从对话里整理出长期记忆。
- 在新会话开始时，能自然想起之前提到过的重要事情。
- 让用户可以查看、补充、删除自己的记忆。

这个项目目前并不是成熟产品，不过欢迎大家提出任何遇到的问题。

## 示例

重新开启对话时，Murphy 可以根据之前的记忆主动问起近况。

![主动问候示例](assets/examples/proactive-greeting.png)

日常聊天时，它更像一个安静的树洞，而不是任务型 agent。

![聊天示例](assets/examples/chat-example.png)

## 现在支持什么

- **原始日记**：每轮对话会保存到本地 `data/journal.md`。
- **长期记忆**：重要信息会整理到 `data/memories.md`。
- **用户画像**：稳定信息会沉淀到 `data/user_profile.md`。
- **相关召回**：回复前会召回最近和相关的长期记忆。
- **主动问候**：启动时可以根据未闭环事件自然问起近况。
- **自定义人格**：首次使用时可以定义树洞的性格，设定保存在本地。
- **记忆管理**：可以查看、手动添加、删除长期记忆。

## 快速开始

```bash
pip install -e ".[dev]"
cp .env.example .env
```

编辑 `.env`，填入你的 OpenAI-compatible API 配置：

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4.1-mini
```

启动 CLI：

```bash
murphy
```

如果使用 Web 版本：

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


## 本地数据

所有对话数据默认保存在本地 `data/` 目录：

```text
data/
├── journal.md        # 原始对话日记
├── memories.md       # 长期记忆
├── user_profile.md   # 用户画像
└── persona.md        # 用户自定义树洞性格
```


## 架构

```text
CLI / Web
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

## 常用命令

| 命令 | 说明 |
| --- | --- |
| `/help` 或 `/` | 查看命令 |
| `/profile` | 查看用户画像 |
| `/memories` | 查看长期记忆 |
| `/remember <内容>` | 手动添加一条记忆 |
| `/forget <编号>` | 删除一条记忆 |
| `/persona` | 查看树洞人格 |
| `/reset` | 清空当前会话，不删除长期记忆 |
| `/quit` | 退出 |

