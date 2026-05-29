---
name: dqe-audit
description: "Audit qualité de données CSV — analyse les 6 dimensions DQE (complétude, dates invalides, doublons, anomalies, relations cassées, formats) et génère 3 rapports HTML standalone brandés DQE Software : rapport d'audit, guide client, guide chef de projet. Utiliser quand l'utilisateur demande un audit, une analyse qualité, une analyse DQE, ou fournit un fichier CSV à analyser. Déclencher avec /dqe-audit <chemin/vers/fichier.csv>"
user-invokable: true
argument-hint: "<chemin/vers/fichier.csv> [--lang=fr|en|us|de|es]"
metadata:
  author: DQE Software
  version: "2.1.0"
  category: data-quality
---

# DQE CSV Audit — Agent Skill

Tu es un agent d'audit qualité de données pour DQE Software. Quand ce skill est déclenché, tu analyses un fichier CSV selon les 6 dimensions DQE et tu génères **3 rapports HTML professionnels** : rapport d'audit technique, guide client, guide chef de projet.

---

## ÉTAPE 0 — Extraction du chemin fichier et de la locale

Le chemin du fichier CSV est fourni dans `$ARGUMENTS`.

Extrait :
1. Le chemin CSV : tout argument qui ne commence pas par `--`
2. La langue : paramètre `--lang=XX` si présent (fr, en, us, de, es). `us` est un alias de `en`. Défaut : `en`

Si aucun fichier CSV n'est trouvé, réponds :
```
Fournis le chemin de ton fichier CSV :
  /dqe-audit /chemin/vers/fichier.csv [--lang=fr|en|us|de|es]
```
Et arrête.

### Tableau de localisation

Utilise ces labels dans tous les HTML générés selon la langue choisie :

| Clé | fr | en | de | es |
|-----|----|----|----|----|
| doc_audit | Rapport d'Audit | Audit Report | Prüfbericht | Informe de Auditoría |
| doc_client | Guide Client | Client Guide | Kundenleitfaden | Guía del Cliente |
| doc_pm | Guide Chef de Projet | Project Manager Guide | PM-Leitfaden | Guía del Jefe de Proyecto |
| nav_audit | 📊 Rapport d'Audit | 📊 Audit Report | 📊 Prüfbericht | 📊 Informe |
| nav_client | 👤 Guide Client | 👤 Client Guide | 👤 Kundenleitfaden | 👤 Guía Cliente |
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
| confidential_client | Confidentiel — Destiné au client | Confidential — For Client | Vertraulich — Für Kunden | Confidencial — Para el cliente |
| confidential_pm | Usage interne DQE | DQE Internal Use | Interne DQE-Nutzung | Uso interno DQE |
| your_score | Votre score de qualité | Your quality score | Ihr Qualitätsscore | Su puntuación de calidad |
| what_it_means | Ce que signifie ce score pour votre activité | What this score means for your business | Was dieser Score für Ihr Unternehmen bedeutet | Lo que este puntaje significa para su negocio |
| next_steps | Prochaines étapes | Next Steps | Nächste Schritte | Próximos pasos |
| tech_context | Contexte technique | Technical Context | Technischer Kontext | Contexto técnico |
| treatment_plan | Plan de traitement | Treatment Plan | Behandlungsplan | Plan de tratamiento |

---

## ÉTAPE 1 — Installation du script d'analyse (auto, silencieuse)

Vérifie si le script existe déjà :
```bash
[ -f /tmp/dqe_analyze.py ] && python3 /tmp/dqe_analyze.py --version 2>/dev/null && echo "OK" || echo "WRITE"
```

Si le résultat n'est pas `OK`, écris le script suivant dans `/tmp/dqe_analyze.py` via le Write tool :

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
    if not os.path.isfile(fp): errs.append(f"Fichier introuvable : {fp}"); return False, errs
    if os.path.getsize(fp)==0: errs.append("Fichier vide."); return False, errs
    try:
        with open(fp, encoding=enc, errors='replace', newline='') as f:
            r = csv.reader(f, delimiter=delim)
            hdr = next(r, None)
            if not hdr or len(hdr)<2: errs.append("Header absent ou mono-colonne."); return False, errs
            nc = len(hdr); rag=0
            for i,row in enumerate(r):
                if i>=200: break
                if len(row)!=nc: rag+=1
            if rag>5: errs.append(f"CSV mal formé : {rag} lignes incohérentes.")
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

DEPT_CITY={'75':'PARIS','69':'LYON','13':'MARSEILLE','31':'TOULOUSE','33':'BORDEAUX',
           '44':'NANTES','59':'LILLE','67':'STRASBOURG','06':'NICE'}

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
        for r in rows:
            cp_=r.get(cp,'').strip(); vi=r.get(vil,'').strip().upper(); dept=cp_[:2] if len(cp_)>=2 else ''
            if dept in DEPT_CITY and vi:
                for od,oc in DEPT_CITY.items():
                    if od!=dept and oc in vi: mm+=1; break
        if mm>0: issues.append({'dimension':'A','type':'postal_code_city_mismatch','count':mm,
                                  'pct':round(mm/total*100,2),'detail':'CP et VILLE semblent de régions différentes'})
    if em:
        bad=sum(1 for r in rows if (r.get(em,'')or'').strip() and classify(r.get(em,'')) not in('EMAIL','EMPTY'))
        if bad>0: issues.append({'dimension':'B','type':'invalid_email_field_content','count':bad,
                                  'pct':round(bad/total*100,2),'detail':'Champ EMAIL contient des non-emails'})
    for col,tk,lbl in [(nom,'digits_in_lastname','NOM'),(pre,'digits_in_firstname','PRENOM')]:
        if col:
            bad=sum(1 for r in rows if re.search(r'\d',r.get(col,''or'')))
            if bad>0: issues.append({'dimension':'B','type':tk,'count':bad,
                                      'pct':round(bad/total*100,2),'detail':f'{lbl} contient des chiffres'})
    if adr and (cp or vil):
        bad=sum(1 for r in rows if (r.get(adr,'')or'').strip() and
                ((cp and not(r.get(cp,'')or'').strip()) or (vil and not(r.get(vil,'')or'').strip())))
        if bad>0: issues.append({'dimension':'C','type':'incomplete_address','count':bad,
                                  'pct':round(bad/total*100,2),'detail':'ADR1 renseigné mais CP ou VILLE manquant'})
    phones=[c for c in [fix,mob] if c]
    if em and phones:
        bad=sum(1 for r in rows if not(r.get(em,'')or'').strip()
                and all(not(r.get(c,'')or'').strip() for c in phones))
        if bad>0: issues.append({'dimension':'C','type':'unreachable_contact','count':bad,
                                  'pct':round(bad/total*100,2),'detail':'Aucun moyen de contact (ni email ni tél)'})
    if em and (nom or pre):
        rwe=[r for r in rows if(r.get(em,'')or'').strip()]; te=len(rwe)
        if te>0:
            if nom:
                nn=sum(1 for r in rwe if not(r.get(nom,'')or'').strip())
                if nn>0: issues.append({'dimension':'C','type':'email_missing_lastname','count':nn,
                                        'pct':round(nn/te*100,2),'pct_base':'emails',
                                        'detail':f'Email renseigné mais NOM manquant ({nn}/{te} emails)'})
            if nom and pre:
                nb=sum(1 for r in rwe if not(r.get(nom,'')or'').strip() and not(r.get(pre,'')or'').strip())
                if nb>0: issues.append({'dimension':'C','type':'email_missing_both_names','count':nb,
                                        'pct':round(nb/te*100,2),'pct_base':'emails',
                                        'detail':f'Email renseigné mais NOM et PRENOM tous deux manquants ({nb}/{te} emails)'})
                na=sum(1 for r in rwe if not(r.get(nom,'')or'').strip() or not(r.get(pre,'')or'').strip())
                if na>0: issues.append({'dimension':'C','type':'email_incomplete_identity','count':na,
                                        'pct':round(na/te*100,2),'pct_base':'emails',
                                        'detail':f'Email renseigné mais NOM ou PRENOM manquant ({na}/{te} emails)'})
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
    prog.emit('PREFLIGHT',0,'Vérification du fichier...')
    fp=os.path.abspath(args.csv_file)
    enc=detect_encoding(fp); delim=detect_delimiter(fp,enc)
    ok,errs=preflight(fp,enc,delim)
    if not ok:
        prog.emit('ERROR',0,' | '.join(errs)); prog.close()
        print(json.dumps({'error':errs},ensure_ascii=False)); sys.exit(1)
    prog.emit('PREFLIGHT',3,'Comptage des lignes...')
    total_lines=count_lines(fp)-1
    if total_lines>SAMPLE_LIMIT:
        msg=f"Fichier trop volumineux : {total_lines:,} lignes (max {SAMPLE_LIMIT:,}). Conseil : head -n {FULL_LIMIT+1} \"{fp}\" > sample.csv"
        prog.emit('ERROR',0,msg); prog.close(); print(json.dumps({'error':msg},ensure_ascii=False)); sys.exit(2)
    is_sampled=total_lines>FULL_LIMIT
    step=max(2,total_lines//TARGET_SAMPLE) if is_sampled else 1
    with open(fp,encoding=enc,errors='replace',newline='') as f:
        reader=csv.DictReader(f,delimiter=delim); headers=list(reader.fieldnames or [])
    eff=total_lines if not is_sampled else total_lines//step
    eta=estimate_eta(eff,len(headers))
    prog.emit('PREFLIGHT',5,f'✓ {total_lines:,} lignes · {len(headers)} colonnes{"  (échantillon 1/"+str(step)+")" if is_sampled else ""}',str(eta))
    prog.emit('STEP',10,'Lecture du fichier...',str(eta-2))
    rows=[]
    with open(fp,encoding=enc,errors='replace',newline='') as f:
        reader=csv.DictReader(f,delimiter=delim)
        for i,row in enumerate(reader):
            if is_sampled and i%step!=0: continue
            rows.append(dict(row))
    cmap={h:detect_context(h) for h in headers}
    def rem(frac): elapsed=time.time()-t0; return str(max(0,int(elapsed/frac-elapsed))) if frac>0 else '?'
    prog.emit('STEP',20,'Taux de complétude...',rem(0.20)); comp=analyze_completion(rows,headers)
    prog.emit('STEP',35,'Validation des dates...',rem(0.35)); dates=analyze_dates(rows,headers,cmap)
    prog.emit('STEP',50,'Détection des doublons...',rem(0.50)); dupes=analyze_duplicates(rows,headers,cmap)
    prog.emit('STEP',65,'Anomalies & valeurs aberrantes...',rem(0.65)); anom=analyze_anomalies(rows,headers,cmap)
    prog.emit('STEP',80,'Relations cassées (A+B+C)...',rem(0.80)); rels=analyze_relationships(rows,headers,cmap)
    prog.emit('STEP',92,'Cohérence des formats...',rem(0.92)); fmts=analyze_formats(rows,headers,cmap)
    prog.emit('STEP',97,'Profilage des colonnes...','1'); cols=profile_columns(rows,headers,cmap)
    fill=comp['global_fill_rate']; dp=min(dupes['deduplication_potential_pct'],20); rp=min(len(rels['issues'])*3,15)
    qs=round(max(0,fill-dp-rp),1)
    result={'filename':os.path.basename(fp),'analysis_date':datetime.now().strftime('%B %d, %Y'),
            'total_rows':total_lines,'analysed_rows':len(rows),'is_sampled':is_sampled,'sample_step':step,
            'total_columns':len(headers),'encoding':enc.upper(),'delimiter':delim,
            'elapsed_seconds':round(time.time()-t0,1),'quality_score':qs,'columns':cols,
            'dimensions':{'1_completion_rate':comp,'2_invalid_dates':dates,'3_duplicate_records':dupes,
                          '4_anomalies_outliers':anom,'5_broken_relationships':rels,'6_format_inconsistencies':fmts}}
    prog.emit('DONE',100,f'Analyse terminée ✓ ({round(time.time()-t0,1)}s)','0')
    prog.close()
    out=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        with open(args.output,'w',encoding='utf-8') as f: f.write(out)
    else: print(out)

if __name__=='__main__': main()
```

---

## ÉTAPE 2 — Validation du fichier CSV

Résous le chemin absolu. Si chemin Windows (`C:\...`), convertis en WSL (`/mnt/c/...`) :

```bash
CSV_PATH=$(realpath "$CSV_FILE" 2>/dev/null || echo "INVALID")
[ -f "$CSV_PATH" ] && echo "OK:$CSV_PATH" || echo "MISSING:$CSV_PATH"
```

Si `MISSING`, informe l'utilisateur et arrête.

---

## ÉTAPE 3 — Lancement de l'analyse avec progression temps réel

```bash
SID=$(date +%s) && echo "SID=$SID"
```

Lance en arrière-plan (`run_in_background: true`) :
```bash
python3 /tmp/dqe_analyze.py "$CSV_PATH" \
  --progress "/tmp/dqe_prog_${SID}.log" \
  --output "/tmp/dqe_result_${SID}.json"
```

Puis Monitor pour la progression :
```bash
tail -n +1 -f /tmp/dqe_prog_${SID}.log | while IFS= read -r line; do
  STAT=$(echo "$line" | cut -d'|' -f1)
  DISP=$(echo "$line" | cut -d'|' -f3)
  echo "$DISP"
  { [ "$STAT" = "DONE" ] || [ "$STAT" = "ERROR" ]; } && break
done
```

En cas d'`ERROR`, affiche le message et arrête.

---

## ÉTAPE 4 — Lecture des résultats

```bash
cat /tmp/dqe_result_${SID}.json
```

Parse le JSON. Normalise la locale (`us` → `en`), puis calcule les chemins de sortie avec détection de collision :

```bash
DIR=$(dirname "$CSV_PATH")
BASE=$(basename "$CSV_PATH" .csv)
[ "$LANG" = "us" ] && LANG="en"
DATE_TAG=$(date +%Y%m%d)

# Retourne le chemin libre : base_suffix_DATE_LANG.html, puis base_suffix_DATE_LANG (2).html, etc.
compute_out() {
  local p="${DIR}/${BASE}_${1}_${DATE_TAG}_${LANG}.html"
  if [ ! -f "$p" ]; then echo "$p"; return; fi
  local n=2
  while [ -f "${DIR}/${BASE}_${1}_${DATE_TAG}_${LANG} (${n}).html" ]; do n=$((n+1)); done
  echo "${DIR}/${BASE}_${1}_${DATE_TAG}_${LANG} (${n}).html"
}

AUDIT_PATH=$(compute_out "dqe_audit")
CLIENT_PATH=$(compute_out "dqe_client_guide")
PM_PATH=$(compute_out "dqe_pm_guide")
echo "AUDIT=$AUDIT_PATH"
echo "CLIENT=$CLIENT_PATH"
echo "PM=$PM_PATH"
```

Les 3 fichiers se linkeront entre eux via la nav-bar avec ces noms de fichiers (basename uniquement, sans chemin).

---

## DESIGN SYSTEM COMMUN

Toutes les pages partagent cette palette et ces classes CSS de base :

```
Couleurs :
  --primary : #1933AC   (bleu DQE)
  --accent  : #00dba3   (vert teal)
  --good    : #00B486 / #00dba3
  --warn    : #FFB700
  --bad     : #E74C3C / #ff6b6b
  --bg      : #F5F5F5
  --text    : #1a1a2e

Logo HTML (avec fallback) :
  <img src="https://dqe.tech/wp-content/uploads/2022/05/logo-DQE-noBase-light.svg"
       alt="DQE Software" height="32"
       onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
  <div class="cover-logo-text" style="display:none">DQE<span style="color:#00dba3">.</span></div>

Score coloring :
  >= 80 → good (#00dba3) · 60-79 → warn (#FFB700) · < 60 → bad (#ff6b6b)

Nav-bar (commune aux 3 fichiers, lien actif = background #1933AC) :
  <div class="nav-bar">
    <span class="nav-label">Livrables</span>
    <div class="nav-links">
      <a href="{AUDIT_BASENAME}" class="nav-link {active|client}">📊 {nav_audit}</a>
      <a href="{CLIENT_BASENAME}" class="nav-link {active|client}">👤 {nav_client}</a>
      <a href="{PM_BASENAME}" class="nav-link {active|pm}">⚙️ {nav_pm}</a>
    </div>
  </div>

CSS commun de base :
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

## ÉTAPE 5 — Document 1 : Rapport d'Audit (technique)

Génère `${AUDIT_PATH}` via Write tool. Ce document est le rapport technique complet.

**Structure du rapport d'audit :**

**Cover** : logo DQE + date | titre = `{doc_audit} — {filename}` | eyebrow = "CSV Data Quality Audit" | métrics couverts :
- Score badge : `{quality_score}/100` coloré selon seuils
- KPIs : `{total_rows:,} {records}` · `{total_columns} {columns}` · `{encoding}` · `{analysed_in} {elapsed_seconds}s`
- Si sampled : banner ⚠️ `Analyse sur échantillon 1/{sample_step}`

**Nav-bar** : lien actif sur "Rapport d'Audit", liens vers client_guide et pm_guide

**Section 1 — Analyse Technique** (`{tech_context}`) :
Tableau : Encodage / Délimiteur / Lignes totales / Colonnes / Colonnes vides / Durée / Mode (complet ou échantillon)

**Section 2 — Profilage des colonnes** :
Tableau par colonne : Nom | Contexte détecté | Confiance | Remplissage (fill bar) | Type dominant | Statut (badge ok/warn/err)

**Section 3 — Résumé exécutif** :
6 dim-cards (grille 3×2), une par dimension. Chaque carte : icône + nom localisé + valeur principale + détail 1 ligne
CSS additionnel :
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
Suivi d'un paragraphe narratif de 3-4 phrases résumant l'état global.

**Section 4 — Analyse détaillée 6 dimensions** :
Sous-sections 4.1 à 4.6 avec pour chaque dimension :
- metric boxes (alert/warn/good) pour les chiffres clés
- tableau détaillé par colonne si applicable
- liste des issues avec icône + titre + détail

CSS additionnel :
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

**Section 5 — Recommandations** :
Grille 2 colonnes de reco-cards (fond #1933AC). Règles de sélection des services :
- Adresses invalides / CP incohérent → DQE Address (RNVP)
- Email vide ou invalide → DQE Email
- Téléphone formats mixtes / vide → DQE Phone
- Doublons > 1% → DQE Deduplication
- Contacts injoignables > 10% → DQE Enrich
- Score < 70 ou anomalies généralisées → DQE One
- Score < 80 (systématique) → DQE Monitoring

CSS :
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

**Section 6 — Conclusion** :
4-5 phrases : score + qualification / point positif / problème critique en chiffres / call to action DQE Software.

**Footer** :
```html
<div class="report-footer">
  Rapport généré par <strong>DQE Software — dqe-quality v2.0.0</strong> · {analysis_date}
</div>
```

---

## ÉTAPE 6 — Document 2 : Guide Client (business)

Génère `${CLIENT_PATH}` via Write tool. Ce document est destiné au client final — langage business, pas technique, focus impact métier.

**Nav-bar** : lien actif sur "Guide Client"

**Cover** :
- eyebrow = "{confidential_client}"
- titre = "{your_score}" (localisé)
- sous-titre = `{filename} — {total_rows:,} {records} analysés`
- 3 key-metrics (big numbers) : Score/100 · % contacts injoignables (dim 5) · % doublons (dim 3)
- cover-meta : date · volume · mode analyse

CSS additionnel pour la cover :
```
.cover-subtitle{font-size:18px;color:rgba(255,255,255,.7);margin-bottom:40px;font-weight:400}
.cover-badge{display:inline-flex;align-items:center;gap:8px;background:rgba(0,219,163,.2);
  border:1px solid rgba(0,219,163,.4);border-radius:20px;padding:6px 16px;font-size:12px;
  color:#00dba3;font-weight:700;letter-spacing:.5px;margin-bottom:32px}
.key-metrics{display:flex;gap:20px;flex-wrap:wrap}
.km{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);
  border-radius:12px;padding:18px 28px;min-width:140px;flex:1}
.km-val{font-size:42px;font-weight:900;line-height:1}
.km-val.bad{color:#ff6b6b}.km-val.warn{color:#FFB700}.km-val.good{color:#00dba3}
.km-label{font-size:11px;opacity:.7;margin-top:6px;text-transform:uppercase;letter-spacing:.5px;line-height:1.4}
.cover-meta{display:flex;gap:20px;flex-wrap:wrap;margin-top:20px;font-size:12px;color:rgba(255,255,255,.55)}
.cover-meta span::before{content:'✦ ';color:#00dba3}
```

**Section 1 — {your_score}** :
- Gauge SVG/CSS circulaire avec le score (conic-gradient), coloré selon seuils
- Titre `{what_it_means}` + paragraphe explicatif (langage non technique : ce que signifie ce score pour l'activité)
- 2-3 alert-boxes (critical/warn/good) avec les findings les plus importants en langage business

CSS :
```
.score-block{display:flex;gap:28px;align-items:center;flex-wrap:wrap;margin-bottom:24px}
.gauge{width:130px;height:130px;border-radius:50%;
  background:conic-gradient({color} 0% {pct}%, #f0f3fc {pct}% 100%);
  display:flex;align-items:center;justify-content:center;position:relative}
.gauge::before{content:'';position:absolute;width:90px;height:90px;background:#fff;border-radius:50%}
.gauge-inner{position:relative;text-align:center}
.gauge-val{font-size:32px;font-weight:900;line-height:1}
.gauge-max{font-size:12px;color:#aaa;font-weight:600}
.score-text h3{font-size:16px;font-weight:800;color:#1933AC;margin-bottom:8px}
.alert-box{border-radius:10px;padding:18px 22px;margin-bottom:16px;display:flex;gap:14px;align-items:flex-start}
.alert-box.critical{background:#fde8e8;border-left:4px solid #E74C3C}
.alert-box.warn{background:#fff3cd;border-left:4px solid #FFB700}
.alert-box.good{background:#d4f5eb;border-left:4px solid #00B486}
.alert-ico{font-size:20px;flex-shrink:0;margin-top:1px}
.alert-body h4{font-size:13px;font-weight:700;margin-bottom:4px}
.alert-body.critical h4{color:#c0392b}
.alert-body.warn h4{color:#856404}
.alert-body.good h4{color:#0a7a56}
.alert-body p{font-size:12.5px;color:#555;line-height:1.55}
```

**Section 2 — Les 6 dimensions (version client)** :
- Grille 2×3 de dim-cards simplifiées : icône + nom localisé + statut (OK/Attention/Critique) + 1 phrase d'explication business, pas technique
- Chaque card indique l'impact concret (ex : "23% de vos contacts sont injoignables")

CSS :
```
.dim-grid-client{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-bottom:20px}
.dim-card{border-radius:10px;padding:20px;position:relative;overflow:hidden}
.dim-card.ok{background:#f0faf6;border-left:4px solid #00B486}
.dim-card.warn{background:#fffbf0;border-left:4px solid #FFB700}
.dim-card.bad{background:#fdf2f2;border-left:4px solid #E74C3C}
.dim-icon{font-size:24px;margin-bottom:8px}
.dim-name{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:#7a7a8c;margin-bottom:4px}
.dim-headline{font-size:22px;font-weight:900;margin-bottom:6px;line-height:1}
.dim-card.ok .dim-headline{color:#0a7a56}
.dim-card.warn .dim-headline{color:#856404}
.dim-card.bad .dim-headline{color:#c0392b}
.dim-explain{font-size:12.5px;color:#555;line-height:1.5}
.dim-impact{margin-top:10px;font-size:11.5px;font-weight:600;display:inline-block;padding:3px 10px;border-radius:4px}
.dim-card.ok .dim-impact{color:#0a7a56;background:#d4f5eb}
.dim-card.warn .dim-impact{color:#856404;background:#fff3cd}
.dim-card.bad .dim-impact{color:#c0392b;background:#fde8e8}
```

**Section 3 — Impact business** :
Tableau d'impact avec colonnes : Problème | Volume estimé | Impact activité | Priorité

**Section 4 — {recommendations}** :
2-4 reco-cards (mêmes règles de sélection que le rapport audit) avec focus ROI client.

**Section 5 — {next_steps}** :
Liste numérotée de 3-5 étapes concrètes que le client peut faire maintenant.

CSS :
```
.steps{list-style:none;margin:0;padding:0}
.step{display:flex;gap:16px;padding:14px 0;border-bottom:1px solid #f0f3f7;align-items:flex-start}
.step:last-child{border-bottom:none}
.step-num{width:34px;height:34px;border-radius:50%;background:#1933AC;color:#fff;
  font-size:14px;font-weight:900;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.step-content h4{font-size:13.5px;font-weight:700;color:#1933AC;margin-bottom:4px}
.step-content p{font-size:12.5px;color:#555;line-height:1.55}
```

**Bloc CTA** :
```html
<div style="background:#1933AC;background-image:radial-gradient(ellipse at 70% 30%,#2a47d4 0%,#1933AC 70%);
  color:#fff;border-radius:14px;padding:36px 40px;text-align:center;margin-top:8px">
  <h2 style="font-size:26px;font-weight:900;margin-bottom:10px">Améliorons votre qualité de données</h2>
  <p style="font-size:14px;opacity:.8;margin-bottom:24px;max-width:500px;margin-left:auto;margin-right:auto">
    Nos experts DQE peuvent traiter ce fichier et vous livrer des données propres, enrichies et conformes.
  </p>
  <a href="https://dqe.tech/contact" style="display:inline-block;background:#00dba3;color:#0f1f6e;
    font-size:14px;font-weight:800;padding:12px 32px;border-radius:8px;text-decoration:none">
    Contacter DQE Software
  </a>
</div>
```

---

## ÉTAPE 7 — Document 3 : Guide Chef de Projet (technique avancé)

Génère `${PM_PATH}` via Write tool. Ce document est à usage interne DQE — technique, avec données d'exemples, plan de traitement.

**Nav-bar** : lien actif sur "Guide Chef de Projet"

**Cover** :
- badges : `⚙️ {confidential_pm}` + si issues critiques : `⚠️ Contient des données sensibles`
- eyebrow = "{doc_pm}"
- titre = "Analyse technique complète + {treatment_plan}"
- KPI row : Score · Lignes · % injoignables · % doublons · Complétude · Temps analyse

CSS additionnel :
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

**Section 1 — {tech_context}** :
- Sous-section 1.1 : Tableau paramètres détectés (Encodage / Délimiteur / Lignes / Colonnes / Colonnes vides) avec méthode de détection et recommandation
- Sous-section 1.2 : Schéma complet des colonnes : pos. | colonne | type détecté | remplissage (fill bar) | valeurs top | statut

CSS sous-sections :
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

**Section 2 — Analyse détaillée par dimension** :
Pour chaque dimension avec issues :
- metric boxes (alert/warn/good) + chiffres précis
- Tableau avec exemples de valeurs problématiques (anonymisées si nécessaire)
- Formule du score de qualité dans une `.formula-block`

CSS :
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

Formule DQE à afficher (valeurs réelles) :
```
Score = fill_rate(%) - min(dup_pct, 20) - min(rel_issues×3, 15)
     = {fill_rate}% - {min(dup_pct,20)} - {min(rel_issues×3,15)}
     = {quality_score}/100
```

**Section 3 — {treatment_plan}** :
Tableau priorité de traitement : priorité (🔴/🟡/🟢) | dimension | volume | service DQE recommandé | effort estimé | gain attendu

**Section 4 — Configuration technique recommandée** :
Grille de config-cards par service DQE pertinent :
```
.config-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:12px}
.config-card{border-radius:10px;border:1px solid #dce3f5;padding:18px;background:#f8f9fd}
.config-card h4{font-size:13px;font-weight:800;color:#1933AC;margin-bottom:8px;display:flex;align-items:center;gap:8px}
.config-tag{background:#1933AC;color:#fff;font-size:10px;padding:2px 8px;border-radius:4px;font-weight:700}
.config-card p{font-size:12px;color:#555;line-height:1.6;margin-bottom:8px}
.config-param{font-family:monospace;font-size:11px;background:#e8ecf8;padding:3px 7px;border-radius:3px;color:#1933AC;display:block;margin:3px 0}
```

**Appendice — Détail complet des colonnes** :
Tableau compact : colonne | contexte | top 5 valeurs | types (DIGIT/ALPHA/EMAIL…) | issues

---

## ÉTAPE 8 — Sauvegarde et rapport final

Les 3 fichiers ont été sauvegardés via Write tool dans les étapes précédentes.

Nettoie les temporaires :
```bash
rm -f /tmp/dqe_prog_${SID}.log /tmp/dqe_result_${SID}.json
```

Affiche à l'utilisateur :

```
✅ 3 rapports générés :

📊 Rapport d'audit  : {AUDIT_PATH}
👤 Guide client     : {CLIENT_PATH}
⚙️  Guide PM         : {PM_PATH}

📊 Score qualité : {quality_score}/100  ({qualification})
📋 {total_rows:,} lignes · {total_columns} colonnes · {elapsed_seconds}s

Points clés :
• [finding critique #1 avec chiffres]
• [finding #2]
• [finding #3]

Ouvrir (Linux)  : xdg-open "{AUDIT_PATH}"
Ouvrir (Windows): explorer.exe "{WINDOWS_PATH}"
```
