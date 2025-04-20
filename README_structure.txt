# README_structure.txt (excerpt)

- system_prompt_template_allcommit.j2: Feature extension template for 'allcommit' (extends main style). Now instructs: "After each step which does a change, perform git commit with a clear message describing what was changed."
- janito/agent/templates/profiles/system_prompt_template_base.j2: Updated to instruct: "After each step which does a change, perform git commit. Check the git diff and summarize the changes in the commit message."

All commit-related instructions now explicitly require a git commit after each step which does a change.- Updated quick action message in .\janito\cli_chat_shell\ui.py to: "Quick action: Press F12 to continue. Make sure to double-check the suggested changes first. 😊"- Changed quick action message in .\janito\cli_chat_shell\ui.py to: "Quick action: Press F12 to continue. Double-check the suggested action first. 😊"- Enhanced <platform> section in system_prompt_template_base.j2 to explicitly recommend attention to platform-specific path conventions and command syntax (Windows vs. Unix).- Updated render_prompt.py to collect and pass python_version and shell_info to prompt templates.
- Enhanced <platform> section in system_prompt_template_base.j2 to display Platform, Python version, and Shell/Environment, with explicit guidance for cross-platform and shell compatibility.- janito/cli/arg_parser.py: Added --verbose-stream CLI option to print raw OpenAI chunks as they are fetched.
- janito/cli/runner.py: Updated streaming logic to print repr(chunk) if --verbose-stream is set.
- janito/agent/tools/replace_text_in_file.py: Success log no longer includes backup file path; only the returned message does.
