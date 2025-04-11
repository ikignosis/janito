# /reload Command for Janito CLI Chat Shell

## Overview
The `/reload` command allows you to reload the system prompt from a file while running the interactive chat shell. This is useful for updating the agent's behavior or instructions without restarting the session.

## Usage
- `/reload` — Reloads the system prompt from the default prompt file.
- `/reload filename` — Reloads the system prompt from the specified file path.

## Behavior
- The command updates the agent's `system_prompt` attribute with the new prompt text.
- If a system message exists in the current conversation, its content is also updated.
- If the file cannot be found or loaded, an error message is displayed.

## Example
```
/reload
/reload my_custom_prompt.txt
```

## Implementation Notes
- The prompt file is read as plain text.
- The default prompt file path is set to the system prompt template used by Janito.
- The command is available in the interactive chat shell along with other commands like `/help`, `/system`, `/reset`, etc.
