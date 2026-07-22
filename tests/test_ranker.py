from curator.models import Post, Reply
from curator.ranker import top_posts, top_replies


def _post(likes, reposts=0, replies=0, conf=1.0):
    return Post(author_handle="@a", author_name="A", text="t",
                likes=likes, replies=replies, reposts=reposts,
                engagement_confidence=conf)


def test_orders_by_likes_desc():
    assert [p.likes for p in top_posts([_post(10), _post(100), _post(50)], 2)] == [100, 50]


def test_tie_breaks_by_reposts():
    assert [p.reposts for p in top_posts([_post(10, reposts=1), _post(10, reposts=9)], 2)] == [9, 1]


def test_drops_low_confidence():
    assert [p.likes for p in top_posts([_post(100, conf=0.2), _post(5, conf=0.9)], 5)] == [5]


def test_drops_unreadable_likes():
    assert [p.likes for p in top_posts([_post(-1), _post(5)], 5)] == [5]


def test_top_replies_orders_and_limits():
    reps = [Reply("@a", "A", "t", likes=3), Reply("@b", "B", "t", likes=30),
            Reply("@c", "C", "t", likes=15)]
    assert [r.likes for r in top_replies(reps, 2)] == [30, 15]
