import asyncio
import json
import os
from dataclasses import asdict, dataclass, field

from openai import AsyncOpenAI

from mirage_eval.config import JudgeConfig
from mirage_eval.runner.common import RunArtifacts

_SYSTEM_INSTRUCTIONS = (
    "You are a strict but fair grader for an AI agent's task output. "
    "Score each rubric item on a 0.0..1.0 scale (1.0 = perfect, 0.0 = "
    "fails the criterion). Return ONLY JSON of shape "
    '{"scores": {"<name>": <0..1>, ...}, "rationale": {"<name>": '
    '"<short string>", ...}}. No prose outside JSON.')


@dataclass
class JudgeResult:
    scores: dict[str, float] = field(default_factory=dict)
    rationale: dict[str, str] = field(default_factory=dict)
    weighted: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _build_user_prompt(artifacts: RunArtifacts, judge: JudgeConfig) -> str:
    rubric_block = "\n".join(
        f"- {name} (weight {item.weight}): {item.criteria.strip()}"
        for name, item in judge.rubric.items())
    files_block = "\n".join(
        f"### {p}\n{body[:8000]}"
        for p, body in artifacts.output_files.items()) or "(no output files)"
    return ("## Task prompt the agent received\n"
            f"{artifacts.prompt}\n\n"
            "## Agent final text output\n"
            f"{artifacts.final_output[:4000]}\n\n"
            "## Files the agent wrote (truncated to 8000 chars each)\n"
            f"{files_block}\n\n"
            "## Rubric (score each independently)\n"
            f"{rubric_block}\n\n"
            "Return JSON only.")


def _weighted_average(scores: dict[str, float], judge: JudgeConfig) -> float:
    total_weight = sum(item.weight for item in judge.rubric.values())
    if total_weight <= 0:
        return 0.0
    s = 0.0
    for name, item in judge.rubric.items():
        s += float(scores.get(name, 0.0)) * item.weight
    return s / total_weight


async def judge_output(artifacts: RunArtifacts,
                       judge: JudgeConfig) -> JudgeResult:
    """Run the LLM-as-judge against the captured artifacts.

    Returns a degenerate result with the error captured (and zero
    scores) if the OpenAI call fails.

    Args:
        artifacts (RunArtifacts): Captured run output.
        judge (JudgeConfig): Judge model + rubric.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        return JudgeResult(scores={k: 0.0
                                   for k in judge.rubric},
                           rationale={
                               k: "OPENAI_API_KEY missing; judge skipped"
                               for k in judge.rubric
                           },
                           weighted=0.0,
                           error="OPENAI_API_KEY missing")
    client = AsyncOpenAI()
    user = _build_user_prompt(artifacts, judge)
    try:
        resp = await client.chat.completions.create(
            model=judge.model,
            messages=[
                {
                    "role": "system",
                    "content": _SYSTEM_INSTRUCTIONS
                },
                {
                    "role": "user",
                    "content": user
                },
            ],
            response_format={"type": "json_object"},
        )
        text = (resp.choices[0].message.content or "").strip()
        data = json.loads(text)
        scores = {
            k: float(data.get("scores", {}).get(k, 0.0))
            for k in judge.rubric
        }
        rationale = {
            k: str(data.get("rationale", {}).get(k, ""))
            for k in judge.rubric
        }
        weighted = _weighted_average(scores, judge)
        return JudgeResult(scores=scores,
                           rationale=rationale,
                           weighted=weighted)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        return JudgeResult(scores={k: 0.0
                                   for k in judge.rubric},
                           rationale={k: ""
                                      for k in judge.rubric},
                           weighted=0.0,
                           error=f"{type(exc).__name__}: {exc}")
