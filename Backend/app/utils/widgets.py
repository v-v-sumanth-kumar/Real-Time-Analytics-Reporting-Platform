"""Widget helpers for ORM collections (defense in depth vs loader criteria edge cases)."""

from collections.abc import Iterable

from app.models.widget import Widget


def filter_active_widgets(widgets: Iterable[Widget]) -> list[Widget]:
    """Return only non-soft-deleted widgets. Always apply before API serialization."""
    return [w for w in widgets if w.deleted_at is None]
