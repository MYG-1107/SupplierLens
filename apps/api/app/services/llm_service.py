from __future__ import annotations

from app.core.config import settings
from app.schemas.verification import CopilotResponse, VerificationResponse


def _deterministic_answer(question: str, report: VerificationResponse) -> CopilotResponse:
    q = question.lower()
    cited = [f.code for f in report.flags if f.severity in {"high", "medium"}]

    if any(term in q for term in ["advance", "pay", "payment", "money"]):
        if any(f.severity == "high" for f in report.flags):
            answer = "The current evidence contains high-severity findings. Resolve those findings and confirm payment ownership before authorizing an advance."
        elif any(f.severity == "medium" for f in report.flags):
            answer = "The current evidence contains review findings. Payment can be considered only after the responsible reviewer documents how those findings were resolved."
        else:
            answer = "The current run did not produce medium/high findings, but the report is still decision support and does not certify the supplier."
    elif any(term in q for term in ["why", "flag", "risk", "problem"]):
        if cited:
            titles = [f.title for f in report.flags if f.code in cited]
            answer = "The main review signals are: " + "; ".join(titles) + ". Open each finding to review the cited evidence and remediation."
        else:
            answer = "No medium/high review findings were generated from the supplied evidence. Coverage remains limited to what was provided."
    elif any(term in q for term in ["missing", "next", "do"]):
        answer = "Next steps: " + " ".join(report.next_steps)
    else:
        answer = (
            f"Current status is {report.overall_status.replace('_', ' ')} with {report.coverage_percent}% evidence coverage, "
            f"{report.identity_match_percent}% identity match, and {report.consistency_percent}% consistency. "
            "The original evidence remains the source of truth."
        )
    return CopilotResponse(answer=answer, cited_findings=cited[:8], mode="deterministic")


def generate_copilot(question: str, report: VerificationResponse) -> CopilotResponse:
    if not settings.llm_enabled or not settings.openai_api_key:
        return _deterministic_answer(question, report)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        prompt = (
            "You are SupplierLens Copilot. Answer only from the supplied verification report. "
            "Do not invent facts. Be explicit that this is decision support, not certification. "
            "Keep the answer under 120 words.\n\n"
            f"Question: {question}\n\nReport:\n{report.model_dump_json(indent=2)}"
        )
        response = client.responses.create(model=settings.openai_model, input=prompt)
        answer = (response.output_text or "").strip()
        if answer:
            return CopilotResponse(
                answer=answer,
                cited_findings=[f.code for f in report.flags if f.severity in {"high", "medium"}][:8],
                mode="llm",
            )
    except Exception:
        pass
    return _deterministic_answer(question, report)
