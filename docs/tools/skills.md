# Skills

Skills are extensions that provide specialized capabilities for specific tasks. They are installed from GitHub repositories and automatically advertised to the AI when relevant.

## What are Skills?

Skills follow a progressive disclosure pattern:

1. **Advertise** - Skill names and descriptions are included in the system prompt (~100 tokens per skill)
2. **Load** - When needed, the full SKILL.md content is loaded (< 5000 tokens)
3. **Resources** - Supplementary files (templates, examples) are available when needed

## Skill Discovery Locations

Skills are discovered from two locations:

| Location | Path | Purpose |
|----------|------|---------|
| **Home** | `~/.janito/skills/` (or `<config_dir>/skills/`) | Global, user-installed skills |
| **Local** | `.janito/skills/` (in the current working directory) | Project-specific skills |

When a skill name exists in both locations, the **local** copy takes precedence, allowing project-specific skills to override globally installed ones.

Each skill tracks its own filesystem path, so resources are always loaded from the correct directory regardless of where the skill was discovered.

## Install a Skill

Install skills from GitHub repositories:

```bash
janito --install-skill https://github.com/user/repo/tree/main/skills/git-commit
```

Skills are installed to `~/.janito/skills/<skill-name>/`.

## List Installed Skills

```bash
janito --list-skills
```

## Uninstall a Skill

```bash
janito --uninstall-skill git-commit
```

## Available Tools

When a skill is installed, two tools become available:

| Tool | Description |
|------|-------------|
| `load_skill` | Load the full SKILL.md content for detailed instructions |
| `read_skill_resource` | Read supplementary files from the skill directory |

The AI automatically uses these tools when your request matches a skill's description.

## Skill Format

Skills are stored as directories containing:

```
<skills-dir>/<skill-name>/
├── SKILL.md          # Main skill documentation
└── resource-file.md  # Optional supplementary files
```

Where `<skills-dir>` is either `~/.janito/skills/` (home) or `.janito/skills/` (local).

### SKILL.md Format

A skill's SKILL.md should include:

- **Name and description** at the top
- **Overview** of what the skill does
- **Usage instructions** with examples
- **Best practices** and tips

## Example: Installing the Git Commit Skill

```bash
# Find a skills repository on GitHub
janito --install-skill https://github.com/joaompinto/janito/tree/main/skills/git-commit
```

## Tips

- Skills are automatically advertised based on your request
- The AI decides when to load a skill's full content
- Keep skill descriptions concise for efficient system prompts
- Use local skills (`.janito/skills/`) for project-specific overrides
