# MCP Support

Janito4 supports the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) for extending functionality with custom tools and servers.

## What is MCP?

MCP is a protocol that allows AI models to connect to external tools and data sources. It provides a standardized way to:

- Discover available tools
- Execute tool calls
- Manage connections to multiple servers

## Available Commands

| Command | Description |
|---------|-------------|
| `/mcp add <name> stdio <command>` | Add a stdio transport service |
| `/mcp add <name> http <url>` | Add an HTTP transport service |
| `/mcp list` | List all configured services |
| `/mcp remove <name>` | Remove a service |

## Stdio Transport

Use stdio transport for local processes.

### Add a Stdio Service

```
/mcp add myserver stdio python -m mcp.server
```

### With Quoted Command

```
/mcp add myserver stdio "python -m mcp.server --port 5000"
```

## HTTP Transport

Use HTTP transport for remote servers.

### Add an HTTP Service

```
/mcp add remote http https://api.example.com/mcp
```

### With Headers

```
/mcp add remote http https://api.example.com/mcp --header Authorization:Bearer xxx
```

### Multiple Headers

```
/mcp add remote http https://api.example.com/mcp --header Authorization:Bearer xxx --header X-API-Key:yyy
```

## List Services

```
/mcp list
```

Shows all configured MCP services and their status.

## Remove a Service

```
/mcp remove myserver
```

## Configuration File

Services are stored in `~/.janito/mcp_services.json`.

### stdio Example

```json
{
  "services": {
    "myserver": {
      "transport": "stdio",
      "command": "python -m mcp.server",
      "env": {}
    }
  }
}
```

### HTTP Example

```json
{
  "services": {
    "remote": {
      "transport": "http",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer xxx"
      }
    }
  }
}
```

## Examples

### Filesystem MCP Server

```
/mcp add files stdio npx -y @modelcontextprotocol/server-filesystem /path/to/directory
```

### GitHub MCP Server

```
/mcp add github stdio npx -y @modelcontextprotocol/server-github
```

### HTTP API

```
/mcp add api http https://your-mcp-server.com/mcp --header Authorization:Bearer token123
```

## Tips

- **Start with stdio**: Local stdio servers are simpler to set up
- **Check service status**: Use `/mcp list` to see connected services
- **Remove unused**: Remove services you no longer need
- **Environment variables**: Some servers may need environment variables set in the command

## Troubleshooting

### Connection Failed

- Verify the command/URL is correct
- Check if the server is running
- For stdio, check if the command is in your PATH

### Service Not Responding

- Restart the service
- Check server logs
- Verify network connectivity (for HTTP)
