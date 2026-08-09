#!/usr/bin/env python3
"""Static analysis script to enforce mocking rules defined in CLAUDE.md.

Checks:
    Rule 1/2/4/5 — No patch() calls in test files (use dependency injection + stubs)
    Rule 6       — Mock() / MagicMock() calls must include a spec= keyword argument

Usage:
    # Check specific files (used by pre-commit with pass_filenames: true)
    python scripts/check_mock_rules.py tests/test_foo.py tests/test_bar.py

    # Check all test files
    python scripts/check_mock_rules.py

Exit codes:
    0 — no violations
    1 — one or more violations found
"""

import ast
import sys
from pathlib import Path


def _is_patch_call(node: ast.Call) -> bool:
    """Return True if *node* is a call to patch(...) in any form.

    Matches:
    - ``patch(...)``               — ``Name(id='patch')``
    - ``mock.patch(...)``          — ``Attribute(attr='patch')``
    - ``unittest.mock.patch(...)`` — ``Attribute(attr='patch')`` (chained)
    """
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "patch"
    if isinstance(func, ast.Attribute):
        return func.attr == "patch"
    return False


def _is_bare_mock_call(node: ast.Call) -> bool:
    """Return True if *node* is Mock(...) or MagicMock(...) without a spec= argument."""
    func = node.func
    name: str | None = None
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr

    if name not in ("Mock", "MagicMock"):
        return False

    has_spec = any(kw.arg == "spec" for kw in node.keywords)
    return not has_spec


def check_file(path: Path) -> list[str]:
    """Run all checks on *path* and return a list of violation strings."""
    source = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source=source, filename=str(path))
    except SyntaxError as exc:
        print(f"WARNING: skipping {path} (syntax error: {exc})", file=sys.stderr)
        return []

    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if _is_patch_call(node):
            violations.append(
                f"{path}:{node.lineno}: [Rule1/2/4/5] patch() is forbidden — "
                "use dependency injection and a handwritten stub instead "
                "(Rule 1/2: only external systems may be patched, and injection is preferred even for those)"
            )
            continue

        if _is_bare_mock_call(node):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr  # type: ignore[union-attr]
            violations.append(
                f"{path}:{node.lineno}: [Rule6] {name}() without spec= — "
                f"use {name}(spec=RealClass) or create_autospec(RealClass)"
            )

    return violations


def collect_test_files() -> list[Path]:
    """Return all test files under tests/ relative to the project root."""
    root = Path(__file__).parent.parent
    return sorted(root.glob("tests/**/*.py"))


def main() -> int:
    """Entry point. Returns 1 if violations found, 0 otherwise."""
    if sys.argv[1:]:
        files = [Path(p) for p in sys.argv[1:]]
    else:
        files = collect_test_files()

    all_violations: list[str] = []
    for path in files:
        all_violations.extend(check_file(path))

    for violation in all_violations:
        print(violation)

    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
