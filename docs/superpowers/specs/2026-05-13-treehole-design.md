# Treehole Agent Design — "永远记得你的 AI 树洞"

## 定位

ChatGPT 超过上下文就失忆。这个项目是一个永远不会忘记你的 AI 树洞——你说过的每一件重要的事，它都记得。

**不是 agent，是树洞。** 不帮你干活，帮你倾听和记住。

与市面产品的区别：
- **OpenClaw**：帮你订外卖 → **我们**：帮你记住你为什么失眠
- **Hermes**：学会技能 → **我们**：学会你
- **ChatGPT/DeepSeek/豆包**：上下文满了就失忆 → **我们**：永远记得

## 核心体验

1. 用户打开终端，随手说任何事情
2. Agent 自动判断什么值得记住，存入长期记忆
3. 每次启动时，自动读取记忆，主动询问用户上次提到的事
4. 聊天中自动召回相关记忆 + 用户画像，融入回复
5. 用户感觉"它真的记得我"

### 启动时主动问候（关键体验）

打开终端后不是等用户说话，而是：

```
❯ murphy

  好久不见！上次你说周五有个面试，结果怎么样？
  还有你提到最近睡眠不好，这几天好些了吗？
```

实现方式：
1. 启动时读取 user_profile.md（用户画像摘要）
2. 读取 memories.md 最近 N 条记忆
3. 从中找出"未闭环"的事件（提到但没说结果的事）
4. LLM 生成一段自然语言问候

## 分层记忆架构（纯文件，无 ChromaDB）

```
data/
├── user_profile.md    # 用户画像（中期，LLM 每隔 N 轮自动整理）
├── memories.md        # 原始记忆条目（长期，按时间排列）
└── bond.json          # 羁绊/关系数据
```

```
┌─────────────────────────────────┐
│  短期：当前对话（session 内）      │  内存中保存
│  - 上下文窗口内的对话历史          │
├─────────────────────────────────┤
│  中期：用户画像摘要               │  data/user_profile.md
│  - 性格特征、习惯、偏好           │  LLM 每隔 5 轮自动整理
│  - 重要的人名、地名、事件          │
│  - 当前生活状态                   │
│  - 未闭环事件（待追问的事）        │
├─────────────────────────────────┤
│  长期：原始记忆条目               │  data/memories.md
│  - 每条值得记住的事（带时间戳）    │  纯文本，按时间排列
│  - 标记是否已闭环                 │
└─────────────────────────────────┘
```

**为什么不用 ChromaDB：**
- 树洞场景撑死几百条记忆，不需要向量检索
- 纯文件可读、可编辑、可移植——用户可以直接打开看
- 零额外依赖，安装更轻
- 截图 memories.md 就是天然的传播素材

### System Prompt 注入顺序

每次聊天的 system prompt：
1. 人格设定（用户可自定义，默认温暖倾听风格）
2. 用户画像摘要（user_profile.md 全文）
3. 相关长期记忆（memories.md 最近 N 条，或根据关键词筛选）
4. 短期对话历史
5. 当前输入

### 用户画像自动整理

每 5 轮对话后触发：
- LLM 读取当前 user_profile.md
- 结合最近 5 轮对话内容
- 更新画像：新增信息、修正过时信息、标记未闭环事件
- 写回 user_profile.md

user_profile.md 示例：

```markdown
## 用户画像

### 基本信息
- 程序员，在学 agent 开发
- 有自己的开源项目

### 性格与偏好
- 喜欢深挖底层原理
- 倾向晚上工作

### 重要的人
- （暂无记录）

### 当前状态
- 最近在准备面试
- 项目方向在调整中

### 未闭环事件
- [ ] 上次提到周五有面试，还没说结果
- [x] 说要尝试跑 murphy（已完成）
```

### 长期记忆格式

memories.md 示例：

```markdown
# 记忆

## 2026-05-13
- [用户偏好] 喜欢暗色主题，晚上工作效率最高
- [事件] 周五有大厂面试
- [情感] 最近因为项目方向选择感到焦虑

## 2026-05-10
- [习惯] 每天大概 11 点睡觉
- [重要的人] 提到室友叫小王，也在做 AI 项目
```

每条记忆：日期 + 分类标签 + 内容。闭环事件标记 `[x]`，未闭环 `[ ]`。

## CLI 命令

| 命令 | 功能 |
|---|---|
| `/profile` | 查看用户画像 |
| `/remember <内容>` | 手动添加一条记忆 |
| `/forget <编号>` | 删除一条记忆 |
| `/memories` | 列出长期记忆 |
| `/mood` | 查看情感状态 |
| `/persona` | 查看或修改人格设定 |
| `/reset` | 清空当前对话（保留长期记忆和画像） |
| `/help` | 显示帮助 |
| `/quit` | 退出 |

## 与现有代码的关系

### 保留
- **LLMClient** — API 调用层
- **情感系统（mood/bond/energy）** — 羁绊等级 = 关系深度
- **CLI 基础框架** — Rich 渲染、prompt_toolkit、流式输出
- **AppConfig** — 配置系统

### 砍掉
- **ReAct 工具循环** — 树洞不需要调用工具
- **ToolRegistry** — 无工具
- **pet_renderer** — 暂时移除
- **内置工具**（web_search, file_ops, shell_exec）
- **ChromaDB** — 替换为纯文件记忆
- **现有 Memory 类** — 替换为基于文件的 Memory

### 新增
- **FileMemory** — 基于文件的记忆系统（memories.md + user_profile.md）
- **UserProfile** — 用户画像管理（读/写/自动整理）
- **启动问候** — 读取画像 + 未闭环事件，生成主动问候
- **纯聊天模式** — 简化 Agent，不走 ReAct，直接 LLM 调用

### 简化 Agent

```python
# 树洞：直接调用，无工具，无循环
def run(self, user_input: str) -> str:
    messages = self.context.build(user_input)
    self.memory.add_message("user", user_input)
    response = self.llm.chat(messages)
    self.memory.add_message("assistant", response.content)
    self._maybe_save_memory(user_input, response.content)
    return response.content
```

更简单，更快，更便宜。

## 安装体验（电脑小白也能用）

**目标：** 3 步开始聊天，不需要懂编程。

```bash
# 1. 安装
pip install murphy-agent

# 2. 配置（只需要一个 API key）
murphy setup
# 交互式引导：选择 API 提供商 → 粘贴 key → 完成

# 3. 开始聊天
murphy
```

### setup 引导流程

```
❯ murphy setup

  欢迎使用树洞！先完成简单配置：

  选择 API 提供商：
  1. ZAI（推荐，免费额度）
  2. OpenAI
  3. DeepSeek
  4. 其他 OpenAI 兼容 API

  > 1

  粘贴你的 API Key：
  > sk-xxxxx

  ✅ 配置完成！运行 murphy 开始聊天。
```

- 自动创建 `~/.murphy/` 目录存放配置和数据
- 不需要 clone 仓库、不需要虚拟环境
- `pip install` 一步搞定所有依赖

## 传播策略

### 一句话 pitch
> ChatGPT 超过上下文就失忆，连你叫什么都忘了。我的树洞不会。

### 传播钩子
1. "它记得我三个月前说的话" — 主动问候截图
2. "它比我妈还了解我" — `/profile` 用户画像截图
3. "我的数字树洞" — 终端截图，温暖的自然语言对话
4. "看看 AI 记住了你什么" — 截图 memories.md

### 与竞品对比话术
- vs OpenClaw："它帮你订外卖。我帮你记住你为什么失眠。"
- vs Hermes："它学会技能。我学会你。"
- vs ChatGPT："它会忘记你。我不会。"

## 路线图

1. **v0.1 — 终端树洞**（当前目标）
   - 基于文件的分层记忆
   - 启动时主动问候
   - 用户画像自动整理
   - 纯聊天模式（无 ReAct）
   - pip install + murphy setup 引导

2. **v0.2 — 渠道扩展**
   - Telegram Bot
   - 飞书 Bot

3. **v0.3 — 体验增强**
   - 宠物形象回归（可选）
   - 主题/皮肤
   - 导出记忆为时间线

## 依赖

最小依赖：
- openai — LLM 调用
- rich + prompt_toolkit — CLI
- python-dotenv — 环境变量

**移除 chromadb 依赖。**
