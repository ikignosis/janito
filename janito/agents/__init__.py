import os

SYSTEM_PROMPT = """I am Janito, your friendly software development buddy. I help you with coding tasks while being clear and concise in my responses."""

ai_backend = os.getenv('AI_BACKEND', 'claudeai').lower()

if ai_backend == 'openai':
    from .openai import OpenAIAgent as AIAgent
elif ai_backend == 'claudeai':
    from .claudeai import ClaudeAIAgent as AIAgent
else:
    raise ValueError(f"Unsupported AI_BACKEND: {ai_backend}")

# Create a singleton instance
agent = AIAgent(SYSTEM_PROMPT)

