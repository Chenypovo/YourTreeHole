# Spec 4: 多平台接入（Telegram + 微信）

## 目标

让 Treehole 走出浏览器，接入 Telegram 和微信。用户在手机上就能跟树洞聊天，记忆自动同步。

## 架构设计

核心思路：**不重复造轮子，复用现有 Agent 层。**

```
Telegram Bot ──┐
               ├── Adapter ──→ Agent（共享 Memory + Profile + Emotion）
微信 Bot ──────┘
Web UI ──────── FastAPI（已有）
```

每个平台只写一个薄薄的 **Adapter 层**，负责：
1. 接收平台消息
2. 转换为统一格式发给 Agent
3. 把 Agent 回复转回平台消息

Agent、Memory、Profile、Emotion 全部复用，同一个 `data/` 目录。

## 平台 1: Telegram Bot

### 技术选型
- **python-telegram-bot** v20+ — 最成熟的 Python Telegram 框架，async 原生支持

### 实现

新建 `bot/telegram_bot.py`：

```python
# 核心流程
1. 启动时加载 Agent（同 app.py）
2. 收到消息 → agent.run_stream(message)
3. 流式/非流式回复给用户
4. Telegram 不支持真正的流式，但可以分块发送（每 N 个字符发一条）
```

### 配置
- `.env` 添加 `TELEGRAM_BOT_TOKEN`
- `config/settings.toml` 添加 `[telegram]` section

### 命令映射
- `/start` → 问候语
- `/memories` → 列出记忆
- `/remember <text>` → 手动添加记忆
- `/forget <n>` → 删除记忆
- `/profile` → 查看画像
- `/reset` → 重置对话

### 启动方式
```bash
python -m bot.telegram_bot
```

## 平台 2: 微信（个人号）

### 技术选型
- **itchat** 或 **gewechat** — 个人微信接口
- itchat 基于 web 协议，2024 年后不太稳定
- **gewechat** 基于桌面协议，更稳定，推荐

### 实现

新建 `bot/wechat_bot.py`：

```python
# 核心流程
1. 扫码登录（首次）
2. 收到文本消息 → agent.run(message)
3. 回复文本
4. 微信不支持流式，直接发完整回复
```

### 风险
- 微信个人号 bot 有风控风险（封号）
- 需要说明：仅供学习研究，用户自担风险
- 建议用小号

### 配置
- `config/settings.toml` 添加 `[wechat]` section

### 启动方式
```bash
python -m bot.wechat_bot
```

## 共享入口

`bot/__init__.py` — 公共的 Agent 初始化逻辑，避免 telegram_bot 和 wechat_bot 重复代码：

```python
def create_shared_agent() -> Agent:
    """创建共享 Agent 实例（同 app.py 的逻辑）"""
    config = AppConfig.from_file()
    agent, emotion = create_agent(config)
    return agent, emotion
```

## 依赖更新

`pyproject.toml` 添加 optional dependencies：

```toml
[project.optional-dependencies]
telegram = ["python-telegram-bot>=20.0"]
wechat = ["itchat>=1.3"]
all = ["python-telegram-bot>=20.0", "itchat>=1.3"]
```

用户按需安装：`pip install ".[telegram]"` 或 `pip install ".[all]"`

## 文件结构

```
bot/
├── __init__.py          # 共享 Agent 初始化
├── telegram_bot.py      # Telegram bot 入口
└── wechat_bot.py        # 微信 bot 入口
```

## 不做什么

- 不做飞书（用户没选）
- 不做 Discord（用户没选）
- 不做多用户支持（当前是单用户项目，一个 bot 一个人用）
- 不做 bot 的 Web 管理后台
- 不做消息加密（本地项目，信任本地环境）

## 验收标准

1. `pip install ".[telegram]"` 安装成功
2. `python -m bot.telegram_bot` 启动，Telegram 搜索到 bot
3. 在 Telegram 中发消息，收到正常回复
4. 记忆/画像/情绪与 Web UI 共享（同一个 data/ 目录）
5. `/memories` 等命令正常工作
6. 微信 bot 同理（如果环境允许）
7. 核心测试 (`pytest tests/`) 仍全部通过
