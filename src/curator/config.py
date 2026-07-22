from dataclasses import dataclass, field


@dataclass
class Config:
    max_posts: int = 18
    max_replies: int = 8
    vision_model: str = "qwen2.5vl"
    text_model: str = "qwen2.5:7b"
    output_dir: str = "output"
    action_budget: int = 300
    min_delay_s: float = 1.0
    max_delay_s: float = 5.0
    window_left: int = 0
    window_top: int = 0
    window_width: int = 1280
    window_height: int = 1000
    chrome_profile_dir: str = "chrome-profile"
    min_confidence: float = 0.4

    @classmethod
    def default(cls) -> "Config":
        return cls()
