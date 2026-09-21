import argparse, hashlib, json, pathlib, sys
import bpy
import numpy as np

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

ap=argparse.ArgumentParser()
ap.add_argument('--root',required=True)
ap.add_argument('--out-dir',required=True)
ap.add_argument('--expected-samples',type=int,required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
root=pathlib.Path(args.root)
out=pathlib.Path(args.out_dir)
out.mkdir(parents=True,exist_ok=True)

receipts=[]
for rp in root.rglob('DIGE_V8_RENDER_RECEIPT.json'):
    r=json.loads(rp.read_text())
    if not r.get('sample_shard_mode'): continue
    files=list(rp.parent.glob('DIGE_SAMPLE_SHARD_*.exr'))
    if len(files)!=1: raise RuntimeError(f'expected one shard EXR beside {rp}, got {len(files)}')
    receipts.append((r,files[0]))
if not receipts: raise RuntimeError('no sample-shard receipts found')
receipts.sort(key=lambda item:str(item[0].get('sample_shard_id')))

total_samples=sum(int(r['sample_shard_samples']) for r,_ in receipts)
if total_samples!=args.expected_samples:
    raise RuntimeError(f'sample total mismatch {total_samples} != {args.expected_samples}')

acc=None
width=height=None
shards=[]
for r,path in receipts:
    img=bpy.data.images.load(str(path),check_existing=False)
    try:
        if width is None:
            width,height=img.size[:]
            acc=np.zeros(len(img.pixels),dtype=np.float64)
        elif tuple(img.size[:])!=(width,height):
            raise RuntimeError('shard dimension mismatch')
        pixels=np.asarray(img.pixels[:],dtype=np.float64)
        samples=int(r['sample_shard_samples'])
        acc += pixels*samples
        shards.append({
            'id':r['sample_shard_id'],
            'samples':samples,
            'seed':int(r['sample_shard_seed']),
            'exr_sha256':sha256(path),
            'runtime_commit':r.get('runtime_commit'),
            'device':r.get('device'),
        })
    finally:
        bpy.data.images.remove(img)

acc /= float(total_samples)
combined=bpy.data.images.new('DIGE_C35_COMBINED',width=width,height=height,alpha=True,float_buffer=True)
combined.pixels.foreach_set(acc.astype(np.float32))

scene=bpy.context.scene
scene.render.resolution_x=width
scene.render.resolution_y=height
scene.render.resolution_percentage=100
scene.view_settings.look='AgX - Medium High Contrast'
scene.render.image_settings.file_format='OPEN_EXR'
scene.render.image_settings.color_mode='RGBA'
scene.render.image_settings.color_depth='32'
out_exr=out/'DIGE_C35_COMBINED_LINEAR.exr'
combined.save_render(str(out_exr),scene=scene)

scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.image_settings.color_depth='8'
out_png=out/'DIGE_C35_COMBINED_PREVIEW.png'
combined.save_render(str(out_png),scene=scene)

receipt={
  'schema':'deus-dige-sample-reducer/1.0',
  'state':'REDUCED',
  'shard_count':len(shards),
  'total_samples':total_samples,
  'width':width,
  'height':height,
  'reducer':'SAMPLE_COUNT_WEIGHTED_LINEAR_EXR_ACCUMULATION',
  'shards':shards,
  'combined_exr':{'file':out_exr.name,'sha256':sha256(out_exr)},
  'combined_png':{'file':out_png.name,'sha256':sha256(out_png)},
  'truth_boundary':'REDUCTION_COMBINES_INDEPENDENT_MONTE_CARLO_ESTIMATES_OF_THE_SAME_SCENE__IT_DOES_NOT_PROVE_IDENTICAL_PIXELS_TO_A_SINGLE_MONOLITHIC_RENDER',
}
(out/'DIGE_C35_MICRO_REDUCE_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,sort_keys=True))
