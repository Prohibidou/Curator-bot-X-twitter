from curator.models import Post, Reply


def _eligible(likes, confidence, min_confidence) -> bool:
    return likes is not None and likes >= 0 and confidence >= min_confidence


def top_posts(posts, n, min_confidence=0.4):
    e = [p for p in posts if _eligible(p.likes, p.engagement_confidence, min_confidence)]
    e.sort(key=lambda p: (p.likes, p.reposts, p.replies), reverse=True)
    return e[:n]


def top_replies(replies, m, min_confidence=0.4):
    e = [r for r in replies if _eligible(r.likes, r.engagement_confidence, min_confidence)]
    e.sort(key=lambda r: r.likes, reverse=True)
    return e[:m]
