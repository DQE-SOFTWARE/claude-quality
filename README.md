<div align="center">
  <img src="docs/banner.svg" alt="dqe-quality — DQE Software" width="100%"/>
</div>

# dqe-quality: Data Quality Audit Plugin for Claude Code

> **Growing suite of data quality tools for Claude Code by [DQE Software](https://github.com/DQE-SOFTWARE).** Currently includes 1 audit skill analysing 6 dimensions and generating up to 2 standalone HTML reports. More skills coming.
>
> **Note:** the plugin is named `dqe-quality` in the marketplace. The GitHub repository is named `claude-quality`.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Plugin-blue)](https://claude.ai/code)
[![Version](https://img.shields.io/badge/version-2.2.0-brightgreen)](https://github.com/DQE-SOFTWARE/claude-quality/releases)
[![Python](https://img.shields.io/badge/Python-stdlib_only-blue)](https://www.python.org/)
[![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](#requirements)
[![Zero-copy](https://img.shields.io/badge/data-zero--copy-blueviolet)](#who-this-is-for)

Analyse CSV files across the 6 DQE quality dimensions and generate standalone branded HTML reports — directly from Claude Code. No pip installs, no API keys, no setup. **Your data never leaves your machine.**

> **Why dqe-quality?**
> - Drop a CSV, get a professional audit report in under 10 seconds
> - Audit report includes Next Steps + CTA; add `--pm` for an internal project manager guide
> - Multilingual output: English, French, German, Spanish — one flag away
> - **Zero-copy** — your data never leaves your machine, everything runs locally

---

## Table of Contents

- [Who this is for](#who-this-is-for)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Skills](#skills)
- [The 6 dimensions](#the-6-dimensions)
- [The reports](#the-reports)
- [Options](#options)
- [Output files](#output-files)
- [Screenshots](#screenshots)
- [File size handling](#file-size-handling)
- [Path handling](#path-handling)
- [Requirements](#requirements)
- [License](#license)

---

## Who this is for

***Data engineers and analysts*** who need a fast, reproducible quality baseline on any CSV before loading it into a pipeline or CRM.

***Project managers and consultants*** who need ready-to-share deliverables — an audit report with actionable next steps and, optionally, an internal treatment plan — without opening a BI tool.

***DQE Software teams*** who audit client data files and need branded, multilingual reports that tie findings directly to DQE service recommendations.

---

## Installation

### Plugin install (recommended — CLI users)

```
/plugin install dqe-quality
```

> The plugin is registered as **`dqe-quality`** in the marketplace. The underlying GitHub repository is `DQE-SOFTWARE/claude-quality`.

---

### Desktop app install — Windows (no git required)

For users with the **Claude.ai desktop app** on Windows who don't have git installed.

Open **PowerShell** and run:

```powershell
irm https://raw.githubusercontent.com/DQE-SOFTWARE/claude-quality/main/install-desktop.ps1 | iex
```

This downloads the skill ZIP from GitHub, extracts it, and copies it to `%USERPROFILE%\.claude\skills\dqe-audit\`. Restart Claude Code desktop when done.

> **Execution policy error?** Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` first, then retry.

---

### Desktop app install — macOS (no git required)

For users with the **Claude.ai desktop app** on macOS who don't have git installed.

Open **Terminal** and run:

```bash
curl -fsSL https://raw.githubusercontent.com/DQE-SOFTWARE/claude-quality/main/install-desktop.sh | bash
```

This downloads the skill ZIP from GitHub, extracts it, and copies it to `~/.claude/skills/dqe-audit/`. Restart Claude Code desktop when done.

---

### Manual install (CLI / Linux / git users)

```bash
git clone --depth 1 https://github.com/DQE-SOFTWARE/claude-quality.git
bash claude-quality/install.sh
```

Or via curl (review before executing):

```bash
curl -fsSL https://raw.githubusercontent.com/DQE-SOFTWARE/claude-quality/main/install.sh > install.sh
cat install.sh
bash install.sh
rm install.sh
```

---

### Requirements

- [Claude Code](https://claude.ai/code) — CLI, desktop app, or IDE extension
- Python 3.x — standard library only, **no `pip install` needed**

---

## Quick start

```bash
# Basic audit — English report (default)
/dqe-audit ~/data/clients.csv

# French report
/dqe-audit ~/data/clients.csv --lang=fr

# Spanish report
/dqe-audit ~/data/clientes.csv --lang=es

# Windows path (auto-converted to WSL)
/dqe-audit "C:\Users\demo\data\export.csv" --lang=de

# Audit + internal PM guide
/dqe-audit ~/data/clients.csv --pm

# French audit + PM guide
/dqe-audit ~/data/clients.csv --lang=fr --pm
```

The audit report is written next to the source CSV within seconds. Add `--pm` to also generate the project manager guide.

---

## Skills

### `/dqe-audit <path/to/file.csv> [--lang=fr|en|us|de|es] [--pm]`

Runs a full data quality audit on a CSV file and generates 1 or 2 standalone HTML reports.

| Argument | Description |
|---|---|
| `path/to/file.csv` | Path to the CSV file — relative, absolute, or Windows format |
| `--lang=XX` | Report language: `en` (default), `us` (alias for en), `fr`, `de`, `es` |
| `--pm` | Also generate the internal Project Manager guide (off by default) |

---

## Multilingual column detection

The engine auto-detects column types from their names across four languages. You do not need to rename your columns — bring the file as-is.

| Context | French | English | German | Spanish |
|---|---|---|---|---|
| First name | `prenom`, `prenom_1` | `firstname`, `first_name` | `vorname` | `nombre`, `nombre_de_pila` |
| Last name | `nom`, `nom_famille` | `lastname`, `last_name`, `surname` | `nachname`, `familienname` | `apellido`, `apellidos` |
| Address | `adresse`, `rue` | `address`, `street` | `strasse` | `direccion`, `calle`, `domicilio` |
| Address 2 | `compl`, `bat`, `appt` | `addr2` | — | `piso`, `complemento` |
| Postal code | `cp`, `code_postal` | `zipcode`, `zip_code`, `postcode` | `plz`, `postleitzahl` | `codigo_postal`, `codigopostal` |
| City | `ville`, `commune` | `city`, `town` | `stadt`, `ort` | `ciudad`, `municipio`, `localidad`, `poblacion` |
| Country | `pays` | `country` | `land` | `pais` |
| Email | `mail`, `courriel` | `email` | `email` | `email` |
| Phone (landline) | `fixe`, `tel`, `telephone` | `phone` | `festnetz` | `telefono`, `fijo`, `tel_fijo` |
| Phone (mobile) | `portable`, `mob` | `mobile`, `cell` | `handy`, `mobilnummer` | `movil`, `celular` |
| Date | `date_*`, `naiss`, `modif` | `date_*`, `birth`, `update` | — | `fecha_*` |
| Salutation | `civ`, `sexe`, `genre` | `gender`, `title` | `anrede` | `tratamiento`, `genero` |
| Company | `entreprise`, `societe`, `enseigne` | `company` | `firma`, `unternehmen` | `empresa`, `compania`, `sociedad` |

> Partial matches work too: a column named `fecha_nacimiento` is detected as a date field, `apellido_paterno` as a last name.

---

## Postal code validation

When a country column is present, postal codes are validated per row against that row's declared country. When no country column exists, the engine infers the dominant format from the data itself.

| Country | Accepted formats | Notes |
|---|---|---|
| France (`FR`, `FRANCE`, `FRA`) | `\d{5}` | Exactly 5 digits |
| Germany (`DE`, `GERMANY`, `DEUTSCHLAND`) | `\d{5}` | Exactly 5 digits |
| Spain (`ES`, `SPAIN`, `ESPAGNE`, `ESPAÑA`) | `\d{5}` | 5 digits, province range 01–52 |
| USA (`US`, `USA`, `UNITED STATES`) | `\d{5}` or `\d{5}-\d{4}` | Base ZIP or ZIP+4 |

Invalid codes are reported in **Dimension 5 — Broken Relationships**, grouped by country.

### ZIP / city cross-check

The engine detects cases where the city name in the city column contradicts the ZIP code prefix — for example, a ZIP starting with `75` (Paris) paired with the city name `LYON`.

**Coverage is intentionally limited to major cities** (~15–20 per country) for France, Germany, Spain, and the US. Detection uses word-boundary matching to avoid partial-word false positives (e.g. `BERLIN` does not match `BERLINCHEN`).

> **For full address validation against official national reference databases**, including all cities and postal codes worldwide, see [DQE RNVP](https://www.dqe-software.com/solutions/rnvp/) — DQE's address standardisation and geocoding service.

---

## The 6 dimensions

| # | Dimension | What it detects |
|---|---|---|
| 1 | **Completeness** | Fill rate per column, globally empty fields |
| 2 | **Invalid dates** | Format errors, future dates, impossible values, mixed formats |
| 3 | **Duplicates** | Exact duplicates, near-duplicates (name+email, name+address) |
| 4 | **Anomalies** | Statistical outliers, generic values (null, test, xxx…), digits in text fields |
| 5 | **Broken relationships** | Postal code format per country (FR/DE/ES/US), ZIP/city mismatches, unreachable contacts (no email, no phone), email with missing identity |
| 6 | **Format inconsistencies** | Mixed phone formats, inconsistent casing, type heterogeneity |

---

## The reports

### 📊 Audit Report — always generated

Full technical analysis for data engineers, analysts, and stakeholders.

- Quality score (0–100) with colour-coded rating
- Column profiling: detected type, fill rate, dominant value type
- Executive summary with 6 dimension cards
- Detailed per-dimension analysis: complete anomaly table per column, all relationship checks (including unreachable contacts, email with missing identity), full format breakdown
- DQE service recommendations based on findings
- Conclusion
- **Next Steps** — numbered action list generated from actual findings, with exact counts and business framing
- **Contact DQE Software** CTA block

### ⚙️ Project Manager Guide — generated with `--pm`

Advanced technical document for DQE internal teams. Only produced when `--pm` is passed.

- Detected parameters: encoding, delimiter, row/column counts, analysis mode
- Full column schema with top values and type distribution
- Detailed per-dimension analysis with problematic value examples
- Quality score formula with actual values
- Prioritised treatment plan: dimension / volume / recommended DQE service / estimated effort / expected gain
- Technical configuration cards per relevant service
- Full column appendix

---

## Options

### `--lang` — Report language

Controls the language of all generated HTML reports. Default: `en`.

| Value | Language | Notes |
|-------|----------|-------|
| `en` | English | Default |
| `us` | English | Alias for `en` |
| `fr` | French | |
| `de` | German | |
| `es` | Spanish | |

### `--pm` — Project Manager guide

When passed, generates the internal Project Manager guide in addition to the audit report. The two files link to each other via a shared navigation bar.

```bash
# Audit only (default)
/dqe-audit clients.csv

# Audit + PM guide
/dqe-audit clients.csv --pm
```

---

## Output files

By default, one HTML file is written next to the source CSV:

```
<basename>_dqe_audit_YYYYMMDD_<lang>.html
```

With `--pm`, a second file is also generated:

```
<basename>_dqe_audit_YYYYMMDD_<lang>.html
<basename>_dqe_pm_guide_YYYYMMDD_<lang>.html
```

The two reports link to each other via a shared navigation bar.

**Collision guard:** if a file with the same name already exists, a numeric suffix is appended automatically:
```
clients_dqe_audit_20260601_en (2).html
```

---

## Screenshots

| 📊 Audit Report | ⚙️ PM Guide |
|---|---|
| ![Audit Report](docs/screenshots/screenshot_audit_en.png) | ![PM Guide](docs/screenshots/screenshot_pm_en.png) |

---

## File size handling

| File size | Behaviour |
|-----------|-----------|
| Up to 200k rows | Full analysis — every row |
| 200k – 500k rows | Auto-sampled (1 in N rows), result extrapolated |
| Above 500k rows | Rejected — tip provided to extract a sample with `head` |

The report indicates when sampling was applied.

---

## Path handling

- Relative and absolute paths are both accepted
- Windows paths (`C:\Users\...`) are automatically converted to WSL paths (`/mnt/c/Users/...`)

---

## Requirements

- [Claude Code](https://claude.ai/code) CLI or IDE extension
- Python 3.x — standard library only, no `pip install` needed

---

## License

MIT — © 2026 [DQE Software](https://github.com/DQE-SOFTWARE)
