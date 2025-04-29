# Tool: memory

**Description:**
Store and retrieve values using a key-value memory for the session. Use this tool to remember information for later steps or requests, or to recall previously stored information.

## Usage
- To store a value: set action="store", provide a key and value.
- To retrieve a value: set action="retrieve", provide a key.

| Argument   | Type | Description                                 |
|------------|------|---------------------------------------------|
| action     | str  | Either "store" or "retrieve"                |
| key        | str  | The key to store/retrieve                   |
| value      | str  | The value to store (required for store)     |
| **Returns**| str  | Status message or retrieved value           |

## Examples

**Store a value:**
```
memory(action="store", key="username", value="alice")
```

**Retrieve a value:**
```
memory(action="retrieve", key="username")
```
