from pathlib import Path
import hashlib,json,datetime
ROOT=Path(__file__).resolve().parents[1]
files=[]
for folder in ['content','claims','critiques','provenance','machine','audit']:
    for p in sorted((ROOT/folder).rglob('*')):
        if p.is_file():
            files.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
root=hashlib.sha256(''.join(x['sha256'] for x in files).encode()).hexdigest()
out={'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'algorithm':'sha256','root':root,'files':files}
(ROOT/'provenance/hash-manifest.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
print(root)
