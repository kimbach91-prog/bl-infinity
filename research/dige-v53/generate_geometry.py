from pathlib import Path
import json, hashlib, math
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage import measure
import trimesh

OUT = Path("research/dige-v53/runtime")
OUT.mkdir(parents=True, exist_ok=True)

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def build_head():
    # Parametric adult craniofacial base mesh, no reference pixels/assets.
    n_theta, n_phi = 144, 192
    theta = np.linspace(0.035, math.pi-0.035, n_theta)
    phi = np.linspace(-math.pi, math.pi, n_phi, endpoint=False)
    verts=[]
    faces=[]
    for i,t in enumerate(theta):
        s=math.sin(t); c=math.cos(t)
        z=1.505 + 0.118*c
        # lower-face taper: restrained V, adult, non-childlike
        jaw = 0.78 + 0.22*np.clip((z-1.395)/0.20,0,1)
        cheek = 1.0 + 0.08*np.exp(-((z-1.515)/0.050)**2)
        for j,p in enumerate(phi):
            cp,sp=math.cos(p),math.sin(p)
            front = max(sp,0.0)
            back = max(-sp,0.0)
            rx = 0.086*jaw*cheek
            ry = (0.090*(0.94+0.06*jaw))
            x = rx*s*cp
            y = ry*s*sp
            # subtle asymmetric adult face, keep low amplitude
            x += 0.0016*np.sin(3.0*p+0.6)*np.exp(-((z-1.50)/0.10)**2)
            # flatten face slightly while preserving cheek volume
            if front>0:
                y -= 0.010*front**2
                y += 0.006*np.exp(-((z-1.505)/0.052)**2)*front
            if back>0:
                y += 0.004*back
            verts.append((x,y,z))
    for i in range(n_theta-1):
        for j in range(n_phi):
            j2=(j+1)%n_phi
            a=i*n_phi+j; b=i*n_phi+j2; c=(i+1)*n_phi+j; d=(i+1)*n_phi+j2
            faces.append((a,c,b)); faces.append((b,c,d))
    m=trimesh.Trimesh(np.array(verts),np.array(faces),process=True)
    m.remove_unreferenced_vertices()
    path=OUT/"dige_head_v53.obj"; m.export(path)
    return path,len(m.vertices),len(m.faces)

def smooth_min(a,b,k=18.0):
    m=np.minimum(a,b)
    return m - np.log(np.exp(-k*(a-m))+np.exp(-k*(b-m)))/k

def build_body():
    nx,ny,nz=132,92,236
    x=np.linspace(-.40,.40,nx); y=np.linspace(-.22,.22,ny); z=np.linspace(0,1.43,nz)
    X,Y,Z=np.meshgrid(x,y,z,indexing="ij")
    def E(cx,cy,cz,rx,ry,rz):
        return np.sqrt(((X-cx)/rx)**2+((Y-cy)/ry)**2+((Z-cz)/rz)**2)-1
    b=E(0,0,.99,.195,.125,.285)
    for e,k in [(E(0,0,.68,.215,.138,.225),14),(E(0,0,1.31,.068,.068,.115),15)]:
        b=smooth_min(b,e,k)
    for side in (-1,1):
        for e,k in [
            (E(side*.22,0,1.16,.097,.090,.24),14),
            (E(side*.275,.01,.90,.075,.068,.245),14),
            (E(side*.279,.02,.66,.055,.050,.145),16),
            (E(side*.092,0,.45,.105,.110,.31),14),
            (E(side*.096,.01,.17,.076,.078,.23),14),
            (E(side*.098,.046,.028,.090,.145,.050),16)
        ]: b=smooth_min(b,e,k)
    b=gaussian_filter(b,.50)
    v,f,_,_=measure.marching_cubes(b,0.0,spacing=(x[1]-x[0],y[1]-y[0],z[1]-z[0]))
    v+=np.array([x[0],y[0],z[0]])
    m=trimesh.Trimesh(v,f,process=True); m.remove_unreferenced_vertices()
    path=OUT/"dige_body_v53.obj"; m.export(path)
    return path,len(m.vertices),len(m.faces)

hp,hv,hf=build_head()
bp,bv,bf=build_body()
manifest={
  "pipeline":"DIGE_V53_FORMULA_GEOMETRY",
  "generator":"parametric craniofacial surface + smooth-union SDF body",
  "head":{"file":hp.name,"vertices":hv,"faces":hf,"sha256":sha256(hp)},
  "body":{"file":bp.name,"vertices":bv,"faces":bf,"sha256":sha256(bp)},
  "provenance":{
    "source_pixels_used":False,
    "reference_pixels_read_by_renderer":False,
    "texture_from_reference":False,
    "reference_images_composited":False,
    "image_model_calls":0
  }
}
(OUT/"geometry_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(json.dumps(manifest,sort_keys=True))
