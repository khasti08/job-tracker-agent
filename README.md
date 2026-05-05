# Job Application Tracker Agent

An autonomous AI agent that monitors your Gmail for job application emails,
tracks status in Google Sheets, and proactively alerts you to upcoming interviews
— without you having to ask it anything.

Built on [OpenClaw](https://github.com/openclaw/openclaw) with Claude as the LLM backend.

---

## What it does

- **Scans Gmail every 2 hours** for application confirmations, interview invites,
  recruiter messages, and rejections
- **Maintains a live Google Sheet** as the source of truth — one row per application,
  auto-updated as status changes
- **Sends proactive notifications** (Telegram/WhatsApp/Slack) when new applications
  are found or when an interview is within 3 days
- **Never duplicates** — uses a stable ID scheme and reads current state before
  writing, so re-scanning old emails doesn't create noise
- **Runs fully autonomously** — no commands needed, no interface to open

---

## Architecture

```
Gmail ──────────────────────────────────────────────────────────┐
                                                                │
                         OpenClaw Gateway                       │
                    ┌─────────────────────────┐                 │
  Heartbeat  ──────▶│  Reads SKILL.md         │                 │
  (every 2h)        │  Calls Claude API       │◀────────────────┘
                    │  Executes tool calls    │
                    └─────────┬───────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       Google Sheets    send_message     workspace/
       (state layer)    (Telegram)       config.json
              │
              ▼
         Dashboard
         (index.html)
```

**Key design decisions and why:**

| Decision | Rationale |
|---|---|
| Google Sheets as state | Accessible anywhere, no database to host, shareable |
| Incremental Gmail scan | Only fetches emails since `last_updated` — avoids re-processing |
| `notified_interview_reminder` flag | Prevents duplicate notifications across heartbeat runs |
| `exec: deny` in SKILL.md | Principle of least privilege — agent can't run shell commands |
| Atomic write pattern | Updates `last_updated` only after successful write — safe on crash |
| Separate append vs update tools | Cleaner LLM intent, harder to accidentally overwrite rows |

---

## Project structure

```
job-tracker/
├── SKILL.md                    # Agent definition: tools, policies, instructions
├── workspace/
│   ├── config.example.json     # Config template (copy to config.json, fill in values)
│   └── config.json             # Your real config — gitignored, never committed
├── dashboard/
│   ├── index.html              # Web dashboard — reads Google Sheet, renders pipeline
│   └── server.py               # Local dev server (10 lines of Python)
├── docs/
│   └── architecture.md         # Deeper technical notes
└── README.md
```

---

## Setup

### Prerequisites

- [OpenClaw](https://github.com/openclaw/openclaw) installed
- A Google account with Gmail
- A Google Sheet (blank — the agent creates the schema)
- Telegram bot (or Slack/WhatsApp) for notifications

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/job-tracker-agent.git
cd job-tracker-agent
```

### 2. Configure

```bash
cp workspace/config.example.json workspace/config.json
```

Open `workspace/config.json` and fill in:
- `google_sheets.sheet_id` — from your Google Sheet URL
- `notifications.platform` — telegram, slack, or whatsapp

### 3. Set up Google Sheets

See [sheets_setup.md](./sheets_setup.md) for the exact column layout.
The first row of your sheet must be the header row with column names exactly
as documented.

### 4. Install the skill

```bash
claw skill install ./SKILL.md
claw skill enable job-tracker
```

### 5. Start the Gateway

```bash
claw start
```

The agent will run its first heartbeat within 2 minutes and send you a
confirmation message.

### 6. Open the dashboard (optional)

```bash
cd dashboard
python server.py
```

Open `http://localhost:3000` in your browser.

---

## The Google Sheet schema

| Column | Type | Description |
|---|---|---|
| id | string | Unique key: `company-role-year` |
| company | string | Company name |
| role | string | Job title |
| status | string | `applied` / `screening` / `interview` / `offer` / `rejected` |
| applied_date | date | YYYY-MM-DD |
| interview_date | date | YYYY-MM-DD or empty |
| last_updated | datetime | ISO 8601 — when this row last changed |
| notified_interview_reminder | boolean | TRUE once 3-day reminder is sent |
| source_email_id | string | Gmail message ID of last update |

---

## What I learned building this

This project covers the full stack of AI agent engineering:

**Agent architecture** — the difference between a reactive chatbot and a proactive
agent with a heartbeat loop. The perceive → think → act cycle and why each step
matters.

**Tool design** — why tool descriptions matter more than their implementation,
why splitting `append` and `update` into separate tools produces more reliable
LLM behaviour than one generic `write` tool.

**State design** — why external state (the Google Sheet) is the agent's long-term
memory, how the `notified_interview_reminder` flag prevents the "amnesia problem"
(duplicate notifications), and how `last_updated` enables incremental scanning.

**Prompt engineering for agents** — chain-of-thought step ordering, negative
constraints ("never create duplicate rows"), persona setting, classification
rules with exact phrases rather than vague descriptions.

**Safety boundaries** — the difference between prompted restrictions and enforced
restrictions (`exec: deny` at the framework level vs instructions in the prompt),
and why the principle of least privilege applies to AI agents.

**Failure mode design** — atomic writes, crash recovery via the `last_updated`
pattern, and conservative classification bias ("when in doubt, skip").

---

## Potential improvements

- [ ] Gmail push webhooks instead of polling — event-driven rather than scheduled
- [ ] SQLite instead of JSON for richer querying (current: Google Sheets)
- [ ] `draft_email` tool for auto-drafting follow-ups (pending approval)
- [ ] Multi-user support with per-user sheet IDs
- [ ] Slack app surface for the dashboard instead of local HTML

---

## License

MIT — use it, fork it, build on it.
