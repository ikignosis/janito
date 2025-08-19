"""Jinja2 template syntax validator."""

import os
from janito.i18n import tr


def validate_jinja2(path: str) -> str:
    """Validate Jinja2 template syntax."""
    try:
        from jinja2 import Environment, TemplateSyntaxError

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Create a Jinja2 environment and try to parse the template
        env = Environment()
        try:
            env.parse(content)
            return tr("✅ Syntax OK")
        except TemplateSyntaxError as e:
            line_num = getattr(e, "lineno", 0)
            return tr(
                "⚠️ Warning: Syntax error: {error} at line {line}",
                error=str(e),
                line=line_num,
            )
        except Exception as e:
            return tr("⚠️ Warning: Syntax error: {error}", error=str(e))

    except ImportError:
        # If jinja2 is not available, just check basic structure
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Basic checks for common Jinja2 syntax issues
            open_tags = content.count("{%")
            close_tags = content.count("%}")
            open_vars = content.count("{{")
            close_vars = content.count("}}")

            if open_tags != close_tags:
                return tr("⚠️ Warning: Syntax error: Mismatched Jinja2 tags")
            if open_vars != close_vars:
                return tr("⚠️ Warning: Syntax error: Mismatched Jinja2 variables")

            return tr("✅ Syntax OK (basic validation)")

        except Exception as e:
            return tr("⚠️ Warning: Syntax error: {error}", error=str(e))
