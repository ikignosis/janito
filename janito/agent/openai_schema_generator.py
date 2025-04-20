"""
MUST BE IMPLEMENTED:
- check that all params found in the signature have documentation in the docstring which is provided in the parameter schema doc
- the Return must be documented and integrated in the sechema description
- backward compatibility is not required
"""

import inspect
import re
import typing

PYTHON_TYPE_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _parse_docstring(docstring: str):
    """
    Parses a docstring to extract summary, parameter descriptions, and return description.
    Expects Google or NumPy style docstrings.
    Returns: summary, {param: description}, return_description
    """
    if not docstring:
        return "", {}, ""
    lines = docstring.strip().split("\n")
    summary = lines[0].strip()
    param_descs = {}
    return_desc = ""
    in_params = False
    in_returns = False
    for line in lines[1:]:
        stripped_line = line.strip()
        if stripped_line.lower().startswith(("args:", "parameters:")):
            in_params = True
            in_returns = False
            continue
        if stripped_line.lower().startswith("returns:"):
            in_returns = True
            in_params = False
            continue
        if in_params:
            m = re.match(
                r"([a-zA-Z_][a-zA-Z0-9_]*)(?: \(([^)]+)\))?: (.+)", stripped_line
            )
            if m:
                param, _, desc = m.groups()
                param_descs[param] = desc.strip()
            elif stripped_line and stripped_line[0] != "-":
                # Continuation of previous param
                if param_descs:
                    last = list(param_descs)[-1]
                    param_descs[last] += " " + stripped_line
        elif in_returns:
            if stripped_line:
                return_desc += (" " if return_desc else "") + stripped_line
    return summary, param_descs, return_desc


def _type_to_json_schema(tp):
    # Handle typing.Optional, typing.Union, typing.List, etc.
    origin = typing.get_origin(tp)
    args = typing.get_args(tp)
    if origin is None:
        return {"type": PYTHON_TYPE_TO_JSON.get(tp, "string")}
    if origin is list or origin is typing.List:
        item_type = args[0] if args else str
        return {"type": "array", "items": _type_to_json_schema(item_type)}
    if origin is dict or origin is typing.Dict:
        return {"type": "object"}
    if origin is typing.Union:
        # Optional[...] is Union[..., NoneType]
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _type_to_json_schema(non_none[0])
        # Otherwise, fallback
        return {"type": "string"}
    return {"type": "string"}


def generate_openai_function_schema(func, tool_name: str, tool_class=None):
    """
    Generates an OpenAI-compatible function schema for a callable.
    Raises ValueError if the return type is not explicitly str.
    """
    sig = inspect.signature(func)
    # Enforce explicit str return type
    if sig.return_annotation is inspect._empty or sig.return_annotation is not str:
        raise ValueError(
            f"Tool '{tool_name}' must have an explicit return type of 'str'. Found: {sig.return_annotation}"
        )
    docstring = func.__doc__
    summary, param_descs, _ = _parse_docstring(docstring)
    # Prepend the tool class docstring if available
    class_doc = tool_class.__doc__.strip() if tool_class and tool_class.__doc__ else ""
    if class_doc:
        description = f"{class_doc}\n\n{summary}" if summary else class_doc
    else:
        description = summary
    # Check that all parameters in the signature have documentation
    undocumented = [
        name
        for name, param in sig.parameters.items()
        if name != "self" and name not in param_descs
    ]
    if undocumented:
        raise ValueError(
            f"Tool '{tool_name}' is missing docstring documentation for parameter(s): {', '.join(undocumented)}"
        )
    properties = {}
    required = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        annotation = param.annotation if param.annotation != inspect._empty else str
        pdesc = param_descs.get(name, "")
        schema = _type_to_json_schema(annotation)
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
