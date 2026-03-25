"""Tool and MCP listing CLI handlers."""

try:
    from ...tooling.tools_registry import get_all_tool_schemas, get_all_tool_permissions
    from ...mcp_config import list_services, MCP_CONFIG_PATH
    from ...mcp_manager import get_mcp_manager
except ImportError:
    from janito4.tooling.tools_registry import get_all_tool_schemas, get_all_tool_permissions
    from janito4.mcp_config import list_services, MCP_CONFIG_PATH
    from janito4.mcp_manager import get_mcp_manager


def handle_list_tools(args) -> int:
    """Handle --list-tools command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success)
    """
    # Add gmail toolset if --gmail flag is set
    if getattr(args, 'gmail', False):
        try:
            from ...tooling.tools_registry import add_toolset
        except ImportError:
            from janito4.tooling.tools_registry import add_toolset
        add_toolset("gmail")
    
    # Add onedrive toolset if --onedrive flag is set
    if getattr(args, 'onedrive', False):
        try:
            from ...tooling.tools_registry import add_toolset
        except ImportError:
            from janito4.tooling.tools_registry import add_toolset
        add_toolset("onedrive")
    
    schemas = get_all_tool_schemas()
    permissions = get_all_tool_permissions()
    
    print("Available Tools:")
    print("=" * 60)
    
    # Group tools by category based on name prefixes
    categories = {
        "File Operations": [],
        "System Operations": [],
        "Email Operations": [],
        "OneDrive Operations": [],
        "Other": []
    }
    
    for schema in schemas:
        func_info = schema['function']
        name = func_info['name']
        perms = permissions.get(name, "")
        
        # Get parameter names only
        params = func_info['parameters']['properties']
        param_names = list(params.keys())
        
        tool_info = {
            'name': name,
            'permissions': perms,
            'params': param_names
        }
        
        if name.startswith(('Create', 'Delete', 'List', 'Read', 'Remove', 'Replace', 'Search', 'Move')) and 'Email' not in name and 'OneDrive' not in name:
            categories["File Operations"].append(tool_info)
        elif name.startswith(('Get', 'Run')):
            categories["System Operations"].append(tool_info)
        elif name.startswith(('Send', 'Read', 'Compose', 'SearchEmail')) or 'Email' in name:
            categories["Email Operations"].append(tool_info)
        elif 'OneDrive' in name:
            categories["OneDrive Operations"].append(tool_info)
        else:
            categories["Other"].append(tool_info)
    
    # Display tools by category
    for category, tools_list in categories.items():
        if tools_list:
            print(f"\n{category}:")
            print("-" * 40)
            
            for tool in sorted(tools_list, key=lambda x: x['name']):
                perms_str = f" [{tool['permissions']}]" if tool['permissions'] else ""
                params_str = f" ({', '.join(tool['params'])})" if tool['params'] else " (no params)"
                print(f"  {tool['name']}{perms_str}{params_str}")
    
    print(f"\nTotal: {len(schemas)} tools")
    print("\nPermission codes: r=read, w=write, x=execute")
    
    return 0


def handle_list_mcp(args) -> int:
    """Handle --list-mcp command.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        int: Exit code (0 for success)
    """
    services = list_services()
    
    print("MCP Services:")
    print("=" * 60)
    print(f"Config file: {MCP_CONFIG_PATH}")
    print()
    
    if not services:
        print("  No MCP services configured.")
        print()
        print("  Use /mcp add to configure MCP services in interactive mode")
    else:
        # Load MCP manager to get tools
        manager = get_mcp_manager()
        manager.load_services()
        
        for name, config in services.items():
            transport = config.get("transport", "unknown")
            connected = name in manager.connected_services
            status = "[connected]" if connected else "[not connected]"
            
            print(f"  {name} ({transport}) {status}")
            
            if connected:
                # Get tools for this service
                try:
                    # Refresh tools to get updated list
                    tools = manager.get_all_tools(force_refresh=True)
                    service_tools = [t for t in tools if t.get("function", {}).get("name", "").startswith(f"{name}_")]
                    
                    for tool in service_tools:
                        func = tool.get("function", {})
                        tool_name = func.get("name", "")
                        # Remove prefix for display
                        display_name = tool_name[len(name) + 1:] if tool_name else tool_name
                        desc = func.get("description", "")[:50]
                        print(f"    - {display_name}")
                        if desc:
                            print(f"      {desc}...")
                except Exception as e:
                    print(f"    Error loading tools: {e}")
            print()
        
        manager.unload_all()
    
    print("=" * 60)
    
    return 0
