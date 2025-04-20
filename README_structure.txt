- janito/agent/conversation.py: Refactored to remove generator/yield logic for streaming; now uses event-driven streaming and handles --verbose-stream directly in the OpenAI stream parsing.
- janito/cli/runner.py: Updated to remove iteration over streaming generator; all output is now handled by MessageHandler and/or the agent.
- janito/agent/profile_manager.py: Updated to forward verbose_stream argument to the agent.

Streaming is now fully event-driven, and --verbose-stream prints raw events as they are received from the OpenAI API.
