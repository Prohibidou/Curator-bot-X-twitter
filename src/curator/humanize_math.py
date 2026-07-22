def bezier_path(start, end, steps, rng):
    """Quadratic Bezier from start to end with a randomized control point."""
    (x0, y0), (x1, y1) = start, end
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    offset = rng.uniform(-0.3, 0.3)
    cx = mx + (y1 - y0) * offset
    cy = my - (x1 - x0) * offset
    points = []
    for i in range(steps):
        t = i / (steps - 1) if steps > 1 else 1.0
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        points.append((round(x), round(y)))
    points[0] = (x0, y0)
    points[-1] = (x1, y1)
    return points


def jittered_delay(lo, hi, rng):
    """Non-uniform delay in [lo, hi], biased toward the low end."""
    return rng.triangular(lo, hi, lo + (hi - lo) * 0.35)


def dwell_seconds(text, wps=3.5):
    """Estimated reading dwell time in seconds, minimum 0.4s."""
    words = len((text or "").split())
    return max(0.4, words / wps)
