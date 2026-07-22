from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Reply:
    author_handle: str
    author_name: str
    text: str
    likes: int
    timestamp: str = ""
    screenshot_path: str = ""
    engagement_confidence: float = 1.0
    parent_post_permalink: str = ""


@dataclass
class Post:
    author_handle: str
    author_name: str
    text: str
    likes: int
    replies: int
    reposts: int
    timestamp: str = ""
    permalink: str = ""
    has_image: bool = False
    screenshot_path: str = ""
    image_screenshot_paths: list = field(default_factory=list)
    engagement_confidence: float = 1.0
    top_replies: list = field(default_factory=list)


@dataclass
class Element:
    kind: str            # 'post' | 'reply' | 'button' | 'image'
    bbox: tuple          # (x, y, w, h) in screen coordinates
    text: str = ""
    numbers: dict = field(default_factory=dict)   # {'likes': (int, confidence), ...}


@dataclass
class ScreenModel:
    elements: list = field(default_factory=list)  # list[Element]
    raw_screenshot_path: str = ""


@dataclass
class RunResult:
    topic: str
    timestamp: str
    posts: list = field(default_factory=list)     # list[Post]
    summary_text: str = ""
    output_dir: str = ""
