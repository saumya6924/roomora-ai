"""Review summaries shared by the seller, designer and admin dashboards."""

from collections.abc import Iterable


def summarize(ratings: Iterable[int]) -> dict:
    """Average, count and the 1-5 star distribution (percent of all reviews)."""
    ratings = list(ratings)
    count = len(ratings)
    distribution = {star: 0 for star in range(1, 6)}
    for rating in ratings:
        distribution[rating] += 1
    return {
        "average": round(sum(ratings) / count, 1) if count else 0,
        "count": count,
        "distribution": {star: round(100 * n / count) if count else 0 for star, n in distribution.items()},
    }
