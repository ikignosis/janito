import os

SYSTEM_PROMPT = """I am Janito, your friendly software development buddy. I help you with coding tasks while being clear and concise in my responses."""

ai_backend = os.getenv('AI_BACKEND', 'claudeai').lower()

if ai_backend == 'openai':
    from .openai import OpenAIAgent as AIAgent
elif ai_backend == 'claudeai':
    from .claudeai import ClaudeAIAgent as AIAgent
else:
    raise ValueError(f"Unsupported AI_BACKEND: {ai_backend}")

class AgentSingleton:
    _instance = None

    @classmethod
    def get_agent(cls):
        if cls._instance is None:
            cls._instance = AIAgent(SYSTEM_PROMPT)
        return cls._instance

