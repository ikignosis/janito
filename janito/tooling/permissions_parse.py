from janito.tooling.tool_base import ToolPermissions


def parse_permissions_string(perm_str: str) -> ToolPermissions:
    """
    Parse a string like 'rwx', 'rw', 'r', etc. into a ToolPermissions object.
    """
    perm_str = perm_str.lower()
    return ToolPermissions(
        read="r" in perm_str,
        write="w" in perm_str,
        execute="x" in perm_str,
    )
