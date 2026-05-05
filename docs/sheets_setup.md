# Google Sheets Setup

This sheet is the shared state layer between the OpenClaw agent and the dashboard.
The agent writes to it. The dashboard reads from it.

---

## Step 1 — Create the sheet

1. Go to sheets.google.com and create a new blank spreadsheet
2. Rename it: **Job Applications**
3. Rename the first tab (bottom left): **Applications**
4. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/THIS_IS_YOUR_SHEET_ID/edit`
5. Paste the Sheet ID into `workspace/config.json` under `google_sheets.sheet_id`

---

## Step 2 — Create the header row

Click cell A1 and add these headers **exactly** as written (case-sensitive):

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| id | company | role | status | applied_date | interview_date | last_updated | notified_interview_reminder | source_email_id |

The agent references columns by name. If a header is misspelled, the agent
will fail silently or write to the wrong column.

---

## Column reference

| Column | Type | Example | Set by |
|---|---|---|---|
| id | string | `stripe-backend-2025` | Agent (on first add) |
| company | string | `Stripe` | Agent |
| role | string | `Backend Engineer` | Agent |
| status | string | `interview` | Agent (updates on change) |
| applied_date | date | `2025-04-10` | Agent (immutable after set) |
| interview_date | date | `2025-04-28` | Agent (empty until confirmed) |
| last_updated | datetime | `2025-04-24T09:00:00Z` | Agent (every write) |
| notified_interview_reminder | boolean | `FALSE` | Agent (flips to TRUE once) |
| source_email_id | string | `msg-18f3a2c...` | Agent |

---

## Step 3 — Format the sheet (optional but recommended)

- **Freeze row 1** (View → Freeze → 1 row) so headers stay visible when scrolling
- **Column D (status)**: add data validation → List of items:
  `applied,screening,interview,offer,rejected`
  This lets you manually update status from a dropdown, same as the agent does.
- **Column G (last_updated)**: format as Date time (Format → Number → Date time)

---

## Step 4 — Share with the service account

When you set up the Google Sheets API (see README), Google gives you a
service account email that looks like:

`job-tracker@your-project.iam.gserviceaccount.com`

Share your sheet with that email address (Editor access).
The agent authenticates as this service account when reading and writing.

---

## Valid status values

The agent only ever writes one of these five values to the status column:

| Value | Meaning |
|---|---|
| `applied` | Application submitted, no response yet |
| `screening` | Recruiter/phone screen scheduled or completed |
| `interview` | Technical or on-site interview confirmed |
| `offer` | Offer received |
| `rejected` | Rejected at any stage |

You can manually change the status in the sheet at any time.
The agent will not overwrite a manual change unless it sees a newer email
that contradicts it.

---

## Troubleshooting

**Agent writes to wrong column** → Check header spelling in row 1. Must be exact.

**Agent can't access the sheet** → Check the service account email has Editor
access to the sheet.

**Duplicate rows appearing** → The `id` column is the deduplication key.
Check if two rows have the same id — if so, delete the duplicate manually.

**Sheet ID not working** → Make sure you copied only the ID portion of the URL,
not the full URL.