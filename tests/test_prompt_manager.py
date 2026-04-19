from app.services.config_loader import load_full_config
from app.services.prompt_manager import load_prompt_file, render_prompt


def test_prompt_manager_loads_expected_prompt() -> None:
    config = load_full_config("config")
    prompt = load_prompt_file(
        config=config,
        config_dir="config",
        prompt_reference="complaint.complex",
    )

    assert prompt["version"] == "v2"
    assert prompt["template_id"] == "complaint_complex_v2"


def test_prompt_manager_renders_variables() -> None:
    config = load_full_config("config")
    prompt = load_prompt_file(
        config=config,
        config_dir="config",
        prompt_reference="booking.standard",
    )
    rendered = render_prompt(
        prompt,
        {
            "query": "Can I move my appointment to Friday?",
            "category": "booking",
            "complexity": "medium",
            "response_type": "standard",
        },
    )

    assert "Friday" in rendered["user_message"]
    assert "booking" in rendered["system_message"].lower() or "booking" in rendered["user_message"].lower()

