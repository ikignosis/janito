from janito.cli.console import shared_console
from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler


class ToolsShellHandler(ShellCmdHandler):
    help_text = "List available tools"

    def _perm_class(self, perms):
        if perms.execute:
            if perms.read and perms.write:
                return "read-write-execute"
            elif perms.read:
                return "read-execute"
            elif perms.write:
                return "write-execute"
            else:
                return "execute-only"
        elif perms.read and perms.write:
            return "read-write"
        elif perms.read:
            return "read-only"
        elif perms.write:
            return "write-only"
        else:
            return "none"

    def _group_tools_by_permission(self, tools, tool_instances):
        perm_groups = {}
        for tool in tools:
            inst = tool_instances.get(tool, None)
            perms = getattr(inst, "permissions", None)
            if not perms:
                group = "unknown"
            else:
                group = self._perm_class(perms)
            perm_groups.setdefault(group, []).append(tool)
        return perm_groups

    def _print_tools_table(self, perm_groups):
        from rich.table import Table

        table = Table(title="Tools by Permission Class")
        table.add_column("Permission Type", style="cyan", no_wrap=True)
        table.add_column("Tools", style="magenta")
        for group, tool_list in sorted(perm_groups.items()):
            table.add_row(group, " ".join(sorted(tool_list)))
        shared_console.print(table)

    def _find_exec_tools(self, registry):
        exec_tools = []
        for tool_instance in registry.get_tools():
            perms = getattr(tool_instance, "permissions", None)
            if perms and perms.execute:
                exec_tools.append(tool_instance.tool_name)
        return exec_tools

    def run(self):
        # Check for no_tools_mode in shell_state
        if self.shell_state and getattr(self.shell_state, "no_tools_mode", False):
            shared_console.print(
                "[yellow]No tools are available in this mode (no tools, no context).[/yellow]"
            )
            return
        try:
            import janito.tools  # Ensure all tools are registered
            from janito.tools.permissions import get_global_allowed_permissions

            registry = janito.tools.get_local_tools_adapter()
            tools = registry.list_tools()
            shared_console.print("Registered tools:")
            tool_instances = {t.tool_name: t for t in registry.get_tools()}
            if not tools:
                shared_console.print(
                    "No tools are enabled under the current permission settings."
                )
                return
            perm_groups = self._group_tools_by_permission(tools, tool_instances)
            self._print_tools_table(perm_groups)
            exec_tools = self._find_exec_tools(registry)
            perms = get_global_allowed_permissions()
            if not perms.execute and exec_tools:
                shared_console.print(
                    "[yellow]⚠️  Warning: Execution tools (e.g., commands, code execution) are disabled. Use -x to enable them.[/yellow]"
                )
        except Exception as e:
            shared_console.print(f"[red]Error loading tools: {e}[/red]")
