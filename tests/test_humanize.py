from curator.config import Config
from curator.humanize import Human


def test_budget_decrements_and_blocks():
    cfg = Config.default()
    cfg.action_budget = 2
    h = Human(cfg)
    assert h.spend_action() is True
    assert h.spend_action() is True
    assert h.spend_action() is False
    assert h.budget_remaining() == 0
