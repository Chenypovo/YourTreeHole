# Spec 1: 开源规范与项目打磨

## 目标

让 Treehole 项目达到开源发布的标准：法律合规、CI 自动化、README 专业、贡献者友好。做完这一步就可以正式对外宣传。

## 改动清单

### 1. LICENSE — MIT

选择 MIT License：
- 最宽松、最友好、采用率最高
- 用户可以自由使用、修改、商用
- 对个人项目和小团队最合适

文件：`LICENSE`（根目录）

### 2. GitHub Actions CI

`.github/workflows/ci.yml`：

触发条件：push to main / PR to main

步骤：
1. Checkout
2. Setup Python 3.13
3. Install dependencies（`pip install -e ".[dev]"`）
4. Run `pytest tests/ -v`
5. Run `ruff check .`（lint，如果加的话）

不做什么：
- 不做 deploy workflow（还没到那步）
- 不做 coverage report（优先级低）

### 3. README 打磨

当前 README 已经不错，需要补充：
- **demo GIF/截图**：用现有 `assets/examples/` 里的截图，或者录一个终端 + Web UI 的 demo
- **Quick Start 简化**：三步上手（clone → 配置 .env → 运行）
- **Feature 列表**：用 badge 展示核心特性（记忆持久化、情感系统、主动问候等）
- **Architecture 图**：简单的模块关系图
- **License badge**：链接到 MIT License

不做什么：
- 不重写整个 README，在现有基础上优化
- 不加英文版（已有 README.en.md）

### 4. CONTRIBUTING.md

简洁的贡献指南：
- 如何 fork & clone
- 开发环境设置（`pip install -e ".[dev]"`）
- 代码风格（跟着现有代码走）
- PR 流程（fork → branch → PR）
- Commit message 风格（conventional commits）

### 5. .gitignore 补充

确认 `.gitignore` 包含：
- `data/` 下的运行时文件（memories.md, user_profile.md, bond.json）
- `.env`
- `__pycache__/`
- `.pytest_cache/`
- `.venv/`
- `.DS_Store`

### 6. pyproject.toml 清理

- 移除 `streamlit` 依赖（已换成 FastAPI，不再需要）
- 移除 `prompt-toolkit`（仅 CLI 用，Web 不需要）— 等等，CLI 还在用，保留
- 确认 `description`、`version`、`license` 字段正确
- 添加 `license = "MIT"`

## 不做什么

- 不加 Docker（那是 Spec 2）
- 不加 pre-commit hooks（过度工程化，项目还小）
- 不加 ruff/black（除非顺手加到 CI 里）
- 不加 CODE_OF_CONDUCT.md（个人小项目，暂不需要）
- 不加 SECURITY.md（暂不需要）
- 不改核心代码

## 验收标准

1. `LICENSE` 文件存在，内容为 MIT
2. `.github/workflows/ci.yml` 存在，push 后 GitHub Actions 绿灯
3. README 有清晰的 Quick Start 和 demo 截图
4. `CONTRIBUTING.md` 存在
5. `pytest tests/` 全部通过
6. `pyproject.toml` 有 `license` 字段
