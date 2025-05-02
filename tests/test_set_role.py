import janito.agent.profile_manager
from janito.agent.profile_manager import AgentProfileManager


class DummyConversationHandler:
    def __init__(self, client, model):
        pass


# Patch ConversationHandler to avoid real OpenAI calls
janito.agent.profile_manager.ConversationHandler = DummyConversationHandler


# Dummy OpenAI client
class DummyOpenAI:
    def __init__(self, **kwargs):
        pass


janito.agent.profile_manager.OpenAI = DummyOpenAI

# Instantiate AgentProfileManager with dummy values
profile_manager = AgentProfileManager(
    api_key="dummy",
    model="gpt-3",
    role="initial role",
    profile_name="concise-technical",
    interaction_mode="chat",
    verbose_tools=False,
    base_url="http://localhost",
    azure_openai_api_version=None,
    use_azure_openai=False,
)

print(f"Role before: {profile_manager.role}")
profile_manager.set_role("new test role")
print(f"Role after: {profile_manager.role}")
