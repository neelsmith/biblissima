"""Small helpers for building and paging RQL queries.

RQL is the query language of the portal's CubicWeb backend. The clause order
matters: ``Any <vars> ORDERBY <var> LIMIT <n> OFFSET <k> WHERE <conditions>``.
Putting ``LIMIT`` after ``WHERE`` silently returns no rows.
"""

from __future__ import annotations

from typing import Iterator

from .client import PortalClient


def quote(value: str) -> str:
    """Return ``value`` as an RQL string literal.

    :raises ValueError: if the value contains a backslash or a line break, or
        both kinds of quote, since those cannot be written safely.
    """
    if "\\" in value or "\n" in value or "\r" in value:
        raise ValueError(f"cannot quote value for RQL: {value!r}")
    if '"' not in value:
        return f'"{value}"'
    if "'" not in value:
        return f"'{value}'"
    raise ValueError(f"cannot quote value for RQL: {value!r}")


def page_query(
    select: str, where: str, *, order_by: str, limit: int, offset: int
) -> str:
    """Build one page of a query."""
    if limit <= 0 or offset < 0:
        raise ValueError("limit must be positive and offset non-negative")
    return (
        f"Any {select} ORDERBY {order_by} LIMIT {limit} OFFSET {offset} "
        f"WHERE {where}"
    )


def iter_rows(
    client: PortalClient,
    select: str,
    where: str,
    *,
    order_by: str,
    page_size: int = 2000,
    limit: int | None = None,
) -> Iterator[list]:
    """Yield every row of a query, fetching ``page_size`` rows at a time.

    The first page must not be empty (an empty first page usually means the
    query is invalid). Iteration ends at the first short page or after
    ``limit`` rows.
    """
    offset = 0
    produced = 0
    while True:
        size = page_size if limit is None else min(page_size, limit - produced)
        if size <= 0:
            return
        query = page_query(
            select, where, order_by=order_by, limit=size, offset=offset
        )
        rows = client.rql(query, allow_empty=offset > 0)
        for row in rows:
            yield row
        produced += len(rows)
        if len(rows) < size:
            return
        offset += size
