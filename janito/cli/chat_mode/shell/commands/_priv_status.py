from janito.tooling.permissions import get_global_allowed_permissions


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
