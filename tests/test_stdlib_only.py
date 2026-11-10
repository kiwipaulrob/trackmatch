import ast
import sys
from pathlib import Path

# Guarded (try/except ImportError) third-party imports allowed anywhere.
ALLOWED_GUARDED = {"rapidfuzz"}


def _imports_of(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name.split(".")[0], node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.level:  # relative: from .x import y — intra-package
                continue
            yield node.module.split(".")[0], node.lineno


def test_core_imports_stdlib_only():
    """core must import nothing beyond stdlib (+guarded rapidfuzz)."""
    stdlib = set(sys.stdlib_module_names)
    violations = []
    for path in sorted(Path("src/trackmatch").rglob("*.py")):
        text = path.read_text()
        for name, lineno in _imports_of(path):
            if name in stdlib or name.startswith("trackmatch"):
                continue
            if name in ALLOWED_GUARDED and "ImportError" in text:
                continue
            violations.append(f"{path}:{lineno}: {name}")
    assert not violations, f"non-stdlib imports: {violations}"
