"""Shared WHERE-clause fragments for version/list queries (joined `products` alias `p`)."""

from __future__ import annotations

from typing import Any, List


def append_joined_product_version_filters(
    clauses: List[str],
    params: List[Any],
    *,
    product_name: str,
    product_name_exact: bool,
    product_part_no: str,
    date_from: str,
    date_to: str,
    date_column: str,
) -> None:
    """Append filters for product name/part and a date column (e.g. `cv.created_at`, `sv.updated_at`)."""
    if product_name:
        if product_name_exact:
            clauses.append("LOWER(p.product_name) = ?")
            params.append(product_name.lower())
        else:
            clauses.append("LOWER(p.product_name) LIKE ?")
            params.append(f"%{product_name.lower()}%")

    if product_part_no:
        clauses.append("LOWER(p.product_part_no) LIKE ?")
        params.append(f"%{product_part_no.lower()}%")

    if date_from:
        clauses.append(f"{date_column} >= ?")
        params.append(date_from)

    if date_to:
        end = date_to if "T" in date_to else f"{date_to}T23:59:59"
        clauses.append(f"{date_column} <= ?")
        params.append(end)
