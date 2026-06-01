---
name: dqe-audit
description: "CSV data quality audit — analyses 6 DQE dimensions (completeness, invalid dates, duplicates, anomalies, broken relationships, formats) and generates a branded standalone HTML audit report (with Next Steps + CTA), and optionally a project manager guide with --pm. Use when the user asks for an audit, quality analysis, DQE analysis, or provides a CSV file to analyse. Trigger with /dqe-audit <path/to/file.csv>"
user-invokable: true
argument-hint: "<path/to/file.csv> [--lang=fr|en|us|de|es] [--pm]"
metadata:
  author: DQE Software
  version: "2.1.0"
  category: data-quality
---

# DQE CSV Audit — Agent Skill

You are a data quality audit agent for DQE Software. When this skill is triggered, you analyse a CSV file across 6 DQE dimensions and generate **1 or 2 professional HTML reports**: a technical audit report (always, includes Next Steps + CTA), and optionally a project manager guide (when `--pm` is passed).

---

## STEP 0 — Extract file path and locale

The CSV file path is provided in `$ARGUMENTS`.

Extract:
1. The CSV path: any argument that does not start with `--`
2. The language: `--lang=XX` parameter if present (fr, en, us, de, es). `us` is an alias for `en`. Default: `en`
3. The PM flag: `--pm` if present. Set `WITH_PM=true`, otherwise `WITH_PM=false`.

If no CSV file is found, reply:
```
Please provide the path to your CSV file:
  /dqe-audit /path/to/file.csv [--lang=fr|en|us|de|es] [--pm]
```
And stop.

### Localization Table

Use these labels in all generated HTML based on the chosen language:

| Key | fr | en | de | es |
|-----|----|----|----|----|
| doc_audit | Rapport d'Audit | Audit Report | Prüfbericht | Informe de Auditoría |
| doc_pm | Guide Chef de Projet | Project Manager Guide | PM-Leitfaden | Guía del Jefe de Proyecto |
| nav_audit | 📊 Rapport d'Audit | 📊 Audit Report | 📊 Prüfbericht | 📊 Informe |
| nav_pm | ⚙️ Guide Chef de Projet | ⚙️ PM Guide | ⚙️ PM-Leitfaden | ⚙️ Guía PM |
| score_label | Score Qualité | Quality Score | Qualitätsscore | Puntuación |
| records | enregistrements | records | Datensätze | registros |
| columns | colonnes | columns | Spalten | columnas |
| analysed_in | Analysé en | Analysed in | Analysiert in | Analizado en |
| completeness | Complétude | Completeness | Vollständigkeit | Completitud |
| invalid_dates | Dates invalides | Invalid Dates | Ungültige Daten | Fechas inválidas |
| duplicates | Doublons | Duplicates | Duplikate | Duplicados |
| anomalies | Anomalies | Anomalies | Anomalien | Anomalías |
| relationships | Relations cassées | Broken Relationships | Defekte Beziehungen | Relaciones rotas |
| formats | Formats | Format Issues | Formatprobleme | Formatos |
| recommendations | Recommandations | Recommendations | Empfehlungen | Recomendaciones |
| conclusion | Conclusion | Conclusion | Fazit | Conclusión |
| confidential_pm | Usage interne DQE | DQE Internal Use | Interne DQE-Nutzung | Uso interno DQE |
| next_steps | Prochaines étapes | Next Steps | Nächste Schritte | Próximos pasos |
| next_steps_sub | Ce qu'il faut faire maintenant | What to do now to improve your data quality | Was jetzt zu tun ist | Qué hacer ahora |
| cta_title | Améliorons votre qualité de données | Let's improve your data quality | Verbessern wir Ihre Datenqualität | Mejoremos su calidad de datos |
| cta_sub | Nos experts DQE peuvent traiter ce fichier et livrer des données propres, enrichies et conformes — avec un score cible supérieur à 80/100. | Our DQE experts can process this file and deliver clean, enriched, and compliant data — targeting a quality score above 80/100. | Unsere DQE-Experten können diese Datei verarbeiten und saubere, angereicherte und konforme Daten liefern — mit einem Ziel-Score über 80/100. | Nuestros expertos DQE pueden procesar este archivo y entregar datos limpios, enriquecidos y conformes — con un puntaje objetivo superior a 80/100. |
| cta_btn | Contacter DQE Software | Contact DQE Software | DQE Software kontaktieren | Contactar DQE Software |
| tech_context | Contexte technique | Technical Context | Technischer Kontext | Contexto técnico |
| treatment_plan | Plan de traitement | Treatment Plan | Behandlungsplan | Plan de tratamiento |

---

## STEP 1 — Install the analysis script (automatic, silent)

Check if the script already exists:
```bash
[ -f /tmp/dqe_analyze.py ] && python3 /tmp/dqe_analyze.py --version 2>/dev/null && echo "OK" || echo "WRITE"
```

If the result is not `OK`, write the following script to `/tmp/dqe_analyze.py` via the Write tool:

```python
#!/usr/bin/env python3
"""DQE CSV Analyzer v1.0 — 6-dimension data quality analysis"""
import csv, json, re, sys, os, time, argparse
from collections import Counter, defaultdict
from datetime import datetime
import statistics

__version__ = "2.1"

FULL_LIMIT   = 200_000
SAMPLE_LIMIT = 500_000
TARGET_SAMPLE = 100_000

CONTEXT_PATTERNS = [
    (r'(?i)(^id$|^(id|num|ref|key|code_c)$)',                                                                  'identifier',    'Identifier',     100),
    (r'(?i)(prenom|firstname|first_name|first$|vorname|given_name|^prenom$|^nombre$|nombre_de_pila)',          'firstname',     'First Name',      95),
    (r'(?i)(nom$|^nom_|lastname|last_name|last$|surname|familienname|nachname|^name$|^apellido)',              'lastname',      'Last Name',       95),
    (r'(?i)(^adr1$|^addr1$|adresse1|^rue$|^street$|^strasse$|^voie$|^adresse$|^address$|^adr$|^direccion$|^calle$|^domicilio$)','address1','Address', 80),
    (r'(?i)(^adr2$|^addr2$|compl|^bat$|^appt$|^piso$|^complemento$)',                                         'address2',      'Address 2',       60),
    (r'(?i)(^cp$|zipcode|zip_code|zip$|code_postal|^postal$|^postcode$|^plz$|postleitzahl|codigo_postal|codigopostal)','postal_code','Postal Code', 90),
    (r'(?i)(^ville$|^city$|^town$|^commune$|^stadt$|^ort$|^ciudad$|^municipio$|^localidad$|^poblacion$)',      'city',          'City',            95),
    (r'(?i)(^pays$|^country$|^land$|^pais$)',                                                                  'country',       'Country',         99),
    (r'(?i)(email|^mail$|courriel)',                                                                            'email',         'Email',           85),
    (r'(?i)(^fixe$|^tel$|telfixe|^telephone$|^phone$|^tel_fixe$|^festnetz$|^telefono$|^fijo$|tel_fijo)',      'phone_landline','Phone (Landline)', 70),
    (r'(?i)(^portable$|^mobile$|^mob$|^gsm$|^cell$|tel_mob|^handy$|mobilnummer|^movil$|^celular$)',           'phone_mobile',  'Phone (Mobile)',   70),
    (r'(?i)(^date|creat|^modif|naiss|birth|^maj$|^update|^fecha)',                                             'date',          'Date',            85),
    (r'(?i)(^civ$|civil|gender|^sexe$|^title$|^genre$|^anrede$|^tratamiento$|^genero$)',                      'salutation',    'Salutation',      90),
    (r'(?i)(siren|siret|^b2b$|entrepri|company|societe|enseigne|^firma$|unternehmen|empresa|compania|^sociedad$)','company',   'Company',         90),
]

def detect_context(col):
    for pat, key, label, prob in CONTEXT_PATTERNS:
        if re.search(pat, col):
            return key, label, prob
    return 'unknown', 'Unknown', 50

POSTAL_CODE_RULES={
    'FR':(r'^\d{5}$','5 digits'),'FRANCE':(r'^\d{5}$','5 digits'),'FRA':(r'^\d{5}$','5 digits'),
    'DE':(r'^\d{5}$','5 digits'),'DEU':(r'^\d{5}$','5 digits'),'GERMANY':(r'^\d{5}$','5 digits'),
    'DEUTSCHLAND':(r'^\d{5}$','5 digits'),'ALLEMAGNE':(r'^\d{5}$','5 digits'),
    'ES':(r'^\d{5}$','5 digits, province 01-52'),'ESP':(r'^\d{5}$','5 digits, province 01-52'),
    'SPAIN':(r'^\d{5}$','5 digits, province 01-52'),'ESPAGNE':(r'^\d{5}$','5 digits, province 01-52'),
    'ESPAÑA':(r'^\d{5}$','5 digits, province 01-52'),
    'US':(r'^\d{5}(-\d{4})?$','5 digits or ZIP+4'),'USA':(r'^\d{5}(-\d{4})?$','5 digits or ZIP+4'),
    'UNITED STATES':(r'^\d{5}(-\d{4})?$','5 digits or ZIP+4'),
    'ÉTATS-UNIS':(r'^\d{5}(-\d{4})?$','5 digits or ZIP+4'),
    'ETATS-UNIS':(r'^\d{5}(-\d{4})?$','5 digits or ZIP+4'),
}
_ES_KEYS={'ES','ESP','SPAIN','ESPAGNE','ESPAÑA'}

def _vcp(val, ck):
    rule=POSTAL_CODE_RULES.get(ck)
    if not rule: return True
    if not re.fullmatch(rule[0],val): return False
    if ck in _ES_KEYS:
        try: return 1<=int(val[:2])<=52
        except: return False
    return True

def _infer_cp_country(vals):
    s=[v for v in vals if v][:500]
    if not s: return None
    n=len(s)
    if sum(1 for v in s if re.fullmatch(r'\d{5}-\d{4}',v))/n>0.10: return 'US'
    if sum(1 for v in s if re.fullmatch(r'\d{5}',v))/n>0.80: return 'FR'
    return None

def detect_encoding(fp):
    for enc in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            with open(fp, encoding=enc, errors='strict') as f: f.read(50_000)
            return enc.replace('utf-8-sig', 'utf-8')
        except: continue
    return 'latin-1'

def detect_delimiter(fp, enc):
    with open(fp, encoding=enc, errors='replace') as f: s = f.read(5_000)
    return max([';',',','\t','|'], key=s.count)

def count_lines(fp):
    n = 0
    with open(fp,'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''): n += chunk.count(b'\n')
    return n

def estimate_eta(rows, cols):
    return max(5, int(rows*0.00025 + cols*1.0))

def classify(v):
    if not v or not v.strip(): return 'EMPTY'
    v = v.strip()
    if re.fullmatch(r'\d+', v): return 'DIGIT'
    if re.fullmatch(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', v): return 'EMAIL'
    if re.fullmatch(r'[\d\s\+\-\.\(\)/]{7,20}', v) and sum(c.isdigit() for c in v)>=7: return 'PHONE'
    if re.fullmatch(r"[a-zA-ZÀ-ÿ\s\-\'\.\«\»\(\)]+", v): return 'ALPHA'
    return 'OTHER'

class Progress:
    def __init__(self, path):
        self.f = open(path, 'w', buffering=1)
    def emit(self, status, pct, step, eta=''):
        bar = '█'*int(pct/5) + '░'*(20-int(pct/5))
        eta_s = f'ETA ~{eta}s' if eta else ''
        self.f.write(f"{status}|{pct}|[{bar}] {pct}% {step} {eta_s}\n")
        self.f.flush()
    def close(self): self.f.close()

def preflight(fp, enc, delim):
    errs = []
    if not os.path.isfile(fp): errs.append(f"File not found: {fp}"); return False, errs
    if os.path.getsize(fp)==0: errs.append("File is empty."); return False, errs
    try:
        with open(fp, encoding=enc, errors='replace', newline='') as f:
            r = csv.reader(f, delimiter=delim)
            hdr = next(r, None)
            if not hdr or len(hdr)<2: errs.append("Missing or single-column header."); return False, errs
            nc = len(hdr); rag=0
            for i,row in enumerate(r):
                if i>=200: break
                if len(row)!=nc: rag+=1
            if rag>5: errs.append(f"Malformed CSV: {rag} inconsistent rows.")
    except Exception as e: errs.append(str(e))
    return len(errs)==0, errs

def analyze_completion(rows, headers):
    total=len(rows); per={}
    for col in headers:
        vals=[r.get(col,''or'') for r in rows]
        empty=sum(1 for v in vals if not v.strip())
        ep=round(empty/total*100,1) if total else 0
        per[col]={'empty_count':empty,'empty_pct':ep,'fill_rate':round(100-ep,1)}
    gf=round(sum(v['fill_rate'] for v in per.values())/max(len(headers),1),1)
    return {'per_column':per,'global_fill_rate':gf}

DATE_PATS=[(r'^(\d{4})(\d{2})(\d{2})\d*$','YMD'),(r'^(\d{2})[/\-\.](\d{2})[/\-\.](\d{4})$','DMY4'),
           (r'^(\d{4})[/\-\.](\d{2})[/\-\.](\d{2})$','Y-M-D'),(r'^(\d{2})[/\-\.](\d{2})[/\-\.](\d{2})$','DMY2')]

def parse_date(val):
    for pat,fmt in DATE_PATS:
        m=re.fullmatch(pat,val.strip())
        if m:
            g=m.groups()
            if fmt=='YMD': return int(g[0]),int(g[1]),int(g[2]),fmt
            if fmt in('DMY4','DMY2'):
                y=int(g[2]) if int(g[2])>100 else 2000+int(g[2])
                return y,int(g[1]),int(g[0]),fmt
            return int(g[0]),int(g[1]),int(g[2]),fmt
    return None

def analyze_dates(rows, headers, cmap):
    date_cols=[h for h in headers if cmap.get(h,('',))[0]=='date']
    res={}; cy=datetime.now().year
    for col in date_cols:
        vals=[r.get(col,''or'') for r in rows if (r.get(col,'')or'').strip()]
        issues=defaultdict(int); fmts=Counter(); errs=[]
        for v in vals:
            p=parse_date(v)
            if p is None:
                issues['invalid_format']+=1
                if len(errs)<5: errs.append(v)
                continue
            y,m,d,fmt=p; fmts[fmt]+=1
            if m<1 or m>12: issues['invalid_month']+=1
            elif d<1 or d>31: issues['invalid_day']+=1
            elif y<1900: issues['year_too_old']+=1
            elif y>cy: issues['future_date']+=1
        res[col]={'issue_count':sum(issues.values()),'issues_detail':dict(issues),
                  'formats_detected':dict(fmts),'mixed_formats':len(fmts)>1,'sample_errors':errs}
    return res

def analyze_duplicates(rows, headers, cmap):
    total=len(rows)
    rk=Counter(tuple(r.get(h,'').strip().upper() for h in headers) for r in rows)
    exact=sum(c-1 for c in rk.values() if c>1)
    nc=[h for h in headers if cmap.get(h,('',))[0] in('lastname','firstname')]
    ec=[h for h in headers if cmap.get(h,('',))[0]=='email']
    ac=[h for h in headers if cmap.get(h,('',))[0] in('address1','postal_code','city')]
    def nk(row,cols): return '|'.join(row.get(c,'').strip().upper() for c in cols if row.get(c,'').strip())
    ne=sum(c-1 for c in Counter(nk(r,nc+ec) for r in rows if nk(r,nc+ec)).values() if c>1)
    na=sum(c-1 for c in Counter(nk(r,nc+ac) for r in rows if nk(r,nc+ac)).values() if c>1)
    dp=round(max(exact,ne)/total*100,2) if total else 0
    return {'exact_duplicates':exact,'exact_duplicate_pct':round(exact/total*100,2) if total else 0,
            'near_duplicates_name_email':ne,'near_duplicates_name_address':na,'deduplication_potential_pct':dp}

def analyze_anomalies(rows, headers, cmap):
    res={}
    for col in headers:
        ctx=cmap.get(col,('unknown',))[0]
        non_empty=[v.strip() for v in (r.get(col,''or'') for r in rows) if v.strip()]
        if not non_empty: continue
        issues=[]
        lengths=[len(v) for v in non_empty]
        if len(lengths)>30:
            ml=statistics.mean(lengths); sl=statistics.stdev(lengths) if len(lengths)>1 else 0
            if sl>0:
                hi=ml+3*sl; lo=max(1,ml-3*sl)
                ol=sum(1 for l in lengths if l>hi); os_=sum(1 for l in lengths if 0<l<lo)
                if ol>0: issues.append({'type':'values_too_long','count':ol,'threshold':f'>{round(hi)} chars'})
                if os_>0: issues.append({'type':'values_too_short','count':os_,'threshold':f'<{round(lo)} chars'})
        if ctx in('lastname','firstname','city'):
            wd=sum(1 for v in non_empty if re.search(r'\d',v))
            if wd>0: issues.append({'type':'digits_in_text_field','count':wd})
        garb=sum(1 for v in non_empty if re.fullmatch(r'[-_\.]+|n/?a|null|none|test|xxx+|yyy+|zzz+|toto|tata',v.lower()))
        if garb>0: issues.append({'type':'placeholder_values','count':garb})
        if ctx in('lastname','firstname','address1'):
            sc=sum(1 for v in non_empty if len(v.strip())==1)
            if sc>0: issues.append({'type':'single_char_values','count':sc})
        if issues: res[col]={'issues':issues,'total_values':len(non_empty)}
    return res

def _norm_cty(s):
    _M={'FR':'FR','FRANCE':'FR','FRA':'FR','DE':'DE','GERMANY':'DE','DEUTSCHLAND':'DE',
        'ALLEMAGNE':'DE','DEU':'DE','ES':'ES','SPAIN':'ES','ESPAGNE':'ES','ESPAÑA':'ES','ESP':'ES',
        'US':'US','USA':'US','UNITED STATES':'US','ÉTATS-UNIS':'US','ETATS-UNIS':'US'}
    return _M.get((s or '').strip().upper())

CZT={
    'FR':(2,{'75':('PARIS',),'69':('LYON',),'13':('MARSEILLE',),'31':('TOULOUSE',),
             '33':('BORDEAUX',),'44':('NANTES',),'59':('LILLE',),'67':('STRASBOURG',),
             '06':('NICE',),'34':('MONTPELLIER',),'76':('ROUEN',),'35':('RENNES',),
             '38':('GRENOBLE',),'57':('METZ',),'21':('DIJON',),'51':('REIMS',),'49':('ANGERS',)}),
    'DE':(2,{'10':('BERLIN',),'11':('BERLIN',),'12':('BERLIN',),'13':('BERLIN',),'14':('BERLIN',),
             '20':('HAMBURG',),'21':('HAMBURG',),'22':('HAMBURG',),
             '80':('MÜNCHEN','MUNICH','MUENCHEN'),'81':('MÜNCHEN','MUNICH','MUENCHEN'),
             '50':('KÖLN','KOELN','COLOGNE'),'51':('KÖLN','KOELN','COLOGNE'),
             '60':('FRANKFURT',),'63':('FRANKFURT',),'65':('FRANKFURT',),
             '70':('STUTTGART',),'40':('DÜSSELDORF','DUSSELDORF','DUESSELDORF'),
             '44':('DORTMUND',),'04':('LEIPZIG',),'01':('DRESDEN',),
             '30':('HANNOVER','HANOVER'),'28':('BREMEN',),'90':('NÜRNBERG','NUREMBERG','NUERNBERG')}),
    'ES':(2,{'28':('MADRID',),'08':('BARCELONA',),'41':('SEVILLA','SEVILLE'),
             '46':('VALENCIA',),'48':('BILBAO',),'29':('MÁLAGA','MALAGA'),
             '15':('A CORUÑA','CORUÑA','CORUNA'),'18':('GRANADA',),'03':('ALICANTE',),
             '14':('CÓRDOBA','CORDOBA'),'47':('VALLADOLID',),'50':('ZARAGOZA',),
             '30':('MURCIA',),'33':('OVIEDO','GIJÓN','GIJON'),'35':('LAS PALMAS',),
             '07':('PALMA',),'20':('SAN SEBASTIÁN','SAN SEBASTIAN','DONOSTIA')}),
    'US':(3,{'100':('NEW YORK',),'101':('NEW YORK',),'102':('NEW YORK',),'103':('NEW YORK',),'104':('NEW YORK',),
             '900':('LOS ANGELES',),'901':('LOS ANGELES',),'902':('LOS ANGELES',),
             '606':('CHICAGO',),'607':('CHICAGO',),'608':('CHICAGO',),
             '770':('HOUSTON',),'771':('HOUSTON',),'772':('HOUSTON',),
             '850':('PHOENIX',),'851':('PHOENIX',),'852':('PHOENIX',),'853':('PHOENIX',),
             '191':('PHILADELPHIA',),'192':('PHILADELPHIA',),
             '782':('SAN ANTONIO',),'783':('SAN ANTONIO',),
             '921':('SAN DIEGO',),'922':('SAN DIEGO',),
             '752':('DALLAS',),'753':('DALLAS',),'754':('DALLAS',),
             '950':('SAN JOSE',),'951':('SAN JOSE',),'941':('SAN FRANCISCO',),
             '787':('AUSTIN',),'981':('SEATTLE',),'802':('DENVER',),'803':('DENVER',),
             '021':('BOSTON',),'022':('BOSTON',),'303':('ATLANTA',),
             '331':('MIAMI',),'332':('MIAMI',),'891':('LAS VEGAS',),
             '972':('PORTLAND',),'554':('MINNEAPOLIS',)}),
}

def _czm(cp,vl,plen,pmap):
    px=cp[:plen]
    if px not in pmap: return False
    own=set(pmap[px]); vu=vl.upper()
    for op,oc in pmap.items():
        if op==px: continue
        if any(c not in own and re.search(r'\b'+re.escape(c)+r'\b',vu) for c in oc): return True
    return False

def gcol(headers, cmap, *keys):
    for h in headers:
        if cmap.get(h,('',))[0] in keys: return h
    return None

def analyze_relationships(rows, headers, cmap):
    issues=[]; total=len(rows)
    cp=gcol(headers,cmap,'postal_code'); vil=gcol(headers,cmap,'city')
    pay=gcol(headers,cmap,'country'); em=gcol(headers,cmap,'email')
    nom=gcol(headers,cmap,'lastname'); pre=gcol(headers,cmap,'firstname')
    adr=gcol(headers,cmap,'address1'); fix=gcol(headers,cmap,'phone_landline')
    mob=gcol(headers,cmap,'phone_mobile')

    if cp:
        if pay:
            bc=Counter()
            for r in rows:
                cv=(r.get(cp,'')or'').strip(); co=(r.get(pay,'')or'').strip().upper()
                if cv and co in POSTAL_CODE_RULES and not _vcp(cv,co): bc[co]+=1
            for ck,cnt in sorted(bc.items()):
                _,desc=POSTAL_CODE_RULES[ck]
                issues.append({'dimension':'A','type':'postal_code_format_invalid','country':ck,
                               'count':cnt,'pct':round(cnt/total*100,2),'detail':f'{ck}: expected {desc}'})
        else:
            cpv=[(r.get(cp,'')or'').strip() for r in rows]
            inf=_infer_cp_country(cpv)
            if inf:
                _,desc=POSTAL_CODE_RULES[inf]
                bl=[v for v in cpv if v and not _vcp(v,inf)]
                if bl: issues.append({'dimension':'A','type':'postal_code_format_invalid','count':len(bl),
                                       'pct':round(len(bl)/total*100,2),'detail':f'Inferred ({inf}): expected {desc}'})
    if cp and vil:
        mm=0
        if pay:
            for r in rows:
                cv=(r.get(cp,'')or'').strip(); vv=(r.get(vil,'')or'').strip()
                cn=_norm_cty(r.get(pay,'')or'')
                if cv and vv and cn and cn in CZT:
                    pl,pm=CZT[cn]
                    if _czm(cv,vv,pl,pm): mm+=1
        else:
            inf=_infer_cp_country([(r.get(cp,'')or'').strip() for r in rows])
            if inf and inf in CZT:
                pl,pm=CZT[inf]
                for r in rows:
                    cv=(r.get(cp,'')or'').strip(); vv=(r.get(vil,'')or'').strip()
                    if cv and vv and _czm(cv,vv,pl,pm): mm+=1
        if mm>0: issues.append({'dimension':'A','type':'postal_code_city_mismatch','count':mm,
                                  'pct':round(mm/total*100,2),
                                  'detail':'ZIP/city mismatch on major cities (FR/DE/ES/US) — DQE RNVP for full coverage'})
    if em:
        bad=sum(1 for r in rows if (r.get(em,'')or'').strip() and classify(r.get(em,'')) not in('EMAIL','EMPTY'))
        if bad>0: issues.append({'dimension':'B','type':'invalid_email_field_content','count':bad,
                                  'pct':round(bad/total*100,2),'detail':'EMAIL field contains non-email values'})
    for col,tk,lbl in [(nom,'digits_in_lastname','LASTNAME'),(pre,'digits_in_firstname','FIRSTNAME')]:
        if col:
            bad=sum(1 for r in rows if re.search(r'\d',r.get(col,''or'')))
            if bad>0: issues.append({'dimension':'B','type':tk,'count':bad,
                                      'pct':round(bad/total*100,2),'detail':f'{lbl} field contains digits'})
    if adr and (cp or vil):
        bad=sum(1 for r in rows if (r.get(adr,'')or'').strip() and
                ((cp and not(r.get(cp,'')or'').strip()) or (vil and not(r.get(vil,'')or'').strip())))
        if bad>0: issues.append({'dimension':'C','type':'incomplete_address','count':bad,
                                  'pct':round(bad/total*100,2),'detail':'Address provided but ZIP or CITY missing'})
    phones=[c for c in [fix,mob] if c]
    if em and phones:
        bad=sum(1 for r in rows if not(r.get(em,'')or'').strip()
                and all(not(r.get(c,'')or'').strip() for c in phones))
        if bad>0: issues.append({'dimension':'C','type':'unreachable_contact','count':bad,
                                  'pct':round(bad/total*100,2),'detail':'No contact method (no email or phone)'})
    if em and (nom or pre):
        rwe=[r for r in rows if(r.get(em,'')or'').strip()]; te=len(rwe)
        if te>0:
            if nom:
                nn=sum(1 for r in rwe if not(r.get(nom,'')or'').strip())
                if nn>0: issues.append({'dimension':'C','type':'email_missing_lastname','count':nn,
                                        'pct':round(nn/te*100,2),'pct_base':'emails',
                                        'detail':f'Email provided but LASTNAME missing ({nn}/{te} emails)'})
            if nom and pre:
                nb=sum(1 for r in rwe if not(r.get(nom,'')or'').strip() and not(r.get(pre,'')or'').strip())
                if nb>0: issues.append({'dimension':'C','type':'email_missing_both_names','count':nb,
                                        'pct':round(nb/te*100,2),'pct_base':'emails',
                                        'detail':f'Email provided but both LASTNAME and FIRSTNAME missing ({nb}/{te} emails)'})
                na=sum(1 for r in rwe if not(r.get(nom,'')or'').strip() or not(r.get(pre,'')or'').strip())
                if na>0: issues.append({'dimension':'C','type':'email_incomplete_identity','count':na,
                                        'pct':round(na/te*100,2),'pct_base':'emails',
                                        'detail':f'Email provided but LASTNAME or FIRSTNAME missing ({na}/{te} emails)'})
    return {'issues':issues,'issue_count':len(issues)}

def analyze_formats(rows, headers, cmap):
    res={}
    for col in headers:
        ctx=cmap.get(col,('unknown',))[0]
        non_empty=[v.strip() for v in (r.get(col,''or'') for r in rows) if v.strip()]
        if not non_empty: continue
        issues=[]
        if ctx in('phone_landline','phone_mobile'):
            fc=Counter()
            for v in non_empty:
                if v.startswith('+33'): fc['international (+33)']+=1
                elif v.startswith('0033'): fc['international (0033)']+=1
                elif re.match(r'^0\d',v): fc['local (0X)']+=1
                else: fc['other']+=1
            if len(fc)>1: issues.append({'type':'mixed_phone_formats','variants':dict(fc)})
            dl=Counter(len(re.sub(r'[\s\.\-\(\)]','',v)) for v in non_empty)
            if len(dl)>2: issues.append({'type':'variable_phone_lengths','distribution':dict(dl.most_common(5))})
        if ctx in('lastname','firstname','city'):
            au=sum(1 for v in non_empty if v==v.upper() and not v.isdigit())
            ot=len(non_empty)-au
            if au>0 and ot>0: issues.append({'type':'mixed_case','all_caps':au,'other':ot,
                                              'pct_all_caps':round(au/len(non_empty)*100,1)})
        if ctx=='postal_code':
            wz=sum(1 for v in non_empty if v.startswith('0'))
            fd=sum(1 for v in non_empty if re.fullmatch(r'\d{4}',v))
            if wz>0 and fd>0: issues.append({'type':'postal_code_missing_leading_zero','with_leading_zero':wz,'four_digit_no_leading_zero':fd})
        types=Counter(classify(v) for v in non_empty)
        if len(types)>1:
            dt,dc=types.most_common(1)[0]; dp=dc/len(non_empty)*100
            if dp<95 and dt!='OTHER': issues.append({'type':'inconsistent_types','dominant':dt,
                                                       'pct':round(dp,1),'dist':dict(types.most_common(4))})
        if issues: res[col]={'issues':issues}
    return res

def profile_columns(rows, headers, cmap):
    out=[]
    for col in headers:
        ck,cl,cp=cmap.get(col,('unknown','Unknown',50))
        vals=[r.get(col,''or'') for r in rows]
        ne=[v.strip() for v in vals if v.strip()]
        out.append({'name':col,'context':cl,'context_key':ck,'context_probability':cp,
                    'type_distribution':dict(Counter(classify(v) for v in vals)),
                    'top_values':[{'value':v,'count':c} for v,c in Counter(ne).most_common(8)]})
    return out

def main():
    if '--version' in sys.argv: print(__version__); sys.exit(0)
    p=argparse.ArgumentParser(); p.add_argument('csv_file')
    p.add_argument('--progress',default='/tmp/dqe_progress.log')
    p.add_argument('--output',default=None)
    args=p.parse_args()
    prog=Progress(args.progress); t0=time.time()
    prog.emit('PREFLIGHT',0,'Checking file...')
    fp=os.path.abspath(args.csv_file)
    enc=detect_encoding(fp); delim=detect_delimiter(fp,enc)
    ok,errs=preflight(fp,enc,delim)
    if not ok:
        prog.emit('ERROR',0,' | '.join(errs)); prog.close()
        print(json.dumps({'error':errs},ensure_ascii=False)); sys.exit(1)
    prog.emit('PREFLIGHT',3,'Counting lines...')
    total_lines=count_lines(fp)-1
    if total_lines>SAMPLE_LIMIT:
        msg=f"File too large: {total_lines:,} rows (max {SAMPLE_LIMIT:,}). Suggestion: head -n {FULL_LIMIT+1} \"{fp}\" > sample.csv"
        prog.emit('ERROR',0,msg); prog.close(); print(json.dumps({'error':msg},ensure_ascii=False)); sys.exit(2)
    is_sampled=total_lines>FULL_LIMIT
    step=max(2,total_lines//TARGET_SAMPLE) if is_sampled else 1
    with open(fp,encoding=enc,errors='replace',newline='') as f:
        reader=csv.DictReader(f,delimiter=delim); headers=list(reader.fieldnames or [])
    eff=total_lines if not is_sampled else total_lines//step
    eta=estimate_eta(eff,len(headers))
    prog.emit('PREFLIGHT',5,f'✓ {total_lines:,} rows · {len(headers)} columns{"  (sample 1/"+str(step)+")" if is_sampled else ""}',str(eta))
    prog.emit('STEP',10,'Reading file...',str(eta-2))
    rows=[]
    with open(fp,encoding=enc,errors='replace',newline='') as f:
        reader=csv.DictReader(f,delimiter=delim)
        for i,row in enumerate(reader):
            if is_sampled and i%step!=0: continue
            rows.append(dict(row))
    cmap={h:detect_context(h) for h in headers}
    def rem(frac): elapsed=time.time()-t0; return str(max(0,int(elapsed/frac-elapsed))) if frac>0 else '?'
    prog.emit('STEP',20,'Completeness rate...',rem(0.20)); comp=analyze_completion(rows,headers)
    prog.emit('STEP',35,'Date validation...',rem(0.35)); dates=analyze_dates(rows,headers,cmap)
    prog.emit('STEP',50,'Duplicate detection...',rem(0.50)); dupes=analyze_duplicates(rows,headers,cmap)
    prog.emit('STEP',65,'Anomalies & outliers...',rem(0.65)); anom=analyze_anomalies(rows,headers,cmap)
    prog.emit('STEP',80,'Broken relationships (A+B+C)...',rem(0.80)); rels=analyze_relationships(rows,headers,cmap)
    prog.emit('STEP',92,'Format consistency...',rem(0.92)); fmts=analyze_formats(rows,headers,cmap)
    prog.emit('STEP',97,'Column profiling...','1'); cols=profile_columns(rows,headers,cmap)
    fill=comp['global_fill_rate']; dp=min(dupes['deduplication_potential_pct'],20); rp=min(len(rels['issues'])*3,15)
    qs=round(max(0,fill-dp-rp),1)
    result={'filename':os.path.basename(fp),'analysis_date':datetime.now().strftime('%B %d, %Y'),
            'total_rows':total_lines,'analysed_rows':len(rows),'is_sampled':is_sampled,'sample_step':step,
            'total_columns':len(headers),'encoding':enc.upper(),'delimiter':delim,
            'elapsed_seconds':round(time.time()-t0,1),'quality_score':qs,'columns':cols,
            'dimensions':{'1_completion_rate':comp,'2_invalid_dates':dates,'3_duplicate_records':dupes,
                          '4_anomalies_outliers':anom,'5_broken_relationships':rels,'6_format_inconsistencies':fmts}}
    prog.emit('DONE',100,f'Analysis complete ✓ ({round(time.time()-t0,1)}s)','0')
    prog.close()
    out=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        with open(args.output,'w',encoding='utf-8') as f: f.write(out)
    else: print(out)

if __name__=='__main__': main()
```

---

## STEP 2 — Validate the CSV file

Resolve the absolute path. If Windows path (`C:\...`), convert to WSL (`/mnt/c/...`):

```bash
CSV_PATH=$(realpath "$CSV_FILE" 2>/dev/null || echo "INVALID")
[ -f "$CSV_PATH" ] && echo "OK:$CSV_PATH" || echo "MISSING:$CSV_PATH"
```

If `MISSING`, inform the user and stop.

---

## STEP 3 — Run the analysis with real-time progress

```bash
SID=$(date +%s) && echo "SID=$SID"
```

Run in background (`run_in_background: true`):
```bash
python3 /tmp/dqe_analyze.py "$CSV_PATH" \
  --progress "/tmp/dqe_prog_${SID}.log" \
  --output "/tmp/dqe_result_${SID}.json"
```

Then Monitor for progress:
```bash
tail -n +1 -f /tmp/dqe_prog_${SID}.log | while IFS= read -r line; do
  STAT=$(echo "$line" | cut -d'|' -f1)
  DISP=$(echo "$line" | cut -d'|' -f3)
  echo "$DISP"
  { [ "$STAT" = "DONE" ] || [ "$STAT" = "ERROR" ]; } && break
done
```

If `ERROR`, display the message and stop.

---

## STEP 4 — Read the results

```bash
cat /tmp/dqe_result_${SID}.json
```

Parse the JSON. Normalize the locale (`us` → `en`), then compute output paths with collision detection:

```bash
DIR=$(dirname "$CSV_PATH")
BASE=$(basename "$CSV_PATH" .csv)
[ "$LANG" = "us" ] && LANG="en"
DATE_TAG=$(date +%Y%m%d)

# Returns the available path: base_suffix_DATE_LANG.html, then base_suffix_DATE_LANG (2).html, etc.
compute_out() {
  local p="${DIR}/${BASE}_${1}_${DATE_TAG}_${LANG}.html"
  if [ ! -f "$p" ]; then echo "$p"; return; fi
  local n=2
  while [ -f "${DIR}/${BASE}_${1}_${DATE_TAG}_${LANG} (${n}).html" ]; do n=$((n+1)); done
  echo "${DIR}/${BASE}_${1}_${DATE_TAG}_${LANG} (${n}).html"
}

AUDIT_PATH=$(compute_out "dqe_audit")
[ "$WITH_PM" = "true" ] && PM_PATH=$(compute_out "dqe_pm_guide") || PM_PATH=""
echo "AUDIT=$AUDIT_PATH"
[ -n "$PM_PATH" ] && echo "PM=$PM_PATH"
```

The generated files will link to each other via the nav-bar using basenames only (without path). The PM guide link only appears in the nav-bar when `--pm` was used.

---

## COMMON DESIGN SYSTEM

All pages share this colour palette and base CSS classes:

```
Colours:
  --primary : #1933AC   (DQE blue)
  --accent  : #00dba3   (teal green)
  --good    : #00B486 / #00dba3
  --warn    : #FFB700
  --bad     : #E74C3C / #ff6b6b
  --bg      : #F5F5F5
  --text    : #1a1a2e

HTML Logo (with fallback):
  <img src="https://dqe.tech/wp-content/uploads/2022/05/logo-DQE-noBase-light.svg"
       alt="DQE Software" height="32"
       onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
  <div class="cover-logo-text" style="display:none">DQE<span style="color:#00dba3">.</span></div>

Score colouring:
  >= 80 → good (#00dba3) · 60-79 → warn (#FFB700) · < 60 → bad (#ff6b6b)

Nav-bar (shared across generated files, active link = background #1933AC):
- If `WITH_PM=false` (audit only): omit the nav-bar entirely.
- If `WITH_PM=true` (audit + PM guide): render the nav-bar with 2 links:
  <div class="nav-bar">
    <span class="nav-label">Deliverables</span>
    <div class="nav-links">
      <a href="{AUDIT_BASENAME}" class="nav-link {active|pm}">📊 {nav_audit}</a>
      <a href="{PM_BASENAME}" class="nav-link {active|pm}">⚙️ {nav_pm}</a>
    </div>
  </div>

Base CSS:
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  html{font-size:14px}
  body{font-family:'Segoe UI',Arial,sans-serif;background:#F5F5F5;color:#1a1a2e;line-height:1.6}
  .page-wrap{max-width:960px;margin:0 auto;padding:32px 24px}
  .nav-bar{background:#fff;border-radius:10px;margin-bottom:20px;padding:12px 24px;
    display:flex;align-items:center;gap:20px;box-shadow:0 1px 4px rgba(0,0,0,.06);flex-wrap:wrap}
  .nav-label{font-size:11px;font-weight:700;color:#7a7a8c;text-transform:uppercase;letter-spacing:.5px;flex-shrink:0}
  .nav-links{display:flex;gap:10px;flex-wrap:wrap}
  .nav-link{font-size:12px;padding:5px 14px;border-radius:20px;text-decoration:none;font-weight:600}
  .nav-link.active{background:#1933AC;color:#fff}
  .nav-link.client,.nav-link.pm{background:#e8ecf8;color:#1933AC}
  .cover{background:#1933AC;
    background-image:radial-gradient(ellipse at 80% 20%,#2a47d4 0%,#1933AC 50%,#0f1f6e 100%);
    color:#fff;border-radius:16px;margin-bottom:28px;overflow:hidden}
  .cover-top-bar{background:rgba(0,0,0,.2);padding:14px 40px;
    display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.1)}
  .cover-logo{display:flex;align-items:center;gap:10px}
  .cover-logo-text{font-size:22px;font-weight:900;letter-spacing:-.5px;color:#fff}
  .cover-body{padding:52px 40px 44px}
  .cover-eyebrow{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#00dba3;margin-bottom:12px;font-weight:600}
  .cover-title{font-size:38px;font-weight:900;line-height:1.15;margin-bottom:6px;letter-spacing:-.5px}
  .cover-date{font-size:12px;opacity:.65;letter-spacing:1px}
  .section{background:#fff;border-radius:12px;margin-bottom:20px;
    box-shadow:0 1px 4px rgba(0,0,0,.06),0 4px 16px rgba(0,0,0,.04);overflow:hidden}
  .sec-header{background:#1933AC;padding:18px 28px;display:flex;align-items:center;gap:14px}
  .sec-num{width:30px;height:30px;border-radius:50%;background:#00dba3;color:#0f1f6e;
    font-size:13px;font-weight:900;display:flex;align-items:center;justify-content:center;flex-shrink:0}
  .sec-title{font-size:16px;font-weight:700;color:#fff}
  .sec-sub{font-size:11px;color:rgba(255,255,255,.55);margin-top:2px}
  .sec-body{padding:24px 28px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  thead tr{background:#f0f3fc}
  th{padding:10px 14px;text-align:left;font-weight:700;color:#1933AC;border-bottom:2px solid #dce3f5}
  td{padding:9px 14px;border-bottom:1px solid #f0f3f7;vertical-align:middle}
  tbody tr:last-child td{border-bottom:none}
  tbody tr:hover{background:#fafbff}
  .badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;white-space:nowrap}
  .b-ok{background:#d4f5eb;color:#0a7a56}
  .b-warn{background:#fff3cd;color:#856404}
  .b-err{background:#fde8e8;color:#c0392b}
  .b-info{background:#e8ecf8;color:#1933AC}
  .bar{display:inline-flex;align-items:center;gap:8px}
  .bar-track{width:80px;height:7px;background:#eee;border-radius:4px;overflow:hidden;flex-shrink:0}
  .bar-fill{height:100%;border-radius:4px}
  .fill-good{background:#00B486}.fill-med{background:#FFB700}.fill-bad{background:#E74C3C}
  .narrative{font-size:13.5px;line-height:1.85;color:#333;margin-bottom:16px}
  .narrative strong{color:#1933AC}
  .report-footer{text-align:center;padding:24px;font-size:12px;color:#aaa;border-top:1px solid #eee;margin-top:32px}
  .report-footer strong{color:#1933AC}
  @media print{body{background:#fff}.section,.nav-bar{box-shadow:none;border:1px solid #ddd}
    .cover{border-radius:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
```

---

## STEP 5 — Document 1: Audit Report (technical)

Generate `${AUDIT_PATH}` via Write tool. This document is the complete technical report.

**Audit report structure:**

**Cover**: DQE logo + date | title = `{doc_audit} — {filename}` | eyebrow = "CSV Data Quality Audit" | covered metrics:
- Score badge: `{quality_score}/100` coloured by thresholds
- KPIs: `{total_rows:,} {records}` · `{total_columns} {columns}` · `{encoding}` · `{analysed_in} {elapsed_seconds}s`
- If sampled: ⚠️ banner `Analysis on sample 1/{sample_step}`

**Nav-bar**: omit if `WITH_PM=false`; if `WITH_PM=true`, render with active link on "Audit Report" and a link to pm_guide

**Section 1 — Technical Analysis** (`{tech_context}`):
Table: Encoding / Delimiter / Total rows / Columns / Empty columns / Duration / Mode (full or sample)

**Section 2 — Column profiling**:
Table per column: Name | Detected context | Confidence | Fill rate (fill bar) | Dominant type | Status (badge ok/warn/err)

**Section 3 — Executive summary**:
6 dim-cards (3×2 grid), one per dimension. Each card: icon + localised name + main value + 1-line detail
Additional CSS:
```
.dim-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:24px}
.dim-card{border-radius:10px;padding:18px;border-top:3px solid #1933AC;background:#f8f9fd}
.dim-card.dg{border-top-color:#00B486;background:#f0faf6}
.dim-card.dw{border-top-color:#FFB700;background:#fffbf0}
.dim-card.db{border-top-color:#E74C3C;background:#fdf2f2}
.dim-icon{font-size:20px;margin-bottom:6px}
.dim-name{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#7a7a8c;margin-bottom:4px}
.dim-val{font-size:28px;font-weight:900;color:#1933AC;line-height:1}
.dim-card.dg .dim-val{color:#0a7a56}
.dim-card.dw .dim-val{color:#856404}
.dim-card.db .dim-val{color:#c0392b}
.dim-detail{font-size:11px;color:#7a7a8c;margin-top:5px;line-height:1.5}
```
Followed by a narrative paragraph of 3–4 sentences summarising the overall state.

**Section 4 — Detailed analysis across 6 dimensions**:
Sub-sections 4.1 to 4.6. **CRITICAL: include EVERY detected issue from the JSON — do not omit minor ones.** Each sub-section contains:
- metric boxes (alert/warn/good) for key figures
- **4.4 Anomalies**: always render as a full table (Column | Issue | Count | Severity) covering ALL columns with issues — including values_too_long, values_too_short, single_char_values, placeholder_values, digits_in_text_field for every affected column (NOM, PRENOM, ADR1, CP, VILLE, EMAIL, FIXE, PORTABLE, etc.)
- **4.5 Broken Relationships**: render ALL issues from `5_broken_relationships.issues` as `.iss` entries with their dimension prefix [A]/[B]/[C] — including low-volume items like `digits_in_firstname` (count: 2), `incomplete_address` (count: 1), and `email_incomplete_identity` (e.g. "6 emails with NOM or PRENOM missing"). Never truncate to only the top 3 issues.
- **4.6 Format Inconsistencies**: render ALL columns with issues including VILLE mixed-case, CP leading-zero detail, FIXE variable digit counts, and ADR2 mixed types

Additional CSS:
```
.metrics{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:20px}
.mbox{flex:1;min-width:150px;border-radius:10px;padding:16px 20px;background:#f8f9fd;border-top:3px solid #1933AC}
.mbox.alert{border-top-color:#E74C3C;background:#fdf2f2}
.mbox.warn{border-top-color:#FFB700;background:#fffbf0}
.mbox.good{border-top-color:#00B486;background:#f0faf6}
.mbox-val{font-size:28px;font-weight:900;color:#1933AC;line-height:1}
.mbox.alert .mbox-val{color:#c0392b}
.mbox.warn .mbox-val{color:#856404}
.mbox.good .mbox-val{color:#0a7a56}
.mbox-label{font-size:11px;color:#7a7a8c;margin-top:4px;line-height:1.4}
.subsec{margin-bottom:32px}
.subsec-title{font-size:14px;font-weight:800;color:#1933AC;margin-bottom:14px;
  padding-bottom:8px;border-bottom:2px solid #e8ecf8;display:flex;align-items:center;gap:8px}
.subsec-title .stag{background:#1933AC;color:#fff;font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700}
.stag.ok{background:#00B486}.stag.warn{background:#FFB700;color:#0f1f6e}.stag.bad{background:#E74C3C}
.iss{display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #f0f3f7}
.iss:last-child{border-bottom:none}
.iss-ico{font-size:16px;flex-shrink:0;margin-top:2px}
.iss-title{font-weight:600;font-size:13px;margin-bottom:3px}
.iss-detail{font-size:12px;color:#7a7a8c;line-height:1.5}
```

**Section 5 — Recommendations**:
2-column grid of reco-cards (background #1933AC). Service selection rules:
- Invalid addresses / inconsistent ZIP / `postal_code_city_mismatch` → DQE Address (RNVP) — specify in the reco text that detection covers only major cities (FR/DE/ES/US) and that the RNVP service enables cross-checking for all cities worldwide
- Empty or invalid email → DQE Email
- Mixed phone formats / empty → DQE Phone
- Duplicates > 1% → DQE Deduplication
- Unreachable contacts > 10% → DQE Enrich
- Score < 70 or widespread anomalies → DQE One
- Score < 80 (systematic) → DQE Monitoring

CSS:
```
.reco-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.reco-card{border-radius:12px;padding:22px;background:#1933AC;color:#fff;position:relative;overflow:hidden}
.reco-card::before{content:'';position:absolute;top:-20px;right:-20px;width:80px;height:80px;
  border-radius:50%;background:rgba(0,219,163,.15)}
.reco-tag{display:inline-block;background:#00dba3;color:#0f1f6e;font-size:10px;
  font-weight:800;padding:2px 8px;border-radius:4px;margin-bottom:10px;letter-spacing:.5px;position:relative}
.reco-svc{font-size:15px;font-weight:800;margin-bottom:8px;position:relative}
.reco-why{font-size:12.5px;opacity:.88;line-height:1.6;margin-bottom:14px;position:relative}
.reco-impact{font-size:12px;background:rgba(0,219,163,.2);border:1px solid rgba(0,219,163,.3);
  border-radius:6px;padding:6px 12px;display:inline-block;font-weight:600;color:#00dba3;position:relative}
```

**Section 6 — Conclusion**:
4–5 sentences: score + qualification / positive point / critical issue in figures / DQE Software call to action.

**Section 7 — {next_steps}** (`{next_steps_sub}`):
Numbered list of 3–5 concrete, prioritised action steps generated dynamically from the actual findings. Each step must reference real numbers from the analysis. Use this logic to select and order steps:
1. If date issues found → "Fix the [column name] date export at source" — explain how (re-export with proper date format) and mention the volume impacted
2. If postal_code_format_invalid or postal_code_city_mismatch → "Run DQE Address to correct postal codes" — cite the exact count of corrections available (e.g., "2,804 corrections available with minimal processing time")
3. If near_duplicates > 0 → "Deduplicate before your next campaign" — cite the exact near-duplicate count; explain the risk (inflated unsubscribe rate, sender reputation damage)
4. If unreachable_contact count > 0 → "Enrich to recover the {N} unreachable contacts" — cite the exact % and count; frame as "real business opportunity"
5. Always add → "Set up ongoing data quality monitoring" — recommend DQE Monitoring to prevent future degradation

CSS:
```
.steps{list-style:none;margin:0;padding:0}
.step{display:flex;gap:16px;padding:16px 0;border-bottom:1px solid #f0f3f7;align-items:flex-start}
.step:last-child{border-bottom:none}
.step-num{width:34px;height:34px;border-radius:50%;background:#1933AC;color:#fff;
  font-size:14px;font-weight:900;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px}
.step-content h4{font-size:13.5px;font-weight:700;color:#1933AC;margin-bottom:4px}
.step-content p{font-size:12.5px;color:#555;line-height:1.6}
```

**CTA block** (placed after the steps list, inside the section body):
```html
<div style="background:#1933AC;background-image:radial-gradient(ellipse at 70% 30%,#2a47d4 0%,#1933AC 70%);
  color:#fff;border-radius:14px;padding:36px 40px;text-align:center;margin-top:28px">
  <h2 style="font-size:26px;font-weight:900;margin-bottom:10px">{cta_title}</h2>
  <p style="font-size:14px;opacity:.8;margin-bottom:24px;max-width:520px;margin-left:auto;margin-right:auto">
    {cta_sub}
  </p>
  <a href="https://dqe.tech/contact" style="display:inline-block;background:#00dba3;color:#0f1f6e;
    font-size:14px;font-weight:800;padding:12px 32px;border-radius:8px;text-decoration:none">
    {cta_btn}
  </a>
</div>
```

**Footer**:
```html
<div class="report-footer">
  Report generated by <strong>DQE Software — dqe-quality v2.0.0</strong> · {analysis_date}
</div>
```

---

## STEP 6 — Document 2: Project Manager Guide (advanced technical, optional)

**Only generate this document if `WITH_PM=true` (i.e., `--pm` was passed). If `WITH_PM=false`, skip this step entirely.**

Generate `${PM_PATH}` via Write tool. This document is for internal DQE use — technical, with sample data, treatment plan.

**Nav-bar**: active link on "Project Manager Guide" (2-link nav: Audit + PM)

**Cover**:
- badges: `⚙️ {confidential_pm}` + if critical issues: `⚠️ Contains sensitive data`
- eyebrow = "{doc_pm}"
- title = "Complete technical analysis + {treatment_plan}"
- KPI row: Score · Rows · % unreachable · % duplicates · Completeness · Analysis time

Additional CSS:
```
.cover-badges{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:28px}
.cover-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(0,219,163,.2);
  border:1px solid rgba(0,219,163,.4);border-radius:20px;padding:6px 16px;font-size:12px;
  color:#00dba3;font-weight:700;letter-spacing:.3px}
.cover-badge.warn{background:rgba(255,183,0,.2);border-color:rgba(255,183,0,.4);color:#FFB700}
.cover-kpi-row{display:flex;gap:16px;flex-wrap:wrap}
.ckpi{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);
  border-radius:10px;padding:14px 20px;flex:1;min-width:110px}
.ckpi-val{font-size:28px;font-weight:900;line-height:1}
.ckpi-val.bad{color:#ff6b6b}.ckpi-val.warn{color:#FFB700}.ckpi-val.good{color:#00dba3}
.ckpi-label{font-size:10px;opacity:.6;margin-top:4px;text-transform:uppercase;letter-spacing:.5px}
.cover-meta{display:flex;gap:20px;flex-wrap:wrap;margin-top:20px;font-size:12px;color:rgba(255,255,255,.55)}
.cover-meta span::before{content:'✦ ';color:#00dba3}
```

**Section 1 — {tech_context}**:
- Sub-section 1.1: Table of detected parameters (Encoding / Delimiter / Rows / Columns / Empty columns) with detection method and recommendation
- Sub-section 1.2: Complete column schema: pos. | column | detected type | fill rate (fill bar) | top values | status

Sub-section CSS:
```
.subsec{margin-bottom:36px}
.subsec:last-child{margin-bottom:0}
.subsec-title{font-size:14px;font-weight:800;color:#1933AC;margin-bottom:16px;
  padding-bottom:8px;border-bottom:2px solid #e8ecf8;display:flex;align-items:center;gap:8px}
.stag{background:#1933AC;color:#fff;font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700;letter-spacing:.5px}
.stag.ok{background:#00B486}.stag.warn{background:#FFB700;color:#0f1f6e}.stag.bad{background:#E74C3C}
.table-wrap{overflow-x:auto}
.num{text-align:right;font-variant-numeric:tabular-nums;font-family:monospace}
```

**Section 2 — Detailed analysis by dimension**:
For each dimension with issues:
- metric boxes (alert/warn/good) + precise figures
- Table with examples of problematic values (anonymised if necessary)
- Quality score formula in a `.formula-block`

CSS:
```
.formula-block{background:#0f1f6e;border-radius:10px;padding:20px 24px;color:#fff;margin:16px 0}
.formula-title{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#00dba3;font-weight:700;margin-bottom:12px}
.formula-main{font-family:'Courier New',monospace;font-size:15px;color:#e8ecf8;margin-bottom:14px;line-height:2}
.formula-main .f-op{color:#FFB700}
.formula-main .f-var{color:#00dba3}
.formula-main .f-val{color:#ff6b6b}
.formula-detail{font-size:12px;color:rgba(255,255,255,.6);line-height:1.8}
.formula-detail span{color:#00dba3}
```

DQE formula to display (with actual values):
```
Score = fill_rate(%) - min(dup_pct, 20) - min(rel_issues×3, 15)
     = {fill_rate}% - {min(dup_pct,20)} - {min(rel_issues×3,15)}
     = {quality_score}/100
```

**Section 3 — {treatment_plan}**:
Treatment priority table: priority (🔴/🟡/🟢) | dimension | volume | recommended DQE service | estimated effort | expected gain

**Section 4 — Recommended technical configuration**:
Grid of config-cards per relevant DQE service:
```
.config-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:12px}
.config-card{border-radius:10px;border:1px solid #dce3f5;padding:18px;background:#f8f9fd}
.config-card h4{font-size:13px;font-weight:800;color:#1933AC;margin-bottom:8px;display:flex;align-items:center;gap:8px}
.config-tag{background:#1933AC;color:#fff;font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700}
.config-card p{font-size:12px;color:#555;line-height:1.6;margin-bottom:8px}
.config-param{font-family:monospace;font-size:11px;background:#e8ecf8;padding:3px 7px;border-radius:3px;color:#1933AC;display:block;margin:3px 0}
```

**Appendix — Complete column details**:
Compact table: column | context | top 5 values | types (DIGIT/ALPHA/EMAIL…) | issues

---

## STEP 7 — Save and final report

The files have been saved via Write tool in the previous steps.

Clean up temp files:
```bash
rm -f /tmp/dqe_prog_${SID}.log /tmp/dqe_result_${SID}.json
```

Display to the user (adapt based on whether `--pm` was used):

Without `--pm`:
```
✅ Audit report generated:

📊 Audit report   : {AUDIT_PATH}

📊 Quality score  : {quality_score}/100  ({qualification})
📋 {total_rows:,} rows · {total_columns} columns · {elapsed_seconds}s

Key findings:
• [critical finding #1 with figures]
• [finding #2]
• [finding #3]

Open (Linux)   : xdg-open "{AUDIT_PATH}"
Open (Windows) : explorer.exe "{WINDOWS_PATH}"

Tip: add --pm to also generate the Project Manager guide.
```

With `--pm`:
```
✅ 2 reports generated:

📊 Audit report   : {AUDIT_PATH}
⚙️  PM guide       : {PM_PATH}

📊 Quality score  : {quality_score}/100  ({qualification})
📋 {total_rows:,} rows · {total_columns} columns · {elapsed_seconds}s

Key findings:
• [critical finding #1 with figures]
• [finding #2]
• [finding #3]

Open (Linux)   : xdg-open "{AUDIT_PATH}"
Open (Windows) : explorer.exe "{WINDOWS_PATH}"
```
