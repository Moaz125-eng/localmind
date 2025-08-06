from dataclasses import dataclass

from localmind.parsers.analyzer import RepositoryAnalysis, RepositoryAnalyzer
from localmind.rag.models import ChatMessage
from localmind.rag.ollama import OllamaClient
from localmind.rag.prompts import PromptBuilder


@dataclass(frozen=True)
class RefactorSuggestion:
    title: str
    severity: str
    rationale: str
    before: str
    after: str


class RefactorAdvisor:
    def __init__(self, ollama: OllamaClient, prompt_builder: PromptBuilder | None = None) -> None:
        self.ollama = ollama
        self.prompt_builder = prompt_builder or PromptBuilder()

    async def generate_report(self, analysis: RepositoryAnalysis, source_samples: dict[str, str]) -> str:
        findings = []
        for function in analysis.large_functions[:5]:
            module = str(function["module"])
            name = str(function["name"])
            sample = source_samples.get(f"{module}:{name}", "")
            findings.append(
                f"- Large function `{name}` in `{module}` ({function['lines']} lines, complexity {function['complexity']})\n"
                f"```python\n{sample[:500]}\n```"
            )
        for class_metric in analysis.large_classes[:3]:
            findings.append(
                f"- Large class `{class_metric['name']}` in `{class_metric['module']}` ({class_metric['lines']} lines)"
            )
        if analysis.circular_imports:
            findings.append(f"- Circular imports detected: {analysis.circular_imports[:3]}")

        question = (
            "Review these repository findings and produce markdown refactor suggestions. "
            "Include split-function, rename, and simplification ideas with before/after previews."
        )
        context = "\n".join(findings) if findings else "No major findings."
        messages = self.prompt_builder.build(question, context)
        return await self.ollama.chat(messages)

    def heuristic_suggestions(self, analysis: RepositoryAnalysis) -> list[RefactorSuggestion]:
        suggestions: list[RefactorSuggestion] = []
        for function in analysis.large_functions[:10]:
            suggestions.append(
                RefactorSuggestion(
                    title=f"Split `{function['name']}` in `{function['module']}`",
                    severity="medium" if int(function["lines"]) < 120 else "high",
                    rationale=f"Function spans {function['lines']} lines with complexity {function['complexity']}.",
                    before=f"def {function['name']}(...):\n    ...",
                    after=f"def {function['name']}_step_a(...):\n    ...\n\ndef {function['name']}_step_b(...):\n    ...",
                )
            )
        for cycle in analysis.circular_imports[:5]:
            suggestions.append(
                RefactorSuggestion(
                    title="Break circular import chain",
                    severity="high",
                    rationale=f"Cycle detected: {' -> '.join(cycle)}",
                    before="from services.shared import helper",
                    after="from services.interfaces import HelperProtocol",
                )
            )
        return suggestions
