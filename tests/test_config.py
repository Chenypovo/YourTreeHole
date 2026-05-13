from core.config import AppConfig


def test_app_config_loads_from_toml(tmp_path):
    config_file = tmp_path / "settings.toml"
    config_file.write_text(
        """
[llm]
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
""".strip(),
        encoding="utf-8",
    )

    config = AppConfig.from_file(str(config_file))

    assert config.llm.model == "test-model"
    assert config.persona.path == "data/test_persona.md"
    assert config.memory.data_dir == "./tmp/data"
    assert config.memory.enable_gating is False
    assert config.memory.profile_update_interval == 10
    assert config.ui.show_input_rules is False
    assert config.ui.input_prompt == ">>> "


def test_app_config_uses_defaults_when_missing(tmp_path):
    config = AppConfig.from_file(str(tmp_path / "missing.toml"))

    assert config.persona.path == "persona.md"
    assert config.memory.data_dir == "./data"
    assert config.memory.enable_gating is True
    assert config.memory.profile_update_interval == 5
