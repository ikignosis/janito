import inspect
import typing
from collections import OrderedDict
from typing import List
from janito.tooling.tools_schema import ToolSchemaBase


class OpenAISchemaGenerator(ToolSchemaBase):
    PYTHON_TYPE_TO_JSON = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    def type_to_json_schema(self, annotation):
        if hasattr(annotation, "__origin__"):
            if annotation.__origin__ is list or annotation.__origin__ is typing.List:
                return {
                    "type": "array",
                    "items": self.type_to_json_schema(annotation.__args__[0]),
                }
            if annotation.__origin__ is dict or annotation.__origin__ is typing.Dict:
                return {"type": "object"}
        return {"type": self.PYTHON_TYPE_TO_JSON.get(annotation, "string")}

    def generate_schema(self, tool_class):
        # DEBUG: Print class and .name for trace
        func, tool_name, sig, summary, param_descs, return_desc, description = (
            self.validate_tool_class(tool_class)
        )
        properties = OrderedDict()
        required = []
        # Removed tool_call_reason from properties and required
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            annotation = param.annotation
            pdesc = param_descs.get(name, "")
            schema = self.type_to_json_schema(annotation)
            schema["description"] = pdesc
            properties[name] = schema
            if param.default == inspect._empty:
                required.append(name)
        return {
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


def generate_tool_schemas(tool_classes: List[type]):
    generator = OpenAISchemaGenerator()
    return [
        {"type": "function", "function": generator.generate_schema(tool_class)}
        for tool_class in tool_classes
    ]
