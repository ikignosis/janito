Documentation structure for Janito (updated):

- docs/index.md: Main landing page with concise product description and feature list
- docs/guides/introduction.md: Project introduction, what Janito is, who it's for
- docs/guides/installation.md: Installation instructions (PyPI, source, requirements)
- docs/guides/using.md: Quickstart and basic usage guide
- docs/guides/using_tools.md: How Janito uses tools and tool selection
- docs/guides/prompt_profiles.md: System prompt profiles (TOML-based, replacing Jinja2)
- docs/guides/terminal_shell.md: Terminal shell features and commands
- docs/guides/costs.md: Costs and value transparency
- docs/guides/developing.md: Guide for contributors and developers
- docs/guides/USING_DEV_VERSION.md: Advanced usage and development environment setup
- docs/guides/why.md: Project motivation and background
- docs/guides/vs_webchats.md: Comparison with web-based chat agents
- docs/supported-models.md: Supported LLMs
- docs/alternatives.md: Alternative tools and approaches
- docs/reference/: Technical reference (architecture, configuration, CLI options, message handler model, tools reference)
- docs/meta/: Meta information (quality checks, developer readme)
- docs/imgs/: Images for documentation

Navigation in mkdocs.yml or sidebar config should reflect:
- Introduction
- Installation
- Using Janito (quickstart, usage, tools, terminal shell, costs)
- Developing & Extending
- Reference
- About (why, alternatives, vs webchats)
