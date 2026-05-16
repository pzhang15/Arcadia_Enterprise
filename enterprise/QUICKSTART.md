# Quickstart — Run the eval on your laptop

The simplest path from zero to seeing a scorecard. Everything below is **L1** (offline, synthetic) so you only need an OpenAI key — no Slack/Google setup.

## 1. One-time setup

```bash
cd enterprise
uv sync                       # installs mirage-eval + the local mirage-ai
cp .env.example .env          # then edit .env and set OPENAI_API_KEY=sk-...
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

- **`OPENAI_API_KEY` not set** — make sure `enterprise/.env` exists and contains `OPENAI_API_KEY=sk-...`. The CLI auto-loads it from there.
- **`scenario not found`** — run from inside `enterprise/` (or use `uv --directory enterprise run ...`).
- **Snapshot missing** — re-run `mirage-eval seed --scenario onboarding_it` before the first `run`.
- **Want to re-render reports for a past sweep** — `uv run mirage-eval report --scenario onboarding_it --sweep-id <ts>`.
