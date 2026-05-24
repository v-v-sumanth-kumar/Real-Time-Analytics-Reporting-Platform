from enum import IntEnum


class Role(IntEnum):
    VIEWER = 1
    ANALYST = 2
    ADMIN = 3
    OWNER = 4


ROLE_LABELS = {
    Role.VIEWER: "viewer",
    Role.ANALYST: "analyst",
    Role.ADMIN: "admin",
    Role.OWNER: "owner",
}

LABEL_TO_ROLE = {v: k for k, v in ROLE_LABELS.items()}


def role_from_label(label: str) -> Role:
    role = LABEL_TO_ROLE.get(label.lower())
    if role is None:
        raise ValueError(f"Invalid role: {label}")
    return role


def has_permission(user_role: Role, required_role: Role) -> bool:
    return user_role >= required_role
