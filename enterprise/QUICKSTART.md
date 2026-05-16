# Quickstart — Run the eval on your laptop

The simplest path from zero to seeing a scorecard. Everything below is **L1** (offline, synthetic) so you only need an OpenAI key — no Slack/Google setup.

> **Heads up — the CLI name is `mirage-eval` (hyphen), not `mirage_eval` (underscore).**
> The Python package is `mirage_eval` (identifiers can't have hyphens), but the
> installed CLI binary is `mirage-eval`. Always invoke it as:
>
> ```bash
> cd enterprise                                  # the CLI lives in this folder's venv
> uv run mirage-eval ...                         # uv handles the venv for you
> ```
>
> If you see `command not found: mirage_eval`, it's almost always one of:
> 1. You typed an underscore instead of a hyphen.
> 2. You're not in the `enterprise/` directory.
> 3. You forgot the `uv run` prefix (the binary lives in `.venv/bin/`, not your global `PATH`).
>
> Sanity check after step 1: `uv run mirage-eval --help` should print the Typer help.

## 1. One-time setup

```bash
cd enterprise
uv sync                       # installs the mirage-eval CLI + the local mirage-ai package
cp .env.example .env          # then edit .env and set OPENAI_API_KEY=sk-...
uv run mirage-eval --help     # verify the CLI is installed (should print Typer help)
```

L1 needs only `OPENAI_API_KEY`. Skip the Slack/Google vars unless you also want L2.

## 2. Seed the synthetic corpus (once)

```bash
uv run mirage-eval seed --scenario onboarding_it
```

What this does:

- Runs `scenarios/onboarding_it/seed.py` to write the ACME corpus to `scenarios/onboarding_it/fixture/disk/` (Slack channels/DMs, GSheets, GDocs, IT tickets).
- Builds `scenarios/onboarding_it/fixture/corpus.tar` — the snapshot every run restores from so each run is bit-identical.

Only re-run this when `seed.py` changes.

## 3. Run a single task (fast, ~$0.01–0.05)

```bash
uv run mirage-eval run \
  --scenario onboarding_it \
  --task onboarding_status \
  --model gpt-5-mini \
  --seed 1
```

You'll see a Rich table printed at the end with `composite`, `passed_gates`, `programmatic_passed`, `judge_weighted`, tokens, and `cost_usd`.

Other tasks you can swap in for `--task`:

- `provision_new_hire`
- `ticket_triage`
- `incident_followup`

## 4. See the result

Each run writes to:

```
enterprise/results/onboarding_it/<sweep_id>/runs/l1__gpt-5-mini__onboarding_status__seed1/
  ├─ scorecard.json        # the same numbers from the printed table
  ├─ final_output.txt      # agent's final reply
  ├─ output_files/         # whatever the agent wrote (e.g. onboarding_status.md)
  ├─ artifacts.json        # full run record (op records, usage, prompt, ...)
  └─ sessions.jsonl        # per-turn trace from the workspace observer
```

The `<sweep_id>` is the timestamp printed at the top of the run (e.g. `20260515-193012`). The CLI also prints `out_dir:` so you can copy-paste it.

Quickest way to eyeball quality:

```bash
open enterprise/results/onboarding_it/<sweep_id>/runs/l1__gpt-5-mini__onboarding_status__seed1/output_files/
cat  enterprise/results/onboarding_it/<sweep_id>/runs/l1__gpt-5-mini__onboarding_status__seed1/scorecard.json
```

## 5. (Optional) Run a small sweep + dashboard

A sweep runs `tasks × models × seeds` and emits a markdown summary + a Cursor canvas dashboard:

```bash
uv run mirage-eval sweep \
  --scenario onboarding_it \
  --models gpt-5-mini \
  --seeds 1 \
  --yes
```

After it finishes:

- `enterprise/results/onboarding_it/<sweep_id>/SUMMARY.md` — open in Cursor for the per-task / per-model table.
- `enterprise/canvases/onboarding_it/dashboard.canvas.tsx` — open in Cursor's canvas viewer for the interactive dashboard.

Or use the wrapper with sensible defaults:

```bash
./scripts/run_sweep.sh
```

## TL;DR three commands

```bash
cd enterprise && uv sync && cp .env.example .env   # then add OPENAI_API_KEY
uv run mirage-eval seed --scenario onboarding_it
uv run mirage-eval run  --scenario onboarding_it --task onboarding_status --model gpt-5-mini --seed 1
```

Then look in `enterprise/results/onboarding_it/<timestamp>/runs/.../` for the agent's output and scorecard.

## Troubleshooting

- **`command not found: mirage_eval`** — the CLI is `mirage-eval` (hyphen), not `mirage_eval` (underscore). Also make sure you're in `enterprise/` and prefixing with `uv run` (or have `.venv` activated).
- **`command not found: mirage-eval`** — `uv sync` hasn't been run yet, or you're not in `enterprise/`. Run `cd enterprise && uv sync`, then retry with `uv run mirage-eval --help`.
- **`OPENAI_API_KEY` not set** — make sure `enterprise/.env` exists and contains `OPENAI_API_KEY=sk-...`. The CLI auto-loads it from there.
- **`scenario not found`** — run from inside `enterprise/` (or use `uv --directory enterprise run mirage-eval ...`).
- **Snapshot missing** — re-run `uv run mirage-eval seed --scenario onboarding_it` before the first `run`.
- **Want to re-render reports for a past sweep** — `uv run mirage-eval report --scenario onboarding_it --sweep-id <ts>`.

### Alternative invocation styles

All three of these are equivalent — pick whichever you prefer:

```bash
uv run mirage-eval seed --scenario onboarding_it          # recommended
./.venv/bin/mirage-eval seed --scenario onboarding_it     # no uv, no activation
source .venv/bin/activate && mirage-eval seed --scenario onboarding_it
```
