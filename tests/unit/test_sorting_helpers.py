"""Unit tests for sorting helpers in app/utilities.py — no database."""
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.config.exceptions import BadRequest
from app.models.owners import Owner
from app.utilities import get_sortable_fields, get_sorted_query


def test_get_sortable_fields_returns_column_names():
    fields = get_sortable_fields(Owner)
    # Owner has these columns; the exact set may grow, so check membership.
    assert "id" in fields
    assert "name" in fields
    assert isinstance(fields, set)


def test_get_sorted_query_rejects_invalid_sort_order():
    sp = SimpleNamespace(sort_order="sideways", sort_by="id")
    with pytest.raises(BadRequest):
        # query is unused on this code path; the order_order check runs first.
        get_sorted_query(Owner, query=None, sort_params=sp)


def test_get_sorted_query_rejects_unknown_sort_by():
    # Neither a column on Owner nor a known cross-table alias → must raise.
    # (Previously this silently returned the query unsorted; see the early
    # validation check added in get_sorted_query.)
    sp = SimpleNamespace(sort_order="asc", sort_by="definitely_not_a_field")
    with pytest.raises(BadRequest):
        get_sorted_query(Owner, query=None, sort_params=sp)


def test_get_sorted_query_applies_order_by_for_valid_field():
    sp = SimpleNamespace(sort_order="asc", sort_by="name")
    sorted_query = get_sorted_query(Owner, select(Owner), sp)
    sql = str(sorted_query.compile())
    assert "ORDER BY" in sql.upper()
    # Field name should appear in the order-by; direction may be implicit ASC.
    assert "name" in sql.lower()
