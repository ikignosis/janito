# Provider Configuration Reorganization

## Summary

Successfully reorganized provider-specific configuration from flat keys to a nested structure under `providers.<provider>`.

## Changes Made

### 1. Context Window Size (Max Tokens) Now Provider-Scoped

**Before:**
```json
{
  "context-window-size": 65536
}
```

**After:**
```json
{
  "providers": {
    "openai": {
      "model": "gpt-4",
      "endpoint": "https://api.openai.com/v1",
      "context-window-size": 65536
    },
    "anthropic": {
      "model": "claude-3-opus",
      "context-window-size": 100000
    }
  }
}
```

### 2. Updated Files

#### `janito/general_config.py`
- Added `context-window-size` to `PROVIDER_SCOPED_KEYS`
- Updated `load_context_window_size()` to accept optional `cli_provider` parameter
- Function now reads from nested structure: `providers.<provider>.context-window-size`

#### `janito/test_general_config.py`
- Updated `test_non_scoped_keys_unaffected` to use `provider` key instead
- Added `test_set_context_window_size_per_provider` - verifies per-provider storage
- Added `test_unset_context_window_size_per_provider` - verifies per-provider removal
- Updated `test_get_model_without_provider_errors` to set provider first

#### `janito/cli/handlers/config.py`
- Updated `handle_config_interactive()` to:
  - Pass `existing_provider` when loading context window size
  - Save context window size with provider parameter
  - Update confirmation message to show provider-scoped key

#### `janito/openai_client/client.py`
- Updated `send_prompt()` to get active provider and pass it to `load_context_window_size()`

#### `janito/web/backend/agent.py`
- Imported `get_active_provider`
- Updated `stream_prompt()` to pass provider to `load_context_window_size()`

#### `janito/shell/cmds/config.py`
- Updated `_print_config_info()` to pass provider to `load_context_window_size()`

### 3. Provider-Scoped Keys

All three keys are now provider-scoped:
1. `model` - Different models per provider
2. `endpoint` - Different endpoints per provider
3. `context-window-size` - Different max tokens per provider

### 4. CLI Usage

**Setting context window size:**
```bash
# Set for current provider (from config)
janito --set context-window-size=65536

# Set for specific provider
janito --provider openai --set context-window-size=65536
```

**Getting context window size:**
```bash
janito --get context-window-size
janito --provider openai --get context-window-size
```

**Interactive configuration:**
The `--config` command now saves context window size under the selected provider's namespace.

### 5. Backward Compatibility

**Breaking Change:** Old configurations with flat `context-window-size` at the root level will no longer be used. Users must manually migrate their configs to the new nested structure.

Example migration:
```json
// Old format (no longer supported)
{
  "context-window-size": 65536
}

// New format (required)
{
  "providers": {
    "openai": {
      "context-window-size": 65536
    }
  }
}
```

## Benefits

1. **Per-Provider Customization**: Each provider can have its own context window size limit
2. **Consistency**: All provider-specific settings now use the same nested structure
3. **Clarity**: Configuration is more organized and easier to understand
4. **Flexibility**: Different providers often have different token limits, and this structure supports that

## Testing

All tests pass, including:
- New tests for provider-scoped context window size
- Existing tests for model and endpoint provider scoping
- Integration tests for CLI commands
