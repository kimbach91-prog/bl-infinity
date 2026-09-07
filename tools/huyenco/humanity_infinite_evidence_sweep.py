#!/usr/bin/env python3
import hashlib, json, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUERY_FILE = ROOT / '.deus/research/humanity-infinite/collector/queries.json'
OUT_DIR = ROOT / '.deus/research/humanity-infinite/inbox'
SNAP_DIR = OUT_DIR / 'snapshots'
UA = 'BL-HC-01-Humanity-Infinite-Collector/1.0 (+https://github.com/kimbach91-prog/bl-infinity)'


def get_json(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def europe_pmc(track_id, query, limit=8):
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urllib.parse.urlencode({
        'query': query, 'format': 'json', 'pageSize': str(limit)
    })
    data = get_json(url)
    out = []
    for x in data.get('resultList', {}).get('result', []):
        out.append({
            'track_id': track_id,
            'source': 'Europe PMC',
            'source_id': x.get('pmid') or x.get('pmcid') or x.get('id'),
            'title': x.get('title'),
            'author': x.get('authorString'),
            'journal': x.get('journalTitle'),
            'pub_year': x.get('pubYear'),
            'doi': x.get('doi'),
            'cited_by_count': x.get('citedByCount'),
            'is_open_access': x.get('isOpenAccess'),
            'url': ('https://europepmc.org/article/MED/' + str(x.get('pmid'))) if x.get('pmid') else None
        })
    return out


def clinical_trials(track_id, query, limit=6):
    url = 'https://clinicaltrials.gov/api/v2/studies?' + urllib.parse.urlencode({
        'query.term': query, 'pageSize': str(limit), 'format': 'json'
    })
    data = get_json(url)
    out = []
    for s in data.get('studies', []):
        p = s.get('protocolSection', {})
        ident = p.get('identificationModule', {})
        status = p.get('statusModule', {})
        design = p.get('designModule', {})
        nct = ident.get('nctId')
        out.append({
            'track_id': track_id,
            'source': 'ClinicalTrials.gov',
            'source_id': nct,
            'title': ident.get('briefTitle') or ident.get('officialTitle'),
            'overall_status': status.get('overallStatus'),
            'study_type': design.get('studyType'),
            'phases': design.get('phases'),
            'start_date': (status.get('startDateStruct') or {}).get('date'),
            'completion_date': (status.get('completionDateStruct') or {}).get('date'),
            'url': ('https://clinicaltrials.gov/study/' + nct) if nct else None
        })
    return out


def stable_record_key(r):
    return '|'.join(str(r.get(k) or '') for k in ('track_id','source','source_id','title'))


def main():
    cfg = json.loads(QUERY_FILE.read_text(encoding='utf-8'))
    now = datetime.now(timezone.utc)
    results, errors = [], []
    for t in cfg['tracks']:
        tid, q = t['id'], t['query']
        for source_name, fn in [('Europe PMC', europe_pmc), ('ClinicalTrials.gov', clinical_trials)]:
            try:
                results.extend(fn(tid, q))
            except Exception as e:
                errors.append({'track_id': tid, 'source': source_name, 'error': type(e).__name__ + ': ' + str(e)[:300]})
            time.sleep(0.2)

    dedup = {}
    for r in results:
        dedup[stable_record_key(r)] = r
    records = sorted(dedup.values(), key=stable_record_key)
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    digest = hashlib.sha256(canonical).hexdigest()

    packet = {
        'schema': 'HUYENCO_HUMANITY_INFINITE_EVIDENCE_PACKET/v1',
        'agent_id': 'BL-HC-01',
        'project': 'HUMANITY-INFINITE/BODY-ASCENSION',
        'generated_at_utc': now.isoformat(),
        'query_set': str(QUERY_FILE.relative_to(ROOT)),
        'sources': cfg['sources'],
        'record_count': len(records),
        'digest_sha256': digest,
        'errors': errors,
        'records': records,
        'truth_policy': {
            'collector_output_is_source_metadata_not_scientific_conclusion': True,
            'phenomenology_not_ontology': True,
            'requires_human_or_llm_synthesis_before_promotion': True
        }
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    latest_json = OUT_DIR / 'latest.json'
    previous_digest = None
    if latest_json.exists():
        try:
            previous_digest = json.loads(latest_json.read_text(encoding='utf-8')).get('digest_sha256')
        except Exception:
            pass

    latest_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = [
        '# Huyền Cơ · Humanity Infinite · Evidence Sweep', '',
        f'- Generated: {packet["generated_at_utc"]}',
        f'- Records: {len(records)}',
        f'- Digest: `{digest}`',
        f'- Changed since previous packet: `{digest != previous_digest}`',
        '',
        'Collector output is source metadata, not a scientific conclusion. Promotion requires synthesis, provenance review, safety review and replication logic.', ''
    ]
    for tid in [x['id'] for x in cfg['tracks']]:
        subset = [r for r in records if r['track_id'] == tid][:8]
        if not subset:
            continue
        lines += [f'## {tid}', '']
        for r in subset:
            title = (r.get('title') or '(untitled)').replace('\n',' ').strip()
            lines.append(f'- [{r.get("source")}] {title} — {r.get("source_id") or "no-id"}')
        lines.append('')
    if errors:
        lines += ['## Collector errors', ''] + [f'- {e["track_id"]} / {e["source"]}: {e["error"]}' for e in errors]
    (OUT_DIR / 'latest.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    if digest != previous_digest:
        stamp = now.strftime('%Y%m%dT%H%M%SZ')
        (SNAP_DIR / f'{stamp}_{digest[:12]}.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
        print('DELTA', digest)
    else:
        print('NO_DELTA', digest)

    # Exit successfully even if one source temporarily fails; errors are carried in packet.
    return 0

if __name__ == '__main__':
    sys.exit(main())
