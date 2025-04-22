from janito.agent.profile_manager import AgentProfileManager
import sys
from io import StringIO


def get_prompt(profile):
    mgr = AgentProfileManager(
        api_key="sk-test",
        model="gpt-test",
        role="software engineer",
        profile=profile,
        interaction_mode="chat",
        verbose_tools=False,
        base_url="https://test",
        azure_openai_api_version="2023-05-15",
        use_azure_openai=False,
    )
    return mgr.render_prompt()


def test_prompt_concise_technical():
    prompt = get_prompt("concise-technical")
    assert "Agent Profile:" in prompt
    assert "concise" in prompt.lower() or "direct" in prompt.lower()
    assert "Prioritizes validation" in prompt or "Technical Workflow" in prompt


def test_prompt_friendly_technical():
    prompt = get_prompt("friendly-technical")
    assert "Agent Profile:" in prompt
    assert "approachable" in prompt.lower() or "encouraging" in prompt.lower()
    assert "Prioritizes validation" in prompt or "Technical Workflow" in prompt


def test_prompt_formal_minimal():
    prompt = get_prompt("formal-minimal")
    assert "professional" in prompt.lower() or "precise tone" in prompt.lower()
    assert "performs only essential steps" in prompt.lower()


def test_prompt_inquisitive_exploratory():
    prompt = get_prompt("inquisitive-exploratory")
    assert (
        "asks clarifying questions" in prompt.lower()
        or "encourages user input" in prompt.lower()
    )
    assert (
        "hypothesis-driven exploration" in prompt.lower()
        or "documents findings" in prompt.lower()
    )


def test_prompt_invalid_profile_fallback():
    # Capture stderr to check for warning
    stderr = sys.stderr
    sys.stderr = StringIO()
    prompt = get_prompt("nonexistent-nonexistent")
    err = sys.stderr.getvalue()
    sys.stderr = stderr
    assert "Defaulting to: concise-technical" in err
    assert "concise" in prompt.lower() and "technical" in prompt.lower()
