from janito.agent.profile_manager import AgentProfileManager


def test_prompt_default(monkeypatch):
    mgr = AgentProfileManager(
        api_key="sk-test",
        model="gpt-test",
        role="software engineer",
        interaction_style="default",
        interaction_mode="chat",
        verbose_tools=False,
        base_url="https://test",
        azure_openai_api_version="2023-05-15",
        use_azure_openai=False,
    )
    prompt = mgr.render_prompt()
    assert "[agent_profile]" in prompt
    assert "software engineer" in prompt
    assert "[platform]" in prompt
    assert "Always pay careful attention" in prompt
    assert "[function_call_summary]" in prompt


def test_prompt_technical(monkeypatch):
    mgr = AgentProfileManager(
        api_key="sk-test",
        model="gpt-test",
        role="software engineer",
        interaction_style="technical",
        interaction_mode="chat",
        verbose_tools=False,
        base_url="https://test",
        azure_openai_api_version="2023-05-15",
        use_azure_openai=False,
    )
    prompt = mgr.render_prompt()
    assert "[agent_profile]" in prompt
    assert "strict adherence" in prompt
    assert "[technical_workflow]" in prompt
    assert "Enumerate and validate the current file system state" in prompt
    assert "[function_call_summary]" in prompt


def test_prompt_inheritance(monkeypatch):
    mgr = AgentProfileManager(
        api_key="sk-test",
        model="gpt-test",
        role="software engineer",
        interaction_style="technical",
        interaction_mode="chat",
        verbose_tools=False,
        base_url="https://test",
        azure_openai_api_version="2023-05-15",
        use_azure_openai=False,
    )
    prompt = mgr.render_prompt()
    # Should inherit context, analysis, etc. from base
    assert "[context]" in prompt
    assert "[analysis]" in prompt
    assert "[decision_policy]" in prompt
    assert "[finalization]" in prompt
