#!/usr/bin/env python3
"""
DQE CSV Analyzer — 6-dimension data quality analysis
Usage: python3 analyze_csv.py <file.csv> [--progress /tmp/p.log] [--output /tmp/r.json]
"""

import csv
import json
import re
import sys
import os
import time
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import statistics

FULL_ANALYSIS_LIMIT = 200_000
SAMPLE_LIMIT = 500_000
TARGET_SAMPLE_SIZE = 100_000

# ─── CONTEXT DETECTION ────────────────────────────────────────────────────────

CONTEXT_PATTERNS = [
    (r'(?i)(^id$|^(id|num|ref|key|code_c)$)',                                                                  'identifier',    'Identifier',     100),
    # firstname MUST precede lastname: "prenom" and "nombre" contain substrings matched by the lastname pattern
    (r'(?i)(prenom|firstname|first_name|first$|vorname|given_name|^prenom$|^nombre$|nombre_de_pila)',          'firstname',     'First Name',      95),
    (r'(?i)(nom$|^nom_|lastname|last_name|last$|surname|familienname|nachname|^name$|^apellido)',              'lastname',      'Last Name',       95),
    (r'(?i)(^adr1$|^addr1$|adresse1|^rue$|^street$|^strasse$|^voie$|^adresse$|^address$|^adr$|^direccion$|^calle$|^domicilio$)', 'address1', 'Address', 80),
    (r'(?i)(^adr2$|^addr2$|^compl|^bat$|^appt$|lieuit|^piso$|^complemento$)',                                 'address2',      'Address 2',       60),
    (r'(?i)(^cp$|zipcode|zip_code|zip$|code_postal|^postal$|^postcode$|^plz$|postleitzahl|codigo_postal|codigopostal)', 'postal_code', 'Postal Code', 90),
    (r'(?i)(^ville$|^city$|^town$|^commune$|^stadt$|^ort$|^ciudad$|^municipio$|^localidad$|^poblacion$)',      'city',          'City',            95),
    (r'(?i)(^pays$|^country$|^land$|^pais$)',                                                                  'country',       'Country',         99),
    (r'(?i)(email|^mail$|courriel)',                                                                            'email',         'Email',           85),
    (r'(?i)(^fixe$|^tel$|telfixe|^telephone$|^phone$|^tel_fixe$|^festnetz$|^telefono$|^fijo$|tel_fijo)',      'phone_landline','Phone (Landline)', 70),
    (r'(?i)(^portable$|^mobile$|^mob$|^gsm$|^cell$|tel_mob|^handy$|mobilnummer|^movil$|^celular$)',           'phone_mobile',  'Phone (Mobile)',   70),
    (r'(?i)(^date|creat|^modif|naiss|birth|^maj$|^update|^fecha)',                                             'date',          'Date',            85),
    (r'(?i)(^civ$|civil|gender|^sexe$|^title$|^genre$|^anrede$|^tratamiento$|^genero$)',                      'salutation',    'Salutation',      90),
    (r'(?i)(siren|siret|^b2b$|entrepri|company|societe|enseigne|^firma$|unternehmen|empresa|compania|^sociedad$)', 'company', 'Company',         90),
]

def detect_context(col_name):
    for pattern, ctx_key, label, prob in CONTEXT_PATTERNS:
        if re.search(pattern, col_name):
            return ctx_key, label, prob
    return 'unknown', 'Unknown', 50

# ─── POSTAL CODE VALIDATION RULES ────────────────────────────────────────────

# Maps normalised country value → (regex, human description)
# Spain adds a province range check (01–52) inside _validate_postal_code()
POSTAL_CODE_RULES = {
    # France
    'FR':           (r'^\d{5}$',          '5 digits'),
    'FRANCE':       (r'^\d{5}$',          '5 digits'),
    'FRA':          (r'^\d{5}$',          '5 digits'),
    # Germany
    'DE':           (r'^\d{5}$',          '5 digits'),
    'DEU':          (r'^\d{5}$',          '5 digits'),
    'GERMANY':      (r'^\d{5}$',          '5 digits'),
    'DEUTSCHLAND':  (r'^\d{5}$',          '5 digits'),
    'ALLEMAGNE':    (r'^\d{5}$',          '5 digits'),
    # Spain
    'ES':           (r'^\d{5}$',          '5 digits, province 01–52'),
    'ESP':          (r'^\d{5}$',          '5 digits, province 01–52'),
    'SPAIN':        (r'^\d{5}$',          '5 digits, province 01–52'),
    'ESPAGNE':      (r'^\d{5}$',          '5 digits, province 01–52'),
    'ESPAÑA':       (r'^\d{5}$',          '5 digits, province 01–52'),
    # United States
    'US':           (r'^\d{5}(-\d{4})?$', '5 digits or ZIP+4 (NNNNN-NNNN)'),
    'USA':          (r'^\d{5}(-\d{4})?$', '5 digits or ZIP+4 (NNNNN-NNNN)'),
    'UNITED STATES':(r'^\d{5}(-\d{4})?$', '5 digits or ZIP+4 (NNNNN-NNNN)'),
    'ÉTATS-UNIS':   (r'^\d{5}(-\d{4})?$', '5 digits or ZIP+4 (NNNNN-NNNN)'),
    'ETATS-UNIS':   (r'^\d{5}(-\d{4})?$', '5 digits or ZIP+4 (NNNNN-NNNN)'),
}

_ES_KEYS = {'ES', 'ESP', 'SPAIN', 'ESPAGNE', 'ESPAÑA'}


def _validate_postal_code(val, country_key):
    """True if val is a valid postal code for country_key. Unknown country → True (skip)."""
    rule = POSTAL_CODE_RULES.get(country_key)
    if rule is None:
        return True
    pattern, _ = rule
    if not re.fullmatch(pattern, val):
        return False
    if country_key in _ES_KEYS:
        try:
            return 1 <= int(val[:2]) <= 52
        except (ValueError, IndexError):
            return False
    return True


def _infer_country_from_postal_codes(vals):
    """Guess the dominant postal code country from a list of values.
    Returns a POSTAL_CODE_RULES key, or None if undetermined."""
    sample = [v for v in vals if v][:500]
    if not sample:
        return None
    n = len(sample)
    zip4 = sum(1 for v in sample if re.fullmatch(r'\d{5}-\d{4}', v))
    five = sum(1 for v in sample if re.fullmatch(r'\d{5}', v))
    if zip4 / n > 0.10:
        return 'US'
    if five / n > 0.80:
        return 'FR'  # canonical 5-digit validator (covers FR/DE/ES format)
    return None

# ─── ENCODING / DELIMITER ─────────────────────────────────────────────────────

def detect_encoding(fp):
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(fp, encoding=enc, errors='strict') as f:
                f.read(50_000)
            return enc.replace('utf-8-sig', 'utf-8')
        except (UnicodeDecodeError, LookupError):
            continue
    return 'latin-1'

def detect_delimiter(fp, encoding):
    with open(fp, encoding=encoding, errors='replace') as f:
        sample = f.read(5_000)
    counts = {d: sample.count(d) for d in [';', ',', '\t', '|']}
    return max(counts, key=counts.get)

def count_lines_fast(fp):
    """Fast line count using binary read."""
    count = 0
    with open(fp, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            count += chunk.count(b'\n')
    return count

def estimate_seconds(row_count, col_count):
    """Rough ETA: ~0.25ms/row + 1s/column overhead."""
    return max(5, int(row_count * 0.00025 + col_count * 1.0))

# ─── VALUE CLASSIFIERS ────────────────────────────────────────────────────────

def classify_value(v):
    if not v or not v.strip():
        return 'EMPTY'
    v = v.strip()
    if re.fullmatch(r'\d+', v):
        return 'DIGIT'
    if re.fullmatch(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', v):
        return 'EMAIL'
    if re.fullmatch(r'[\d\s\+\-\.\(\)/]{7,20}', v) and sum(c.isdigit() for c in v) >= 7:
        return 'PHONE'
    if re.fullmatch(r"[a-zA-ZÀ-ÿ\s\-\'\.\«\»\(\)]+", v):
        return 'ALPHA'
    return 'OTHER'

# ─── DIMENSION 1 — COMPLETION RATE ───────────────────────────────────────────

def analyze_completion(rows, headers):
    total = len(rows)
    per_col = {}
    for col in headers:
        vals = [r.get(col, '') or '' for r in rows]
        empty = sum(1 for v in vals if not v.strip())
        empty_pct = round(empty / total * 100, 1) if total else 0
        per_col[col] = {
            'empty_count': empty,
            'empty_pct': empty_pct,
            'fill_rate': round(100 - empty_pct, 1),
        }
    global_fill = round(sum(v['fill_rate'] for v in per_col.values()) / max(len(headers), 1), 1)
    return {'per_column': per_col, 'global_fill_rate': global_fill}

# ─── DIMENSION 2 — INVALID DATES ─────────────────────────────────────────────

DATE_PATTERNS = [
    (r'^(\d{4})(\d{2})(\d{2})\d*$', 'YYYYMMDD+'),
    (r'^(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})$', 'DD/MM/YYYY'),
    (r'^(\d{4})[/\-\.](\d{2})[/\-\.](\d{2})$', 'YYYY-MM-DD'),
    (r'^(\d{2})[/\-\.](\d{2})[/\-\.](\d{2})$', 'DD/MM/YY'),
]

def parse_date_parts(val):
    for pattern, fmt in DATE_PATTERNS:
        m = re.fullmatch(pattern, val.strip())
        if m:
            g = m.groups()
            if fmt == 'YYYYMMDD+':
                return int(g[0]), int(g[1]), int(g[2]), fmt
            elif 'DD/MM' in fmt:
                year = int(g[2]) if int(g[2]) > 100 else 2000 + int(g[2])
                return year, int(g[1]), int(g[0]), fmt
            else:
                return int(g[0]), int(g[1]), int(g[2]), fmt
    return None

def analyze_dates(rows, headers, contexts_map):
    date_cols = [h for h in headers if contexts_map.get(h, ('',))[0] == 'date']
    result = {}
    current_year = datetime.now().year
    for col in date_cols:
        vals = [r.get(col, '') or '' for r in rows if (r.get(col, '') or '').strip()]
        issues = defaultdict(int)
        formats_seen = Counter()
        sample_errors = []
        for v in vals:
            parsed = parse_date_parts(v)
            if parsed is None:
                issues['invalid_format'] += 1
                if len(sample_errors) < 5:
                    sample_errors.append(v)
                continue
            year, month, day, fmt = parsed
            formats_seen[fmt] += 1
            if month < 1 or month > 12:
                issues['invalid_month'] += 1
            elif day < 1 or day > 31:
                issues['invalid_day'] += 1
            elif year < 1900:
                issues['year_too_old'] += 1
            elif year > current_year:
                issues['future_date'] += 1
        result[col] = {
            'issue_count': sum(issues.values()),
            'issues_detail': dict(issues),
            'formats_detected': dict(formats_seen),
            'mixed_formats': len(formats_seen) > 1,
            'sample_errors': sample_errors,
        }
    return result

# ─── DIMENSION 3 — DUPLICATE RECORDS ─────────────────────────────────────────

def analyze_duplicates(rows, headers, contexts_map):
    total = len(rows)

    # Exact duplicates
    row_keys = Counter(tuple(r.get(h, '').strip().upper() for h in headers) for r in rows)
    exact_dupes = sum(c - 1 for c in row_keys.values() if c > 1)

    # Near-duplicates
    name_cols = [h for h in headers if contexts_map.get(h, ('',))[0] in ('lastname', 'firstname')]
    email_cols = [h for h in headers if contexts_map.get(h, ('',))[0] == 'email']
    addr_cols  = [h for h in headers if contexts_map.get(h, ('',))[0] in ('address1', 'postal_code', 'city')]

    def near_key(row, cols):
        return '|'.join(row.get(c, '').strip().upper() for c in cols if row.get(c, '').strip())

    near_name_email = sum(
        c - 1
        for c in Counter(near_key(r, name_cols + email_cols) for r in rows
                         if near_key(r, name_cols + email_cols)).values()
        if c > 1
    )
    near_name_addr = sum(
        c - 1
        for c in Counter(near_key(r, name_cols + addr_cols) for r in rows
                         if near_key(r, name_cols + addr_cols)).values()
        if c > 1
    )

    dedup_potential = round(max(exact_dupes, near_name_email) / total * 100, 2) if total else 0
    return {
        'exact_duplicates': exact_dupes,
        'exact_duplicate_pct': round(exact_dupes / total * 100, 2) if total else 0,
        'near_duplicates_name_email': near_name_email,
        'near_duplicates_name_address': near_name_addr,
        'deduplication_potential_pct': dedup_potential,
    }

# ─── DIMENSION 4 — ANOMALIES & OUTLIERS ──────────────────────────────────────

def analyze_anomalies(rows, headers, contexts_map):
    result = {}
    total = len(rows)
    for col in headers:
        ctx = contexts_map.get(col, ('unknown',))[0]
        vals = [r.get(col, '') or '' for r in rows]
        non_empty = [v.strip() for v in vals if v.strip()]
        if not non_empty:
            continue

        issues = []

        # Length outliers (z-score)
        lengths = [len(v) for v in non_empty]
        if len(lengths) > 30:
            mean_l = statistics.mean(lengths)
            stdev_l = statistics.stdev(lengths) if len(lengths) > 1 else 0
            if stdev_l > 0:
                hi = mean_l + 3 * stdev_l
                lo = max(1, mean_l - 3 * stdev_l)
                outlier_long  = sum(1 for l in lengths if l > hi)
                outlier_short = sum(1 for l in lengths if 0 < l < lo)
                if outlier_long > 0:
                    issues.append({'type': 'values_too_long', 'count': outlier_long,
                                   'threshold': f'>{round(hi)} chars'})
                if outlier_short > 0:
                    issues.append({'type': 'values_too_short', 'count': outlier_short,
                                   'threshold': f'<{round(lo)} chars'})

        # Digits inside text fields
        if ctx in ('lastname', 'firstname', 'city'):
            with_digits = sum(1 for v in non_empty if re.search(r'\d', v))
            if with_digits > 0:
                issues.append({'type': 'digits_in_text_field', 'count': with_digits})

        # Placeholder / garbage values
        garbage = sum(1 for v in non_empty
                      if re.fullmatch(r'[-_\.]+|n/?a|null|none|test|xxx+|yyy+|zzz+|toto|tata', v.lower()))
        if garbage > 0:
            issues.append({'type': 'placeholder_values', 'count': garbage})

        # Single-character in meaningful fields
        if ctx in ('lastname', 'firstname', 'address1'):
            single = sum(1 for v in non_empty if len(v.strip()) == 1)
            if single > 0:
                issues.append({'type': 'single_char_values', 'count': single})

        if issues:
            result[col] = {'issues': issues, 'total_values': len(non_empty)}

    return result

# ─── DIMENSION 5 — BROKEN RELATIONSHIPS (A + B + C) ──────────────────────────

def get_col_by_ctx(headers, contexts_map, *ctx_keys):
    for h in headers:
        if contexts_map.get(h, ('',))[0] in ctx_keys:
            return h
    return None

def analyze_broken_relationships(rows, headers, contexts_map):
    issues = []
    total = len(rows)

    cp_col     = get_col_by_ctx(headers, contexts_map, 'postal_code')
    ville_col  = get_col_by_ctx(headers, contexts_map, 'city')
    pays_col   = get_col_by_ctx(headers, contexts_map, 'country')
    email_col  = get_col_by_ctx(headers, contexts_map, 'email')
    nom_col    = get_col_by_ctx(headers, contexts_map, 'lastname')
    prenom_col = get_col_by_ctx(headers, contexts_map, 'firstname')
    adr1_col   = get_col_by_ctx(headers, contexts_map, 'address1')
    fixe_col   = get_col_by_ctx(headers, contexts_map, 'phone_landline')
    mobile_col = get_col_by_ctx(headers, contexts_map, 'phone_mobile')

    # A1 — Postal code format validation (country-aware)
    if cp_col:
        if pays_col:
            # Validate each row against its declared country
            by_country = Counter()
            for r in rows:
                cp_val  = (r.get(cp_col,  '') or '').strip()
                country = (r.get(pays_col, '') or '').strip().upper()
                if cp_val and country in POSTAL_CODE_RULES and not _validate_postal_code(cp_val, country):
                    by_country[country] += 1
            for country_key, count in sorted(by_country.items()):
                _, desc = POSTAL_CODE_RULES[country_key]
                issues.append({'dimension': 'A', 'type': 'postal_code_format_invalid',
                               'country': country_key, 'count': count,
                               'pct': round(count / total * 100, 2),
                               'detail': f'{country_key}: expected {desc}'})
        else:
            # No country column — infer dominant format from the postal codes themselves
            cp_vals = [(r.get(cp_col, '') or '').strip() for r in rows]
            inferred = _infer_country_from_postal_codes(cp_vals)
            if inferred:
                _, desc = POSTAL_CODE_RULES[inferred]
                bad_list = [v for v in cp_vals if v and not _validate_postal_code(v, inferred)]
                if bad_list:
                    issues.append({'dimension': 'A', 'type': 'postal_code_format_invalid',
                                   'count': len(bad_list),
                                   'pct': round(len(bad_list) / total * 100, 2),
                                   'detail': f'Inferred format ({inferred}): expected {desc}'})

    # A2 — CP / VILLE mismatch (major cities)
    DEPT_CITY = {
        '75': 'PARIS', '69': 'LYON', '13': 'MARSEILLE',
        '31': 'TOULOUSE', '33': 'BORDEAUX', '44': 'NANTES',
        '59': 'LILLE', '67': 'STRASBOURG', '06': 'NICE',
    }
    if cp_col and ville_col:
        mismatches = 0
        for r in rows:
            cp    = (r.get(cp_col, '') or '').strip()
            ville = (r.get(ville_col, '') or '').strip().upper()
            dept  = cp[:2] if len(cp) >= 2 else ''
            if dept in DEPT_CITY and ville:
                for other_dept, other_city in DEPT_CITY.items():
                    if other_dept != dept and other_city in ville:
                        mismatches += 1
                        break
        if mismatches > 0:
            issues.append({'dimension': 'A', 'type': 'postal_code_city_mismatch',
                           'count': mismatches, 'pct': round(mismatches / total * 100, 2),
                           'detail': 'Code postal et ville semblent appartenir à des régions différentes'})

    # B1 — Email field contains non-email content
    if email_col:
        bad = sum(
            1 for r in rows
            if (r.get(email_col, '') or '').strip()
            and classify_value(r.get(email_col, '')) not in ('EMAIL', 'EMPTY')
        )
        if bad > 0:
            issues.append({'dimension': 'B', 'type': 'invalid_email_field_content',
                           'count': bad, 'pct': round(bad / total * 100, 2),
                           'detail': 'Champ EMAIL contient des valeurs qui ne sont pas des emails valides'})

    # B2 — Name fields containing digits
    for col, type_key, label in [(nom_col, 'digits_in_lastname', 'NOM'), (prenom_col, 'digits_in_firstname', 'PRENOM')]:
        if col:
            bad = sum(1 for r in rows if re.search(r'\d', r.get(col, '') or ''))
            if bad > 0:
                issues.append({'dimension': 'B', 'type': type_key,
                               'count': bad, 'pct': round(bad / total * 100, 2),
                               'detail': f'Champ {label} contient des chiffres (valeurs suspectes)'})

    # C1 — Incomplete addresses (ADR1 filled but CP or VILLE missing)
    if adr1_col and (cp_col or ville_col):
        bad = sum(
            1 for r in rows
            if (r.get(adr1_col, '') or '').strip()
            and (
                (cp_col    and not (r.get(cp_col, '') or '').strip()) or
                (ville_col and not (r.get(ville_col, '') or '').strip())
            )
        )
        if bad > 0:
            issues.append({'dimension': 'C', 'type': 'incomplete_address',
                           'count': bad, 'pct': round(bad / total * 100, 2),
                           'detail': 'Adresse renseignée (ADR1) mais CP ou VILLE manquant'})

    # C2 — Unreachable contacts (no email AND no phone)
    phone_cols = [c for c in [fixe_col, mobile_col] if c]
    if email_col and phone_cols:
        bad = sum(
            1 for r in rows
            if not (r.get(email_col, '') or '').strip()
            and all(not (r.get(c, '') or '').strip() for c in phone_cols)
        )
        if bad > 0:
            issues.append({'dimension': 'C', 'type': 'unreachable_contact',
                           'count': bad, 'pct': round(bad / total * 100, 2),
                           'detail': 'Aucun moyen de contact disponible (ni email, ni téléphone)'})

    # C3/C4/C5 — Email-identity coherence (ratio over rows with email)
    if email_col and (nom_col or prenom_col):
        rows_with_email = [r for r in rows if (r.get(email_col, '') or '').strip()]
        total_email = len(rows_with_email)
        if total_email > 0:
            # C3 — email present but no lastname
            if nom_col:
                no_nom = sum(1 for r in rows_with_email if not (r.get(nom_col, '') or '').strip())
                if no_nom > 0:
                    issues.append({'dimension': 'C', 'type': 'email_missing_lastname',
                                   'count': no_nom, 'pct': round(no_nom / total_email * 100, 2),
                                   'pct_base': 'emails',
                                   'detail': f'Email renseigné mais NOM manquant ({no_nom}/{total_email} emails)'})

            # C4/C5 — require both nom and prenom columns
            if nom_col and prenom_col:
                # C4 — email present, no lastname AND no firstname (anonymous email)
                no_both = sum(
                    1 for r in rows_with_email
                    if not (r.get(nom_col, '') or '').strip()
                    and not (r.get(prenom_col, '') or '').strip()
                )
                if no_both > 0:
                    issues.append({'dimension': 'C', 'type': 'email_missing_both_names',
                                   'count': no_both, 'pct': round(no_both / total_email * 100, 2),
                                   'pct_base': 'emails',
                                   'detail': f'Email renseigné mais NOM et PRENOM tous deux manquants ({no_both}/{total_email} emails)'})

                # C5 — email present, no lastname OR no firstname (incomplete identity)
                no_any = sum(
                    1 for r in rows_with_email
                    if not (r.get(nom_col, '') or '').strip()
                    or not (r.get(prenom_col, '') or '').strip()
                )
                if no_any > 0:
                    issues.append({'dimension': 'C', 'type': 'email_incomplete_identity',
                                   'count': no_any, 'pct': round(no_any / total_email * 100, 2),
                                   'pct_base': 'emails',
                                   'detail': f'Email renseigné mais NOM ou PRENOM manquant ({no_any}/{total_email} emails)'})

    return {'issues': issues, 'issue_count': len(issues)}

# ─── DIMENSION 6 — FORMAT INCONSISTENCIES ────────────────────────────────────

def analyze_formats(rows, headers, contexts_map):
    result = {}
    for col in headers:
        ctx = contexts_map.get(col, ('unknown',))[0]
        vals = [r.get(col, '') or '' for r in rows]
        non_empty = [v.strip() for v in vals if v.strip()]
        if not non_empty:
            continue

        issues = []

        # Phone format variants
        if ctx in ('phone_landline', 'phone_mobile'):
            fmt_counter = Counter()
            for v in non_empty:
                if v.startswith('+33'):
                    fmt_counter['international (+33...)'] += 1
                elif v.startswith('0033'):
                    fmt_counter['international (0033...)'] += 1
                elif re.match(r'^0\d', v):
                    fmt_counter['local (0X...)'] += 1
                else:
                    fmt_counter['other'] += 1
            if len(fmt_counter) > 1:
                issues.append({'type': 'mixed_phone_formats', 'variants': dict(fmt_counter)})
            # Variable digit counts after stripping separators
            digit_lengths = Counter(
                len(re.sub(r'[\s\.\-\(\)]', '', v)) for v in non_empty
            )
            if len(digit_lengths) > 2:
                issues.append({'type': 'variable_phone_lengths',
                               'distribution': dict(digit_lengths.most_common(5))})

        # Case inconsistencies
        if ctx in ('lastname', 'firstname', 'city'):
            all_upper = sum(1 for v in non_empty if v == v.upper() and not v.isdigit())
            other     = len(non_empty) - all_upper
            if all_upper > 0 and other > 0:
                pct_caps = round(all_upper / len(non_empty) * 100, 1)
                issues.append({'type': 'mixed_case',
                               'all_caps': all_upper, 'other': other,
                               'pct_all_caps': pct_caps})

        # Postal code: missing leading zero (4-digit instead of 5)
        if ctx == 'postal_code':
            with_zero    = sum(1 for v in non_empty if v.startswith('0'))
            four_digit   = sum(1 for v in non_empty if re.fullmatch(r'\d{4}', v))
            if with_zero > 0 and four_digit > 0:
                issues.append({'type': 'postal_code_missing_leading_zero',
                               'with_leading_zero': with_zero, 'four_digit_no_leading_zero': four_digit})

        # Type consistency within column
        types = Counter(classify_value(v) for v in non_empty)
        if len(types) > 1:
            dominant_type, dominant_count = types.most_common(1)[0]
            dominant_pct = dominant_count / len(non_empty) * 100
            if dominant_pct < 95 and dominant_type != 'OTHER':
                issues.append({'type': 'inconsistent_types',
                               'dominant_type': dominant_type,
                               'dominant_pct': round(dominant_pct, 1),
                               'distribution': dict(types.most_common(4))})

        if issues:
            result[col] = {'issues': issues}

    return result

# ─── COLUMN PROFILING ─────────────────────────────────────────────────────────

def profile_columns(rows, headers, contexts_map):
    result = []
    for col in headers:
        ctx_key, ctx_label, ctx_prob = contexts_map.get(col, ('unknown', 'Unknown', 50))
        vals = [r.get(col, '') or '' for r in rows]
        non_empty = [v.strip() for v in vals if v.strip()]
        types = Counter(classify_value(v) for v in vals)
        top_values = Counter(non_empty).most_common(8)
        result.append({
            'name': col,
            'context': ctx_label,
            'context_key': ctx_key,
            'context_probability': ctx_prob,
            'type_distribution': dict(types),
            'top_values': [{'value': v, 'count': c} for v, c in top_values],
        })
    return result

# ─── PRE-FLIGHT CHECKS ────────────────────────────────────────────────────────

def preflight(fp, encoding, delimiter):
    """Returns (ok, errors) — errors is a list of blocking issues."""
    errors = []

    if not os.path.isfile(fp):
        errors.append(f"Fichier introuvable : {fp}")
        return False, errors

    if os.path.getsize(fp) == 0:
        errors.append("Le fichier est vide.")
        return False, errors

    if encoding is None:
        errors.append("Impossible de détecter l'encodage du fichier.")
        return False, errors

    # Check header presence and column consistency (sample first 200 lines)
    try:
        with open(fp, encoding=encoding, errors='replace', newline='') as f:
            reader = csv.reader(f, delimiter=delimiter)
            header = next(reader, None)
            if not header or len(header) < 2:
                errors.append("Header absent ou fichier mono-colonne : vérifiez le délimiteur.")
                return False, errors
            col_count = len(header)
            ragged_lines = 0
            for i, row in enumerate(reader):
                if i >= 200:
                    break
                if len(row) != col_count:
                    ragged_lines += 1
            if ragged_lines > 5:
                errors.append(f"CSV mal formé : {ragged_lines} lignes avec un nombre de colonnes incohérent (attendu {col_count}).")
    except Exception as e:
        errors.append(f"Erreur de lecture du fichier : {e}")
        return False, errors

    return len(errors) == 0, errors

# ─── PROGRESS REPORTER ────────────────────────────────────────────────────────

class Progress:
    def __init__(self, path):
        self.f = open(path, 'w', buffering=1)

    def emit(self, status, pct, step, eta=''):
        bar_filled = int(pct / 5)
        bar = '█' * bar_filled + '░' * (20 - bar_filled)
        eta_str = f'ETA ~{eta}s' if eta else ''
        line = f"{status}|{pct}|[{bar}] {pct}% {step} {eta_str}"
        self.f.write(line + '\n')
        self.f.flush()

    def close(self):
        self.f.close()

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='DQE CSV Analyzer')
    parser.add_argument('csv_file')
    parser.add_argument('--progress', default='/tmp/dqe_progress.log',
                        help='Path for real-time progress log')
    parser.add_argument('--output', default=None,
                        help='Path for JSON result (stdout if omitted)')
    args = parser.parse_args()

    prog = Progress(args.progress)
    t0 = time.time()

    # ── Pre-flight ─────────────────────────────────────────────────────────────
    prog.emit('PREFLIGHT', 0, 'Vérification du fichier...')

    fp = os.path.abspath(args.csv_file)
    encoding  = detect_encoding(fp)
    delimiter = detect_delimiter(fp, encoding)

    ok, errors = preflight(fp, encoding, delimiter)
    if not ok:
        prog.emit('ERROR', 0, ' | '.join(errors))
        prog.close()
        print(json.dumps({'error': errors}, ensure_ascii=False))
        sys.exit(1)

    prog.emit('PREFLIGHT', 3, 'Comptage des lignes...')
    total_lines = count_lines_fast(fp) - 1  # subtract header

    # ── Row limit check ────────────────────────────────────────────────────────
    is_sampled  = False
    sample_step = 1

    if total_lines > SAMPLE_LIMIT:
        msg = (
            f"Fichier trop volumineux : {total_lines:,} lignes (limite : {SAMPLE_LIMIT:,}).\n"
            f"Conseil : head -n {FULL_ANALYSIS_LIMIT + 1} \"{fp}\" > sample.csv"
        )
        prog.emit('ERROR', 0, msg)
        prog.close()
        print(json.dumps({'error': msg}, ensure_ascii=False))
        sys.exit(2)

    if total_lines > FULL_ANALYSIS_LIMIT:
        is_sampled  = True
        sample_step = max(2, total_lines // TARGET_SAMPLE_SIZE)

    # ── ETA estimate ───────────────────────────────────────────────────────────
    # Read headers first to get col count for ETA
    with open(fp, encoding=encoding, errors='replace', newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        headers = list(reader.fieldnames or [])

    effective_rows = total_lines if not is_sampled else (total_lines // sample_step)
    eta_total = estimate_seconds(effective_rows, len(headers))

    sample_note = f' (échantillon 1/{sample_step})' if is_sampled else ''
    prog.emit('PREFLIGHT', 5,
              f'✓ {total_lines:,} lignes · {len(headers)} colonnes{sample_note}',
              str(eta_total))

    # ── Load rows (with optional sampling) ────────────────────────────────────
    prog.emit('STEP', 10, 'Lecture et parsing du fichier...', str(eta_total - 2))
    rows = []
    with open(fp, encoding=encoding, errors='replace', newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for i, row in enumerate(reader):
            if is_sampled and i % sample_step != 0:
                continue
            rows.append(dict(row))

    contexts_map = {h: detect_context(h) for h in headers}
    elapsed = time.time() - t0

    def remaining_eta(fraction_done):
        if fraction_done <= 0:
            return '?'
        total_est = elapsed / fraction_done
        return str(max(0, int(total_est - elapsed)))

    # ── Dimension 1 — Completion ───────────────────────────────────────────────
    prog.emit('STEP', 20, 'Taux de complétude...', remaining_eta(0.20))
    completion = analyze_completion(rows, headers)

    # ── Dimension 2 — Dates ───────────────────────────────────────────────────
    prog.emit('STEP', 35, 'Validation des dates...', remaining_eta(0.35))
    dates = analyze_dates(rows, headers, contexts_map)

    # ── Dimension 3 — Duplicates ──────────────────────────────────────────────
    prog.emit('STEP', 50, 'Détection des doublons...', remaining_eta(0.50))
    dupes = analyze_duplicates(rows, headers, contexts_map)

    # ── Dimension 4 — Anomalies ───────────────────────────────────────────────
    prog.emit('STEP', 65, 'Anomalies & valeurs aberrantes...', remaining_eta(0.65))
    anomalies = analyze_anomalies(rows, headers, contexts_map)

    # ── Dimension 5 — Broken relationships ───────────────────────────────────
    prog.emit('STEP', 80, 'Relations cassées (A+B+C)...', remaining_eta(0.80))
    relationships = analyze_broken_relationships(rows, headers, contexts_map)

    # ── Dimension 6 — Format inconsistencies ─────────────────────────────────
    prog.emit('STEP', 92, 'Cohérence des formats...', remaining_eta(0.92))
    formats = analyze_formats(rows, headers, contexts_map)

    # ── Column profiling ──────────────────────────────────────────────────────
    prog.emit('STEP', 97, 'Profilage des colonnes...', '1')
    columns = profile_columns(rows, headers, contexts_map)

    # ── Quality score ─────────────────────────────────────────────────────────
    fill         = completion['global_fill_rate']
    dupe_penalty = min(dupes['deduplication_potential_pct'], 20)
    rel_penalty  = min(len(relationships['issues']) * 3, 15)
    quality_score = round(max(0, fill - dupe_penalty - rel_penalty), 1)

    result = {
        'filename':      os.path.basename(fp),
        'analysis_date': datetime.now().strftime('%B %d, %Y'),
        'total_rows':    total_lines,
        'analysed_rows': len(rows),
        'is_sampled':    is_sampled,
        'sample_step':   sample_step,
        'total_columns': len(headers),
        'encoding':      encoding.upper(),
        'delimiter':     delimiter,
        'elapsed_seconds': round(time.time() - t0, 1),
        'quality_score': quality_score,
        'columns':       columns,
        'dimensions': {
            '1_completion_rate':        completion,
            '2_invalid_dates':          dates,
            '3_duplicate_records':      dupes,
            '4_anomalies_outliers':     anomalies,
            '5_broken_relationships':   relationships,
            '6_format_inconsistencies': formats,
        },
    }

    prog.emit('DONE', 100, f'Analyse terminée ✓ ({round(time.time()-t0, 1)}s)', '0')
    prog.close()

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as out:
            out.write(output_json)
    else:
        print(output_json)


if __name__ == '__main__':
    main()
