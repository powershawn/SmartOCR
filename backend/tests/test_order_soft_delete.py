import uuid
from types import SimpleNamespace

from app.api.orders import scoped_query


def test_user_order_query_excludes_soft_deleted_rows_and_scopes_owner():
    user = SimpleNamespace(role="user", id=uuid.uuid4())
    sql = str(scoped_query(user)).lower()

    assert "orders.deleted_at is null" in sql
    assert "orders.owner_id" in sql


def test_admin_order_query_excludes_soft_deleted_rows():
    admin = SimpleNamespace(role="admin", id=uuid.uuid4())
    sql = str(scoped_query(admin)).lower()

    assert "orders.deleted_at is null" in sql
    assert "orders.owner_id =" not in sql
