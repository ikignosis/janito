"""
Test for in-memory memory tools: store_memory and retrieve_memory.
"""

import types
import json
from janito.agent import tool_registry


class DummyFunction:
    def __init__(self, name, arguments):
        self.function = types.SimpleNamespace(
            name=name, arguments=json.dumps(arguments)
        )
        self.id = "dummy-id"


def test_memory_tool_registration():
    schemas = tool_registry.get_tool_schemas()
    tool_names = [s["function"]["name"] for s in schemas]
    assert "store_memory" in tool_names, "store_memory tool not registered"
    assert "retrieve_memory" in tool_names, "retrieve_memory tool not registered"


def test_store_and_retrieve_memory():
    # Store a value
    store_call = DummyFunction("store_memory", {"key": "foo", "value": "bar"})
    from janito.agent.tool_executor import ToolExecutor

    store_entry = tool_registry._tool_registry[store_call.function.name]
    store_result = ToolExecutor().execute(store_entry, store_call)
    assert "✅" in store_result, f"Unexpected store result: {store_result}"

    # Retrieve the value
    retrieve_call = DummyFunction("retrieve_memory", {"key": "foo"})
    retrieve_entry = tool_registry._tool_registry[retrieve_call.function.name]
    retrieve_result = ToolExecutor().execute(retrieve_entry, retrieve_call)
    assert "🔎" in retrieve_result, f"Unexpected retrieve result: {retrieve_result}"
    assert (
        "bar" in retrieve_result
    ), f"Value not found in retrieve result: {retrieve_result}"

    # Retrieve a missing key
    missing_call = DummyFunction("retrieve_memory", {"key": "notfound"})
    missing_entry = tool_registry._tool_registry[missing_call.function.name]
    missing_result = ToolExecutor().execute(missing_entry, missing_call)
    assert (
        "⚠️" in missing_result
    ), f"Expected warning for missing key, got: {missing_result}"
