import os


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
            cls._instance = AIAgent(system_prompt="You are a helpful assistant.")
        return cls._instance

