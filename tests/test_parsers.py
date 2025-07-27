from pathlib import Path

from localmind.parsers.analyzer import RepositoryAnalyzer
from localmind.parsers.import_graph import DependencyGraphBuilder
from localmind.parsers.python_ast import PythonModuleAnalyzer


def build_repo(root: Path) -> Path:
    services = root / "services"
    services.mkdir(parents=True)
    (services / "__init__.py").write_text("")
    (services / "billing.py").write_text(
        "from services.shared import normalize_amount\n\n"
        "def charge(amount):\n"
        "    value = normalize_amount(amount)\n"
        "    if value <= 0:\n"
        "        return False\n"
        "    return True\n"
    )
    (services / "shared.py").write_text(
        "from services.billing import charge\n\n"
        "def normalize_amount(amount):\n"
        "    return float(amount)\n"
    )
    (services / "reports.py").write_text(
        "def build_report(rows):\n"
        "    total = 0\n"
        "    for row in rows:\n"
        "        if row.get('active'):\n"
        "            total += row['value']\n"
        "    return total\n"
    )
    return root


def test_detects_circular_imports(tmp_path: Path) -> None:
    repo = build_repo(tmp_path / "repo")
    builder = DependencyGraphBuilder()
    report = builder.build(repo)
    assert report.circular_imports


def test_large_function_detection(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    long_body = "\n".join(f"    x = {index}" for index in range(90))
    (repo / "heavy.py").write_text(f"def heavy():\n{long_body}\n    return x\n")
    builder = DependencyGraphBuilder()
    report = builder.build(repo)
    assert report.large_functions
    assert report.large_functions[0]["name"] == "heavy"


def test_repository_analyzer_summary(tmp_path: Path) -> None:
    repo = build_repo(tmp_path / "repo2")
    analyzer = RepositoryAnalyzer()
    result = analyzer.analyze(1, repo)
    assert result.module_count >= 3
    assert result.dependency_count >= 1
