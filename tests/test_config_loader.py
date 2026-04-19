from pathlib import Path

import pytest
import yaml

from app.services.config_loader import load_full_config


def test_load_full_config_reads_all_sections() -> None:
    config = load_full_config("config")

    assert config["app"]["name"] == "fixit-support-llmops"
    assert "models" in config
    assert "routing" in config
    assert "feature_flags" in config
    assert "budget" in config


def test_load_full_config_rejects_unknown_model_reference(tmp_path: Path) -> None:
    source_config_dir = Path("config")
    target_config_dir = tmp_path / "config"
    target_config_dir.mkdir()

    for file_path in source_config_dir.glob("*.yaml"):
        target_file = target_config_dir / file_path.name
        target_file.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")

    routing_path = target_config_dir / "routing.yaml"
    routing_data = yaml.safe_load(routing_path.read_text(encoding="utf-8"))
    routing_data["routing"]["FAQ"]["low"]["simple"]["model"] = "does_not_exist"
    routing_path.write_text(yaml.safe_dump(routing_data), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown model"):
        load_full_config(str(target_config_dir))

