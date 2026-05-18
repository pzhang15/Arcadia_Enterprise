from pathlib import Path

from mirage_eval.report.aggregate import AggregateReport


def write_markdown_summary(report: AggregateReport, target: Path) -> Path:
    """Write a human-readable per-sweep summary as Markdown.

    Args:
        report (AggregateReport): Aggregated sweep results.
        target (Path): Output Markdown path (parents created).
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# Sweep `{report.sweep_id}` ({report.scenario_id} / "
                 f"{report.surface})")
    lines.append("")
    lines.append(f"- Runs: {report.n_runs} ({report.n_succeeded} succeeded)")
    lines.append(f"- Mean composite: **{report.composite_mean:.3f}**")
    lines.append(f"- Models: {', '.join(report.models)}")
    lines.append(f"- Seeds: {', '.join(map(str, report.seeds))}")
    lines.append(f"- Tasks: {', '.join(report.tasks)}")
    lines.append("")
    lines.append("## Composite by task")
    lines.append("")
    lines.append("| Task | Composite (mean) |")
    lines.append("|---|---:|")
    for t, v in sorted(report.composite_by_task.items()):
        lines.append(f"| {t} | {v:.3f} |")
    lines.append("")
    lines.append("## Composite by model")
    lines.append("")
    lines.append("| Model | Composite (mean) |")
    lines.append("|---|---:|")
    for m, v in sorted(report.composite_by_model.items()):
        lines.append(f"| {m} | {v:.3f} |")
    lines.append("")
    lines.append("## Heatmap (model x task -> composite mean)")
    lines.append("")
    if report.models and report.tasks:
        header = "| Model | " + " | ".join(report.tasks) + " |"
        sep = "|---|" + "|".join(["---:"] * len(report.tasks)) + "|"
        lines.append(header)
        lines.append(sep)
        for m in report.models:
            row = [m]
            for t in report.tasks:
                cell = report.cell_by_model_task.get(m, {}).get(t)
                row.append(f"{cell.composite_mean:.3f}" if cell else "—")
            lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    if report.failure_modes:
        lines.append("## Failure modes (count across all runs)")
        lines.append("")
        lines.append("| Mode | Count |")
        lines.append("|---|---:|")
        for fm, count in sorted(report.failure_modes.items(),
                                key=lambda kv: -kv[1]):
            lines.append(f"| {fm} | {count} |")
        lines.append("")
    target.write_text("\n".join(lines))
    return target
