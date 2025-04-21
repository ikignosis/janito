# Prompt Profiles: TOML-based System Prompts

Janito now uses TOML files for all system prompt profiles and agent instructions. This replaces the previous Jinja2 template system.

## Key Points
- **Format:** All prompt profiles are written in TOML (`.toml`) files.
- **Variable Substitution:** Only flat (non-nested) variable substitution is supported, using Python's `string.Template` syntax (e.g., `${role}`).
- **Inheritance:** Profiles can extend a base profile using the `extends` key. The system merges sections from the base and the child.
- **No Jinja2:** Jinja2 templating and `.j2` files are no longer used or supported.
- **Location:** Prompt profiles are stored in `janito/agent/templates/profiles/`.

## Example
```toml
[agent_profile]
role = "${role}"
description = "Agent for analysis and development tool operating on files and directories using text-based operations."

[platform]
platform = "${platform}"
python_version = "${python_version}"
shell_info = "${shell_info}"
```

## Migration Notes
- Remove any `.j2` files and Jinja2 dependencies from your environment.
- Update any custom prompt profiles to TOML format.
- See the default and technical profiles in `janito/agent/templates/profiles/` for reference.
