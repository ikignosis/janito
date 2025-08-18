# Janito Profiles

Janito supports predefined system prompts called "profiles" that help the AI understand the context and role it should play when responding to your requests.

## Available Profiles

### Developer Profile (`--developer` or `--profile developer`)

The default profile optimized for software development tasks. This profile:

- Focuses on code generation and debugging
- Provides access to Python tools and development utilities
- Emphasizes best practices and clean code
- Includes file system operations and code execution capabilities

**Usage:**
```bash
janito --developer "Create a REST API with FastAPI"
janito --profile developer "Debug this Python script"
```

### Market Analyst Profile (`--market` or `--profile market-analyst`)

A specialized profile for market analysis and business insights. This profile:

- Focuses on data analysis and market research
- Provides tools for web scraping and data processing
- Emphasizes business context and market trends
- Includes tools for generating reports and visualizations

**Usage:**
```bash
janito --market "Analyze stock market trends for tech companies"
janito --profile market-analyst "Scrape competitor pricing data"
```

## How Profiles Work

Profiles are implemented as Jinja2 templates that generate system prompts based on:

- The selected profile type
- Available tools and permissions
- Platform-specific configurations
- User preferences

When you use a profile, Janito automatically:

1. Loads the appropriate template
2. Injects relevant tool definitions
3. Sets up platform-specific configurations
4. Provides context-aware responses

## Custom Profiles

You can create custom profiles by adding system prompt files to:
```
~/.janito/profiles/
```

Each file should contain a plain text system prompt. The filename becomes the profile name.

**Example:**
```bash
# Create a custom profile
echo "You are a cybersecurity expert. Focus on security best practices, vulnerability analysis, and secure coding patterns." > ~/.janito/profiles/security-expert

# Use the custom profile
janito --profile security-expert "Review this code for security vulnerabilities"
```

## Profile Selection

### Command Line
Use `--profile <name>` to specify a profile:
```bash
janito --profile developer "Create a Python script"
janito --profile market-analyst "Analyze this data"
janito --profile security-expert "Review security"
```

### Shorthand Flags
Use convenience flags for built-in profiles:
```bash
janito --developer "Create a Python script"      # Same as --profile developer
janito --market "Analyze this data"              # Same as --profile market-analyst
```

### Interactive Mode
When starting Janito in interactive mode without specifying a profile, it defaults to the Developer profile.

## Profile Templates

Profile templates are located in:
```
janito/agent/templates/profiles/
├── system_prompt_template_developer.txt.j2
└── system_prompt_template_market_analyst.txt.j2
```

These templates use Jinja2 syntax and can include:

- Tool definitions
- Platform-specific configurations
- Dynamic content based on available tools
- Conditional logic for different environments

## Best Practices

1. **Use appropriate profiles**: Choose the profile that best matches your task type

2. **Create custom profiles**: For specialized domains, create custom profiles

3. **Combine with tools**: Profiles work best when combined with Janito's built-in tools

4. **Test and iterate**: Refine custom profiles based on results

## Troubleshooting

**Profile not found:**

- Ensure custom profiles are saved in `~/.janito/profiles/`
- Check file permissions and encoding (UTF-8 recommended)
- Verify the profile name matches the filename

**Profile not working as expected:**

- Use `janito --show-system-prompt --profile <name>` to inspect the generated prompt
- Check if tools are properly configured for your platform
- Review the profile template for any platform-specific conditions