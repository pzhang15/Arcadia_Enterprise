import json
from dataclasses import asdict, dataclass

from mirage_eval.config import TrajectoryBudget
from mirage_eval.runner.common import RunArtifacts

# Approximate USD per 1M tokens. Tunable; keep conservative defaults so
# cost reporting is never silently zero.
_PRICE_TABLE_USD_PER_MTOK = {
    "gpt-5":         {"in": 1.25, "out": 10.00},
    "gpt-5-mini":    {"in": 0.25, "out": 2.00},
    "gpt-5-nano":    {"in": 0.05, "out": 0.40},
    "gpt-4.1":       {"in": 2.00, "out": 8.00},
    "gpt-4.1-mini":  {"in": 0.40, "out": 1.60},
    "gpt-4.1-nano":  {"in": 0.10, "out": 0.40},
    "gpt-4o":        {"in": 2.50, "out": 10.00},
    "gpt-4o-mini":   {"in": 0.15, "out": 0.60},
    "o4-mini":       {"in": 1.10, "out": 4.40},
}


def _price_for(model: str) -> dict[str, float]:
    if model in _PRICE_TABLE_USD_PER_MTOK:
        return _PRICE_TABLE_USD_PER_MTOK[model]
    for k, v in _PRICE_TABLE_USD_PER_MTOK.items():
        if model.startswith(k):
            return v
    return {"in": 0.0, "out": 0.0}


@dataclass
class TrajectoryMetrics:
    n_turns: int
    n_commands: int
    n_ops: int
    n_unique_paths: int
    bytes_read: int
    bytes_written: int
    cache_hit_rate: float
    wallclock_s: float
    tokens_in: int
    tokens_out: int
    requests: int
    cost_usd: float
    within_budget: bool
    budget_breaches: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _count_commands_in_journal(jsonl: str) -> int:
    n = 0
    for line in jsonl.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if entry.get("type") == "command":
            n += 1
    return n


def score_trajectory(artifacts: RunArtifacts,
                     budget: TrajectoryBudget) -> TrajectoryMetrics:
    """Compute trajectory metrics + budget compliance.

    Args:
        artifacts (RunArtifacts): Captured run output.
        budget (TrajectoryBudget): Limits from the task YAML.
    """
    n_ops = len(artifacts.op_records)
    paths = {r.path for r in artifacts.op_records if r.path}
    bytes_read = sum(
        r.bytes for r in artifacts.op_records if r.op in {"read", "read_bytes"})
    bytes_written = sum(
        r.bytes for r in artifacts.op_records
        if r.op in {"write", "write_bytes", "append"})
    cache_hits = sum(1 for r in artifacts.op_records if r.is_cache)
    cache_hit_rate = (cache_hits / n_ops) if n_ops else 0.0
    n_commands = _count_commands_in_journal(artifacts.sessions_jsonl)
    n_turns = artifacts.raw_responses_count
    pricing = _price_for(artifacts.model)
    cost = ((artifacts.usage.input_tokens / 1_000_000) * pricing["in"]
            + (artifacts.usage.output_tokens / 1_000_000) * pricing["out"])
    breaches: list[str] = []
    if n_turns > budget.max_turns:
        breaches.append(f"max_turns {n_turns}>{budget.max_turns}")
    if n_commands > budget.max_commands:
        breaches.append(f"max_commands {n_commands}>{budget.max_commands}")
    if artifacts.wallclock_s > budget.max_wallclock_s:
        breaches.append(
            f"max_wallclock_s {artifacts.wallclock_s:.1f}>{budget.max_wallclock_s}")
    if (artifacts.usage.input_tokens
            + artifacts.usage.output_tokens) > budget.max_tokens:
        breaches.append(
            f"max_tokens {artifacts.usage.input_tokens + artifacts.usage.output_tokens}"
            f">{budget.max_tokens}")
    return TrajectoryMetrics(
        n_turns=n_turns,
        n_commands=n_commands,
        n_ops=n_ops,
        n_unique_paths=len(paths),
        bytes_read=bytes_read,
        bytes_written=bytes_written,
        cache_hit_rate=cache_hit_rate,
        wallclock_s=artifacts.wallclock_s,
        tokens_in=artifacts.usage.input_tokens,
        tokens_out=artifacts.usage.output_tokens,
        requests=artifacts.usage.requests,
        cost_usd=cost,
        within_budget=not breaches,
        budget_breaches=breaches,
    )
