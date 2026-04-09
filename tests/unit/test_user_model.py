from sqlalchemy import CheckConstraint

from app.models.user import User, UserRole


def test_user_model_has_expected_table_and_columns() -> None:
    assert User.__tablename__ == "users"
    assert User.__table__.columns["email"].nullable is True
    assert User.__table__.columns["username"].nullable is True
    assert User.__table__.columns["password_hash"].nullable is False
    assert User.__table__.columns["role"].default.arg == UserRole.USER


def test_user_model_requires_at_least_one_identifier() -> None:
    constraints = [
        constraint
        for constraint in getattr(User.__table__, "constraints", set())
        if isinstance(constraint, CheckConstraint)
    ]

    assert any(
        "email IS NOT NULL OR username IS NOT NULL" in str(constraint.sqltext)
        for constraint in constraints
    )
