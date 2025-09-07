def check_tools_registry():
    # Import and use the singleton tools adapter instance
    from janito.plugins.tools.local import local_tools_adapter

    print("Available tool names:", local_tools_adapter.list_tools())
    print(
        "Available tool classes:",
        [cls.__name__ for cls in local_tools_adapter.get_tool_classes()],
    )
    print(
        "Available tool instances:",
        [tool.name for tool in local_tools_adapter.get_tools()],
    )


if __name__ == "__main__":
    check_tools_registry()
