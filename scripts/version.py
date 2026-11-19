"""Canonical product release identity shared by the offline runtime and wheel."""

import sys

if sys.version_info < (3, 8):
    sys.exit("sdlc version resource requires Python >= 3.8")
sys.dont_write_bytecode = True

import ast
import re

VERSION = "0.3.0"


def read_version(data):
    """Read a literal version from source data without executing that source."""
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    if not isinstance(data, str):
        raise ValueError("product version resource must be UTF-8 source text")
    tree = ast.parse(data)
    declarations = [node for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "VERSION" for target in node.targets)]
    if len(declarations) != 1:
        raise ValueError("product version resource must declare VERSION exactly once")
    value = ast.literal_eval(declarations[0].value)
    if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value):
        raise ValueError("product version must be a literal major.minor.patch release")
    return value
