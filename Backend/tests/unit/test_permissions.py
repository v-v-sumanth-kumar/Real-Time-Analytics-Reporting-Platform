import pytest

from app.core.permissions import Role, has_permission, role_from_label


@pytest.mark.parametrize(
    ("user_role", "required", "expected"),
    [
        (Role.OWNER, Role.VIEWER, True),
        (Role.OWNER, Role.ADMIN, True),
        (Role.ANALYST, Role.ADMIN, False),
        (Role.VIEWER, Role.VIEWER, True),
        (Role.VIEWER, Role.ANALYST, False),
    ],
)
def test_has_permission(user_role: Role, required: Role, expected: bool) -> None:
    assert has_permission(user_role, required) is expected


def test_role_from_label() -> None:
    assert role_from_label("admin") == Role.ADMIN
    assert role_from_label("Viewer") == Role.VIEWER


def test_role_from_label_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid role"):
        role_from_label("superuser")
