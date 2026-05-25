# Scenario: NorthHill Corp new-hire onboarding + IT helpdesk

## Story

NorthHill Corp is a 250-person B2B SaaS company. Alex Rivera starts on Monday 2026-05-12 as a Software Engineer on the Platform team. Diana Park (HR) owns the onboarding playbook. Sam Chen (IT Lead) and Priya Patel (IT Agent) own the helpdesk queue. Marcus Johnson (Eng Lead) is Alex's manager. Jordan Kim is Alex's Week-1 buddy. Bob Lee is an existing employee with an unrelated open VPN ticket — he's the "control" persona that tests whether agents conflate distinct people.

The corpus is intentionally cross-referenced: ticket bodies cite spreadsheet rows, the IT runbook drives the SLA matrix, the postmortem references hires whose Day-1 fell in the outage window, etc. The four task families (and their adversarial variants) all require crossing at least three of {Slack, GSheets, GDocs, ITSM} to answer correctly.

See [`personas.yaml`](personas.yaml) for the full cast.

## Layout (built by `seed.py`)

```
~/mirage-eval/onboarding_it/
  slack/{channels,dms,users}/...
  sheets/owned/*.gsheet.json
  gdocs/owned/*.gdoc.json
  tickets/queues/it-helpdesk/{open,in_progress,resolved}/*.json
  tickets/{users,teams}/...
```

## Mounts

L1 (synthetic, offline):

| Mount      | Resource                                                         |
| ---------- | ---------------------------------------------------------------- |
| `/`        | `RAMResource` (write target for the agent)                       |
| `/slack`   | `FakeSlackResource` (Disk + real Slack PROMPT)                   |
| `/sheets`  | `FakeGSheetsResource` (Disk + real GSheets PROMPT)               |
| `/gdocs`   | `FakeGDocsResource` (Disk + real GDocs PROMPT)                   |
| `/tickets` | `FakeTicketingResource` (Disk + ITSM PROMPT, helpdesk-\* writes) |

L2 (real Slack + real Google; tickets stay disk-backed in v1):

| Mount      | Resource                                       |
| ---------- | ---------------------------------------------- |
| `/`        | `RAMResource`                                  |
| `/slack`   | `SlackResource` (real bot + user tokens)       |
| `/sheets`  | `GSheetsResource` (real OAuth)                 |
| `/gdocs`   | `GDocsResource` (real OAuth)                   |
| `/tickets` | `FakeTicketingResource` (same disk path as L1) |

## L2 setup (Phase 3)

L2 = same task YAMLs, but mounts swap to real `SlackResource`, `GSheetsResource`, `GDocsResource`. Tickets stay on disk via `FakeTicketingResource` (Linear mapping is a future L3 milestone).

### One-time, ~30 minutes

1. **Slack** — create a brand-new workspace you own at https://slack.com/get-started.
   - Apps → Create New App → From scratch → name `mirage-eval`.
   - OAuth & Permissions → Bot Token Scopes:
     - `channels:history`, `channels:read`, `groups:history`, `im:history`,
       `users:read`, `chat:write`, `chat:write.customize`, `files:read`.
   - Install to workspace; copy the Bot Token (`xoxb-...`) into `enterprise/.env` as `SLACK_BOT_TOKEN`.
   - (Optional) Generate a User Token for `search:read` and put it in `SLACK_USER_TOKEN` to enable `slack-search`.
1. **Google** — use a personal account dedicated to testing (do NOT pollute your work account).
   - Google Cloud Console → create a project `mirage-eval`.
   - Enable Drive API, Sheets API, Docs API.
   - OAuth consent screen → External + scopes: `drive`, `spreadsheets`, `documents`.
   - Credentials → OAuth client ID (Desktop) → download the JSON.
   - Use the existing flow at [examples/python/google/](../../../examples/python/google/) (or any tool of your choice) to mint a refresh token.
   - Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` in `enterprise/.env`.
1. **Bootstrap the corpus on real services** (idempotent):
   ```bash
   uv run mirage-eval seed --scenario onboarding_it --surface l2
   ```
   This pushes the same synthetic NorthHill corpus into your test Slack workspace + Google account, prefixed with `mirage-eval__` so it doesn't pollute your account. Records `scenarios/onboarding_it/l2_mapping.yaml` with `synthetic-id → real-id`.

### Run L2

```bash
uv run mirage-eval run --scenario onboarding_it --task onboarding_status \
                       --model gpt-5-mini --seed 1 --surface l2
uv run mirage-eval sweep --scenario onboarding_it \
                         --models gpt-5-mini --seeds 1 --surface l2
```

The same task YAMLs and the same scorers drive both surfaces. The canvas dashboard surfaces L1-vs-L2 deltas (composite, cost, latency, cache hit rate).

### Cleanup

The Slack workspace is yours and isolated. To wipe the test Google content:

```bash
uv run mirage-eval seed --scenario onboarding_it --surface l2 --clean
```

## Tasks

| Task                 | Cross-domain surfaces                     | Notes                                          |
| -------------------- | ----------------------------------------- | ---------------------------------------------- |
| `onboarding_status`  | GSheets + ITSM + Slack channel + Slack DM | Phase 1 vertical slice                         |
| `provision_new_hire` | ITSM (R+W) + GSheets + GDocs              | Tests `helpdesk-ticket-comment-add` write path |
| `ticket_triage`      | ITSM + GDocs (SLA matrix + runbook)       | Tests duplicate detection                      |
| `incident_followup`  | GDocs + Slack + GSheets + ITSM            | Hardest task, joins 4 surfaces                 |

Adversarial variants under [`tasks/adversarial/`](tasks/adversarial/) test failure modes (missing data, contradictions, ambiguous referents).
