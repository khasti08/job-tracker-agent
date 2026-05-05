# Architecture Notes

Technical decisions, trade-offs, and design reasoning behind the job tracker agent.
This document exists so anyone reading the repo (including future me) understands
*why* things are built the way they are, not just *what* they do.

---

## System overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        OpenClaw Gateway                         │
│                     (background process)                        │
│                                                                 │
│  Every 120 min:                                                 │
│  1. Read SKILL.md                                               │
│  2. Build system prompt (instructions + tool definitions)       │
│  3. Call Claude API → get tool_use response                     │
│  4. Execute tool → feed result back                             │
│  5. Loop until no more tool calls                               │
│  6. Sleep until next heartbeat                                  │
└────────────────┬────────────────────────────────────────────────┘
                 │ reads/writes
                 ▼
        ┌────────────────┐        ┌─────────────────┐
        │  Google Sheets │◀───────│  Dashboard      │
        │  (state layer) │  reads │  index.html     │
        └────────────────┘        └─────────────────┘
                 │
                 │ on change
                 ▼
        ┌────────────────┐
        │ send_message   │
        │ (Telegram etc) │
        └────────────────┘
```

---

## Key design decisions

### 1. Google Sheets as state layer (not a database)

**What we chose:** A Google Sheet with one row per application.

**Why not a local JSON file?**
A local file only exists on the machine running the agent. The dashboard,
running in a browser, can't read local files (browser security — file:// CORS).
We'd need a local server to bridge them, which adds a dependency and breaks
if the machine is off.

**Why not SQLite?**
SQLite would be the right choice for a production system — queryable, crash-safe,
concurrent-write-safe. For a portfolio project used by one person, the operational
overhead isn't worth it. Google Sheets is accessible from anywhere, shareable,
and has a free API.

**The trade-off we're accepting:**
Google Sheets has API rate limits (60 reads/min, 60 writes/min). Our agent
runs every 120 minutes and makes at most ~5 API calls per run — nowhere near
the limit. If this were a multi-user app, Sheets would be the wrong choice.

---

### 2. Incremental Gmail scanning (not full re-scan)

**The problem:** Gmail search on "application OR interview" would return
hundreds of emails going back years. Re-processing all of them every 2 hours
is wasteful and risks re-sending notifications.

**The solution:** We store `last_updated` on every sheet row. At the start
of each heartbeat, the agent reads the sheet and finds the most recent
`last_updated` timestamp. Gmail is then searched only for emails *after*
that timestamp.

**The edge case:** If the sheet is empty (first run), we default to searching
the last 30 days. Configurable in `config.json`.

**The crash-recovery implication:** We only update `last_updated` after a
successful write. If the agent crashes mid-run, `last_updated` is not
advanced — so the next heartbeat re-scans the same window and catches
anything that was missed. This is the "at least once" delivery guarantee.

---

### 3. Deduplication via stable IDs

**The problem:** Gmail search will return the same email on every run
(emails don't disappear). Without deduplication, every heartbeat would
try to add the same application again.

**The solution:** A stable `id` field: `lowercase(company)-lowercase(first-word-of-role)-year`.
Example: `stripe-backend-2025`.

Before writing, the agent reads all existing rows and checks if the id
already exists. If it does, it updates the row (if status changed). If not,
it appends a new row.

**The failure mode:** If two different jobs at the same company have a similar
title (e.g. "Backend Engineer I" and "Backend Engineer II"), they'd get the
same id `stripe-backend-2025` and collide. Acceptable for a personal tracker;
unacceptable for a multi-user system. Fix: append a hash of the source email ID.

---

### 4. Notification deduplication via flag field

**The problem:** The agent runs every 2 hours. An interview 2 days away would
trigger a reminder on every single run — 24+ messages before the interview.

**The solution:** `notified_interview_reminder` boolean column. Starts as FALSE.
The agent checks this before sending. Once sent, it flips to TRUE and never
sends again for that application.

**Why a column in the sheet, not a local file?**
If the agent runs on a different machine (or is reinstalled), a local flag file
would be lost and reminders would re-send. The flag in the sheet persists
regardless of where the agent runs.

---

### 5. Separating append vs update tools

**What we did:** Two separate tools — `google_sheets_append` (new row) and
`google_sheets_update` (edit existing row) — rather than one generic write tool.

**Why:** When you give an LLM one tool that does everything, it has to figure
out internally when to use which behaviour. This produces inconsistent results.
When you give it two tools with clear names and distinct descriptions, it
expresses precise intent. "I want to append a new row" vs "I want to update
row 5" are different operations — they should be different tools.

This also means if `google_sheets_append` has a bug, it can't accidentally
overwrite existing rows. The blast radius of any single tool failure is smaller.

---

### 6. exec: deny — enforced vs prompted safety

**The problem with prompt-level restrictions:**
You can write "never run shell commands" in a system prompt, but a sufficiently
creative prompt injection could talk the agent into doing it anyway. Prompt
restrictions are guidelines; they can be reasoned around.

**The solution:** `exec: deny` in the SKILL.md frontmatter is enforced at the
OpenClaw framework level. The Gateway rejects any shell execution attempt
before it even reaches the LLM response processor. No instruction in the
prompt can override it.

**The principle:** Use framework-level restrictions for hard safety boundaries.
Use prompt-level instructions for behavioural guidance. Never rely on a
prompt to enforce a security guarantee.

---

### 7. Dashboard is read-only

The dashboard calls the Google Sheets API with a read-only API key (restricted
in Google Cloud Console to GET requests only). It cannot write to the sheet.

This means:
- You can't corrupt data by clicking something in the UI
- The API key can be committed to config.example.json with lower risk
  (though we still gitignore the real config.json)
- The agent is the single writer — one source of mutations, easier to debug

---

## What I would change for production

| Current | Production alternative | Reason |
|---|---|---|
| Google Sheets | PostgreSQL / Supabase | Querying, concurrent writes, proper types |
| API key auth | OAuth 2.0 | User-specific access, no shared credentials |
| Polling (heartbeat) | Gmail push webhooks | Event-driven, instant response, no wasted API calls |
| Single-user | Per-user sheet IDs in DB | Multi-tenancy |
| Local dashboard | Deployed (Vercel/Netlify) | Accessible from anywhere, no local server needed |
| JSON config | Environment variables | 12-factor app pattern, works in containers |

---

## Concepts demonstrated

| Concept | Where it appears |
|---|---|
| Agent loop (perceive → think → act) | Gateway heartbeat cycle |
| Tool use | 6 tools in SKILL.md, executed by Gateway |
| External state | Google Sheets as persistent memory |
| Deduplication | `id` field + read-before-write pattern |
| Notification deduplication | `notified_interview_reminder` flag |
| Incremental processing | `last_updated` as scan cursor |
| Least privilege | `exec: deny`, read-only API key, minimal tool list |
| Crash recovery | Atomic `last_updated` advancement |
| Chain-of-thought prompting | Numbered steps in SKILL.md |
| Negative constraints | "Rules you must always follow" section |
| Separation of concerns | Agent writes, dashboard reads, sheet is shared state |
