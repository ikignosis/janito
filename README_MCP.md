# MCP (Model Context Protocol) Services

Janito4 supports MCP services with two transport types: **stdio** (for local processes) and **http** (for remote servers).

## Command Reference

| Command | Description |
|---------|-------------|
| `/mcp add <name> stdio <command>` | Add a stdio transport service |
| `/mcp add <name> http <url>` | Add an HTTP transport service |
| `/mcp list` | List all configured services |
| `/mcp remove <name>` | Remove a service |

## Examples

### Add a stdio service

```
/mcp add myserver stdio python -m mcp.server
```

### Add a stdio service with quoted command

```
/mcp add myserver stdio "python -m mcp.server --port 5000"
```

### Add an HTTP service

```
/mcp add remote http https://api.example.com/mcp
```

### Add an HTTP service with headers

```
/mcp add remote http https://api.example.com/mcp --header Authorization:Bearer xxx
```

### List all services

```
/mcp list
```

### Remove a service

```
/mcp remove myserver
```

## Configuration

Services are stored in `~/.janito/mcp_services.json`.

### stdio transport

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

### http transport

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

## Multiple Headers

```
/mcp add remote http https://api.example.com/mcp --header Authorization:Bearer xxx --header X-API-Key:yyy
```

Resulting JSON:

```json
{
  "services": {
    "remote": {
      "transport": "http",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer xxx",
        "X-API-Key": "yyy"
      }
    }
  }
}
```
