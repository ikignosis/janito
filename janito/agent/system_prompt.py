"""janito.agent.system_prompt

System prompt template management.

This module centralizes:
- Finding system prompt templates across multiple sources
- Rendering Jinja2 templates
- Listing available templates with precedence rules

Precedence (highest to lowest):
1) local templates_dir (project / install-time directory override)
2) user profiles directory (~/.janito/profiles)
3) package resources (janito.agent.templates.profiles)

Template filename convention:
    system_prompt_template_<profile>.txt.j2
where <profile> is normalized to lowercase and spaces are replaced with underscores.
"""

from __future__ import annotations

import importlib.resources
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from jinja2 import Template

from janito.platform_discovery import PlatformDiscovery
from janito.tooling.permissions import get_global_allowed_permissions
from janito.tooling.tool_base import ToolPermissions


_PREFIX = "system_prompt_template_"
_SUFFIX = ".txt.j2"


@dataclass(frozen=True)
class SystemPromptTemplateInfo:
    """Describes a resolved template candidate."""

    name: str
    source: str  # "local" | "user" | "package"
    path: Path


class SystemPromptTemplateManager:
    """API for finding, listing and rendering system prompt templates."""

    def __init__(
        self,
        *,
        templates_dir: Optional[Path] = None,
        user_profiles_dir: Optional[Path] = None,
        package: str = "janito.agent.templates.profiles",
        debug_argv: Optional[List[str]] = None,
    ):
        self.templates_dir = templates_dir
        self.user_profiles_dir = user_profiles_dir or Path(
            os.path.expanduser("~/.janito/profiles")
        )
        self.package = package
        self.debug_argv = debug_argv if debug_argv is not None else sys.argv

    # ----------------------------
    # Naming helpers
    # ----------------------------
    def normalize_profile_name(self, profile: str) -> str:
        return profile.strip().lower().replace(" ", "_")

    def template_filename_for_profile(self, profile: str) -> str:
        normalized_profile = self.normalize_profile_name(profile)
        return f"{_PREFIX}{normalized_profile}{_SUFFIX}"

    def extract_profile_name(self, filename: str) -> str:
        """Return the human-readable profile name from template file name."""
        if filename.startswith(_PREFIX):
            filename = filename[len(_PREFIX) :]
        if filename.endswith(_SUFFIX):
            filename = filename[: -len(_SUFFIX)]

        name = filename.replace("_", " ")

        special_cases = {
            "python": "Python",
            "tools": "Tools",
            "model": "Model",
            "context": "Context",
            "developer": "Developer",
            "analyst": "Analyst",
            "conversation": "Conversation",
            "without": "Without",
        }

        words = name.split()
        capitalized_words = []
        for word in words:
            lower_word = word.lower()
            if lower_word in special_cases:
                capitalized_words.append(special_cases[lower_word])
            else:
                capitalized_words.append(word.capitalize())

        return " ".join(capitalized_words)

    # ----------------------------
    # Template discovery
    # ----------------------------
    def _iter_template_candidates(self, template_filename: str) -> Iterable[SystemPromptTemplateInfo]:
        """Yield possible locations in precedence order."""
        # 1) local templates directory
        if self.templates_dir is not None:
            local_path = self.templates_dir / template_filename
            if local_path.exists():
                yield SystemPromptTemplateInfo(
                    name=self.extract_profile_name(template_filename),
                    source="local",
                    path=local_path,
                )

        # 2) user profiles directory
        user_path = self.user_profiles_dir / template_filename
        if user_path.exists():
            yield SystemPromptTemplateInfo(
                name=self.extract_profile_name(template_filename),
                source="user",
                path=user_path,
            )

        # 3) package resources (virtual path)
        try:
            package_path = Path(
                str(importlib.resources.files(self.package).joinpath(template_filename))
            )
            # We cannot rely on .exists() for all importlib resource backends;
            # attempt to open on read instead.
            yield SystemPromptTemplateInfo(
                name=self.extract_profile_name(template_filename),
                source="package",
                path=package_path,
            )
        except Exception:
            return

    def load_template_content(self, profile: str) -> Tuple[str, Path]:
        template_filename = self.template_filename_for_profile(profile)

        # 1) local
        if self.templates_dir is not None:
            local_path = self.templates_dir / template_filename
            if local_path.exists():
                return local_path.read_text(encoding="utf-8"), local_path

        # 2) user
        user_path = self.user_profiles_dir / template_filename
        if user_path.exists():
            return user_path.read_text(encoding="utf-8"), user_path

        # 3) package
        try:
            with importlib.resources.files(self.package).joinpath(template_filename).open(
                "r", encoding="utf-8"
            ) as f:
                return f.read(), Path(template_filename)
        except (FileNotFoundError, ModuleNotFoundError, AttributeError):
            pass

        raise FileNotFoundError(self._profile_not_found_error(profile))

    def list_profiles(self) -> List[SystemPromptTemplateInfo]:
        """List available profiles, deduplicated by name.

        Deduplication rule: if the same profile name exists in multiple sources,
        keep only the winner according to precedence.

        The returned list contains only winners and their winning source.
        """

        winners: Dict[str, SystemPromptTemplateInfo] = {}

        def consider(info: SystemPromptTemplateInfo):
            key = info.name.strip().lower()
            if key not in winners:
                winners[key] = info

        # Precedence order: local -> user -> package
        # local
        if self.templates_dir is not None and self.templates_dir.exists():
            for p in self.templates_dir.iterdir():
                if p.is_file() and p.name.startswith(_PREFIX) and p.name.endswith(_SUFFIX):
                    consider(
                        SystemPromptTemplateInfo(
                            name=self.extract_profile_name(p.name),
                            source="local",
                            path=p,
                        )
                    )

        # user
        if self.user_profiles_dir.exists() and self.user_profiles_dir.is_dir():
            for p in self.user_profiles_dir.iterdir():
                if p.is_file() and p.name.startswith(_PREFIX) and p.name.endswith(_SUFFIX):
                    consider(
                        SystemPromptTemplateInfo(
                            name=self.extract_profile_name(p.name),
                            source="user",
                            path=p,
                        )
                    )

        # package
        try:
            for p in importlib.resources.files(self.package).iterdir():
                name = getattr(p, "name", None)
                if not name:
                    continue
                if name.startswith(_PREFIX) and name.endswith(_SUFFIX):
                    consider(
                        SystemPromptTemplateInfo(
                            name=self.extract_profile_name(name),
                            source="package",
                            path=Path(name),
                        )
                    )
        except Exception:
            pass

        return sorted(winners.values(), key=lambda i: i.name.lower())

    def _profile_not_found_error(self, profile: str) -> str:
        available = self.list_profiles()
        if available:
            profile_list = "\n".join([f"  - {p.name} ({p.source})" for p in available])

            normalized_input = re.sub(r"\s+", " ", profile.strip().lower())
            close_matches = []
            for p in available:
                normalized_name = p.name.lower()
                if normalized_input in normalized_name or normalized_name in normalized_input:
                    close_matches.append(p.name)

            suggestion = f"\nDid you mean: {', '.join(close_matches)}?" if close_matches else ""
            return (
                f"[janito] Could not find profile '{profile}'. Available profiles:\n"
                f"{profile_list}{suggestion}"
            )
        return f"[janito] Could not find profile '{profile}'. No profiles available."

    # ----------------------------
    # Template rendering
    # ----------------------------
    def prepare_template_context(
        self,
        *,
        role: Optional[str],
        profile: str,
        allowed_permissions: Optional[object] = None,
        args: Optional[dict] = None,
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
        context["role"] = role or "developer"
        context["profile"] = profile

        if allowed_permissions is None:
            allowed_permissions = get_global_allowed_permissions()

        if isinstance(allowed_permissions, ToolPermissions):
            perm_str = ""
            if allowed_permissions.read:
                perm_str += "r"
            if allowed_permissions.write:
                perm_str += "w"
            if allowed_permissions.execute:
                perm_str += "x"
            allowed_permissions = perm_str or None

        context["allowed_permissions"] = allowed_permissions

        if allowed_permissions and "x" in str(allowed_permissions):
            pd = PlatformDiscovery()
            context["platform"] = pd.get_platform_name()
            context["python_version"] = pd.get_python_version()
            context["shell_info"] = pd.detect_shell()
            if pd.is_linux():
                context["linux_distro"] = pd.get_linux_distro()
                context["distro_info"] = pd.get_distro_info()

        if profile == "market-analyst":
            from janito.tooling.url_whitelist import get_url_whitelist_manager

            whitelist_manager = get_url_whitelist_manager()
            allowed_sites = whitelist_manager.get_allowed_sites()
            context["allowed_sites"] = allowed_sites
            if not allowed_sites:
                context["allowed_sites_info"] = "No whitelist restrictions - all sites allowed"
            else:
                context["allowed_sites_info"] = f"Restricted to: {', '.join(allowed_sites)}"

        local_time = datetime.now()
        import time as _time

        offset = _time.altzone if _time.daylight else _time.timezone
        offset_hours = -offset // 3600
        offset_minutes = abs(offset) % 3600 // 60
        offset_str = f"{offset_hours:+03d}{offset_minutes:02d}"
        tz_name = _time.tzname[_time.daylight and _time.daylight or 0]

        context["current_datetime"] = local_time.strftime(
            f"%Y-%m-%d %H:%M:%S {tz_name}{offset_str}"
        )
        context["timezone"] = f"{tz_name} (UTC{offset_str})"

        return context

    def _debug_enabled(self) -> bool:
        try:
            argv = self.debug_argv or []
            return "--debug" in argv or "--verbose" in argv or "-v" in argv
        except Exception:
            return False

    def render_profile(
        self,
        *,
        profile: str,
        role: Optional[str] = None,
        allowed_permissions: Optional[object] = None,
    ) -> Tuple[str, Dict[str, Any], Path]:
        template_content, template_path = self.load_template_content(profile)
        template = Template(template_content)
        context = self.prepare_template_context(
            role=role, profile=profile, allowed_permissions=allowed_permissions
        )

        if self._debug_enabled():
            from rich import print as rich_print

            rich_print(
                f"[bold magenta][DEBUG][/bold magenta] Rendering system prompt template "
                f"'[cyan]{Path(template_path).name}[/cyan]' with allowed_permissions: "
                f"[yellow]{context.get('allowed_permissions')}[/yellow]"
            )
            rich_print(
                f"[bold magenta][DEBUG][/bold magenta] Template context: [green]{context}[/green]"
            )

        start_render = time.time()
        rendered_prompt = template.render(**context)
        _ = time.time() - start_render

        rendered_prompt = re.sub(r"\n{3,}", "\n\n", rendered_prompt)
        return rendered_prompt, context, template_path
