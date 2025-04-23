import os
from janito.agent.profile_manager import AgentProfileManager
from janito.agent.runtime_config import unified_config
from janito.agent.config import get_api_key


def scan_project():
    prompt_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "agent",
            "templates",
            "detect_tech_prompt.j2",
        )
    )
    with open(prompt_path, "r", encoding="utf-8") as f:
        detect_prompt = f.read()
    api_key = get_api_key()
    model = unified_config.get("model")
    base_url = unified_config.get("base_url", "https://openrouter.ai/api/v1")
    azure_openai_api_version = unified_config.get(
        "azure_openai_api_version", "2023-05-15"
    )
    use_azure_openai = unified_config.get("use_azure_openai", False)
    profile_manager = AgentProfileManager(
        api_key=api_key,
        model=model,
        role=unified_config.get("role", "software engineer"),
        profile=unified_config.get("profile", "default"),
        interaction_mode=unified_config.get("interaction_mode", "prompt"),
        verbose_tools=True,
        base_url=base_url,
        azure_openai_api_version=azure_openai_api_version,
        use_azure_openai=use_azure_openai,
    )
    agent = profile_manager.agent
    from janito.agent.rich_message_handler import RichMessageHandler

    message_handler = RichMessageHandler()
    messages = [{"role": "system", "content": detect_prompt}]
    print("🔍 Scanning project for relevant tech/skills...")
    result = agent.chat(
        messages,
        message_handler=message_handler,
        spinner=True,
        max_rounds=50,
        verbose_response=False,
        verbose_events=False,
        stream=False,
    )
    os.makedirs(".janito", exist_ok=True)
    tech_txt = os.path.join(".janito", "tech.txt")
    with open(tech_txt, "w", encoding="utf-8") as f:
        f.write(result["content"].strip() + "\n")
    print(f"✅ Tech/skills detected and saved to {tech_txt}")
