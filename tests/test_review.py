from pathlib import Path

from localmind.parsers.pr_analyzer import GitDiffParser, PullRequestAnalyzer
from localmind.visualization.graphs import ArchitectureVisualizer
from tests.test_parsers import build_repo


SAMPLE_DIFF = """diff --git a/services/billing.py b/services/billing.py
index abc..def 100644
--- a/services/billing.py
+++ b/services/billing.py
@@ -1,5 +1,12 @@
 from services.shared import normalize_amount
 
 def charge(amount):
     value = normalize_amount(amount)
+    if value <= 0:
+        return False
+    if value <= 0:
+        return False
+    if value <= 0:
+        return False
     return True
"""


def test_git_diff_parser_extracts_hunks() -> None:
    parser = GitDiffParser()
    hunks = parser.parse(SAMPLE_DIFF)
    assert hunks
    assert hunks[0].file_path == "services/billing.py"
    assert hunks[0].added_lines >= 3


def test_pull_request_analyzer_flags_risk_and_duplicates(tmp_path: Path) -> None:
    repo = build_repo(tmp_path / "repo")
    analyzer = PullRequestAnalyzer()
    analysis = analyzer.analyze(SAMPLE_DIFF, repository_root=repo)
    assert analysis.files_changed == 1
    assert analysis.lines_added >= 3
    assert analysis.duplicate_introductions


def test_architecture_visualizer_summary(tmp_path: Path) -> None:
    repo = build_repo(tmp_path / "repo")
    visualizer = ArchitectureVisualizer()
    summary = visualizer.graph_summary(repo)
    assert summary["module_count"] >= 3
    assert "top_dependencies" in summary
