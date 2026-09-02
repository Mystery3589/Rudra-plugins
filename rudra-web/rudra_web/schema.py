"""Click / Typer Schema Introspection Engine for Rudra Web UI.

Extracts command hierarchies, parameters, types, defaults, and docstrings
at runtime so the frontend can dynamically render controls for any command.
"""

from __future__ import annotations

import click
import typer
from typing import Any, Dict, List, Optional


def _inspect_param_type(param: Any) -> dict:
    """Classify Click param type into web-friendly representation."""
    ptype = getattr(param, "type", None)
    info: dict = {"type": "string", "choices": None}
    is_flag = getattr(param, "is_flag", False)

    type_name = getattr(ptype, "name", "").lower() if ptype else ""

    if is_flag or type_name == "boolean" or isinstance(ptype, click.types.BoolParamType):
        info["type"] = "bool"
    elif type_name == "integer" or isinstance(ptype, click.types.IntParamType):
        info["type"] = "int"
    elif type_name == "float" or isinstance(ptype, click.types.FloatParamType):
        info["type"] = "float"
    elif hasattr(ptype, "choices"):
        info["type"] = "choice"
        info["choices"] = list(ptype.choices)
    elif "path" in type_name or "file" in type_name or isinstance(ptype, (click.types.Path, click.types.File)):
        info["type"] = "path"
    else:
        info["type"] = "string"

    return info


def _inspect_param(param: click.Parameter) -> dict:
    """Serialize a single Click Option or Argument."""
    type_info = _inspect_param_type(param)
    opts = list(param.opts)
    secondary_opts = list(param.secondary_opts) if hasattr(param, "secondary_opts") else []
    all_flags = opts + secondary_opts

    # Extract clean display name
    clean_name = param.name or (opts[0].lstrip("-") if opts else "arg")
    default_val = param.default
    if callable(default_val):
        try:
            default_val = default_val()
        except Exception:
            default_val = None

    return {
        "name": clean_name,
        "is_argument": isinstance(param, click.Argument),
        "is_flag": getattr(param, "is_flag", False) or type_info["type"] == "bool",
        "flags": all_flags,
        "type": type_info["type"],
        "choices": type_info["choices"],
        "required": bool(param.required),
        "default": default_val,
        "help": getattr(param, "help", "") or "",
    }


def _inspect_command(cmd: click.Command, path_prefix: list[str]) -> dict:
    """Inspect a leaf command."""
    params = [_inspect_param(p) for p in cmd.params if not getattr(p, "hidden", False)]
    # Filter out standard --help param from form fields
    form_params = [p for p in params if p["name"] != "help"]

    return {
        "name": cmd.name,
        "full_path": path_prefix + ([cmd.name] if cmd.name else []),
        "command_str": " ".join(path_prefix + ([cmd.name] if cmd.name else [])),
        "help": (cmd.help or cmd.short_help or "").strip(),
        "params": form_params,
    }


def build_schema_from_click(click_obj: Any) -> dict:
    """Build full hierarchical command dictionary from Click / Typer root."""
    groups: dict[str, list[dict]] = {}
    top_level_commands: list[dict] = []

    if hasattr(click_obj, "commands"):
        # Inspect top level commands & groups
        for name, sub in click_obj.commands.items():
            if getattr(sub, "hidden", False):
                continue
            if hasattr(sub, "commands") and sub.commands:
                sub_cmds = []
                for sub_name, leaf in sub.commands.items():
                    if getattr(leaf, "hidden", False):
                        continue
                    if hasattr(leaf, "commands") and leaf.commands:
                        for sub_sub_name, sub_leaf in leaf.commands.items():
                            sub_cmds.append(_inspect_command(sub_leaf, ["rudra", name, sub_name]))
                    else:
                        sub_cmds.append(_inspect_command(leaf, ["rudra", name]))
                if sub_cmds:
                    groups[name] = sub_cmds
            else:
                top_level_commands.append(_inspect_command(sub, ["rudra"]))

    if top_level_commands:
        groups["general"] = top_level_commands

    return {
        "groups": groups,
        "group_names": list(groups.keys()),
    }


def get_rudra_schema() -> dict:
    """Load the live Rudra Typer app and generate its schema."""
    from rudra.main import app
    click_root = typer.main.get_command(app)
    return build_schema_from_click(click_root)
