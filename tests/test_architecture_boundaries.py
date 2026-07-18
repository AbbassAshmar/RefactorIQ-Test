from __future__ import annotations

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INFRASTRUCTURE_ROOT = PROJECT_ROOT / "src" / "nimbus_ops" / "infrastructure"
REPOSITORY_AGGREGATE = "nimbus_ops.infrastructure.repositories"


def _imports_repository_aggregate(statement: ast.Import | ast.ImportFrom) -> bool:
    if isinstance(statement, ast.Import):
        return any(alias.name == REPOSITORY_AGGREGATE for alias in statement.names)

    if statement.level == 0:
        if statement.module == REPOSITORY_AGGREGATE:
            return True
        return statement.module == "nimbus_ops.infrastructure" and any(
            alias.name == "repositories" for alias in statement.names
        )

    return statement.level == 1 and (
        statement.module == "repositories"
        or statement.module is None
        and any(alias.name == "repositories" for alias in statement.names)
    )


def test_focused_repositories_do_not_import_repository_aggregate() -> None:
    focused_repositories = sorted(INFRASTRUCTURE_ROOT.glob("*_repository.py"))
    assert focused_repositories, "Expected at least one focused repository module"

    violations = []
    for repository_path in focused_repositories:
        tree = ast.parse(
            repository_path.read_text(encoding="utf-8"),
            filename=str(repository_path),
        )
        if any(
            _imports_repository_aggregate(statement)
            for statement in ast.walk(tree)
            if isinstance(statement, (ast.Import, ast.ImportFrom))
        ):
            violations.append(repository_path.relative_to(PROJECT_ROOT).as_posix())

    assert violations == [], (
        "Focused repositories must not import the aggregate repositories module: "
        f"{violations}"
    )
