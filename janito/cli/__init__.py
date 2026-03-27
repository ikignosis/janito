"""CLI module for janito.

This module handles command-line interface parsing and command dispatch.
"""

from .parser import create_parser, parse_args

__all__ = ["create_parser", "parse_args"]
