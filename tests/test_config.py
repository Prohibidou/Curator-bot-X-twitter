import dataclasses
from curator.config import Config


def test_defaults_present():
    c = Config.default()
    assert c.max_posts == 18
    assert c.max_replies == 8
    assert c.debug_port == 9222


def test_no_local_model_fields():
    names = {f.name for f in dataclasses.fields(Config)}
    assert "vision_model" not in names
    assert "text_model" not in names
