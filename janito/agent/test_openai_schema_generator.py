"""
Tests for OpenAISchemaGenerator class-based API.
"""

import pytest
from janito.agent.openai_schema_generator import OpenAISchemaGenerator


class DummyTool:
    """
    Dummy tool for testing.

    Args:
        foo (str): Foo parameter.
        bar (int): Bar parameter.
    Returns:
        The result as a string.
    """

    name = "dummy_tool"

    def run(self, foo: str, bar: int) -> str:
        """Run the dummy tool."""
        return f"{foo}-{bar}"


# Simulate decorator metadata for tests
DummyTool._tool_run_method = DummyTool().run
DummyTool._tool_name = DummyTool.name


def test_generate_schema_success():
    generator = OpenAISchemaGenerator()
    tool = DummyTool
    schema = generator.generate_schema(tool)
    assert schema["name"] == tool.name
    assert "foo" in schema["parameters"]["properties"]
    assert "bar" in schema["parameters"]["properties"]
    assert schema["parameters"]["properties"]["foo"]["type"] == "string"
    assert schema["parameters"]["properties"]["bar"]["type"] == "integer"
    assert schema["description"].startswith("Dummy tool for testing.")


def test_generate_schema_missing_type():
    class BadTool:
        """
        Args:
            foo (str): Foo parameter.
        Returns:
            String result.
        """

        name = "bad_tool"

        def run(self, foo):
            return str(foo)

    BadTool._tool_run_method = BadTool().run
    BadTool._tool_name = BadTool.name
    generator = OpenAISchemaGenerator()
    with pytest.raises(ValueError):
        generator.generate_schema(BadTool)


def test_generate_schema_missing_doc():
    class BadTool2:
        """
        Args:
            foo (str): Foo parameter.
        Returns:
            String result.
        """

        name = "bad_tool2"

        def run(self, foo: str, bar: int) -> str:
            return str(foo)

    BadTool2._tool_run_method = BadTool2().run
    BadTool2._tool_name = BadTool2.name
    generator = OpenAISchemaGenerator()
    with pytest.raises(ValueError):
        generator.generate_schema(BadTool2)


def test_generate_schema_requires_metadata():
    class NotRegisteredTool:
        def run(self, foo: str) -> str:
            return foo

    generator = OpenAISchemaGenerator()
    with pytest.raises(ValueError):
        generator.generate_schema(NotRegisteredTool)
