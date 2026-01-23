import inspect
import typing
import re


class ToolSchemaBase:
    def parse_param_section(self, lines, param_section_headers):
        param_descs = {}
        in_params = False
        for line in lines:
            stripped_line = line.strip()
            if any(
                stripped_line.lower().startswith(h + ":") or stripped_line.lower() == h
                for h in param_section_headers
            ):
                in_params = True
                continue
            if in_params:
                m = re.match(
                    r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(([^)]+)\))?\s*[:\-]?\s*(.+)",
                    stripped_line,
                )
                if m:
                    param, _, desc = m.groups()
                    param_descs[param] = desc.strip()
                elif stripped_line and stripped_line[0] != "-":
                    if param_descs:
                        last = list(param_descs)[-1]
                        param_descs[last] += " " + stripped_line
            if (
                stripped_line.lower().startswith("returns:")
                or stripped_line.lower() == "returns"
            ):
                break
        return param_descs

    def parse_return_section(self, lines):
        in_returns = False
        return_desc = ""
        for line in lines:
            stripped_line = line.strip()
            if (
                stripped_line.lower().startswith("returns:")
                or stripped_line.lower() == "returns"
            ):
                in_returns = True
                continue
            if in_returns:
                if stripped_line:
                    return_desc += (" " if return_desc else "") + stripped_line
        return return_desc

    def parse_docstring(self, docstring: str):
        if not docstring:
            return "", {}, ""
        lines = docstring.strip().split("\n")
        summary = lines[0].strip()
        param_section_headers = ("args", "arguments", "params", "parameters")
        param_descs = self.parse_param_section(lines[1:], param_section_headers)
        return_desc = self.parse_return_section(lines[1:])
        return summary, param_descs, return_desc

    def validate_tool_class(self, tool_class):
        # Create instance to get tool_name property
        instance = tool_class()
        tool_name = instance.tool_name
        if not tool_name or not isinstance(tool_name, str):
            raise ValueError(
                "Tool class must have a valid 'tool_name' property for registry and schema generation."
            )
        if not hasattr(tool_class, "run") or not callable(getattr(tool_class, "run")):
            raise ValueError("Tool class must have a callable 'run' method.")
        run_func = tool_class.run
        sig = inspect.signature(run_func)
        if sig.return_annotation is inspect._empty or sig.return_annotation is not str:
            raise ValueError(
                f"Tool '{tool_name}' must have an explicit return type of 'str'. Found: {sig.return_annotation}"
            )
        missing_type_hints = [
            name
            for name, param in sig.parameters.items()
            if name != "self" and param.annotation is inspect._empty
        ]
        if missing_type_hints:
            raise ValueError(
                f"Tool '{tool_name}' is missing type hints for parameter(s): {', '.join(missing_type_hints)}.\nAll parameters must have explicit type hints for schema generation."
            )
        run_doc = (
            run_func.__doc__.strip() if run_func and run_func.__doc__ else ""
        )
        summary, param_descs, return_desc = self.parse_docstring(run_doc)
        description = summary
        if return_desc:
            description += f"\n\nReturns: {return_desc}"
        undocumented = [
            name
            for name, param in sig.parameters.items()
            if name != "self" and name not in param_descs
        ]
        if undocumented:
            raise ValueError(
                f"Tool '{tool_name}' is missing docstring documentation for parameter(s): {', '.join(undocumented)}.\nParameter documentation must be provided in the Tool class docstring, not the method docstring."
            )
        return run_func, tool_name, sig, summary, param_descs, return_desc, description
