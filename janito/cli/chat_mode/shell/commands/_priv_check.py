from janito.tooling.permissions import get_global_allowed_permissions


def user_has_any_privileges():
    perms = get_global_allowed_permissions()
    return perms.read or perms.write or perms.execute
