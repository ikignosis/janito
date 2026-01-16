from janito.tooling.tool_base import ToolPermissions


class AllowedPermissionsState:
    _instance = None
    _permissions = ToolPermissions(read=False, write=False, execute=False)
    _default_permissions = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_permissions(cls):
        return cls._permissions

    @classmethod
    def set_permissions(cls, permissions):
        if not isinstance(permissions, ToolPermissions):
            raise ValueError("permissions must be a ToolPermissions instance")
        cls._permissions = permissions

    @classmethod
    def set_default_permissions(cls, permissions):
        if not isinstance(permissions, ToolPermissions):
            raise ValueError("permissions must be a ToolPermissions instance")
        cls._default_permissions = permissions

    @classmethod
    def get_default_permissions(cls):
        return cls._default_permissions


# Convenience functions


def get_global_allowed_permissions():
    return AllowedPermissionsState.get_permissions()


def set_global_allowed_permissions(permissions):
    AllowedPermissionsState.set_permissions(permissions)


def set_default_allowed_permissions(permissions):
    AllowedPermissionsState.set_default_permissions(permissions)


def get_default_allowed_permissions():
    return AllowedPermissionsState.get_default_permissions()


def user_has_any_privileges():
    perms = get_global_allowed_permissions()
    return perms.read or perms.write or perms.execute

def get_privilege_status_message():
    perms = get_global_allowed_permissions()
    if perms.read and perms.write:
        return "[cyan]Read-Write tools enabled[/cyan]"
    elif perms.read:
        return "[cyan]Read-Only tools enabled[/cyan]"
    elif perms.write:
        return "[cyan]Write-Only tools enabled[/cyan]"
    else:
        return "[yellow]No tool permissions enabled[/yellow]"
