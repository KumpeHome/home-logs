from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import DomainError
from app.forms.catalog import FORM_TYPES


@dataclass(frozen=True)
class PermissionResource:
    code: str
    name: str
    group: str
    actions: tuple[str, ...]
    path: str | None = None


TAB_RESOURCES: tuple[PermissionResource, ...] = (
    PermissionResource("tab.dashboard", "Dashboard", "tab", ("view",), "/"),
    PermissionResource(
        "tab.people", "People", "tab", ("view", "add", "edit"), "/people"
    ),
    PermissionResource("tab.logs", "Logs", "tab", ("view",), "/logs"),
    PermissionResource("tab.forms", "Forms", "tab", ("view",), "/forms"),
    PermissionResource(
        "tab.school", "School", "tab", ("view", "add", "edit"), "/school"
    ),
    PermissionResource(
        "tab.discipline", "Discipline", "tab", ("view", "add", "edit"), "/discipline"
    ),
    PermissionResource(
        "tab.documents", "Documents", "tab", ("view", "add", "edit"), "/documents"
    ),
    PermissionResource("tab.export", "Export", "tab", ("view",), "/export"),
    PermissionResource(
        "tab.settings", "Settings", "tab", ("view", "edit"), "/settings"
    ),
    PermissionResource("tab.audit", "Audit", "tab", ("view",), "/audit"),
)

FORM_ACTIONS = ("view", "add", "edit", "export")


def list_permission_resources() -> list[PermissionResource]:
    forms = [
        PermissionResource(f"form.{item.code}", item.name, "form", FORM_ACTIONS)
        for item in FORM_TYPES
    ]
    return [*TAB_RESOURCES, *forms]


def serialize_catalog() -> list[dict]:
    return [
        {
            "code": item.code,
            "name": item.name,
            "group": item.group,
            "actions": list(item.actions),
            "path": item.path,
        }
        for item in list_permission_resources()
    ]


_RESOURCES = {item.code: item for item in list_permission_resources()}


def get_resource(code: str) -> PermissionResource:
    try:
        return _RESOURCES[code]
    except KeyError as exc:
        raise DomainError(f"Unknown permission resource: {code}") from exc


def validate_grant(resource: str, action: str) -> None:
    spec = get_resource(resource)
    if action not in spec.actions:
        raise DomainError(f"Unknown action {action} for {resource}")


def all_grants() -> list[tuple[str, str]]:
    return [
        (item.code, action)
        for item in list_permission_resources()
        for action in item.actions
    ]
