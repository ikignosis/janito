import os

SYSTEM_PROMPT = """I am Janito, your friendly software development buddy. I help you with coding tasks while being clear and concise in my responses."""

# Try to determine backend from available API keys if not explicitly set
ai_backend = os.getenv('AI_BACKEND', '').lower()

if not ai_backend:
    if os.getenv('ANTHROPIC_API_KEY'):
        ai_backend = 'claudeai'
    elif os.getenv('DEEPSEEK_API_KEY'):
        ai_backend = 'deepseekai'
    elif os.getenv('OPENAI_API_KEY'):
        ai_backend = 'openai'
    else:
        raise ValueError("No AI backend API keys found. Please set either ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, or OPENAI_API_KEY")

if ai_backend == 'openai':
    import warnings
    warnings.warn(
        "Using deprecated OpenAI backend. Please switch to Claude AI backend by removing AI_BACKEND=openai "
        "from your environment variables.",
        DeprecationWarning,
        stacklevel=2
    )
    from .openai import OpenAIAgent as AIAgent
elif ai_backend == "deepseekai":
    from .deepseekai import DeepSeekAIAgent as AIAgent
elif ai_backend == 'claudeai':
    from .claudeai import ClaudeAIAgent as AIAgent
else:
    raise ValueError(f"Unsupported AI_BACKEND: {ai_backend}")

# Create a singleton instance
agent = AIAgent(SYSTEM_PROMPT)