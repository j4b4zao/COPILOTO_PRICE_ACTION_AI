"""Evaluate caller-supplied local headlines against explicit reference time."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True, slots=True)
class NewsHeadline:
    id: str
    title: str
    source: str
    published_at: str
    published_at_utc: str
    freshness: str


@dataclass(frozen=True, slots=True)
class LocalNewsState:
    status: str
    observed_at: str
    headlines: tuple[NewsHeadline, ...] = ()
    reasons: tuple[str, ...] = ()
    observational_only: bool = True

    def __post_init__(self):
        if type(self.headlines) not in (list, tuple) or any(
            type(item) is not NewsHeadline for item in self.headlines
        ):
            raise TypeError("Expected immutable headline records")
        if type(self.reasons) not in (list, tuple) or any(
            type(reason) is not str for reason in self.reasons
        ):
            raise TypeError("Expected reason strings")
        object.__setattr__(self, "headlines", tuple(self.headlines))
        object.__setattr__(self, "reasons", tuple(self.reasons))


def evaluate_local_news(payload, *, now: datetime, max_age: timedelta) -> LocalNewsState:
    """Reject an invalid batch without returning partially accepted headlines."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Reference time requires a timezone")
    if type(max_age) is not timedelta or max_age <= timedelta(0):
        raise ValueError("Maximum age must be a positive timedelta")
    observed = now.astimezone(timezone.utc)
    if type(payload) not in (list, tuple):
        return LocalNewsState("UNAVAILABLE", observed.isoformat(), reasons=("INVALID_PAYLOAD",))

    selected = {}
    try:
        for row in payload:
            if type(row) is not dict or set(row) != {"id", "title", "source", "published_at"}:
                raise ValueError("Unexpected headline fields")
            if any(type(value) is not str or not value.strip() for value in row.values()):
                raise ValueError("Headline fields require nonempty strings")
            published = datetime.fromisoformat(row["published_at"])
            if published.tzinfo is None or published.utcoffset() is None:
                raise ValueError("Publication time requires a timezone")
            published = published.astimezone(timezone.utc)
            if published > observed:
                freshness = "FUTURE"
            elif observed - published > max_age:
                freshness = "STALE"
            else:
                freshness = "FRESH"
            headline = NewsHeadline(
                row["id"], row["title"], row["source"], row["published_at"],
                published.isoformat(), freshness,
            )
            key = (headline.source, headline.id)
            if key in selected and selected[key] != headline:
                return LocalNewsState(
                    "UNAVAILABLE", observed.isoformat(), reasons=("CONFLICTING_DUPLICATE",)
                )
            selected[key] = headline
    except (ValueError, TypeError, OverflowError):
        return LocalNewsState("UNAVAILABLE", observed.isoformat(), reasons=("INVALID_PAYLOAD",))

    headlines = tuple(sorted(
        selected.values(),
        key=lambda item: (
            datetime.fromisoformat(item.published_at_utc), item.source, item.id
        ),
    ))
    return LocalNewsState("READY" if headlines else "NO_NEWS", observed.isoformat(), headlines)

