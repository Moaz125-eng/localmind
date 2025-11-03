from pathlib import Path

from localmind.parsers.call_graph import CallGraphBuilder


def build_call_repo(root: Path) -> Path:
    pkg = root / "app"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "runner.py").write_text(
        "from app.worker import execute\n\n"
        "def bootstrap():\n"
        "    return execute()\n"
    )
    (pkg / "worker.py").write_text(
        "from app.util import normalize\n\n"
        "def execute():\n"
        "    value = normalize(10)\n"
        "    return value\n"
    )
    (pkg / "util.py").write_text(
        "def normalize(value):\n"
        "    return int(value)\n"
    )
    return root


def test_call_graph_builds_edges(tmp_path: Path) -> None:
    repo = build_call_repo(tmp_path / "repo")
    builder = CallGraphBuilder()
    report = builder.build(repo)
    assert report.edges
    callers = {edge.caller for edge in report.edges}
    assert any("bootstrap" in caller for caller in callers)


def test_call_graph_entry_points(tmp_path: Path) -> None:
    repo = build_call_repo(tmp_path / "repo2")
    builder = CallGraphBuilder()
    report = builder.build(repo)
    payload = builder.to_payload(report)
    assert payload["entry_points"]


def test_call_graph_prefix_filter(tmp_path: Path) -> None:
    repo = build_call_repo(tmp_path / "repo3")
    builder = CallGraphBuilder()
    report = builder.build(repo)
    filtered = builder.filter_by_prefix(report, "app.worker")
    assert filtered["nodes"]
