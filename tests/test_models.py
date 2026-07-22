from curator.models import Post, Reply, Element, ScreenModel, RunResult


def test_post_defaults():
    p = Post(author_handle="@a", author_name="A", text="hi",
             likes=10, replies=2, reposts=1)
    assert p.permalink == ""
    assert p.has_image is False
    assert p.top_replies == []
    assert p.engagement_confidence == 1.0


def test_reply_and_screenmodel():
    r = Reply(author_handle="@b", author_name="B", text="yo", likes=5)
    e = Element(kind="post", bbox=(0, 0, 100, 50), text="yo",
                numbers={"likes": (5, 0.9)})
    sm = ScreenModel(elements=[e])
    assert r.likes == 5
    assert sm.elements[0].numbers["likes"] == (5, 0.9)


def test_runresult():
    rr = RunResult(topic="x", timestamp="2026-07-22", posts=[], summary_text="",
                   output_dir="out")
    assert rr.posts == []
