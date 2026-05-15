from core.config import AppConfig


def test_app_config_loads_from_toml(tmp_path):
    config_file = tmp_path / "settings.toml"
    config_file.write_text(
        """
[llm]
base_url = "http://config-base"
model = "test-model"

[persona]
path = "data/test_persona.md"

[memory]
data_dir = "./tmp/data"
enable_gating = false
profile_update_interval = 10

[agent]

[ui]
show_input_rules = false
input_prompt = ">>> "

[telegram]
enabled = true
allowed_user_ids = [123, 456]
reply_mode = "final"
""".strip(),
        encoding="utf-8",
    )

    config = AppConfig.from_file(str(config_file))

    assert config.llm.model == "test-model"
    assert config.llm.base_url == "http://config-base"
    assert config.persona.path == "data/test_persona.md"
    assert config.memory.data_dir == "./tmp/data"
    assert config.memory.enable_gating is False
    assert config.memory.profile_update_interval == 10
    assert config.ui.show_input_rules is False
    assert config.ui.input_prompt == ">>> "
    assert config.telegram.enabled is True
    assert config.telegram.allowed_user_ids == [123, 456]
    assert config.telegram.reply_mode == "final"


def test_app_config_uses_defaults_when_missing(tmp_path):
    config = AppConfig.from_file(str(tmp_path / "missing.toml"))

    assert config.persona.path == "persona.md"
    assert config.llm.base_url is None
    assert config.llm.model is None
    assert config.memory.data_dir == "./data"
    assert config.memory.enable_gating is True
    assert config.memory.profile_update_interval == 5
    assert config.telegram.enabled is False
    assert config.telegram.allowed_user_ids == []
