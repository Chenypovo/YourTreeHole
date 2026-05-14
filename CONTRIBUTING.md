# Contributing

Thanks for taking a look at YourTreeHole. This is a personal learning project, so the contribution process is intentionally lightweight.

## Setup

```bash
git clone https://github.com/Chenypovo/YourTreeHole.git
cd YourTreeHole
python -m pip install -e ".[dev]"
cp .env.example .env
```

Fill in your local `.env` before running the app.

## Run Locally

```bash
python app.py
```

Open:

```text
http://127.0.0.1:7860/
```

## Tests

```bash
python -m pytest tests/ -v
```

## Pull Requests

1. Fork the repository.
2. Create a feature branch.
3. Make focused changes.
4. Run tests.
5. Open a pull request with a short explanation.

## Commit Messages

Prefer conventional commit style:

```text
feat: add memory search
fix: avoid duplicate greeting
docs: update quick start
test: cover profile update
```

## Privacy

Do not commit local runtime data. Files under `data/` can contain private conversations, memories, profiles, and persona settings.

Do not commit `.env` or API keys.
