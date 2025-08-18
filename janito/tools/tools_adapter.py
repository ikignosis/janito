from janito.tools.tool_base import ToolBase
from janito.tools.tool_events import ToolCallStarted, ToolCallFinished, ToolCallError
from janito.exceptions import ToolCallException
from janito.tools.tool_base import ToolPermissions


class ToolsAdapterBase:
    """
    Composable entry point for tools management and provisioning in LLM pipelines.
    This class represents an external or plugin-based provider of tool definitions.
    Extend and customize this to load, register, or serve tool implementations dynamically.
    After refactor, also responsible for tool execution.
    """

    def __init__(self, tools=None, event_bus=None):
        self._tools = tools or []
        self._event_bus = event_bus  # event bus can be set on all adapters
        self.verbose_tools = False

    def set_verbose_tools(self, value: bool):
        self.verbose_tools = value

    @property
    def event_bus(self):
        return self._event_bus

    @event_bus.setter
    def event_bus(self, bus):
        self._event_bus = bus

    def is_tool_allowed(self, tool):
        """Check if a tool is allowed based on current global AllowedPermissionsState."""
        from janito.tools.permissions import get_global_allowed_permissions

        allowed_permissions = get_global_allowed_permissions()
        perms = tool.permissions  # permissions are mandatory and type-checked
        # If all permissions are False, block all tools
        if not (
            allowed_permissions.read
            or allowed_permissions.write
            or allowed_permissions.execute
        ):
            return False
        for perm in ["read", "write", "execute"]:
            if getattr(perms, perm) and not getattr(allowed_permissions, perm):
                return False
        return True

    def get_tools(self):
        """Return the list of enabled tools managed by this provider, filtered by allowed permissions and disabled tools."""
        from janito.tools.disabled_tools import is_tool_disabled

        tools = [
            tool
            for tool in self._tools
            if self.is_tool_allowed(tool)
            and not is_tool_disabled(getattr(tool, "tool_name", str(tool)))
        ]
        return tools

    def set_allowed_permissions(self, allowed_permissions):
        """Set the allowed permissions at runtime. This now updates the global AllowedPermissionsState only."""
        from janito.tools.permissions import set_global_allowed_permissions

        set_global_allowed_permissions(allowed_permissions)

    def add_tool(self, tool):
        self._tools.append(tool)

    def _validate_arguments_against_schema(self, arguments: dict, schema: dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        missing = [field for field in required if field not in arguments]
        if missing:
            return f"Missing required argument(s): {', '.join(missing)}"
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        for key, value in arguments.items():
            if key not in properties:
                continue
            expected_type = properties[key].get("type")
            if expected_type and expected_type in type_map:
                if not isinstance(value, type_map[expected_type]):
                    return f"Argument '{key}' should be of type '{expected_type}', got '{type(value).__name__}'"
        return None

    def execute(self, tool, *args, **kwargs):

        if self.verbose_tools:
            print(
                f"[tools-adapter] [execute] Executing tool: {getattr(tool, 'tool_name', repr(tool))} with args: {args}, kwargs: {kwargs}"
            )
        if isinstance(tool, ToolBase):
            tool.event_bus = self._event_bus
        result = None
        if callable(tool):
            result = tool(*args, **kwargs)
        elif hasattr(tool, "execute") and callable(getattr(tool, "execute")):
            result = tool.execute(*args, **kwargs)
        elif hasattr(tool, "run") and callable(getattr(tool, "run")):
            result = tool.run(*args, **kwargs)
        else:
            raise ValueError("Provided tool is not executable.")

        return result

    def _get_tool_callable(self, tool):
        """Helper to retrieve the primary callable of a tool instance."""
        if callable(tool):
            return tool
        if hasattr(tool, "execute") and callable(getattr(tool, "execute")):
            return getattr(tool, "execute")
        if hasattr(tool, "run") and callable(getattr(tool, "run")):
            return getattr(tool, "run")
        raise ValueError("Provided tool is not executable.")

    def _validate_arguments_against_signature(self, func, arguments: dict):
        """Validate provided arguments against a callable signature.

        Returns an error string if validation fails, otherwise ``None``.
        """
        import inspect

        if arguments is None:
            arguments = {}
        # If arguments are provided as a non-dict (e.g. a list or a scalar)
        # we skip signature *keyword* validation completely and defer the
        # decision to Python's own call mechanics when the function is
        # eventually invoked.  This allows positional / variadic arguments to
        # be supplied by callers that intentionally bypass the structured
        # JSON-schema style interface.
        if not isinstance(arguments, dict):
            # Nothing to validate at this stage – treat as OK.
            return None

        sig = inspect.signature(func)
        params = sig.parameters

        # Check for unexpected arguments (unless **kwargs is accepted)
        accepts_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        if not accepts_kwargs:
            unexpected = [k for k in arguments.keys() if k not in params]
            if unexpected:
                # Build detailed error message with received arguments
                error_parts = [
                    "Unexpected argument(s): " + ", ".join(sorted(unexpected))
                ]
                error_parts.append(
                    "Valid parameters: " + ", ".join(sorted(params.keys()))
                )
                error_parts.append("Arguments received:")
                for key, value in arguments.items():
                    error_parts.append(
                        f"  {key}: {repr(value)} ({type(value).__name__})"
                    )
                return "\n".join(error_parts)

        # Check for missing required arguments (ignoring *args / **kwargs / self)
        required_params = [
            name
            for name, p in params.items()
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
            and p.default is inspect._empty
            and name != "self"
        ]
        missing = [name for name in required_params if name not in arguments]
        if missing:
            # Build detailed error message with received arguments
            error_parts = [
                "Missing required argument(s): " + ", ".join(sorted(missing))
            ]
            error_parts.append("Arguments received:")
            if isinstance(arguments, dict):
                for key, value in arguments.items():
                    error_parts.append(
                        f"  {key}: {repr(value)} ({type(value).__name__})"
                    )
            elif arguments is not None:
                error_parts.append(f"  {repr(arguments)} ({type(arguments).__name__})")
            else:
                error_parts.append("  None")
            return "\n".join(error_parts)

        return None

    def execute_by_name(
        self, tool_name: str, *args, request_id=None, arguments=None, **kwargs
    ):
        self._check_tool_permissions(tool_name, request_id, arguments)
        tool = self.get_tool(tool_name)
        self._ensure_tool_exists(tool, tool_name, request_id, arguments)
        func = self._get_tool_callable(tool)

        validation_error = self._validate_tool_arguments(
            tool, func, arguments, tool_name, request_id
        )
        if validation_error:
            return validation_error

        # --- SECURITY: Path restriction enforcement ---
        if not getattr(self, "unrestricted_paths", False):
            workdir = getattr(self, "workdir", None)
            # Ensure workdir is always set; default to current working directory.
            if not workdir:
                import os

                workdir = os.getcwd()
            from janito.tools.path_security import (
                validate_paths_in_arguments,
                PathSecurityError,
            )

            schema = getattr(tool, "schema", None)
            # Only validate paths for dictionary-style arguments
            if isinstance(arguments, dict):
                try:
                    validate_paths_in_arguments(arguments, workdir, schema=schema)
                except PathSecurityError as sec_err:
                    # Publish both a ToolCallError and a user-facing ReportEvent for path security errors
                    self._publish_tool_call_error(
                        tool_name, request_id, str(sec_err), arguments
                    )
                    if self._event_bus:
                        from janito.report_events import (
                            ReportEvent,
                            ReportSubtype,
                            ReportAction,
                        )

                        self._event_bus.publish(
                            ReportEvent(
                                subtype=ReportSubtype.ERROR,
                                message=f"[SECURITY] Path access denied: {sec_err}",
                                action=ReportAction.EXECUTE,
                                tool=tool_name,
                                context={
                                    "arguments": arguments,
                                    "request_id": request_id,
                                },
                            )
                        )
                    return f"Security error: {sec_err}"
        # --- END SECURITY ---

        self._publish_tool_call_started(tool_name, request_id, arguments)
        self._print_verbose(
            f"[tools-adapter] Executing tool: {tool_name} with arguments: {arguments}"
        )
        try:
            # Normalize arguments to ensure proper type handling
            normalized_args = self._normalize_arguments(arguments, tool, func)

            if isinstance(normalized_args, (list, tuple)):
                # Positional arguments supplied as an array → expand as *args
                result = self.execute(tool, *normalized_args, **kwargs)
            elif isinstance(normalized_args, dict) or normalized_args is None:
                # Keyword-style arguments (the default) – pass as **kwargs
                result = self.execute(tool, **(normalized_args or {}), **kwargs)
            else:
                # Single positional argument (scalar/str/int/…)
                result = self.execute(tool, normalized_args, **kwargs)
        except Exception as e:
            # Handle exception and return error message instead of raising
            error_result = self._handle_execution_error(
                tool_name, request_id, e, arguments
            )
            if error_result is not None:
                return error_result
            # If _handle_execution_error returns None, re-raise
            raise
        self._print_verbose(
            f"[tools-adapter] Tool execution finished: {tool_name} -> {result}"
        )
        self._publish_tool_call_finished(tool_name, request_id, result)
        return result

    def _validate_tool_arguments(self, tool, func, arguments, tool_name, request_id):
        sig_error = self._validate_arguments_against_signature(func, arguments)
        if sig_error:
            self._publish_tool_call_error(tool_name, request_id, sig_error, arguments)
            return sig_error
        schema = getattr(tool, "schema", None)
        if schema and arguments is not None:
            validation_error = self._validate_arguments_against_schema(
                arguments, schema
            )
            if validation_error:
                self._publish_tool_call_error(
                    tool_name, request_id, validation_error, arguments
                )
                return validation_error
        return None

    def _publish_tool_call_error(self, tool_name, request_id, error, arguments):
        if self._event_bus:
            self._event_bus.publish(
                ToolCallError(
                    tool_name=tool_name,
                    request_id=request_id,
                    error=error,
                    arguments=arguments,
                )
            )

    def _publish_tool_call_started(self, tool_name, request_id, arguments):
        if self._event_bus:
            self._event_bus.publish(
                ToolCallStarted(
                    tool_name=tool_name, request_id=request_id, arguments=arguments
                )
            )

    def _publish_tool_call_finished(self, tool_name, request_id, result):
        if self._event_bus:
            self._event_bus.publish(
                ToolCallFinished(
                    tool_name=tool_name, request_id=request_id, result=result
                )
            )

    def _print_verbose(self, message):
        if self.verbose_tools:
            print(message)

    def _normalize_arguments(self, arguments, tool, func):
        """
        Normalize arguments to ensure proper type handling at the adapter level.

        This handles cases where:
        1. String is passed instead of list for array parameters
        2. JSON string parsing issues
        3. Other type mismatches that can be automatically resolved
        """
        import inspect
        import json

        # If arguments is already a dict or None, return as-is
        if isinstance(arguments, dict) or arguments is None:
            return arguments

        # If arguments is a list/tuple, return as-is (positional args)
        if isinstance(arguments, (list, tuple)):
            return arguments

        # Handle string arguments
        if isinstance(arguments, str):
            # Try to parse as JSON if it looks like JSON
            stripped = arguments.strip()
            if (stripped.startswith("{") and stripped.endswith("}")) or (
                stripped.startswith("[") and stripped.endswith("]")
            ):
                try:
                    parsed = json.loads(arguments)
                    return parsed
                except json.JSONDecodeError:
                    # If it looks like JSON but failed, try to handle common issues
                    pass

            # Check if the function expects a list parameter
            try:
                sig = inspect.signature(func)
                params = list(sig.parameters.values())

                # Skip 'self' parameter for methods
                if len(params) > 0 and params[0].name == "self":
                    params = params[1:]

                # If there's exactly one parameter that expects a list, wrap string in list
                if len(params) == 1:
                    param = params[0]
                    annotation = param.annotation

                    # Check if annotation is list[str] or similar
                    if (
                        hasattr(annotation, "__origin__")
                        and annotation.__origin__ is list
                    ):
                        return [arguments]
                    elif (
                        str(annotation).startswith("list[") or str(annotation) == "list"
                    ):
                        return [arguments]

            except (ValueError, TypeError):
                pass

        # Return original arguments for other cases
        return arguments

    def execute_function_call_message_part(self, function_call_message_part):
        """
        Execute a FunctionCallMessagePart by extracting the tool name and arguments and dispatching to execute_by_name.
        """
        import json

        function = getattr(function_call_message_part, "function", None)
        tool_call_id = getattr(function_call_message_part, "tool_call_id", None)
        if function is None or not hasattr(function, "name"):
            raise ValueError(
                "FunctionCallMessagePart does not contain a valid function object."
            )
        tool_name = function.name
        arguments = function.arguments
        # Parse arguments if they are a JSON string
        if isinstance(arguments, str):
            try:
                # Try to parse as JSON first
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                # Handle single quotes in JSON strings
                try:
                    # Replace single quotes with double quotes for JSON compatibility
                    fixed_json = arguments.replace("'", '"')
                    arguments = json.loads(fixed_json)
                except (json.JSONDecodeError, ValueError):
                    # If it's a string that looks like it might be a single path parameter,
                    # try to handle it gracefully
                    if arguments.startswith("{") and arguments.endswith("}"):
                        # Looks like JSON but failed to parse - this is likely an error
                        pass
                    else:
                        # Single string argument - let the normalization handle it
                        pass
        if self.verbose_tools:
            print(
                f"[tools-adapter] Executing FunctionCallMessagePart: tool={tool_name}, arguments={arguments}, tool_call_id={tool_call_id}"
            )
        return self.execute_by_name(
            tool_name, request_id=tool_call_id, arguments=arguments
        )

    def _check_tool_permissions(self, tool_name, request_id, arguments):
        # No enabled_tools check anymore; permission checks are handled by is_tool_allowed
        pass

    def _ensure_tool_exists(self, tool, tool_name, request_id, arguments):
        if tool is None:
            error_msg = f"Tool '{tool_name}' not found in registry."
            if self._event_bus:
                self._event_bus.publish(
                    ToolCallError(
                        tool_name=tool_name,
                        request_id=request_id,
                        error=error_msg,
                        arguments=arguments,
                    )
                )
            raise ToolCallException(tool_name, error_msg, arguments=arguments)

    def _handle_execution_error(self, tool_name, request_id, exception, arguments):
        # Check if this is a loop protection error that should trigger a new strategy
        if isinstance(exception, RuntimeError) and "Loop protection:" in str(exception):
            error_msg = str(exception)
            if self._event_bus:
                self._event_bus.publish(
                    ToolCallError(
                        tool_name=tool_name,
                        request_id=request_id,
                        error=error_msg,
                        exception=exception,
                        arguments=arguments,
                    )
                )
            # Return the loop protection message as string to trigger new strategy
            return f"Loop protection triggered - requesting new strategy: {error_msg}"

        # Check if this is a string return from loop protection (new behavior)
        if isinstance(exception, str) and "Loop protection:" in exception:
            error_msg = str(exception)
            if self._event_bus:
                self._event_bus.publish(
                    ToolCallError(
                        tool_name=tool_name,
                        request_id=request_id,
                        error=error_msg,
                        arguments=arguments,
                    )
                )
            return f"Loop protection triggered - requesting new strategy: {error_msg}"

        error_msg = f"Exception during execution of tool '{tool_name}': {exception}"
        if self._event_bus:
            self._event_bus.publish(
                ToolCallError(
                    tool_name=tool_name,
                    request_id=request_id,
                    error=error_msg,
                    exception=exception,
                    arguments=arguments,
                )
            )
        raise ToolCallException(
            tool_name, error_msg, arguments=arguments, exception=exception
        )

    def get_tool(self, tool_name):
        """Abstract method: implement in subclass to return tool instance by name"""
        raise NotImplementedError()
