from dataclasses import asdict, dataclass, field

from mirage_eval.config import TaskConfig
from mirage_eval.runner.common import RunArtifacts


@dataclass
class GateResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ProgrammaticResult:
    gates: list[GateResult] = field(default_factory=list)

    @property
    def fraction_passed(self) -> float:
        if not self.gates:
            return 1.0
        passed = sum(1 for g in self.gates if g.passed)
        return passed / len(self.gates)

    @property
    def all_passed(self) -> bool:
        return all(g.passed for g in self.gates)

    def by_category(self) -> dict[str, float]:
        cats: dict[str, list[bool]] = {}
        for g in self.gates:
            cat = g.name.split(":", 1)[0]
            cats.setdefault(cat, []).append(g.passed)
        return {k: sum(v) / len(v) for k, v in cats.items()}

    def to_dict(self) -> dict:
        return {
            "gates": [asdict(g) for g in self.gates],
            "fraction_passed": self.fraction_passed,
            "all_passed": self.all_passed,
            "by_category": self.by_category(),
        }


_KNOWN_MOUNT_PREFIXES = ("/slack", "/sheets", "/gdocs", "/tickets",
                         "/.sessions", "/dev")


def _normalize_path(p: str) -> str:
    p = p.strip()
    if not p.startswith("/"):
        p = "/" + p
    return p


def _path_alternates(p: str) -> tuple[str, ...]:
    """Return the path itself and its mount-stripped form (if any).

    Mirage's streaming reads record paths AFTER the mount-prefix
    contextvar has been reset, so disk-backed mounts emit
    resource-relative paths (``/owned/...``) instead of fully-qualified
    virtual paths (``/sheets/owned/...``). We accept either form for
    matching.

    Args:
        p (str): A normalized path beginning with ``/``.
    """
    p = _normalize_path(p)
    out = [p]
    for m in _KNOWN_MOUNT_PREFIXES:
        if p.startswith(m + "/") or p == m:
            out.append(p[len(m):] or "/")
            break
    return tuple(out)


def _matches_prefix(touched: list[str], required: str) -> bool:
    required = _normalize_path(required)
    required_alts = _path_alternates(required)
    for tp in touched:
        for tp_alt in _path_alternates(tp):
            for req_alt in required_alts:
                if tp_alt.startswith(req_alt):
                    return True
    return False


def _all_touched_paths(artifacts: RunArtifacts) -> list[str]:
    """Distinct virtual paths the agent touched (any op).

    Args:
        artifacts (RunArtifacts): Captured run output.
    """
    seen: set[str] = set()
    for r in artifacts.op_records:
        if r.path:
            seen.add(_normalize_path(r.path))
    return sorted(seen)


def _enoent_paths(artifacts: RunArtifacts) -> list[str]:
    """Paths the agent referenced via shell command that returned ENOENT.

    Args:
        artifacts (RunArtifacts): Captured run output.
    """
    out: list[str] = []
    for line in (artifacts.sessions_jsonl or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = __import__("json").loads(line)
        except Exception:
            continue
        if entry.get("type") != "command":
            continue
        if (entry.get("exit_code") or 0) == 0:
            continue
        out_text = (entry.get("stdout") or "")
        cmd = (entry.get("command") or "")
        lowered = (out_text + " " + cmd).lower()
        if ("no such file" in lowered or "enoent" in lowered):
            out.append(cmd)
    return out


def score_programmatic(artifacts: RunArtifacts,
                       task: TaskConfig) -> ProgrammaticResult:
    """Apply programmatic gates from the task YAML to the run artifacts.

    Args:
        artifacts (RunArtifacts): Captured run output.
        task (TaskConfig): Task definition (with oracles).
    """
    gates: list[GateResult] = []
    o = task.oracles
    for path in o.files_must_exist:
        gates.append(
            GateResult(
                name=f"file_exists:{path}",
                passed=path in artifacts.output_files,
                detail=("present" if path in artifacts.output_files else
                        "missing in output_files"),
            ))
    for path, needles in o.must_contain_in_file.items():
        body = artifacts.output_files.get(path, "")
        for needle in needles:
            present = needle in body
            gates.append(
                GateResult(
                    name=f"must_contain:{path}:{needle}",
                    passed=present,
                    detail=("present" if present else "missing"),
                ))
    for path, banned in o.must_not_contain_in_file.items():
        body = artifacts.output_files.get(path, "")
        for needle in banned:
            absent = needle not in body
            gates.append(
                GateResult(
                    name=f"must_not_contain:{path}:{needle}",
                    passed=absent,
                    detail=("absent" if absent else "found unexpectedly"),
                ))
    touched = _all_touched_paths(artifacts)
    for prefix in o.ops_must_touch_prefix:
        hit = _matches_prefix(touched, prefix)
        gates.append(
            GateResult(
                name=f"ops_must_touch:{prefix}",
                passed=hit,
                detail=("touched" if hit else "no op under this prefix"),
            ))
    for prefix in o.ops_must_not_touch_prefix:
        hit = _matches_prefix(touched, prefix)
        gates.append(
            GateResult(
                name=f"ops_must_not_touch:{prefix}",
                passed=not hit,
                detail=("avoided" if not hit else "touched unexpectedly"),
            ))
    enoents = _enoent_paths(artifacts)
    gates.append(
        GateResult(
            name="no_enoent",
            passed=len(enoents) <= o.max_enoent,
            detail=
            f"{len(enoents)} ENOENT-like commands; budget {o.max_enoent}",
        ))
    return ProgrammaticResult(gates=gates)
