# Spec 2: Docker 一键部署

## 目标

让用户 clone 之后一行命令就能跑起来，零 Python 环境、零配置烦恼。对 GitHub stars 转化率至关重要——试用门槛越低，star 概率越高。

## 改动清单

### 1. Dockerfile

多阶段构建，镜像精简：

```
阶段 1 (builder): Python 3.13-slim, pip install
阶段 2 (runtime): 拷贝依赖 + 项目代码
```

关键点：
- 基于 `python:3.13-slim`
- `pip install --no-cache-dir` 减小镜像体积
- 暴露端口 7860
- 工作目录 `/app`
- `data/` 目录用 volume 持久化
- 用 `uvicorn` 直接启动（不用 gunicorn，单用户场景够了）
- `.env` 文件通过 volume 或 env vars 注入

### 2. docker-compose.yml

一键启动配置：

```yaml
services:
  treehole:
    build: .
    ports:
      - "7860:7860"
    volumes:
      - ./data:/app/data        # 记忆持久化
      - ./.env:/app/.env        # API key 配置
    environment:
      - OPENAI_BASE_URL=${OPENAI_BASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=${OPENAI_MODEL:-gpt-4.1-mini}
```

用户体验：
1. `cp .env.example .env` → 填入 API key
2. `docker compose up -d`
3. 打开 `http://localhost:7860`
4. 完事

### 3. .dockerignore

排除不需要进镜像的文件：
```
.git
.venv
__pycache__
.pytest_cache
.DS_Store
data/
*.pyc
.env
docs/
tests/
.claude/
```

### 4. README 更新

在 Quick Start 部分添加 Docker 方式：

```markdown
## Docker（推荐）

```bash
cp .env.example .env
# 编辑 .env 填入你的 API key
docker compose up -d
# 打开 http://localhost:7860
```
```

## 不做什么

- 不做 Docker Hub 镜像发布（clone + build 更简单）
- 不做 Kubernetes 配置（个人项目不需要）
- 不做 Nginx 反代配置（用户自己按需加）
- 不做 GPU 支持（纯 CPU 推理，LLM 在远端 API）

## 验收标准

1. `docker compose up -d` 成功启动
2. `http://localhost:7860` 打开 Treehole 界面
3. 聊天、记忆、画像功能正常
4. `docker compose down` 后再 `up`，数据不丢失（volume 持久化）
5. 镜像体积 < 300MB
