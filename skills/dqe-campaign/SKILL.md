---
name: dqe-campaign
description: "End-to-end campaign data quality workflow. Audits contact data (emails, phones, names, addresses) and cleans it via the dqe-one MCP server — email validation, phone validation, deduplication — producing a campaign-ready contact count. Data can come from a local CSV file OR from any remote source accessible via the DQE One Server: Salesforce, Microsoft Dynamics, PostgreSQL, BigQuery, Snowflake, or SFTP. Replicates the VivaTech demo scenario in Claude Code. Use when the user has contact data to clean before a marketing campaign, or asks for a full DQE flow."
user-invokable: true
argument-hint: "[path/to/contacts.csv | --source=salesforce|dynamics|postgres|bigquery|snowflake|sftp|csv] [--lang=fr|en] [--no-server]"
metadata:
  author: DQE Software
  version: "2.0.0"
  category: dqe-one
  requires_mcp: dqe-one (optional — local CSV audit works without it)
---

# DQE Campaign — Contact Data Quality Workflow

Full end-to-end contact data quality: **data source selection → local audit (CSV only) → DQE server cleaning (email · phone · dedup) → campaign-ready count**.

The data can come from a **local CSV file** or from any **remote source** connected to the DQE One Server: Salesforce, Microsoft Dynamics 365, PostgreSQL, BigQuery, Snowflake, or SFTP.

---

## STEP 0 — Parse arguments and determine the data source mode

From `$ARGUMENTS`:
- Any argument that doesn't start with `--` and ends with `.csv` → **LOCAL mode** (CSV path provided)
- `--source=<type>` → **REMOTE mode** with pre-selected source type
- `--lang=fr|en` → output language (default: `en`)
- `--no-server` → skip all MCP server calls; local audit only (only valid in LOCAL mode)

**If neither a CSV path nor `--source` is provided**, go to STEP 1.
**If a CSV path is provided**, go to STEP 2 (LOCAL flow).
**If `--source` is provided**, go to STEP 3 (REMOTE flow).

---

## STEP 1 — Ask where the data lives

> "Where is the contact data you want to analyse and clean?
>
> **A — Local CSV file**
>    Upload or provide a local file path.
>    _Works with or without the DQE One Server._
>
> **B — Remote database (via DQE One Server)**
>    Connect to one of your configured data sources:
>    - Salesforce (Contacts, Leads, or any object)
>    - Microsoft Dynamics 365
>    - PostgreSQL
>    - Google BigQuery
>    - Snowflake
>    - SFTP (remote file)
>    _Requires the `dqe-one` MCP server to be configured._"

- If the user chooses **A** → ask for the CSV file path → go to STEP 2 (LOCAL flow)
- If the user chooses **B** → go to STEP 3 (REMOTE flow)

---

---

# ── LOCAL FLOW (CSV file) ─────────────────────────────────────────────────────

---

## STEP 2 — Install and run the local analysis script

### 2a — Install script (silent)

```bash
[ -f /tmp/dqe_campaign.py ] && python3 /tmp/dqe_campaign.py --version 2>/dev/null && echo "OK" || echo "WRITE"
```

If the result is not `OK`, write the following script to `/tmp/dqe_campaign.py` using the Write tool:

```python
#!/usr/bin/env python3
"""DQE Campaign Analyzer v2.0 — contact data quality for campaign use"""
import csv, json, re, sys, argparse
from collections import Counter

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$')
PHONE_RE = re.compile(r'^\+?[\d][\d\s\-\(\)\.]{6,18}[\d]$')
VERSION = "2.0"

def detect_col_type(name, values):
    n = name.lower().replace('_', '').replace(' ', '').replace('-', '')
    if any(k in n for k in ['email', 'mail', 'courriel', 'e-mail']):
        return 'email'
    if any(k in n for k in ['phone', 'tel', 'mobile', 'fax', 'telephone', 'gsm', 'portable', 'phonenumber']):
        return 'phone'
    if any(k in n for k in ['firstname', 'prenom', 'givenname', 'forename', 'nom1']):
        return 'first_name'
    if any(k in n for k in ['lastname', 'nom', 'surname', 'familyname', 'nom2']):
        return 'last_name'
    if any(k in n for k in ['address', 'adresse', 'rue', 'street', 'addr', 'ligne']):
        return 'address'
    if any(k in n for k in ['zip', 'postal', 'postcode', 'cp', 'codepostal']):
        return 'postal'
    if any(k in n for k in ['city', 'ville', 'town', 'localite', 'commune']):
        return 'city'
    non_empty = [v.strip() for v in values if v.strip()]
    if len(non_empty) >= 10:
        if sum(1 for v in non_empty if EMAIL_RE.match(v)) / len(non_empty) > 0.5:
            return 'email'
        if sum(1 for v in non_empty if PHONE_RE.match(v)) / len(non_empty) > 0.4:
            return 'phone'
    return 'other'

def analyze_email(col, values):
    total = len(values)
    non_empty = [v.strip() for v in values if v.strip()]
    missing = total - len(non_empty)
    valid = [v for v in non_empty if EMAIL_RE.match(v)]
    invalid = len(non_empty) - len(valid)
    domains = Counter(v.split('@')[1].lower() for v in valid if '@' in v)
    return {'column': col, 'total': total, 'missing': missing,
            'valid': len(valid), 'invalid': invalid,
            'top_domains': dict(domains.most_common(3))}

def analyze_phone(col, values):
    total = len(values)
    non_empty = [v.strip() for v in values if v.strip()]
    missing = total - len(non_empty)
    valid = sum(1 for v in non_empty if PHONE_RE.match(v))
    invalid = len(non_empty) - valid
    return {'column': col, 'total': total, 'missing': missing, 'valid': valid, 'invalid': invalid}

def detect_duplicates(rows, key_cols):
    if not key_cols:
        return {'duplicate_records': 0, 'duplicate_groups': 0}
    seen = Counter()
    for row in rows:
        key = tuple(row.get(c, '').strip().lower() for c in key_cols)
        if any(k for k in key):
            seen[key] += 1
    dups = sum(c - 1 for c in seen.values() if c > 1)
    groups = sum(1 for c in seen.values() if c > 1)
    return {'duplicate_records': dups, 'duplicate_groups': groups}

def check_completeness(rows, cols):
    n = len(rows)
    return {col: {'missing': sum(1 for r in rows if not r.get(col, '').strip()),
                  'pct': round(sum(1 for r in rows if not r.get(col, '').strip()) / n * 100, 1) if n else 0}
            for col in cols}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path')
    parser.add_argument('--version', action='version', version=VERSION)
    args = parser.parse_args()

    try:
        with open(args.csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = list(reader.fieldnames or [])
            rows = [dict(r) for r in reader]
    except FileNotFoundError:
        print(json.dumps({'error': f'File not found: {args.csv_path}'}))
        sys.exit(1)

    total = len(rows)
    samples = {h: [r.get(h, '') for r in rows[:300]] for h in headers}
    col_types = {h: detect_col_type(h, samples[h]) for h in headers}

    email_cols = [h for h, t in col_types.items() if t == 'email']
    phone_cols = [h for h, t in col_types.items() if t == 'phone']
    name_cols  = [h for h, t in col_types.items() if t in ('first_name', 'last_name')]
    addr_cols  = [h for h, t in col_types.items() if t in ('address', 'postal', 'city')]

    email_stats = [analyze_email(c, [r.get(c, '') for r in rows]) for c in email_cols]
    phone_stats = [analyze_phone(c, [r.get(c, '') for r in rows]) for c in phone_cols]
    dup_stats   = detect_duplicates(rows, email_cols + phone_cols)

    completeness = check_completeness(rows, email_cols + phone_cols + name_cols[:2])

    issues = 0; max_pts = 0
    for s in email_stats:
        issues += s['invalid'] + s['missing']; max_pts += s['total']
    for s in phone_stats:
        issues += s['invalid'] + s['missing']; max_pts += s['total']
    issues += dup_stats['duplicate_records']; max_pts += total
    score = max(0, round((1 - issues / max_pts) * 100)) if max_pts else 70

    total_invalid_emails = sum(s['invalid'] for s in email_stats)
    total_missing_emails = sum(s['missing'] for s in email_stats)
    total_invalid_phones = sum(s['invalid'] for s in phone_stats)
    duplicates = dup_stats['duplicate_records']
    unusable = max(total_invalid_emails + total_missing_emails, 0) + duplicates
    campaign_ready = max(0, total - unusable)

    print(json.dumps({
        'total_records': total, 'columns': headers, 'column_types': col_types,
        'email_columns': email_cols, 'phone_columns': phone_cols,
        'name_columns': name_cols, 'address_columns': addr_cols,
        'email_stats': email_stats, 'phone_stats': phone_stats,
        'duplicates': dup_stats, 'completeness': completeness,
        'score': score, 'campaign_ready': campaign_ready,
        'issues': {'invalid_emails': total_invalid_emails,
                   'missing_emails': total_missing_emails,
                   'invalid_phones': total_invalid_phones,
                   'duplicates': duplicates}
    }, indent=2))

if __name__ == '__main__':
    main()
```

### 2b — Run the analysis

```bash
python3 /tmp/dqe_campaign.py "<csv_path>"
```

Parse the JSON. If `"error"` key present, show the error and stop.

---

## STEP 2c — Show the local audit card

```
╔══════════════════════════════════════════════════════════════╗
║  DQE Data Quality Audit                                      ║
║  <filename> · <total_records> records · <N> columns          ║
╠══════════════════════════════════════════════════════════════╣
║  Quality Score: <score>/100                                  ║
╠════════════════════════════════════╦═════════════════════════╣
║  📧 Email validation               ║  📱 Phone validation    ║
║  Valid   : <N> (<pct>%)            ║  Valid : <N> (<pct>%)   ║
║  Invalid : <N>                     ║  Invalid: <N>           ║
║  Missing : <N>                     ║  Missing: <N>           ║
╠════════════════════════════════════╩═════════════════════════╣
║  👥 Duplicates detected: <N> records in <N> groups           ║
╠══════════════════════════════════════════════════════════════╣
║  🎯 Campaign-ready estimate: <campaign_ready> / <total>      ║
╚══════════════════════════════════════════════════════════════╝
```

Score label: ≥80 → `🟢 Good quality`, 60–79 → `🟡 Moderate quality`, <60 → `🔴 Low quality — cleaning essential`.

---

## STEP 2d — Propose server-side cleaning

If `--no-server` is set, jump to STEP 6 (next steps, no MCP).

Otherwise ask:
> "I can now run the following through the **DQE One Server**:
> - ✓ Email validation — `check_email` process
> - ✓ Phone validation — `check_phone` process
> - ✓ Deduplication — `check_duplicate` process
>
> This requires the `dqe-one` MCP server to be configured.
> **Proceed?**"

If the user declines → STEP 6.

---

## STEP 2e — Verify MCP + upload file

### Check MCP
Call `list_files` via `dqe-one`. If it fails, show the configuration instructions and stop.

### Read server config
```bash
python3 - <<'PY'
import json, sys
for f in ['.claude/settings.json', '.claude/settings.local.json']:
    try:
        data = json.load(open(f))
        s = data.get('mcpServers', {}).get('dqe-one', {})
        if s.get('url'):
            url = s['url'].replace('/mcp', '')
            auth = s.get('headers', {}).get('Authorization', '')
            print(f"{url}|{auth}")
            sys.exit(0)
    except Exception:
        pass
print("NOT_CONFIGURED")
PY
```

Store `DQE_URL` and `DQE_AUTH`.

### Upload the CSV
```bash
curl -s -X POST "${DQE_URL}/api/File/add" \
  -H "Authorization: ${DQE_AUTH}" \
  -F "file=@<csv_path>"
```

Parse the file `id` from the response.
_"✅ File uploaded — DQE file ID: <id>"_

### Set process parameters
- `source`: `"csv"`
- `file`: `<file_id>` (integer)
- `credential`: not needed
- `object`: not needed
- `primary_key`: first non-email, non-phone column detected; if none found, use the first column
- `email_col`: first detected email column
- `phone_col`: first detected phone column
- `all_fields`: build `{ col: col }` dict from all headers

→ Go to STEP 5 (create + run processes).

---

---

# ── REMOTE FLOW (database / cloud / SFTP) ────────────────────────────────────

---

## STEP 3 — Verify MCP and load available credentials

Call `list_files` via `dqe-one` to verify the MCP server is reachable.
If not connected, show configuration instructions and stop.

In parallel, call `list_credentials` and `list_rulesets`.

Show the list of available credential connections:

| ID | Name | Type |
|----|------|------|
| 1 | Dynamics 365 — Production | Microsoft Dynamics |
| 2 | Salesforce — Marketing Cloud | Salesforce |
| 3 | BigQuery — Data Warehouse | BigQuery |
| … | … | … |

---

## STEP 4 — Collect connection details

### 4a — Choose the credential

> "Which connection holds the contact data for your campaign?"

If only one credential matches the type the user described, propose it automatically.
If `list_credentials` is empty:
> "No data source connections are configured yet. Add one via the DQE One interface at `/connector/`, or use `/dqe-quality:dqe-dedup` to create a process manually."
> Stop.

### 4b — Choose the object / table / file

Ask the user for the object or table name based on the credential type:

| Source type | What to ask | Example |
|-------------|-------------|---------|
| `salesforce` | Salesforce object API name | `Contact`, `Lead`, `Campaign_Response__c` |
| `dynamics` | Dynamics entity / table name | `contact`, `lead`, `cr123_landing_page_june2026` |
| `postgres` | Schema and table name | `public.campaign_contacts` |
| `bigquery` | Dataset and table | `marketing.fathers_day_registrations` |
| `snowflake` | Database, schema, table | `PROD.MARKETING.CAMPAIGN_LEADS` |
| `sftp` | Full remote file path | `/exports/fathers_day_june2026.csv` (and output dir) |

For SFTP, also ask for the output directory path.

### 4c — Identify key fields

Ask the user:
> "Which fields in **<table_name>** contain:
> - The **primary key** (unique record ID) — e.g. `Id`, `ContactId`, `record_id`
> - The **email address** — e.g. `Email`, `EmailAddress`, `mail`
> - The **phone number** — e.g. `Phone`, `MobilePhone`, `PhoneNumber`
>
> Leave blank to skip validation for that field type."

If the user is unsure, suggest common names for the chosen source type:
- Salesforce: `Id` / `Email` / `Phone` or `MobilePhone`
- Dynamics: `contactid` / `emailaddress1` / `mobilephone` or `telephone1`
- PostgreSQL / BigQuery / Snowflake: ask the user — no standard names
- SFTP: ask the user

### 4d — Summarise and confirm

Show a configuration summary before proceeding:

```
Data source : <credential name> (<type>)
Table/Object: <object or table>
Primary key : <pk_field>
Email field : <email_field> (or — if not provided)
Phone field : <phone_field> (or — if not provided)
Operations  : check_email · check_phone · check_duplicate (if ruleset available)
```

Ask for confirmation.

### 4e — Set process parameters

- `source`: credential type (`salesforce`, `dynamics`, `postgres`, `bigquery`, `snowflake`, `sftp`)
- `credential`: credential ID (integer)
- `object`: table / entity / object name (for all types except sftp)
- `input_file_path` / `output_dir_path`: for sftp only
- `primary_key`: as provided by the user
- `email_col`: as provided
- `phone_col`: as provided
- `all_fields`: `{ pk: pk, email_col: "Email", phone_col: "Phone" }` — extend with any other fields the user wants included

→ Go to STEP 5.

---

---

# ── SHARED: CREATE AND RUN PROCESSES ─────────────────────────────────────────

---

## STEP 5 — Create and run cleaning processes

All `create_process` calls use the parameters collected in STEP 2e (LOCAL) or STEP 4e (REMOTE).

The three base parameters that all calls share:
```
name       → "<dataset name> — <operation>"
source     → <source type>
primaryKey → <pk_field>
fields     → <field mapping dict>

# LOCAL only:
file       → <file_id>

# REMOTE only:
credential → <credential_id>
object     → <table_name>     (not sftp)
input_file_path  → <path>     (sftp only)
output_dir_path  → <dir>      (sftp only)
```

### 5a — Email validation (if email field available)

Call `create_process`:
```json
{
  "name": "<dataset> — Email Check",
  "kind": "check_email",
  "source": "<source>",
  "primaryKey": "<pk>",
  "fields": { "<email_col>": "Email" },
  ...source_params
}
```
Call `run_process` immediately with the returned ID.
_"⏳ Email validation running…"_

### 5b — Phone validation (if phone field available)

Call `create_process`:
```json
{
  "name": "<dataset> — Phone Check",
  "kind": "check_phone",
  "source": "<source>",
  "primaryKey": "<pk>",
  "fields": { "<phone_col>": "Phone" },
  ...source_params
}
```
Call `run_process` immediately.
_"⏳ Phone validation running…"_

### 5c — Deduplication (if a ruleset is available)

From the `list_rulesets` result (loaded in STEP 3 or 2e):
- If at least one published ruleset exists: pick the first one (or ask the user if multiple exist)
- If no ruleset: warn and skip — _"⚠️ No deduplication ruleset configured — skipping dedup. Create one in DQEOne, then run `/dqe-quality:dqe-dedup`."_

Call `create_process`:
```json
{
  "name": "<dataset> — Deduplication",
  "kind": "check_duplicate",
  "source": "<source>",
  "primaryKey": "<pk>",
  "fields": { "<pk>": "ID", "<email_col>": "Email", "<phone_col>": "Phone" },
  "ruleSet": <ruleset_id>,
  ...source_params
}
```
Call `run_process` immediately.
_"⏳ Deduplication running…"_

---

## STEP 5d — Poll results

Call `list_runs` for each triggered process ID (in parallel). Show current status.

If any run is still `running` or `queued` after a first poll, check once more after a short delay, then report:
_"⏳ Processes are still executing. Use `/dqe-quality:dqe-list` in a few minutes to see final results."_

Build the cleaning results table for completed runs:

| Operation | Field | Valid (OK) | Invalid (NOK) | Missing | Status |
|-----------|-------|-----------|--------------|---------|--------|
| Email check | `<email_col>` | N (pct%) | N | N | ✅ / ⏳ / ❌ |
| Phone check | `<phone_col>` | N (pct%) | N | N | ✅ / ⏳ / ❌ |
| Deduplication | — | N unique | N duplicates removed | — | ✅ / ⏳ / ❌ |

Then show the campaign-ready summary:

```
═══════════════════════════════════════════
  🎯 Campaign-Ready Dataset
═══════════════════════════════════════════
  Source              : <source type> — <table/file>
  Total contacts      : <total>
  Invalid emails      : -<N>
  Invalid phones      : -<N>
  Duplicates removed  : -<N>
  ─────────────────────────────────────────
  ✅ Ready for campaign : <campaign_ready>
═══════════════════════════════════════════
```

---

## STEP 6 — Next steps

```
What would you like to do next?

  📄 Full HTML audit report (local CSV only)  → /dqe-quality:dqe-audit <csv_path>
  📋 See all processes & runs                 → /dqe-quality:dqe-list
  🔁 Run another process                      → /dqe-quality:dqe-run
  ➕ Create another dedup process             → /dqe-quality:dqe-dedup
```

If the user asks about syncing results to a CRM or sending the validated contacts to a campaign platform, respond:
> "DQE One Server can write results back to your source system or sync to an external platform. Contact DQE Software to configure a sync connector for your campaign tool."
