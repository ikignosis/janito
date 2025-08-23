"""Security commands for managing allowed sites."""

from janito.cli.chat_mode.shell.commands.base import ShellCmdHandler as BaseCommand
from janito.tools.url_whitelist import get_url_whitelist_manager


class SecurityAllowedSitesCommand(BaseCommand):
    """Manage allowed sites for fetch_url tool."""

    def get_name(self) -> str:
        return "allowed-sites"

    def get_description(self) -> str:
        return "Manage allowed sites for the fetch_url tool"

    def get_usage(self):
        return (
            self.get_description()
            + """
Usage: /security allowed-sites [command] [site]

Commands:
  list                    List all allowed sites
  add <site>              Add a site to the whitelist
  remove <site>           Remove a site from the whitelist
  clear                   Clear all allowed sites (allow all)
  
Examples:
  /security allowed-sites list
  /security allowed-sites add tradingview.com
  /security allowed-sites remove yahoo.com
  /security allowed-sites clear
"""
        )
        return """
Usage: /security allowed-sites [command] [site]

Commands:
  list                    List all allowed sites
  add <site>              Add a site to the whitelist
  remove <site>           Remove a site from the whitelist
  clear                   Clear all allowed sites (allow all)
  
Examples:
  /security allowed-sites list
  /security allowed-sites add tradingview.com
  /security allowed-sites remove yahoo.com
  /security allowed-sites clear
"""

    def run(self):
        """Execute the allowed-sites command."""
        args = self.after_cmd_line.strip().split()

        if not args:
            print(self.get_usage())
            return

        command = args[0].lower()
        whitelist_manager = get_url_whitelist_manager()

        handlers = {
            "list": self._handle_list,
            "add": self._handle_add,
            "remove": self._handle_remove,
            "clear": self._handle_clear,
        }

        handler = handlers.get(command)
        if handler:
            handler(args, whitelist_manager)
        else:
            print(f"Error: Unknown command '{command}'")
            print(self.get_usage())

    def _handle_list(self, args, whitelist_manager):
        """Handle list command."""
        sites = whitelist_manager.get_allowed_sites()
        if sites:
            print("Allowed sites:")
            for site in sites:
                print(f"  • {site}")
        else:
            print("No sites are whitelisted (all sites are allowed)")

    def _handle_add(self, args, whitelist_manager):
        """Handle add command."""
        if len(args) < 2:
            print("Error: Please specify a site to add")
            return
        site = args[1]
        if whitelist_manager.add_allowed_site(site):
            print(f"✅ Added '{site}' to allowed sites")
        else:
            print(f"ℹ️ '{site}' is already in allowed sites")

    def _handle_remove(self, args, whitelist_manager):
        """Handle remove command."""
        if len(args) < 2:
            print("Error: Please specify a site to remove")
            return
        site = args[1]
        if whitelist_manager.remove_allowed_site(site):
            print(f"✅ Removed '{site}' from allowed sites")
        else:
            print(f"ℹ️ '{site}' was not in allowed sites")

    def _handle_clear(self, args, whitelist_manager):
        """Handle clear command."""
        whitelist_manager.clear_whitelist()
        print("✅ Cleared all allowed sites (all sites are now allowed)")
