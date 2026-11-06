"""Project-root entry point for the authoritative context-pack helper."""

import importlib.util
import os
import runpy
import sys


root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
implementation = os.path.join(root, "skills", "context-pack", "scripts", "check_brief.py")
if __name__ == "__main__":
    runpy.run_path(implementation, run_name="__main__")
else:
    spec = importlib.util.spec_from_file_location(__name__, implementation)
    module = importlib.util.module_from_spec(spec)
    sys.modules[__name__] = module
    spec.loader.exec_module(module)
