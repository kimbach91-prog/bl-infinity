from pathlib import Path
import argparse, subprocess, sys, json, hashlib, zipfile, shutil
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description='Configure, audit, build and hash BL∞ for a GitHub release.')
p.add_argument('--github',required=True)
p.add_argument('--repo',default='bl-infinity')
p.add_argument('--url',default=None)
p.add_argument('--zip',action='store_true',help='also create a configured upload ZIP in dist/')
a=p.parse_args()

def run(cmd):
    print('+',' '.join(cmd)); subprocess.run(cmd,cwd=ROOT,check=True)
run([sys.executable,'-m','pip','install','-r','requirements.txt'])
cmd=[sys.executable,'scripts/configure.py','--github',a.github,'--repo',a.repo]
if a.url: cmd += ['--url',a.url]
run(cmd)
run([sys.executable,'scripts/audit.py','--strict','--release'])
run([sys.executable,'scripts/build.py'])
run([sys.executable,'scripts/hash_manifest.py'])
run([sys.executable,'scripts/audit.py','--strict','--release'])
if a.zip:
    dist=ROOT/'dist'; dist.mkdir(exist_ok=True)
    out=dist/f'BL_INFINITY_{a.repo}_configured.zip'
    excluded={'.git','dist','__pycache__'}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for f in ROOT.rglob('*'):
            if not f.is_file() or any(part in excluded for part in f.relative_to(ROOT).parts): continue
            z.write(f,f.relative_to(ROOT))
    print('ZIP:',out)
print('READY:',a.url or f'https://{a.github}.github.io/{a.repo}/')
