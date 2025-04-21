- janito/agent/conversation.py: Refactored to remove generator/yield logic for streaming; now uses event-driven streaming and handles --verbose-stream directly in the OpenAI stream parsing.
- janito/cli/runner.py: Updated to remove iteration over streaming generator; all output is now handled by MessageHandler and/or the agent.
- janito/agent/profile_manager.py: Updated to forward verbose_stream argument to the agent.
- janito/agent/templates/profiles/system_prompt_template_base.j2: Now conditionally renders a tech section if janito/tech.txt exists, otherwise warns and omits the section.

Streaming is now fully event-driven, and --verbose-stream prints raw events as they are received from the OpenAI API.
