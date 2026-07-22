import dataclasses
from curator.config import Config


def test_defaults_present():
    c = Config.default()
    assert c.max_posts == 18
    assert c.max_replies == 8
    assert c.output_dir == "output"
    assert c.action_budget == 300


def test_local_model_fields_removed():
    names = {f.name for f in dataclasses.fields(Config)}
    assert "vision_model" not in names
    assert "text_model" not in names
