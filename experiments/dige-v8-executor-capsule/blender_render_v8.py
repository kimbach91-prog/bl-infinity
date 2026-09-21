import bpy, bmesh, math, json, hashlib, random, os, sys
import numpy as np
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/"runtime"
OUTPUT_TAG=os.environ.get("DIGE_OUTPUT_TAG","").strip()
OUT=RUNTIME/"renders"
if OUTPUT_TAG:
    OUT=OUT/OUTPUT_TAG
OUT.mkdir(parents=True,exist_ok=True)
CANON_PATH=ROOT/"DIGE_CANON_EXECUTION_MANIFEST.json"
CANON_BYTES=CANON_PATH.read_bytes()
CANON=json.loads(CANON_BYTES)
CANON_SHA256=hashlib.sha256(CANON_BYTES).hexdigest()

def sha(p):
    p=Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

def set_input(node,name,val):
    s=node.inputs.get(name)
    if s is not None:
        s.default_value=val

def c25_mpfb_data_root():
    if not C25_MATURE_STACK:
        return None
    if not C25_MPFB2_SRC:
        raise RuntimeError("C25 requires DIGE_MPFB2_SRC")
    src=Path(C25_MPFB2_SRC).resolve()
    data=src/"mpfb"/"data"
    if not data.exists():
        raise RuntimeError(f"C25 MPFB2 data root missing: {data}")
    return data

def c25_socket(sockets,key):
    try:
        if isinstance(key,int):
            return sockets[key]
        return sockets.get(key)
    except Exception:
        return None

def c25_set_default(socket,value):
    if socket is None or not hasattr(socket,"default_value"):
        return
    try:
        socket.default_value=tuple(value) if isinstance(value,list) else value
    except Exception:
        try:
            socket.default_value=value
        except Exception:
            pass

def c25_collect_groups(tree_dict,out):
    for name,gdef in (tree_dict.get("groups") or {}).items():
        out[name]=gdef
        c25_collect_groups(gdef,out)

def c25_reset_tree(tree):
    for n in list(tree.nodes):
        tree.nodes.remove(n)

def c25_ensure_interface(name,gdef):
    tree=bpy.data.node_groups.get(name)
    if tree is None:
        tree=bpy.data.node_groups.new(name,"ShaderNodeTree")
    c25_reset_tree(tree)
    # Keep the interface itself; unique C25 group names avoid stale collisions.
    existing_in={item.name for item in tree.interface.items_tree if getattr(item,"item_type",None)=="SOCKET" and getattr(item,"in_out",None)=="INPUT"}
    existing_out={item.name for item in tree.interface.items_tree if getattr(item,"item_type",None)=="SOCKET" and getattr(item,"in_out",None)=="OUTPUT"}
    for iname,idef in (gdef.get("inputs") or {}).items():
        if idef.get("create",True) is False:
            continue
        if iname not in existing_in:
            s=tree.interface.new_socket(iname,in_out="INPUT",socket_type=idef["type"])
            if "value" in idef and "Vector" not in idef["type"]:
                c25_set_default(s,idef["value"])
    for oname,otype in (gdef.get("outputs") or {}).items():
        if oname not in existing_out:
            tree.interface.new_socket(oname,in_out="OUTPUT",socket_type=otype)
    return tree

def c25_find_io_node(tree,bl_idname,name):
    for n in tree.nodes:
        if n.bl_idname==bl_idname:
            n.name=name
            return n
    n=tree.nodes.new(bl_idname); n.name=name
    return n

def c25_update_node(node,info):
    if info.get("type")=="ShaderNodeGroup":
        gname=info.get("group_name") or info.get("name")
        gt=bpy.data.node_groups.get(gname)
        if gt is None:
            raise RuntimeError(f"C25 missing node group {gname}")
        node.node_tree=gt
    if "location" in info:
        node.location=info["location"]
    if info.get("type")=="ShaderNodeTexImage":
        filename=info.get("filename")
        if filename and Path(filename).exists():
            img=bpy.data.images.load(str(filename),check_existing=True)
            if info.get("colorspace"):
                try: img.colorspace_settings.name=info["colorspace"]
                except Exception: pass
            node.image=img
    if info.get("type") in ("ShaderNodeMix","ShaderNodeMixRGB") and "blend_type" in info:
        try: node.blend_type=info["blend_type"]
        except Exception: pass
    if info.get("type") in ("ShaderNodeMath","ShaderNodeVectorMath"):
        if "operation" in info:
            try: node.operation=info["operation"]
            except Exception: pass
        if "use_clamp" in info:
            try: node.use_clamp=info["use_clamp"]
            except Exception: pass
    if info.get("type")=="ShaderNodeValToRGB" and info.get("stops"):
        elems=node.color_ramp.elements
        while len(elems)<len(info["stops"]):
            elems.new(1.0)
        for i,p in enumerate(info["stops"]):
            elems[i].position=p
    if info.get("type")=="ShaderNodeValue" and "value" in info:
        node.outputs[0].default_value=info["value"]
    for key,val in (info.get("values") or {}).items():
        s=c25_socket(node.inputs,key)
        c25_set_default(s,val)
    node.name=info.get("name",node.name)
    if "label" in info:
        node.label=info["label"]

def c25_populate_tree(tree,tree_dict):
    c25_reset_tree(tree)
    node_by_name={}
    for node_name,info in (tree_dict.get("nodes") or {}).items():
        if info.get("create",True) is False:
            continue
        t=info["type"]
        if t=="NodeGroupInput":
            n=c25_find_io_node(tree,"NodeGroupInput",node_name)
        elif t=="NodeGroupOutput":
            n=c25_find_io_node(tree,"NodeGroupOutput",node_name)
        else:
            n=tree.nodes.new(t)
        c25_update_node(n,info)
        node_by_name[node_name]=n
    for link in (tree_dict.get("links") or []):
        if link.get("disabled"):
            continue
        a=node_by_name.get(link.get("from_node")); b=node_by_name.get(link.get("to_node"))
        if a is None or b is None:
            continue
        so=c25_socket(a.outputs,link.get("from_socket"))
        si=c25_socket(b.inputs,link.get("to_socket"))
        if so is None or si is None:
            continue
        try:
            tree.links.new(so,si)
        except Exception:
            pass

def c25_apply_tree(target_tree,tree_dict):
    groups={}
    c25_collect_groups(tree_dict,groups)
    for name,gdef in groups.items():
        c25_ensure_interface(name,gdef)
    for name,gdef in groups.items():
        c25_populate_tree(bpy.data.node_groups[name],gdef)
    c25_populate_tree(target_tree,tree_dict)

def c25_first_group(tree):
    for n in tree.nodes:
        if n.bl_idname=="ShaderNodeGroup":
            return n
    return None

def c25_group_values(group):
    out={}
    for s in group.inputs:
        if hasattr(s,"default_value"):
            v=s.default_value
            if hasattr(v,"__len__") and not isinstance(v,(str,bytes)):
                try: out[s.name]=list(v)
                except Exception: out[s.name]=v
            else:
                out[s.name]=v
    return out

def c25_set_group_values(group,settings):
    for key,val in settings.items():
        s=c25_socket(group.inputs,key)
        c25_set_default(s,val)

def c25_apply_mpfb_enhanced_skin(material):
    if not C25_MATURE_STACK:
        return {"enabled":False}
    data=c25_mpfb_data_root()
    template=(data/"node_trees"/"enhanced_skin.json").read_text(encoding="utf-8")
    diffuse=Path(SKIN_ALBEDO_PATH)
    if not diffuse.is_absolute():
        diffuse=ROOT/diffuse
    diffuse=diffuse.resolve()
    sss=(data/"textures"/"sss.png").resolve()
    if not diffuse.exists() or not sss.exists():
        raise RuntimeError(f"C25 mature skin inputs missing diffuse={diffuse.exists()} sss={sss.exists()}")
    replacements={
        '"$group_name"':json.dumps("DIGE_C25_MPFB_ENHANCED_SKIN"),
        '"$Roughness"':"0.45",
        '"$has_sss"':"true",
        '"$has_diffusetexture"':"true",
        '"$diffusetexture_filename"':json.dumps(str(diffuse)),
        '"$has_normalmap"':"false",
        '"$normalmap_filename"':json.dumps(""),
        '"$ssstexture_filename"':json.dumps(str(sss)),
    }
    for a,b in replacements.items():
        template=template.replace(a,b)
    tree_dict=json.loads(template)
    c25_apply_tree(material.node_tree,tree_dict)
    group=c25_first_group(material.node_tree)
    if group is None:
        raise RuntimeError("C25 MPFB enhanced skin group missing after JSON apply")
    settings={
        "Brightness":0.0,
        "Clearcoat":0.10,
        "Clearcoat Roughness":0.30,
        "Contrast":0.0,
        "Pore detail":2.0,
        "Pore distortion":1.0,
        "Pore scale":2500.0,
        "Pore strength":0.20,
        "Roughness":0.45,
        "colorMixIn":(1.0,0.2,0.2,1.0),
        "colorMixInStrength":0.05,
        "SSS strength":0.20,
        "SSS radius scale":0.10,
        "SSS radius R":1.0,
        "SSS radius G":0.2,
        "SSS radius B":0.1,
    }
    if C26_PHOTOMETRIC:
        # C25 material machinery was the correct base, but C25 hero was washed out.
        # C26 keeps the official MPFB2 graph and only makes a conservative, single
        # material refinement for visible pore/pigment retention under lower-energy light.
        settings.update({
            "Clearcoat":0.05,
            "Clearcoat Roughness":0.38,
            "Pore detail":3.0,
            "Pore distortion":0.80,
            "Pore scale":2800.0,
            "Pore strength":0.30,
            "Roughness":0.50,
            "colorMixInStrength":0.02,
            "SSS strength":0.10,
            "SSS radius scale":0.07,
        })
    c25_set_group_values(group,settings)
    values=c25_group_values(group)
    for key in ("Pore detail","Pore scale","Pore strength","Roughness","SSS strength"):
        if key not in values:
            raise RuntimeError(f"C25 MPFB skin missing socket {key}")
    return {
        "enabled":True,
        "source":"makehumancommunity/mpfb2",
        "commit":C25_MPFB2_COMMIT or None,
        "material_model":"ENHANCED_SSS",
        "integration":"PINNED_JSON_NODE_TREE",
        "template_sha256":sha(data/"node_trees"/"enhanced_skin.json"),
        "source_albedo_file":diffuse.name,
        "source_albedo_sha256":sha(diffuse),
        "group_name":group.node_tree.name if group.node_tree else group.name,
        "settings":{k:values.get(k) for k in settings},
    }

def c25_apply_mpfb_procedural_eyes(material):
    if not C25_MATURE_STACK:
        return {"enabled":False}
    data=c25_mpfb_data_root()
    p=data/"node_trees"/"procedural_eyes.json"
    tree_dict=json.loads(p.read_text(encoding="utf-8"))
    c25_apply_tree(material.node_tree,tree_dict)
    group=c25_first_group(material.node_tree)
    if group is None:
        raise RuntimeError("C25 procedural eye group missing after JSON apply")
    settings={
        "Clearcoat":0.40,
        "Clearcoat Roughness":0.0,
        "EyeWhiteColor":(0.94,0.92,0.90,1.0),
        "InnerLayerRoughness":0.05,
        "IrisBumpStrength":0.30,
        "IrisClockwiseMult":3.5,
        "IrisFeatureScale":16.9,
        "IrisMajorColor":(0.16,0.055,0.018,1.0),
        "IrisMinorColor":(0.055,0.018,0.008,1.0),
        "IrisRadialMult":0.30,
        "IrisSection1End":0.10,
        "IrisSection2End":0.80,
        "IrisSection3End":0.85,
        "IrisSection4Color":(0.020,0.010,0.006,1.0),
        "IrisToEyeWhiteRelation":0.39,
        "OuterLayerAlpha":1.0,
        "OuterLayerColor":(1.0,1.0,1.0,1.0),
        "OuterLayerIOR":1.33,
        "OuterLayerRoughness":0.0,
        "OuterLayerTransmission":1.0,
        "PupilColor":(0.0,0.0,0.0,1.0),
        "PupilSize":0.30,
    }
    c25_set_group_values(group,settings)
    values=c25_group_values(group)
    for key in ("IrisBumpStrength","IrisToEyeWhiteRelation","OuterLayerIOR","OuterLayerTransmission","PupilSize"):
        if key not in values:
            raise RuntimeError(f"C25 MPFB eye missing socket {key}")
    return {
        "enabled":True,
        "source":"makehumancommunity/mpfb2",
        "commit":C25_MPFB2_COMMIT or None,
        "material_model":"PROCEDURAL_EYES",
        "integration":"PINNED_JSON_NODE_TREE",
        "template_sha256":sha(p),
        "group_name":group.node_tree.name if group.node_tree else group.name,
        "settings":{k:values.get(k) for k in settings},
    }

SKIN_SSS_WEIGHT=float(os.environ.get("DIGE_SKIN_SSS_WEIGHT","0.35"))
SKIN_SSS_SCALE=float(os.environ.get("DIGE_SKIN_SSS_SCALE","0.0025"))
SKIN_SSS_ANISO=float(os.environ.get("DIGE_SKIN_SSS_ANISO","0.80"))
SKIN_ROUGH_MIN=float(os.environ.get("DIGE_SKIN_ROUGH_MIN","0.30"))
SKIN_ROUGH_MAX=float(os.environ.get("DIGE_SKIN_ROUGH_MAX","0.48"))
SKIN_ALBEDO_PATH=os.environ.get("DIGE_SKIN_ALBEDO_PATH","").strip()
SKIN_ALBEDO_EXPECTED_SHA256=os.environ.get("DIGE_SKIN_ALBEDO_SHA256","").strip().lower()
SKIN_ALBEDO_NAME=os.environ.get("DIGE_SKIN_ALBEDO_NAME","onlytheghosts_young_eurasian_female").strip()
SKIN_ALBEDO_SAT=float(os.environ.get("DIGE_SKIN_ALBEDO_SAT","0.92"))
SKIN_ALBEDO_VALUE=float(os.environ.get("DIGE_SKIN_ALBEDO_VALUE","0.74"))
EYE_TEX_SAT=float(os.environ.get("DIGE_EYE_TEX_SAT","1.0"))
EYE_TEX_VALUE=float(os.environ.get("DIGE_EYE_TEX_VALUE","1.0"))
HAIR_TEX_SAT=float(os.environ.get("DIGE_HAIR_TEX_SAT","1.0"))
HAIR_TEX_VALUE=float(os.environ.get("DIGE_HAIR_TEX_VALUE","1.0"))
FACE_MESO_SCALE=float(os.environ.get("DIGE_FACE_MESO_SCALE","1.0"))
SKIN_TONE_R=float(os.environ.get("DIGE_SKIN_TONE_R","0.86"))
SKIN_TONE_G=float(os.environ.get("DIGE_SKIN_TONE_G","0.72"))
SKIN_TONE_B=float(os.environ.get("DIGE_SKIN_TONE_B","0.66"))
SKIN_TONE_MIX=float(os.environ.get("DIGE_SKIN_TONE_MIX","0.32"))
SKIN_MICRO_STRENGTH=float(os.environ.get("DIGE_SKIN_MICRO_STRENGTH","0.18"))
SKIN_MESO_FREQ=float(os.environ.get("DIGE_SKIN_MESO_FREQ","72.0"))
SKIN_PORE_FREQ=float(os.environ.get("DIGE_SKIN_PORE_FREQ","420.0"))
SKIN_MICRO_FREQ=float(os.environ.get("DIGE_SKIN_MICRO_FREQ","1400.0"))
SKIN_BUMP_DISTANCE=float(os.environ.get("DIGE_SKIN_BUMP_DISTANCE","0.00016"))
SKIN_COAT_WEIGHT=float(os.environ.get("DIGE_SKIN_COAT_WEIGHT","0.004"))
SKIN_COAT_ROUGHNESS=float(os.environ.get("DIGE_SKIN_COAT_ROUGHNESS","0.34"))
C18_HYBRID_BULK=os.environ.get("DIGE_C18_HYBRID_BULK","0").strip()=="1"
C19_HUMANIZATION=os.environ.get("DIGE_C19_HUMANIZATION","0").strip()=="1"
C19_PHOTO_LIGHTING=os.environ.get("DIGE_C19_PHOTO_LIGHTING","0").strip()=="1"
C20_VISUAL_REPAIR=os.environ.get("DIGE_C20_VISUAL_REPAIR","0").strip()=="1"
C21_NATURAL_DETAIL=os.environ.get("DIGE_C21_NATURAL_DETAIL","0").strip()=="1"
C22_PHYSICAL_SKIN=os.environ.get("DIGE_C22_PHYSICAL_SKIN","0").strip()=="1"
C22_LANDMARK_GROOM=os.environ.get("DIGE_C22_LANDMARK_GROOM","0").strip()=="1"
C22_HAIR_MASS_WARP=os.environ.get("DIGE_C22_HAIR_MASS_WARP","0").strip()=="1"
C23_CALIBRATED_EYES=os.environ.get("DIGE_C23_CALIBRATED_EYES","0").strip()=="1"
C23_FACE_PLANES=os.environ.get("DIGE_C23_FACE_PLANES","0").strip()=="1"
C23_HAIRLINE_REPAIR=os.environ.get("DIGE_C23_HAIRLINE_REPAIR","0").strip()=="1"
C24_SURFACE_EYES=os.environ.get("DIGE_C24_SURFACE_EYES","0").strip()=="1"
C24_SOURCE_ALBEDO=os.environ.get("DIGE_C24_SOURCE_ALBEDO","0").strip()=="1"
C24_HAIRLINE_REPAIR=os.environ.get("DIGE_C24_HAIRLINE_REPAIR","0").strip()=="1"
C25_MATURE_STACK=os.environ.get("DIGE_C25_MATURE_STACK","0").strip()=="1"
C25_MPFB2_SRC=os.environ.get("DIGE_MPFB2_SRC","").strip()
C25_MPFB2_COMMIT=os.environ.get("DIGE_MPFB2_COMMIT","").strip()
C25_MHMAT_PATH=os.environ.get("DIGE_C25_MHMAT_PATH","").strip()
C25_GROOM_CLIP=os.environ.get("DIGE_C25_GROOM_CLIP","0").strip()=="1"
C26_PHOTOMETRIC=os.environ.get("DIGE_C26_PHOTOMETRIC","0").strip()=="1"
C26_SAFE_GROOM=os.environ.get("DIGE_C26_SAFE_GROOM","0").strip()=="1"
C26_FIBER_GROOM=os.environ.get("DIGE_C26_FIBER_GROOM","0").strip()=="1"
C27_SURFACE_FIBERS=os.environ.get("DIGE_C27_SURFACE_FIBERS","0").strip()=="1"
C27_NATIVE_INTERFACES=os.environ.get("DIGE_C27_NATIVE_INTERFACES","0").strip()=="1"
C28_GNM_HEAD=os.environ.get("DIGE_C28_GNM_HEAD","0").strip()=="1"
C28_GNM_DIR=os.environ.get("DIGE_C28_GNM_DIR","runtime/gnm_c28").strip()
C28_GNM_COMMIT=os.environ.get("DIGE_GNM_COMMIT","").strip()
C28_HEAD_SCALE_BIAS=float(os.environ.get("DIGE_C28_HEAD_SCALE_BIAS","1.00"))
C28_HEAD_Z_OFFSET=float(os.environ.get("DIGE_C28_HEAD_Z_OFFSET","0.000"))
C29_GNM_PRESENTATION=os.environ.get("DIGE_C29_GNM_PRESENTATION","0").strip()=="1"
C30_GNM_SEMANTIC_IDENTITY=os.environ.get("DIGE_C30_GNM_SEMANTIC_IDENTITY","0").strip()=="1"
C31_GNM_FACE_APPEARANCE=os.environ.get("DIGE_C31_GNM_FACE_APPEARANCE","0").strip()=="1"
C32_GNM_DERMAL_HAIR=os.environ.get("DIGE_C32_GNM_DERMAL_HAIR","0").strip()=="1"
C19_HAIRLINE_CENTER_Z=float(os.environ.get("DIGE_C19_HAIRLINE_CENTER_Z","1.600"))
C19_HAIRLINE_TEMPLE_RISE=float(os.environ.get("DIGE_C19_HAIRLINE_TEMPLE_RISE","0.08"))
HAIR_STRANDS_PER_ROOT=max(4,int(os.environ.get("DIGE_HAIR_STRANDS_PER_ROOT","16")))
HAIR_ACCENT_LENGTH_SCALE=float(os.environ.get("DIGE_HAIR_ACCENT_LENGTH_SCALE","0.72"))
HAIR_FRONT_SAFE_BLEND=float(os.environ.get("DIGE_HAIR_FRONT_SAFE_BLEND","0.92"))
RENDER_SET=os.environ.get("DIGE_RENDER_SET","FULL").strip().upper()
HAIR_ASSET_KEY=os.environ.get("DIGE_HAIR_ASSET_KEY",CANON["assets"]["system_assets_c12"].get("hair_default_key","hair_short03")).strip()

def make_skin():
    m=bpy.data.materials.new("DIGE_V8_SKIN")
    m.use_nodes=True
    nt=m.node_tree; bs=nt.nodes.get("Principled BSDF")
    set_input(bs,"IOR",1.42)
    set_input(bs,"Subsurface Weight",SKIN_SSS_WEIGHT)
    set_input(bs,"Subsurface Scale",SKIN_SSS_SCALE)
    if hasattr(bs,"subsurface_method"):
        bs.subsurface_method='RANDOM_WALK_SKIN'
    if hasattr(bs,"distribution"):
        bs.distribution='MULTI_GGX'
    set_input(bs,"Subsurface Radius",(1.0,.45,.18))
    set_input(bs,"Specular IOR Level",.30)
    set_input(bs,"Subsurface Anisotropy",SKIN_SSS_ANISO)
    set_input(bs,"Coat Weight",SKIN_COAT_WEIGHT)
    set_input(bs,"Coat Roughness",SKIN_COAT_ROUGHNESS)

    tex=nt.nodes.new("ShaderNodeTexCoord")
    skin_vec=tex.outputs["Object"] if C22_PHYSICAL_SKIN else tex.outputs["Generated"]
    skin_coord_space="OBJECT_METERS" if C22_PHYSICAL_SKIN else "GENERATED_NORMALIZED"
    skin_asset={
        "enabled":False,
        "file":None,
        "sha256":None,
        "expected_sha256":SKIN_ALBEDO_EXPECTED_SHA256 or None,
        "license":"CC0",
        "source_pack":"MakeHuman Skins01 CC0",
        "source_url":"https://files2.makehumancommunity.org/asset_packs/skins01/skins01_cc0.zip",
        "asset_name":SKIN_ALBEDO_NAME,
    }

    regional=nt.nodes.new("ShaderNodeTexNoise")
    regional.inputs["Scale"].default_value=3.2
    regional.inputs["Detail"].default_value=2.4
    regional.inputs["Roughness"].default_value=.50
    nt.links.new(skin_vec,regional.inputs["Vector"])
    tint=nt.nodes.new("ShaderNodeValToRGB")
    tint.color_ramp.elements[0].position=.18
    tint.color_ramp.elements[0].color=(0.92,0.86,0.83,1)
    tint.color_ramp.elements[1].position=.82
    tint.color_ramp.elements[1].color=(1.06,1.02,.98,1)
    nt.links.new(regional.outputs["Fac"],tint.inputs["Fac"])

    if SKIN_ALBEDO_PATH:
        p=Path(SKIN_ALBEDO_PATH)
        if not p.is_absolute():
            p=ROOT/p
        if not p.exists():
            raise RuntimeError(f"Configured skin albedo missing: {p}")
        got=sha(p)
        if SKIN_ALBEDO_EXPECTED_SHA256 and got.lower()!=SKIN_ALBEDO_EXPECTED_SHA256:
            raise RuntimeError(f"Skin albedo hash drift: expected={SKIN_ALBEDO_EXPECTED_SHA256} got={got}")
        img=bpy.data.images.load(str(p),check_existing=True)
        try:
            img.colorspace_settings.name='sRGB'
        except Exception:
            pass
        albedo=nt.nodes.new("ShaderNodeTexImage")
        albedo.image=img
        albedo.interpolation='Linear'
        albedo.extension='EXTEND'
        nt.links.new(tex.outputs["UV"],albedo.inputs["Vector"])
        grade=nt.nodes.new("ShaderNodeHueSaturation")
        grade.inputs["Saturation"].default_value=SKIN_ALBEDO_SAT
        grade.inputs["Value"].default_value=SKIN_ALBEDO_VALUE
        nt.links.new(albedo.outputs["Color"],grade.inputs["Color"])
        skin_tone=nt.nodes.new("ShaderNodeRGB")
        skin_tone.outputs[0].default_value=(SKIN_TONE_R,SKIN_TONE_G,SKIN_TONE_B,1)
        warm_mix=nt.nodes.new("ShaderNodeMixRGB")
        warm_mix.blend_type='MULTIPLY'
        warm_mix.inputs["Fac"].default_value=.08 if C24_SOURCE_ALBEDO else SKIN_TONE_MIX
        nt.links.new(grade.outputs["Color"],warm_mix.inputs[1])
        nt.links.new(skin_tone.outputs["Color"],warm_mix.inputs[2])
        color_mix=nt.nodes.new("ShaderNodeMixRGB")
        color_mix.blend_type='MULTIPLY'
        color_mix.inputs["Fac"].default_value=.045 if C24_SOURCE_ALBEDO else (.22 if C20_VISUAL_REPAIR else .10)
        nt.links.new(warm_mix.outputs["Color"],color_mix.inputs[1])
        nt.links.new(tint.outputs["Color"],color_mix.inputs[2])
        nt.links.new(color_mix.outputs["Color"],bs.inputs["Base Color"])
        skin_asset.update({"enabled":True,"file":p.name,"sha256":got})
    else:
        tone=nt.nodes.new("ShaderNodeValToRGB")
        tone.color_ramp.elements[0].position=.20
        tone.color_ramp.elements[0].color=(0.255,0.090,0.058,1)
        tone.color_ramp.elements[1].position=.80
        tone.color_ramp.elements[1].color=(0.335,0.145,0.090,1)
        nt.links.new(regional.outputs["Fac"],tone.inputs["Fac"])
        nt.links.new(tone.outputs["Color"],bs.inputs["Base Color"])

    # Roughness is independent from albedo so pigmentation never becomes gloss directly.
    rough_macro=nt.nodes.new("ShaderNodeTexNoise")
    rough_macro.inputs["Scale"].default_value=6.0
    rough_macro.inputs["Detail"].default_value=3.0
    rough_macro.inputs["Roughness"].default_value=.55
    nt.links.new(skin_vec,rough_macro.inputs["Vector"])
    rough_micro=nt.nodes.new("ShaderNodeTexNoise")
    rough_micro.inputs["Scale"].default_value=650.0 if C22_PHYSICAL_SKIN else 78.0
    rough_micro.inputs["Detail"].default_value=3.0
    rough_micro.inputs["Roughness"].default_value=.62
    nt.links.new(skin_vec,rough_micro.inputs["Vector"])
    r1=nt.nodes.new("ShaderNodeMath"); r1.operation='MULTIPLY'; r1.inputs[1].default_value=.70
    r2=nt.nodes.new("ShaderNodeMath"); r2.operation='MULTIPLY'; r2.inputs[1].default_value=.30
    rsum=nt.nodes.new("ShaderNodeMath"); rsum.operation='ADD'
    nt.links.new(rough_macro.outputs["Fac"],r1.inputs[0]); nt.links.new(rough_micro.outputs["Fac"],r2.inputs[0])
    nt.links.new(r1.outputs[0],rsum.inputs[0]); nt.links.new(r2.outputs[0],rsum.inputs[1])
    rough_map=nt.nodes.new("ShaderNodeMapRange")
    rough_map.inputs["From Min"].default_value=0.0
    rough_map.inputs["From Max"].default_value=1.0
    rough_map.inputs["To Min"].default_value=SKIN_ROUGH_MIN
    rough_map.inputs["To Max"].default_value=SKIN_ROUGH_MAX
    nt.links.new(rsum.outputs[0],rough_map.inputs["Value"])
    nt.links.new(rough_map.outputs["Result"],bs.inputs["Roughness"])

    # Meso / pore / micro normal remain independent from the color texture.
    meso=nt.nodes.new("ShaderNodeTexNoise")
    meso.inputs["Scale"].default_value=SKIN_MESO_FREQ
    meso.inputs["Detail"].default_value=5.0
    meso.inputs["Roughness"].default_value=.68
    nt.links.new(skin_vec,meso.inputs["Vector"])
    pore=nt.nodes.new("ShaderNodeTexNoise")
    pore.inputs["Scale"].default_value=SKIN_PORE_FREQ
    pore.inputs["Detail"].default_value=4.0
    pore.inputs["Roughness"].default_value=.62
    nt.links.new(skin_vec,pore.inputs["Vector"])
    micro=nt.nodes.new("ShaderNodeTexNoise")
    micro.inputs["Scale"].default_value=SKIN_MICRO_FREQ
    micro.inputs["Detail"].default_value=2.0
    micro.inputs["Roughness"].default_value=.58
    nt.links.new(skin_vec,micro.inputs["Vector"])
    m1=nt.nodes.new("ShaderNodeMath"); m1.operation='MULTIPLY'; m1.inputs[1].default_value=.28
    m2=nt.nodes.new("ShaderNodeMath"); m2.operation='MULTIPLY'; m2.inputs[1].default_value=.50
    m3=nt.nodes.new("ShaderNodeMath"); m3.operation='MULTIPLY'; m3.inputs[1].default_value=.22
    ma=nt.nodes.new("ShaderNodeMath"); ma.operation='ADD'
    mb=nt.nodes.new("ShaderNodeMath"); mb.operation='ADD'
    nt.links.new(meso.outputs["Fac"],m1.inputs[0]); nt.links.new(pore.outputs["Fac"],m2.inputs[0]); nt.links.new(micro.outputs["Fac"],m3.inputs[0])
    nt.links.new(m1.outputs[0],ma.inputs[0]); nt.links.new(m2.outputs[0],ma.inputs[1]); nt.links.new(ma.outputs[0],mb.inputs[0]); nt.links.new(m3.outputs[0],mb.inputs[1])
    bump=nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value=SKIN_MICRO_STRENGTH
    bump.inputs["Distance"].default_value=SKIN_BUMP_DISTANCE
    nt.links.new(mb.outputs[0],bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
    skin_asset["coordinate_space"]=skin_coord_space
    return m,skin_asset

def principled(name,base,rough=.45,ior=1.45,subsurface=0.0,transmission=0.0,metallic=0.0,sheen=0.0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes.get("Principled BSDF")
    set_input(n,"Base Color",(*base,1)); set_input(n,"Roughness",rough)
    set_input(n,"IOR",ior); set_input(n,"Subsurface Weight",subsurface)
    set_input(n,"Transmission Weight",transmission); set_input(n,"Metallic",metallic)
    set_input(n,"Sheen Weight",sheen)
    return m

def hair_material():
    m=bpy.data.materials.new("DIGE_V8_HAIR"); m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    try:
        h=nt.nodes.new("ShaderNodeBsdfHairPrincipled")
        if hasattr(h,"parametrization"):
            try: h.parametrization='MELANIN'
            except Exception: pass
        if hasattr(h,"model"):
            try: h.model='HUANG'
            except Exception: pass
        set_input(h,"Aspect Ratio",.90)
        set_input(h,"Reflection",1.0)
        set_input(h,"Transmission",1.0)
        set_input(h,"Secondary Reflection",1.0)
        set_input(h,"Melanin",.82 if C32_GNM_DERMAL_HAIR else .93)
        set_input(h,"Melanin Redness",.065 if C32_GNM_DERMAL_HAIR else .04)
        set_input(h,"Random Color",.085 if C32_GNM_DERMAL_HAIR else .03)
        set_input(h,"Roughness",.34 if C32_GNM_DERMAL_HAIR else .28)
        set_input(h,"Radial Roughness",.42 if C32_GNM_DERMAL_HAIR else .30)
        set_input(h,"Random Roughness",.11 if C32_GNM_DERMAL_HAIR else .06)
        set_input(h,"Coat",.03 if C32_GNM_DERMAL_HAIR else .02)
        set_input(h,"IOR",1.55)
        if h.inputs.get("Color"): h.inputs["Color"].default_value=(0.018,0.010,0.006,1)
    except Exception:
        h=nt.nodes.new("ShaderNodeBsdfPrincipled")
        set_input(h,"Base Color",(0.018,0.010,0.006,1)); set_input(h,"Roughness",.31)
    nt.links.new(h.outputs[0],out.inputs["Surface"])
    return m

def uv(name,loc,scale,mat,seg=48,rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=loc)
    o=bpy.context.object; o.name=name; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat); bpy.ops.object.shade_smooth()
    return o

def cylinder(name,loc,radius,depth,mat,rot=(math.radians(90),0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object; o.name=name; o.data.materials.append(mat); bpy.ops.object.shade_smooth()
    return o

def curve_object(name,splines,bevel,mat):
    cu=bpy.data.curves.new(name,"CURVE"); cu.dimensions='3D'; cu.resolution_u=2
    cu.bevel_depth=bevel; cu.bevel_resolution=2; cu.fill_mode='FULL'
    ob=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(ob)
    for pts in splines:
        sp=cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts)-1)
        n=max(1,len(pts)-1)
        for idx,(p,co) in enumerate(zip(sp.bezier_points,pts)):
            p.co=co
            p.handle_left_type='AUTO'
            p.handle_right_type='AUTO'
            p.radius=max(.26,1.0-.74*(idx/n))
    ob.data.materials.append(mat); return ob


def verify_asset(path,expected_sha256):
    p=Path(path)
    if not p.exists():
        raise RuntimeError(f"Required C12 system asset missing: {p}")
    got=sha(p)
    if got != expected_sha256:
        raise RuntimeError(f"C12 system asset hash drift: {p.name} expected={expected_sha256} got={got}")
    return p

def parse_mhclo(path):
    spec={"x_scale":None,"y_scale":None,"z_scale":None,"verts":{}}
    status=None
    first=0
    vn=0
    for raw in Path(path).read_text(encoding="utf-8",errors="replace").splitlines():
        words=raw.split()
        if not words:
            continue
        if words[0].startswith("#"):
            continue
        if status=="verts":
            # Official MHCLO files may place metadata such as "material" after
            # the verts marker and before the first numeric mapping (short04 does).
            # Keep the verts section armed until the first mapping arrives; only
            # close it on a non-numeric directive after mappings have started.
            if words[0].lstrip("-").isdigit():
                idx=first+vn
                if len(words)==1:
                    v=int(words[0])
                    spec["verts"][idx]=((v,v,v),(1.0,0.0,0.0),(0.0,0.0,0.0))
                else:
                    v0,v1,v2=(int(words[0]),int(words[1]),int(words[2]))
                    w0,w1,w2=(float(words[3]),float(words[4]),float(words[5]))
                    d0,d1,d2=(float(words[6]),float(words[7]),float(words[8]))
                    # Official MakeClothes importer converts MakeHuman offsets to Blender as (d0,-d2,d1).
                    spec["verts"][idx]=((v0,v1,v2),(w0,w1,w2),(d0,-d2,d1))
                vn+=1
                continue
            elif vn>0:
                status=None
        key=words[0]
        if key in ("x_scale","y_scale","z_scale"):
            spec[key]=(int(words[1]),int(words[2]),float(words[3]))
        elif key=="verts":
            first=int(words[1]) if len(words)>1 else 0
            vn=0
            status="verts"
    if not spec["verts"]:
        raise RuntimeError(f"C12 MHCLO has no vertex mappings: {path}")
    if spec["x_scale"] is None or spec["y_scale"] is None or spec["z_scale"] is None:
        raise RuntimeError(f"C12 MHCLO missing scale contract: {path}")
    return spec

def fit_mhclo_asset(name,obj_path,mhclo_path,fit_vertices,material,contract):
    obj_path=verify_asset(obj_path,contract["obj"]["sha256"])
    mhclo_path=verify_asset(mhclo_path,contract["mhclo"]["sha256"])
    spec=parse_mhclo(mhclo_path)
    bpy.ops.wm.obj_import(
        filepath=str(obj_path),
        forward_axis='Y',
        up_axis='Z',
        use_split_objects=False,
        use_split_groups=False,
    )
    imported=[o for o in bpy.context.selected_objects if o.type=='MESH']
    if len(imported)!=1:
        raise RuntimeError(f"C12 expected one imported mesh for {name}, got {len(imported)}")
    obj=imported[0]
    obj.name=name
    expected=contract["obj"]["vertices"]
    if len(obj.data.vertices)!=expected:
        raise RuntimeError(f"C12 {name} vertex count drift: expected={expected} got={len(obj.data.vertices)}")
    if len(spec["verts"])!=expected or min(spec["verts"])!=0 or max(spec["verts"])!=expected-1:
        raise RuntimeError(f"C12 {name} MHCLO mapping range drift: count={len(spec['verts'])} min={min(spec['verts'])} max={max(spec['verts'])}")
    if not obj.data.uv_layers:
        raise RuntimeError(f"C12 {name} has no UV layer after OBJ import")

    hverts=fit_vertices
    hl=len(hverts)
    xs,ys,zs=spec["x_scale"],spec["y_scale"],spec["z_scale"]
    for pair in (xs,ys,zs):
        if pair[0]>=hl or pair[1]>=hl or pair[2]==0:
            raise RuntimeError(f"C12 {name} MHCLO scale reference invalid: {pair} body_vertices={hl}")
    s0=abs(hverts[xs[0]].x-hverts[xs[1]].x)/xs[2]
    # MakeClothes Blender importer maps y_scale to Blender Z and z_scale to Blender Y.
    s2=abs(hverts[ys[0]].z-hverts[ys[1]].z)/ys[2]
    s1=abs(hverts[zs[0]].y-hverts[zs[1]].y)/zs[2]
    scales=(s0,s1,s2)

    for n in range(expected):
        refs,weights,offset=spec["verts"][n]
        if max(refs)>=hl:
            raise RuntimeError(f"C12 {name} MHCLO ref outside body: {refs} body_vertices={hl}")
        co=(
            hverts[refs[0]]*weights[0] +
            hverts[refs[1]]*weights[1] +
            hverts[refs[2]]*weights[2] +
            Vector((offset[0]*s0,offset[1]*s1,offset[2]*s2))
        )
        obj.data.vertices[n].co=co

    obj.data.materials.clear()
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.shade_smooth()
    pts=[obj.matrix_world @ v.co for v in obj.data.vertices]
    mi=[min(p[i] for p in pts) for i in range(3)]
    ma=[max(p[i] for p in pts) for i in range(3)]
    return obj,{
        "name":name,
        "obj_sha256":sha(obj_path),
        "mhclo_sha256":sha(mhclo_path),
        "vertices":len(obj.data.vertices),
        "polygons":len(obj.data.polygons),
        "uv_layers":len(obj.data.uv_layers),
        "fit_scales":scales,
        "bbox_min":mi,
        "bbox_max":ma,
        "fit_algorithm":"MAKEHUMAN_MHCLO_BARYCENTRIC_OFFSETS_SCALED",
    }

def c28_gnm_skin_material():
    m=bpy.data.materials.new("DIGE_C28_GNM_SKIN")
    m.use_nodes=True
    if C31_GNM_FACE_APPEARANCE:
        nt=m.node_tree
        nt.nodes.clear()
        out=nt.nodes.new("ShaderNodeOutputMaterial")
        bs=nt.nodes.new("ShaderNodeBsdfPrincipled")
        set_input(bs,"IOR",1.42)
        set_input(bs,"Specular IOR Level",.28)
        set_input(bs,"Subsurface Weight",.045 if C32_GNM_DERMAL_HAIR else .070)
        set_input(bs,"Subsurface Scale",.00064 if C32_GNM_DERMAL_HAIR else .00082)
        set_input(bs,"Subsurface Radius",(1.0,.34,.12) if C32_GNM_DERMAL_HAIR else (1.0,.38,.15))
        set_input(bs,"Coat Weight",.004 if C32_GNM_DERMAL_HAIR else .010)
        set_input(bs,"Coat Roughness",.50 if C32_GNM_DERMAL_HAIR else .44)
        if hasattr(bs,"subsurface_method"):
            bs.subsurface_method='RANDOM_WALK_SKIN'

        tex=nt.nodes.new("ShaderNodeTexCoord")
        base_noise=nt.nodes.new("ShaderNodeTexNoise")
        base_noise.inputs["Scale"].default_value=18.0 if C32_GNM_DERMAL_HAIR else 10.0
        base_noise.inputs["Detail"].default_value=5.0 if C32_GNM_DERMAL_HAIR else 4.0
        base_noise.inputs["Roughness"].default_value=.68 if C32_GNM_DERMAL_HAIR else .62
        nt.links.new(tex.outputs["Object"],base_noise.inputs["Vector"])
        base_ramp=nt.nodes.new("ShaderNodeValToRGB")
        base_ramp.color_ramp.elements[0].position=.18
        base_ramp.color_ramp.elements[0].color=((0.205,0.073,0.048,1) if C32_GNM_DERMAL_HAIR else (0.245,0.082,0.042,1))
        base_ramp.color_ramp.elements[1].position=.82
        base_ramp.color_ramp.elements[1].color=((0.395,0.176,0.118,1) if C32_GNM_DERMAL_HAIR else (0.445,0.190,0.102,1))
        nt.links.new(base_noise.outputs["Fac"],base_ramp.inputs["Fac"])

        vc=nt.nodes.new("ShaderNodeVertexColor")
        vc.layer_name="C31_FaceMask"
        sep=nt.nodes.new("ShaderNodeSeparateColor")
        sep.mode='RGB'
        nt.links.new(vc.outputs["Color"],sep.inputs["Color"])

        lip_color=nt.nodes.new("ShaderNodeRGB")
        lip_color.outputs[0].default_value=(0.42,0.075,0.068,1)
        lip_mix=nt.nodes.new("ShaderNodeMixRGB")
        lip_mix.blend_type='MIX'
        nt.links.new(sep.outputs["Red"],lip_mix.inputs[0])
        nt.links.new(base_ramp.outputs["Color"],lip_mix.inputs[1])
        nt.links.new(lip_color.outputs[0],lip_mix.inputs[2])

        blush_color=nt.nodes.new("ShaderNodeRGB")
        blush_color.outputs[0].default_value=(0.46,0.135,0.088,1)
        blush_mix=nt.nodes.new("ShaderNodeMixRGB")
        blush_mix.blend_type='MIX'
        nt.links.new(sep.outputs["Green"],blush_mix.inputs[0])
        nt.links.new(lip_mix.outputs["Color"],blush_mix.inputs[1])
        nt.links.new(blush_color.outputs[0],blush_mix.inputs[2])
        nt.links.new(blush_mix.outputs["Color"],bs.inputs["Base Color"])

        rough_noise=nt.nodes.new("ShaderNodeTexNoise")
        rough_noise.inputs["Scale"].default_value=145.0 if C32_GNM_DERMAL_HAIR else 52.0
        rough_noise.inputs["Detail"].default_value=5.0 if C32_GNM_DERMAL_HAIR else 4.0
        rough_noise.inputs["Roughness"].default_value=.70 if C32_GNM_DERMAL_HAIR else .62
        nt.links.new(tex.outputs["Object"],rough_noise.inputs["Vector"])
        rough_map=nt.nodes.new("ShaderNodeMapRange")
        rough_map.inputs["From Min"].default_value=0.0
        rough_map.inputs["From Max"].default_value=1.0
        rough_map.inputs["To Min"].default_value=.46 if C32_GNM_DERMAL_HAIR else .44
        rough_map.inputs["To Max"].default_value=.64 if C32_GNM_DERMAL_HAIR else .60
        nt.links.new(rough_noise.outputs["Fac"],rough_map.inputs["Value"])
        tzone_scale=nt.nodes.new("ShaderNodeMath"); tzone_scale.operation='MULTIPLY'; tzone_scale.inputs[1].default_value=.055
        lip_rough_scale=nt.nodes.new("ShaderNodeMath"); lip_rough_scale.operation='MULTIPLY'; lip_rough_scale.inputs[1].default_value=.070
        nt.links.new(sep.outputs["Blue"],tzone_scale.inputs[0])
        nt.links.new(sep.outputs["Red"],lip_rough_scale.inputs[0])
        rough_sub1=nt.nodes.new("ShaderNodeMath"); rough_sub1.operation='SUBTRACT'
        rough_sub2=nt.nodes.new("ShaderNodeMath"); rough_sub2.operation='SUBTRACT'
        nt.links.new(rough_map.outputs["Result"],rough_sub1.inputs[0]); nt.links.new(tzone_scale.outputs[0],rough_sub1.inputs[1])
        nt.links.new(rough_sub1.outputs[0],rough_sub2.inputs[0]); nt.links.new(lip_rough_scale.outputs[0],rough_sub2.inputs[1])
        nt.links.new(rough_sub2.outputs[0],bs.inputs["Roughness"])

        pore=nt.nodes.new("ShaderNodeTexNoise")
        pore.inputs["Scale"].default_value=2400.0 if C32_GNM_DERMAL_HAIR else 1900.0
        pore.inputs["Detail"].default_value=5.0
        pore.inputs["Roughness"].default_value=.68
        nt.links.new(tex.outputs["Object"],pore.inputs["Vector"])
        micro=nt.nodes.new("ShaderNodeTexNoise")
        micro.inputs["Scale"].default_value=9000.0 if C32_GNM_DERMAL_HAIR else 6200.0
        micro.inputs["Detail"].default_value=3.0
        micro.inputs["Roughness"].default_value=.60
        nt.links.new(tex.outputs["Object"],micro.inputs["Vector"])
        pscale=nt.nodes.new("ShaderNodeMath"); pscale.operation='MULTIPLY'; pscale.inputs[1].default_value=.58 if C32_GNM_DERMAL_HAIR else .70
        mscale=nt.nodes.new("ShaderNodeMath"); mscale.operation='MULTIPLY'; mscale.inputs[1].default_value=.42 if C32_GNM_DERMAL_HAIR else .30
        nt.links.new(pore.outputs["Fac"],pscale.inputs[0]); nt.links.new(micro.outputs["Fac"],mscale.inputs[0])
        add=nt.nodes.new("ShaderNodeMath"); add.operation='ADD'
        nt.links.new(pscale.outputs[0],add.inputs[0]); nt.links.new(mscale.outputs[0],add.inputs[1])
        bump=nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value=.34 if C32_GNM_DERMAL_HAIR else .24
        bump.inputs["Distance"].default_value=.000052 if C32_GNM_DERMAL_HAIR else .000070
        nt.links.new(add.outputs[0],bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
        nt.links.new(bs.outputs[0],out.inputs["Surface"])
        return m,{
            "model":"C32_GNM_DERMAL_MULTISCALE_SKIN" if C32_GNM_DERMAL_HAIR else "C31_GNM_REGIONAL_RANDOM_WALK_SKIN",
            "mask_attribute":"C31_FaceMask",
            "base_color_range":[[0.245,0.082,0.042],[0.445,0.190,0.102]],
            "lip_color":[0.42,0.075,0.068],
            "blush_color":[0.46,0.135,0.088],
            "roughness_range":([0.46,0.64] if C32_GNM_DERMAL_HAIR else [0.44,0.60]),
            "subsurface_weight":0.045 if C32_GNM_DERMAL_HAIR else 0.070,
            "subsurface_scale":0.00064 if C32_GNM_DERMAL_HAIR else 0.00082,
            "pore_scale":2400.0 if C32_GNM_DERMAL_HAIR else 1900.0,
            "micro_scale":9000.0 if C32_GNM_DERMAL_HAIR else 6200.0,
            "bump_distance":0.000052 if C32_GNM_DERMAL_HAIR else 0.000070,
        }
    if C29_GNM_PRESENTATION:
        nt=m.node_tree
        bs=nt.nodes.get("Principled BSDF")
        set_input(bs,"IOR",1.42)
        set_input(bs,"Roughness",.49)
        set_input(bs,"Specular IOR Level",.27)
        set_input(bs,"Subsurface Weight",.075)
        set_input(bs,"Subsurface Scale",.00085)
        set_input(bs,"Subsurface Radius",(1.0,.38,.16))
        set_input(bs,"Coat Weight",.015)
        set_input(bs,"Coat Roughness",.42)
        if hasattr(bs,"subsurface_method"):
            bs.subsurface_method='RANDOM_WALK_SKIN'

        tex=nt.nodes.new("ShaderNodeTexCoord")
        regional=nt.nodes.new("ShaderNodeTexNoise")
        regional.inputs["Scale"].default_value=8.5
        regional.inputs["Detail"].default_value=3.2
        regional.inputs["Roughness"].default_value=.58
        nt.links.new(tex.outputs["Object"],regional.inputs["Vector"])
        ramp=nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position=.22
        ramp.color_ramp.elements[0].color=(0.30,0.105,0.055,1)
        ramp.color_ramp.elements[1].position=.78
        ramp.color_ramp.elements[1].color=(0.50,0.215,0.125,1)
        nt.links.new(regional.outputs["Fac"],ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"],bs.inputs["Base Color"])

        rough=nt.nodes.new("ShaderNodeTexNoise")
        rough.inputs["Scale"].default_value=46.0
        rough.inputs["Detail"].default_value=4.0
        rough.inputs["Roughness"].default_value=.60
        nt.links.new(tex.outputs["Object"],rough.inputs["Vector"])
        rmap=nt.nodes.new("ShaderNodeMapRange")
        rmap.inputs["From Min"].default_value=0.0
        rmap.inputs["From Max"].default_value=1.0
        rmap.inputs["To Min"].default_value=.43
        rmap.inputs["To Max"].default_value=.58
        nt.links.new(rough.outputs["Fac"],rmap.inputs["Value"])
        nt.links.new(rmap.outputs["Result"],bs.inputs["Roughness"])

        pore=nt.nodes.new("ShaderNodeTexNoise")
        pore.inputs["Scale"].default_value=2500.0
        pore.inputs["Detail"].default_value=4.0
        pore.inputs["Roughness"].default_value=.63
        nt.links.new(tex.outputs["Object"],pore.inputs["Vector"])
        micro=nt.nodes.new("ShaderNodeTexNoise")
        micro.inputs["Scale"].default_value=7800.0
        micro.inputs["Detail"].default_value=2.0
        micro.inputs["Roughness"].default_value=.56
        nt.links.new(tex.outputs["Object"],micro.inputs["Vector"])
        mix=nt.nodes.new("ShaderNodeMath")
        mix.operation='MULTIPLY_ADD'
        mix.inputs[1].default_value=.46
        mix.inputs[2].default_value=.08
        nt.links.new(pore.outputs["Fac"],mix.inputs[0])
        micro_mix=nt.nodes.new("ShaderNodeMath")
        micro_mix.operation='ADD'
        nt.links.new(mix.outputs[0],micro_mix.inputs[0])
        nt.links.new(micro.outputs["Fac"],micro_mix.inputs[1])
        bump=nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value=.16
        bump.inputs["Distance"].default_value=.000045
        nt.links.new(micro_mix.outputs[0],bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
        return m,{
            "model":"C29_PROCEDURAL_RANDOM_WALK_SKIN",
            "mpfb2":False,
            "base_color_range":[[0.30,0.105,0.055],[0.50,0.215,0.125]],
            "roughness_range":[0.43,0.58],
            "subsurface_weight":0.075,
            "subsurface_scale":0.00085,
            "pore_scale":2500.0,
            "micro_scale":7800.0,
            "bump_distance":0.000045,
        }
    if not C25_MATURE_STACK:
        nt=m.node_tree; bs=nt.nodes.get("Principled BSDF")
        set_input(bs,"Base Color",(0.42,0.20,0.13,1))
        set_input(bs,"Roughness",.49)
        set_input(bs,"IOR",1.42)
        set_input(bs,"Subsurface Weight",.085)
        set_input(bs,"Subsurface Scale",.0010)
        if hasattr(bs,"subsurface_method"):
            bs.subsurface_method='RANDOM_WALK_SKIN'
        set_input(bs,"Subsurface Radius",(1.0,.42,.16))
        set_input(bs,"Specular IOR Level",.27)
        tex=nt.nodes.new("ShaderNodeTexCoord")
        pore=nt.nodes.new("ShaderNodeTexNoise")
        pore.inputs["Scale"].default_value=2400.0
        pore.inputs["Detail"].default_value=4.0
        pore.inputs["Roughness"].default_value=.62
        nt.links.new(tex.outputs["Object"],pore.inputs["Vector"])
        bump=nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value=.24
        bump.inputs["Distance"].default_value=.000055
        nt.links.new(pore.outputs["Fac"],bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
        return m,{"model":"RANDOM_WALK_SKIN_OBJECT_SCALE","mpfb2":False}

    data=c25_mpfb_data_root()
    template=(data/"node_trees"/"enhanced_skin.json").read_text(encoding="utf-8")
    replacements={
        '"$group_name"':json.dumps("DIGE_C28_GNM_ENHANCED_SKIN"),
        '"$Roughness"':"0.48",
        '"$has_sss"':"false",
        '"$has_diffusetexture"':"false",
        '"$diffusetexture_filename"':json.dumps(""),
        '"$has_normalmap"':"false",
        '"$normalmap_filename"':json.dumps(""),
        '"$ssstexture_filename"':json.dumps(""),
    }
    for a,b in replacements.items():
        template=template.replace(a,b)
    tree_dict=json.loads(template)
    c25_apply_tree(m.node_tree,tree_dict)
    group=c25_first_group(m.node_tree)
    if group is None:
        raise RuntimeError("C28 MPFB2 enhanced skin group missing")
    settings={
        "DiffuseColor":(0.47,0.235,0.145,1.0),
        "Brightness":-0.02,
        "Clearcoat":0.04,
        "Clearcoat Roughness":0.40,
        "Contrast":0.04,
        "Pore detail":3.4,
        "Pore distortion":0.85,
        "Pore scale":2600.0,
        "Pore strength":0.28,
        "Roughness":0.49,
        "colorMixIn":(0.60,0.24,0.14,1.0),
        "colorMixInStrength":0.08,
        "SSS strength":0.11,
        "SSS radius scale":0.08,
        "SSS radius R":1.0,
        "SSS radius G":0.20,
        "SSS radius B":0.09,
    }
    c25_set_group_values(group,settings)
    values=c25_group_values(group)
    return m,{
        "model":"MPFB2_ENHANCED_SSS_PROCEDURAL_ALBEDO",
        "mpfb2":True,
        "mpfb2_commit":C25_MPFB2_COMMIT or None,
        "settings":{k:values.get(k) for k in settings},
    }

def c28_import_component(path,name,material,scale,translation):
    bpy.ops.wm.obj_import(
        filepath=str(path),
        forward_axis='Y',
        up_axis='Z',
        use_split_objects=False,
        use_split_groups=False,
    )
    imported=[o for o in bpy.context.selected_objects if o.type=='MESH']
    if len(imported)!=1:
        raise RuntimeError(f"C28 expected one imported mesh for {name}, got {len(imported)}")
    obj=imported[0]
    obj.name=name
    tr=Vector(translation)
    for v in obj.data.vertices:
        v.co=v.co*scale+tr
    obj.data.materials.clear()
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.shade_smooth()
    return obj

def alpha_card_material(name,image_path,expected_sha256,rough=.42,ior=1.50,anisotropy=.0,sat=1.0,value=1.0,spec=.28,coat=.025):
    image_path=verify_asset(image_path,expected_sha256)
    m=bpy.data.materials.new(name); m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    tex=nt.nodes.new("ShaderNodeTexImage")
    tex.image=bpy.data.images.load(str(image_path),check_existing=True)
    try: tex.image.colorspace_settings.name='sRGB'
    except Exception: pass
    tex.interpolation='Linear'
    trans=nt.nodes.new("ShaderNodeBsdfTransparent")
    bs=nt.nodes.new("ShaderNodeBsdfPrincipled")
    set_input(bs,"Roughness",rough); set_input(bs,"IOR",ior)
    set_input(bs,"Specular IOR Level",spec)
    set_input(bs,"Anisotropic IOR Level",anisotropy)
    set_input(bs,"Coat Weight",coat)
    grade=nt.nodes.new("ShaderNodeHueSaturation")
    grade.inputs["Saturation"].default_value=sat
    grade.inputs["Value"].default_value=value
    nt.links.new(tex.outputs["Color"],grade.inputs["Color"])
    nt.links.new(grade.outputs["Color"],bs.inputs["Base Color"])
    mix=nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tex.outputs["Alpha"],mix.inputs[0])
    nt.links.new(trans.outputs[0],mix.inputs[1])
    nt.links.new(bs.outputs[0],mix.inputs[2])
    nt.links.new(mix.outputs[0],out.inputs["Surface"])
    return m

def eye_texture_material(name,image_path,expected_sha256):
    image_path=verify_asset(image_path,expected_sha256)
    m=bpy.data.materials.new(name); m.use_nodes=True
    nt=m.node_tree; nt.nodes.clear()
    out=nt.nodes.new("ShaderNodeOutputMaterial")
    tex=nt.nodes.new("ShaderNodeTexImage")
    tex.image=bpy.data.images.load(str(image_path),check_existing=True)
    try: tex.image.colorspace_settings.name='sRGB'
    except Exception: pass
    tex.interpolation='Linear'
    base=nt.nodes.new("ShaderNodeBsdfPrincipled")
    set_input(base,"Roughness",.24); set_input(base,"IOR",1.376)
    set_input(base,"Specular IOR Level",.34)
    set_input(base,"Subsurface Weight",.012)
    eye_grade=nt.nodes.new("ShaderNodeHueSaturation")
    eye_grade.inputs["Saturation"].default_value=EYE_TEX_SAT
    eye_grade.inputs["Value"].default_value=EYE_TEX_VALUE
    nt.links.new(tex.outputs["Color"],eye_grade.inputs["Color"])
    nt.links.new(eye_grade.outputs["Color"],base.inputs["Base Color"])
    glass=nt.nodes.new("ShaderNodeBsdfGlass")
    set_input(glass,"Roughness",.012); set_input(glass,"IOR",1.376)
    mix=nt.nodes.new("ShaderNodeMixShader")
    # Opaque texels are sclera/iris; transparent texels become refractive cornea.
    nt.links.new(tex.outputs["Alpha"],mix.inputs[0])
    nt.links.new(glass.outputs[0],mix.inputs[1])
    nt.links.new(base.outputs[0],mix.inputs[2])
    nt.links.new(mix.outputs[0],out.inputs["Surface"])
    return m


bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

skin,skin_asset=make_skin()
sclera=principled("SCLERA",(0.58,0.52,0.48),rough=.30,ior=1.376,subsurface=.02)
iris=principled("IRIS",(0.070,0.026,0.012),rough=.32,ior=1.40)
iris_ring=principled("IRIS_RING",(0.012,0.005,0.003),rough=.34,ior=1.40)
black=principled("BLACK",(0.005,0.004,0.004),rough=.28)
cornea=principled("CORNEA",(0.92,0.92,0.92),rough=.008,ior=1.376,transmission=1.0)
wetline=principled("EYE_WETLINE",(0.90,0.92,0.94),rough=.018,ior=1.333,transmission=1.0)
lip=principled("LIP",(0.18,0.035,0.032),rough=.44,ior=1.40,subsurface=.04)
mouth_dark=principled("MOUTH_DARK",(0.018,0.004,0.004),rough=.58,ior=1.35)
scalp_shadow=principled("SCALP_SHADOW",(0.075,0.026,0.018),rough=.50,ior=1.42,subsurface=.06)
hair=hair_material()
hair_mass=principled("DIGE_V8_HAIR_MASS",(0.006,0.0035,0.0022),rough=.46,ior=1.55)
hm_bs=hair_mass.node_tree.nodes.get("Principled BSDF")
set_input(hm_bs,"Specular IOR Level",.22)
set_input(hm_bs,"Coat Weight",.10)
set_input(hm_bs,"Coat Roughness",.30)
set_input(hm_bs,"Anisotropic IOR Level",.35)
cloth=principled("CLOTH",(0.020,0.026,0.040),rough=.72,sheen=.12)
floor_mat=principled("FLOOR",(0.12,0.12,0.125),rough=.70)

mesh_path=RUNTIME/"dige_makehuman_v8.obj"
# Builder already writes Blender-space coordinates (Y forward, Z up). Import with an identity axis convention;
# Blender's default OBJ convention (-Z forward, Y up) would rotate the body a second time.
bpy.ops.wm.obj_import(
    filepath=str(mesh_path),
    forward_axis='Y',
    up_axis='Z',
    use_split_objects=False,
    use_split_groups=False,
)
imported_meshes=[o for o in bpy.context.selected_objects if o.type == 'MESH']
if len(imported_meshes) != 1:
    raise RuntimeError(f"Expected exactly one body mesh, got {len(imported_meshes)}")
body=imported_meshes[0]
body.name="DIGE_V8_MAKEHUMAN_BODY"
body.data.materials.append(skin)
bpy.ops.object.shade_smooth()
c25_mpfb_skin={"enabled":False}
if C25_MATURE_STACK:
    c25_mpfb_skin=c25_apply_mpfb_enhanced_skin(skin)
    skin_asset.update({
        "c25_mpfb2_enhanced":True,
        "c25_mpfb2_commit":C25_MPFB2_COMMIT or None,
        "c25_mpfb2_material_model":"ENHANCED_SSS",
    })

# Hard orientation gate before any cosmetic layer can hide an ingestion error.
bbox_world=[body.matrix_world @ Vector(corner) for corner in body.bound_box]
bbox_min=[min(v[i] for v in bbox_world) for i in range(3)]
bbox_max=[max(v[i] for v in bbox_world) for i in range(3)]
bbox_extent=[bbox_max[i]-bbox_min[i] for i in range(3)]
if not (1.60 <= bbox_extent[2] <= 1.80):
    raise RuntimeError(f"Body vertical extent invalid after OBJ import: {bbox_extent}")
if bbox_extent[1] >= 0.65:
    raise RuntimeError(f"Body depth indicates axis-rotation regression: {bbox_extent}")
if bbox_min[2] < -0.03 or bbox_max[2] > 1.75:
    raise RuntimeError(f"Body Z placement invalid: min={bbox_min[2]} max={bbox_max[2]}")

geom=json.loads((RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json").read_text())
if geom.get("canon_execution_manifest_sha256") != CANON_SHA256:
    raise RuntimeError("geometry/canon manifest causal binding mismatch")
landmarks=geom["landmarks"]
mouth_z=landmarks["mouth_front"]["center"][2]
eye_mid_z=(landmarks["left_eye"]["center"][2]+landmarks["right_eye"]["center"][2])*.5
cheek_z=mouth_z+.034
nose_bridge_z=eye_mid_z-.010
nose_tip_z=mouth_z+.027
chin_z=mouth_z-.038
jaw_z=mouth_z-.026

# No hard polygon scalp-shadow assignment in C6; canonical scalp remains skin under strand coverage.
scalp_shadow_polygons=0

craniofacial_deform={
  "cheek_y_m":0.0045,
  "nose_bridge_y_m":0.0035,
  "nose_tip_y_m":0.0060,
  "chin_y_m":0.0030,
  "lip_volume_y_m":0.0018,
  "jaw_x_scale":0.985,
  "asymmetry_y_m":0.0007,
  "brow_ridge_y_m":0.0013,
  "tear_trough_y_m":0.00075,
  "nasolabial_y_m":0.00085,
  "philtrum_groove_y_m":0.00065,
  "philtrum_ridge_y_m":0.00055,
  "alar_groove_y_m":0.00075,
  "labiomental_groove_y_m":0.00070,
  "lip_corner_y_m":0.00045,
  "lower_lid_roll_y_m":0.00050,
}
# FACE_MESO_SCALE_APPLIED
for _k in ("cheek_y_m","nose_bridge_y_m","nose_tip_y_m","chin_y_m","lip_volume_y_m","brow_ridge_y_m","tear_trough_y_m","nasolabial_y_m","philtrum_groove_y_m","philtrum_ridge_y_m","alar_groove_y_m","labiomental_groove_y_m","lip_corner_y_m","lower_lid_roll_y_m"):
    craniofacial_deform[_k] *= FACE_MESO_SCALE
if C23_FACE_PLANES:
    # C23 shifts emphasis from uniform over-scaling to photographic facial planes.
    craniofacial_deform["cheek_y_m"] *= 1.12
    craniofacial_deform["nose_bridge_y_m"] *= 1.22
    craniofacial_deform["nose_tip_y_m"] *= 1.20
    craniofacial_deform["chin_y_m"] *= 1.12
    craniofacial_deform["brow_ridge_y_m"] *= 1.10
    craniofacial_deform["tear_trough_y_m"] *= .90
    craniofacial_deform["nasolabial_y_m"] *= 1.18
    craniofacial_deform["philtrum_groove_y_m"] *= 1.15
    craniofacial_deform["alar_groove_y_m"] *= 1.16
    craniofacial_deform["labiomental_groove_y_m"] *= 1.15
def g2(x,z,cx,cz,sx,sz):
    return math.exp(-0.5*(((x-cx)/sx)**2+((z-cz)/sz)**2))

for v in body.data.vertices:
    co=v.co
    # Only the forward facial surface; back/head/body vertices remain untouched.
    if co.y <= 0.0 or co.z < chin_z-.035 or co.z > eye_mid_z+.085 or abs(co.x) > .120:
        continue

    # Cheek/malar projection with tiny natural asymmetry.
    wl=g2(co.x,co.z,.052,cheek_z,.031,.031)
    wr=g2(co.x,co.z,-.052,cheek_z,.031,.031)
    co.y += craniofacial_deform["cheek_y_m"]*(wl+wr)
    co.y += craniofacial_deform["asymmetry_y_m"]*(wr-wl)

    # Nose bridge and tip remain bounded around the midline.
    co.y += craniofacial_deform["nose_bridge_y_m"]*g2(co.x,co.z,0.0,nose_bridge_z,.015,.030)
    co.y += craniofacial_deform["nose_tip_y_m"]*g2(co.x,co.z,0.0,nose_tip_z,.014,.015)

    # Native lip volume: geometry, not a painted/floating replacement.
    co.y += craniofacial_deform["lip_volume_y_m"]*g2(co.x,co.z,0.0,mouth_z,.030,.008)

    # Meso facial planes. All offsets remain sub-1.5 mm and are landmark-relative.
    co.y += craniofacial_deform["brow_ridge_y_m"]*(
        g2(co.x,co.z,.030,eye_mid_z+.024,.020,.013)+
        g2(co.x,co.z,-.030,eye_mid_z+.024,.020,.013)
    )
    co.y -= craniofacial_deform["tear_trough_y_m"]*(
        g2(co.x,co.z,.032,eye_mid_z-.016,.023,.010)+
        g2(co.x,co.z,-.032,eye_mid_z-.016,.023,.010)
    )
    co.y -= craniofacial_deform["nasolabial_y_m"]*(
        g2(co.x,co.z,.027,mouth_z+.020,.015,.024)+
        g2(co.x,co.z,-.027,mouth_z+.020,.015,.024)
    )
    co.y -= craniofacial_deform["philtrum_groove_y_m"]*g2(co.x,co.z,0.0,mouth_z+.014,.0055,.010)
    co.y += craniofacial_deform["philtrum_ridge_y_m"]*(
        g2(co.x,co.z,.006,mouth_z+.014,.004,.010)+
        g2(co.x,co.z,-.006,mouth_z+.014,.004,.010)
    )
    co.y -= craniofacial_deform["alar_groove_y_m"]*(
        g2(co.x,co.z,.013,nose_tip_z-.004,.007,.010)+
        g2(co.x,co.z,-.013,nose_tip_z-.004,.007,.010)
    )
    co.y -= craniofacial_deform["labiomental_groove_y_m"]*g2(co.x,co.z,0.0,mouth_z-.018,.026,.008)
    co.y -= craniofacial_deform["lip_corner_y_m"]*(
        g2(co.x,co.z,.023,mouth_z,.007,.008)+
        g2(co.x,co.z,-.023,mouth_z,.007,.008)
    )
    co.y += craniofacial_deform["lower_lid_roll_y_m"]*(
        g2(co.x,co.z,.032,eye_mid_z-.006,.022,.008)+
        g2(co.x,co.z,-.032,eye_mid_z-.006,.022,.008)
    )

    # Chin projection.
    co.y += craniofacial_deform["chin_y_m"]*g2(co.x,co.z,0.0,chin_z,.035,.022)

    # Mild lower-face taper from the existing canonical topology.
    jaw_w=max(0.0,1.0-abs(co.z-jaw_z)/.052)
    if jaw_w>0 and abs(co.x)>.030:
        s=1.0-(1.0-craniofacial_deform["jaw_x_scale"])*jaw_w
        co.x *= s

sub=body.modifiers.new("DIGE_V8_SUBDIV","SUBSURF"); sub.levels=2 if C25_MATURE_STACK else 1; sub.render_levels=3 if C25_MATURE_STACK else 2
# Preserve topology metrics before subdivision
bm=bmesh.new(); bm.from_mesh(body.data)
nonmanifold=sum(1 for e in bm.edges if not e.is_manifold)
boundary=sum(1 for e in bm.edges if e.is_boundary)
bm.free()
topology={
    "vertices":len(body.data.vertices),
    "polygons":len(body.data.polygons),
    "nonmanifold_edges":nonmanifold,
    "boundary_edges":boundary,
    "bbox_min":bbox_min,
    "bbox_max":bbox_max,
    "bbox_extent":bbox_extent,
    "orientation_gate":"PASS",
}

geom=json.loads((RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json").read_text())
if geom.get("canon_execution_manifest_sha256") != CANON_SHA256:
    raise RuntimeError("geometry/canon manifest causal binding mismatch")
landmarks=geom["landmarks"]

# C12 full normalized hm08 fit reference emitted by the builder.
fit_ref_meta=geom["fit_reference"]
fit_ref_path=RUNTIME/fit_ref_meta["output"]
if not fit_ref_path.exists() or sha(fit_ref_path)!=fit_ref_meta["sha256"]:
    raise RuntimeError("C12 fit-reference missing/hash mismatch")
fit_payload=json.loads(fit_ref_path.read_text(encoding="utf-8"))
fit_vertices=[Vector(v) for v in fit_payload["vertices"]]
if len(fit_vertices)!=fit_ref_meta["vertices"]:
    raise RuntimeError(f"C12 fit-reference vertex-count drift: expected={fit_ref_meta['vertices']} got={len(fit_vertices)}")
if len(fit_vertices) < len(body.data.vertices):
    raise RuntimeError("C12 fit-reference shorter than compact body")
# Preserve runtime craniofacial meso deformation on the body prefix while retaining normalized helper vertices.
for i,v in enumerate(body.data.vertices):
    fit_vertices[i]=v.co.copy()

# C12: replace proxy helper eyes + flat iris discs with the official high-poly hm08 eye asset.
system_contract=CANON["assets"]["system_assets_c12"]
system_dir=RUNTIME/"system_assets"
system_asset_fits={}
eye_asset=system_contract["high_poly_eyes"]
eye_mat=eye_texture_material(
    "DIGE_C12_HIGH_POLY_EYE",
    system_dir/eye_asset["diffuse"]["runtime_name"],
    eye_asset["diffuse"]["sha256"],
)
eye_obj,eye_fit=fit_mhclo_asset(
    "DIGE_C12_HIGH_POLY_EYES",
    system_dir/eye_asset["obj"]["runtime_name"],
    system_dir/eye_asset["mhclo"]["runtime_name"],
    fit_vertices,eye_mat,eye_asset,
)
system_asset_fits["high_poly_eyes"]=eye_fit
c25_mpfb_eyes={"enabled":False}
if C25_MATURE_STACK:
    c25_mpfb_eyes=c25_apply_mpfb_procedural_eyes(eye_mat)

# C23 root-cause replacement for the eye interface. C22 human audit showed that
# the fitted high-poly eye asset remained visibly asymmetric/occluded. Keep it
# for provenance, but hide it and build calibrated neutral eyes from live eye
# landmarks so both globes/irises share one deterministic geometric contract.
c23_eye_count=0
c23_eye_contract=[]
if C23_CALIBRATED_EYES and not C24_SURFACE_EYES and not C25_MATURE_STACK:
    eye_obj.hide_render=True
    try:
        eye_obj.hide_set(True)
    except Exception:
        pass
    for eye_key in ("left_eye","right_eye"):
        ec=landmarks[eye_key]["center"]
        ex,ey,ez=(float(ec[0]),float(ec[1]),float(ec[2]))
        center=(ex,ey-.0046,ez)
        scl=uv(f"DIGE_C23_{eye_key.upper()}_SCLERA",center,(.0114,.0104,.0107),sclera,seg=64,rings=32)
        # Front-facing iris stack. Face-forward is +Y in this pipeline.
        side=1.0 if ex>=0 else -1.0
        iris_y=center[1]+.01025
        ring=cylinder(f"DIGE_C23_{eye_key.upper()}_IRIS_RING",(ex,iris_y,ez),.00555,.00024,iris_ring)
        iri=cylinder(f"DIGE_C23_{eye_key.upper()}_IRIS",(ex,iris_y+.00018,ez),.00495,.00020,iris)
        pup=cylinder(f"DIGE_C23_{eye_key.upper()}_PUPIL",(ex,iris_y+.00034,ez),.00210,.00018,black)
        cor=cylinder(f"DIGE_C23_{eye_key.upper()}_CORNEA",(ex,iris_y+.00048,ez),.00585,.00020,cornea)
        c23_eye_count+=1
        c23_eye_contract.append({"eye":eye_key,"center":[ex,ey,ez],"sclera_center":list(center),"iris_y":iris_y})

# C24 surface-calibrated eyes. C23 proved that landmark centers alone were
# insufficient because one globe remained behind the eyelid/face surface. C24
# measures the actual local forward face surface and places a shallow eye
# aperture directly at that surface, keeping both sides symmetric by contract.
c24_eye_count=0
c24_eye_contract=[]
c24_lid_curve_count=0
if C24_SURFACE_EYES and not C25_MATURE_STACK:
    eye_obj.hide_render=True
    try:
        eye_obj.hide_set(True)
    except Exception:
        pass
    lid_curves=[]
    for eye_key in ("left_eye","right_eye"):
        ec=landmarks[eye_key]["center"]
        ex,ey,ez=(float(ec[0]),float(ec[1]),float(ec[2]))
        local_front=[
            float(v.co.y) for v in body.data.vertices
            if abs(float(v.co.x)-ex) <= .0165 and abs(float(v.co.z)-ez) <= .0105 and float(v.co.y) > 0
        ]
        if len(local_front) < 8:
            raise RuntimeError(f"C24 eye surface probe too sparse for {eye_key}: {len(local_front)}")
        surface_y=max(local_front)
        scl_center=(ex,surface_y+.00075,ez)
        uv(f"DIGE_C24_{eye_key.upper()}_SCLERA",scl_center,(.0118,.00105,.00545),sclera,seg=64,rings=32)
        iris_y=surface_y+.00195
        cylinder(f"DIGE_C24_{eye_key.upper()}_IRIS_RING",(ex,iris_y,ez),.00515,.00020,iris_ring)
        cylinder(f"DIGE_C24_{eye_key.upper()}_IRIS",(ex,iris_y+.00018,ez),.00455,.00016,iris)
        cylinder(f"DIGE_C24_{eye_key.upper()}_PUPIL",(ex,iris_y+.00034,ez),.00195,.00014,black)
        cylinder(f"DIGE_C24_{eye_key.upper()}_CORNEA",(ex,iris_y+.00048,ez),.00535,.00014,cornea)
        half_w=.0118
        upper=[]; lower=[]
        for i in range(19):
            t=i/18.0
            x=(ex-half_w)+2*half_w*t
            a=math.sin(math.pi*t)
            upper.append((x,surface_y+.00212,ez+.00525*a))
            lower.append((x,surface_y+.00210,ez-.00435*a))
        lid_curves.extend([upper,lower])
        c24_eye_count+=1
        c24_eye_contract.append({"eye":eye_key,"landmark_center":[ex,ey,ez],"surface_y":surface_y,"iris_y":iris_y})
    curve_object("DIGE_C24_SURFACE_LID_MARGINS",lid_curves,.000050,mouth_dark)
    c24_lid_curve_count=len(lid_curves)

# Mouth: preserve native face topology; add only a thin, source-anchored mouth gap.
mouth_center=landmarks["mouth_front"]["center"]
my=mouth_center[1]+.0010
mz=mouth_center[2]-.0012
mouth_line=[
    (-.020,my,mz),
    (-.010,my+.0005,mz-.0004),
    (0.0,my+.0007,mz-.0006),
    (.010,my+.0005,mz-.0004),
    (.020,my,mz)
]
curve_object("DIGE_V8_MOUTH_GAP",[mouth_line],.000045 if C27_NATIVE_INTERFACES else (.00013 if C20_VISUAL_REPAIR else .00010),mouth_dark)

# Thin vermilion tint uses tiny curves; native lip volume remains the geometry source.
upper_lip=[
    (-.018,my+.0002,mz+.0015),
    (-.009,my+.0006,mz+.0031),
    (0.0,my+.0008,mz+.0020),
    (.009,my+.0006,mz+.0031),
    (.018,my+.0002,mz+.0015),
]
lower_lip=[
    (-.018,my+.0002,mz-.0012),
    (-.009,my+.0005,mz-.0025),
    (0.0,my+.0007,mz-.0030),
    (.009,my+.0005,mz-.0025),
    (.018,my+.0002,mz-.0012),
]
curve_object("DIGE_V8_UPPER_LIP_TINT",[upper_lip],.000070 if C27_NATIVE_INTERFACES else (.00018 if C20_VISUAL_REPAIR else .00010),lip)
curve_object("DIGE_V8_LOWER_LIP_TINT",[lower_lip],.000075 if C27_NATIVE_INTERFACES else (.00020 if C20_VISUAL_REPAIR else .00013),lip)

# Small recessed nostril discs add depth without altering topology.
nose_z=mouth_center[2]+.0275
nose_y=mouth_center[1]+.0030
for sx in (-1,1):
    cylinder(f"NOSTRIL_{sx}",(sx*.0065,nose_y,nose_z),.00145,.00022,mouth_dark)

# C12: official system eyebrow/eyelash cards fitted through their hm08 MHCLO mappings.
brow_asset=system_contract["eyebrow001"]
brow_mat=alpha_card_material(
    "DIGE_C12_EYEBROW001",
    system_dir/brow_asset["diffuse"]["runtime_name"],
    brow_asset["diffuse"]["sha256"],
    rough=.58 if C19_HUMANIZATION else .52,
    ior=1.46,
    anisotropy=.10 if C19_HUMANIZATION else .15,
    sat=.72 if C19_HUMANIZATION else 1.0,
    value=.42 if C19_HUMANIZATION else 1.0,
    spec=.10 if C19_HUMANIZATION else .28,
    coat=.0 if C19_HUMANIZATION else .025,
)
brow_obj,brow_fit=fit_mhclo_asset(
    "DIGE_C12_EYEBROW001",
    system_dir/brow_asset["obj"]["runtime_name"],
    system_dir/brow_asset["mhclo"]["runtime_name"],
    fit_vertices,brow_mat,brow_asset,
)
system_asset_fits["eyebrow001"]=brow_fit

lash_asset=system_contract["eyelashes01"]
lash_mat=alpha_card_material(
    "DIGE_C12_EYELASHES01",
    system_dir/lash_asset["diffuse"]["runtime_name"],
    lash_asset["diffuse"]["sha256"],
    rough=.54 if C19_HUMANIZATION else .48,
    ior=1.46,
    anisotropy=.16 if C19_HUMANIZATION else .25,
    sat=.60 if C19_HUMANIZATION else 1.0,
    value=.30 if C19_HUMANIZATION else 1.0,
    spec=.08 if C19_HUMANIZATION else .28,
    coat=.0 if C19_HUMANIZATION else .025,
)
lash_obj,lash_fit=fit_mhclo_asset(
    "DIGE_C12_EYELASHES01",
    system_dir/lash_asset["obj"]["runtime_name"],
    system_dir/lash_asset["mhclo"]["runtime_name"],
    fit_vertices,lash_mat,lash_asset,
)
system_asset_fits["eyelashes01"]=lash_fit

# C26 dedicated fiber groom. Preserve the mature MPFB2 eye geometry/material,
# hide only the weak alpha-card brow/lash assets, and create landmark-bound
# individual fibers. No artificial lid-margin curves are introduced.
c26_brow_fiber_count=0
c26_lash_fiber_count=0
if C26_FIBER_GROOM:
    brow_obj.hide_render=True
    lash_obj.hide_render=True
    try:
        brow_obj.hide_set(True); lash_obj.hide_set(True)
    except Exception:
        pass
    grng=random.Random(20262626)
    brow_fibers=[]
    lash_fibers=[]
    for eye_key in ("left_eye","right_eye"):
        ec=landmarks[eye_key]["center"]
        ex,ey,ez=(float(ec[0]),float(ec[1]),float(ec[2]))
        side=1.0 if ex>=0 else -1.0
        half_w=.0210
        for i in range(76):
            t=(i+grng.uniform(-.30,.30))/75.0
            t=max(0.0,min(1.0,t))
            x=(ex-half_w)+2*half_w*t
            arch=math.sin(math.pi*t)
            root_z=ez+.0190+.0058*arch+grng.uniform(-.00055,.00055)
            if C27_SURFACE_FIBERS:
                local=[float(v.co.y) for v in body.data.vertices if abs(float(v.co.x)-x)<=.0035 and abs(float(v.co.z)-root_z)<=.0045 and float(v.co.y)>0]
                root_y=(max(local)+.00065) if local else (ey+.0060)
            else:
                root_y=ey+.0060+grng.uniform(-.00030,.00030)
            root=(x,root_y,root_z)
            length=grng.uniform(.0028,.0050)
            dx=side*length*(.32+.48*t)
            dz=length*(.78-.42*t)
            brow_fibers.append([
                root,
                (root[0]+dx*.48,root[1]+.00040,root[2]+dz*.48),
                (root[0]+dx,root[1]+.00070,root[2]+dz),
            ])
        for i in range(28):
            t=(i+.5)/28.0
            x=(ex-half_w*.86)+2*half_w*.86*t
            arch=math.sin(math.pi*t)
            root_z=ez+.0024*arch+.0008
            if C27_SURFACE_FIBERS:
                local=[float(v.co.y) for v in body.data.vertices if abs(float(v.co.x)-x)<=.0030 and abs(float(v.co.z)-root_z)<=.0035 and float(v.co.y)>0]
                root_y=(max(local)+.00070) if local else (ey+.0054)
            else:
                root_y=ey+.0054
            root=(x,root_y,root_z)
            length=(.0016+.0022*arch)*grng.uniform(.90,1.10)
            lash_fibers.append([
                root,
                (x+side*.00018,root[1]+length*.58,root[2]+length*.16),
                (x+side*.00038,root[1]+length,root[2]+length*.28),
            ])
    curve_object("DIGE_C26_LANDMARK_BROW_FIBERS",brow_fibers,.000070,hair)
    curve_object("DIGE_C26_LANDMARK_LASH_FIBERS",lash_fibers,.000042,hair)
    c26_brow_fiber_count=len(brow_fibers)
    c26_lash_fiber_count=len(lash_fibers)

# C22 replaces the fitted alpha-card brows/lashes with landmark-anchored
# individual fibers. The source assets remain in provenance/readback but are not
# rendered because C21 audit showed card misfit/weak read around the eye interface.
c22_brow_fiber_count=0
c22_lash_fiber_count=0
c22_lid_margin_curve_count=0
c23_brow_fiber_count=0
c23_lash_fiber_count=0
c23_hairline_fiber_count=0
if C22_LANDMARK_GROOM and not C23_CALIBRATED_EYES:
    brow_obj.hide_render=True
    lash_obj.hide_render=True
    try:
        brow_obj.hide_set(True); lash_obj.hide_set(True)
    except Exception:
        pass

    lrng=random.Random(20262222)
    brow_fibers=[]
    lash_fibers=[]
    lid_margins=[]
    for eye_key,lid_key in (("left_eye","left_lowerlid"),("right_eye","right_lowerlid")):
        ec=landmarks[eye_key]["center"]
        lid=landmarks[lid_key]
        lmin=lid["bbox_min"]; lmax=lid["bbox_max"]
        half_w=max(.015,(lmax[0]-lmin[0])*.62)
        # Brow arch: root positions are derived from the live eye center/eyelid span.
        for i in range(54):
            t=(i+lrng.uniform(-.35,.35))/53.0
            t=max(0.0,min(1.0,t))
            x=(ec[0]-half_w*.95)+2*half_w*.95*t
            arch=math.sin(math.pi*t)
            root=(x,ec[1]+.0045+lrng.uniform(-.00035,.00035),ec[2]+.020+.0065*arch+lrng.uniform(-.00055,.00055))
            direction=1.0 if t<.58 else .35
            dx=(.0018+.0022*t)*(1.0 if ec[0] >= 0 else -1.0)*direction
            dz=.0038-.0018*t+lrng.uniform(-.0004,.0004)
            brow_fibers.append([root,(root[0]+dx*.5,root[1]+.0004,root[2]+dz*.5),(root[0]+dx,root[1]+.0007,root[2]+dz)])
        # Upper lashes: short fibers follow the upper half of the eye ellipse.
        for i in range(24):
            t=(i+.5)/24.0
            x=(ec[0]-half_w*.88)+2*half_w*.88*t
            arch=math.sin(math.pi*t)
            root=(x,ec[1]+.0035,ec[2]+.0032*arch+.0011)
            sgn=1.0 if ec[0]>=0 else -1.0
            length=(.0016+.0022*arch)*lrng.uniform(.88,1.12)
            lash_fibers.append([root,(x+sgn*.00018,root[1]+length*.55,root[2]+length*.16),(x+sgn*.00034,root[1]+length,root[2]+length*.28)])
        # Upper/lower lid margin definition, kept very thin to read contact rather than makeup.
        upper=[]; lower=[]
        for i in range(17):
            t=i/16.0
            x=(ec[0]-half_w)+2*half_w*t
            a=math.sin(math.pi*t)
            upper.append((x,ec[1]+.0029,ec[2]+.0036*a))
            lower.append((x,ec[1]+.0028,ec[2]-.0029*a))
        lid_margins.extend([upper,lower])
    curve_object("DIGE_C22_LANDMARK_BROW_FIBERS",brow_fibers,.000060,hair)
    curve_object("DIGE_C22_LANDMARK_LASH_FIBERS",lash_fibers,.000038,hair)
    curve_object("DIGE_C22_LID_MARGINS",lid_margins,.000045,mouth_dark)
    c22_brow_fiber_count=len(brow_fibers)
    c22_lash_fiber_count=len(lash_fibers)
    c22_lid_margin_curve_count=len(lid_margins)

# C23 landmark fibers are rebuilt after replacing the eye globes so their placement
# follows the live eye centers instead of C21/C22 hard-coded positions.
if C23_CALIBRATED_EYES and not C25_MATURE_STACK:
    frng=random.Random(20262323)
    brow_fibers=[]
    lash_fibers=[]
    for eye_key in ("left_eye","right_eye"):
        ec=landmarks[eye_key]["center"]
        ex,ey,ez=(float(ec[0]),float(ec[1]),float(ec[2]))
        half_w=.0205
        for i in range(74):
            t=(i+frng.uniform(-.38,.38))/73.0
            t=max(0.0,min(1.0,t))
            x=(ex-half_w)+2*half_w*t
            arch=math.sin(math.pi*t)
            root=(x,ey+.0062+frng.uniform(-.00035,.00035),ez+.0195+.0054*arch+frng.uniform(-.00065,.00065))
            outward=(1.0 if ex>=0 else -1.0)*(.0015+.0026*t)
            dz=.0033-.0016*t+frng.uniform(-.00045,.00045)
            brow_fibers.append([root,(root[0]+outward*.48,root[1]+.00045,root[2]+dz*.48),(root[0]+outward,root[1]+.00075,root[2]+dz)])
        for i in range(26):
            t=(i+.5)/26.0
            x=(ex-half_w*.90)+2*half_w*.90*t
            arch=math.sin(math.pi*t)
            root=(x,ey+.0062,ez+.0025*arch+.0009)
            sgn=1.0 if ex>=0 else -1.0
            length=(.0015+.0023*arch)*frng.uniform(.86,1.14)
            lash_fibers.append([root,(x+sgn*.00018,root[1]+length*.55,root[2]+length*.16),(x+sgn*.00036,root[1]+length,root[2]+length*.30)])
    curve_object("DIGE_C23_LANDMARK_BROW_FIBERS",brow_fibers,.000082,hair)
    curve_object("DIGE_C23_LANDMARK_LASH_FIBERS",lash_fibers,.000046,hair)
    c23_brow_fiber_count=len(brow_fibers)
    c23_lash_fiber_count=len(lash_fibers)

    # Sparse natural hairline fibers bridge the lowered bulk mass into forehead skin.
    hairline_fibers=[]
    for i in range(108):
        if frng.random() < .26:
            continue
        u=(i+frng.uniform(-.45,.45))/107.0
        x=-.082+.164*u
        temple=min(1.0,abs(x)/.082)
        root_z=1.607+.015*(temple**1.45)+frng.uniform(-.0017,.0017)
        root_y=.044+frng.uniform(-.0011,.0011)
        length=frng.uniform(.007,.016)
        side=1.0 if x>=0 else -1.0
        dx=side*frng.uniform(-.0014,.0024)
        hairline_fibers.append([(x,root_y,root_z),(x+dx*.35,root_y-.0035,root_z+length*.35),(x+dx*.70,root_y-.0075,root_z+length*.72),(x+dx,root_y-.0120,root_z+length)])
    curve_object("DIGE_C23_HAIRLINE_FIBERS",hairline_fibers,.000052,hair)
    c23_hairline_fiber_count=len(hairline_fibers)

# C20 visual repair: the fitted alpha cards are still retained for provenance,
# but explicit micro-curve brows/upper lashes provide geometric silhouette/read
# under hero lighting. This is bounded cosmetic geometry, not anatomy authority.
c20_brow_curve_count=0
c20_lash_curve_count=0
if C20_VISUAL_REPAIR and not C21_NATURAL_DETAIL:
    brow_splines=[]
    for side in (-1,1):
        xs=[.014,.023,.033,.043,.052]
        base=[1.6080,1.6120,1.6140,1.6110,1.6055]
        for lane in range(7):
            dz=(lane-3)*.00042
            dy=((lane%3)-1)*.00028
            pts=[]
            for x,z in zip(xs,base):
                xx=side*x
                pts.append((xx,.0475+dy,z+dz))
            if side<0:
                pts=list(reversed(pts))
            brow_splines.append(pts)
    curve_object("DIGE_C20_BROW_CURVES",brow_splines,.00018,hair)
    c20_brow_curve_count=len(brow_splines)

    lash_splines=[]
    for side in (-1,1):
        for i in range(11):
            t=i/10.0
            x=side*(.010+.039*t)
            z=1.5898 + .0040*math.sin(math.pi*t)
            y=.0435
            # short outward/upward upper-lash strand
            lash_splines.append([
                (x,y,z),
                (x+side*.00035,y+.0012,z+.0006),
                (x+side*.00065,y+.0022,z+.0010),
            ])
    curve_object("DIGE_C20_UPPER_LASH_CURVES",lash_splines,.000075,hair)
    c20_lash_curve_count=len(lash_splines)

# Preserve C5 tear meniscus: it is landmark-bound and complements the high-poly eye asset.
wetlines=[]
for eye_key,lid_key in (("left_eye","left_lowerlid"),("right_eye","right_lowerlid")):
    ec=landmarks[eye_key]["center"]
    lid=landmarks[lid_key]
    mi=lid["bbox_min"]; ma=lid["bbox_max"]
    pts=[]
    for i in range(9):
        t=i/8
        x=mi[0]+(ma[0]-mi[0])*t
        arch=math.sin(t*math.pi)
        y=max(ma[1]+.00045,ec[1]+.0070)
        z=ma[2]-.0008+.0012*arch
        pts.append((x,y,z))
    wetlines.append(pts)
curve_object("DIGE_V8_EYE_WETLINES",wetlines,.00016,wetline)

# C17: keep the exact fitted short03 asset only as a non-rendered groom guide, then
# materialize real Blender Hair Curves. This moves the realism bottleneck from alpha-card
# silhouette swaps to strand geometry + Principled Hair BSDF + Cycles 3D curves.
if HAIR_ASSET_KEY not in system_contract or not HAIR_ASSET_KEY.startswith("hair_short"):
    raise RuntimeError(f"Unsupported DIGE_HAIR_ASSET_KEY={HAIR_ASSET_KEY}")
hair_asset=system_contract[HAIR_ASSET_KEY]
hair_label=HAIR_ASSET_KEY.replace("hair_","").upper()
hair_guide_mat=alpha_card_material(
    f"DIGE_C18_BULK_{hair_label}" if C18_HYBRID_BULK else f"DIGE_C17_GUIDE_{hair_label}",
    system_dir/hair_asset["diffuse"]["runtime_name"],
    hair_asset["diffuse"]["sha256"],
    rough=.64 if C18_HYBRID_BULK else .54,
    ior=1.55,
    anisotropy=.24 if C18_HYBRID_BULK else .34,
    sat=HAIR_TEX_SAT,
    value=HAIR_TEX_VALUE,
    spec=.07 if C18_HYBRID_BULK else .16,
    coat=.0 if C18_HYBRID_BULK else .004,
)
hair_obj,hair_fit=fit_mhclo_asset(
    f"DIGE_C17_GUIDE_{hair_label}",
    system_dir/hair_asset["obj"]["runtime_name"],
    system_dir/hair_asset["mhclo"]["runtime_name"],
    fit_vertices,hair_guide_mat,hair_asset,
)
system_asset_fits[HAIR_ASSET_KEY]=hair_fit

# C28: replace the diminishing-return MakeHuman head prior with Google GNM Head.
# Body/camera/lighting remain fixed so this is a causal geometry-prior ablation.
c28_gnm={"enabled":False}
c28_gnm_objects={}
c28_brow_fiber_count=0
c28_lash_fiber_count=0
c28_hairline_fiber_count=0
c28_body_cut_z=None
c28_hairline_delta=0.0
c28_hairline_warp_vertices=0
c29_iris_count=0
c31_mask_vertex_count=0
c31_wetline_count=0
c31_mouth_gap_count=0
if C28_GNM_HEAD:
    gnm_dir=Path(C28_GNM_DIR)
    if not gnm_dir.is_absolute():
        gnm_dir=ROOT/gnm_dir
    manifest_path=gnm_dir/"DIGE_C28_GNM_HEAD_MANIFEST.json"
    if not manifest_path.exists():
        raise RuntimeError(f"C28 GNM manifest missing: {manifest_path}")
    gm=json.loads(manifest_path.read_text(encoding="utf-8"))
    if C28_GNM_COMMIT and gm.get("source_commit")!=C28_GNM_COMMIT:
        raise RuntimeError(f"C28 GNM commit drift: expected={C28_GNM_COMMIT} got={gm.get('source_commit')}")
    src_left=Vector(gm["anchors"]["left_eye_center"])
    src_right=Vector(gm["anchors"]["right_eye_center"])
    src_eye_mid=(src_left+src_right)*.5
    src_dist=(src_left-src_right).length
    tgt_left=Vector(landmarks["left_eye"]["center"])
    tgt_right=Vector(landmarks["right_eye"]["center"])
    tgt_eye_mid=(tgt_left+tgt_right)*.5
    tgt_dist=(tgt_left-tgt_right).length
    if src_dist<=1e-6 or tgt_dist<=1e-6:
        raise RuntimeError(f"C28 invalid interocular distances src={src_dist} target={tgt_dist}")
    head_scale=(tgt_dist/src_dist)*C28_HEAD_SCALE_BIAS
    head_translation=tgt_eye_mid-src_eye_mid*head_scale+Vector((0,0,C28_HEAD_Z_OFFSET))

    raw_lm=json.loads((gnm_dir/gm["landmarks68_file"]).read_text(encoding="utf-8"))
    transformed_landmarks=[Vector(p)*head_scale+head_translation for p in raw_lm]
    gnm_eye_mid=(sum(transformed_landmarks[36:42],Vector())/6 + sum(transformed_landmarks[42:48],Vector())/6)*.5
    gnm_brow_left=transformed_landmarks[17:22]
    gnm_brow_right=transformed_landmarks[22:27]

    gnm_skin_mat,c28_skin_contract=c28_gnm_skin_material()
    if C29_GNM_PRESENTATION:
        gnm_eye_mat=sclera
        c28_eye_contract={
            "enabled":True,
            "material_model":"C29_GNM_SCLERA_PLUS_CALIBRATED_IRIS_STACK",
            "integration":"GNM_EYEBALL_MESH_PLUS_GEOMETRIC_IRIS_CORNEA",
        }
    else:
        gnm_eye_mat=bpy.data.materials.new("DIGE_C28_GNM_PROCEDURAL_EYE")
        gnm_eye_mat.use_nodes=True
        c28_eye_contract=c25_apply_mpfb_procedural_eyes(gnm_eye_mat) if C25_MATURE_STACK else {"enabled":False}
        if not C25_MATURE_STACK:
            gnm_eye_mat=eye_mat
    teeth_mat=principled("DIGE_C28_TEETH",(0.72,0.63,0.54),rough=.34,ior=1.52,subsurface=.018)
    tongue_mat=principled("DIGE_C28_TONGUE",(0.30,0.055,0.050),rough=.48,ior=1.40,subsurface=.05)
    component_material={
        "skin":gnm_skin_mat,
        "left_eye":gnm_eye_mat,
        "right_eye":gnm_eye_mat,
        "eye_interiors":gnm_eye_mat,
        "eye_exteriors":cornea,
        "upper_teeth_and_gums":teeth_mat,
        "lower_teeth_and_gums":teeth_mat,
        "tongue":tongue_mat,
    }
    for comp,rec in gm["files"].items():
        p=gnm_dir/rec["file"]
        if not p.exists() or sha(p)!=rec["sha256"]:
            raise RuntimeError(f"C28 GNM component missing/hash drift: {comp}")
        obj=c28_import_component(
            p,
            f"DIGE_C28_GNM_{comp.upper()}",
            component_material.get(comp,gnm_skin_mat),
            head_scale,
            head_translation,
        )
        c28_gnm_objects[comp]=obj

    if C31_GNM_FACE_APPEARANCE:
        skin_obj=c28_gnm_objects.get("skin")
        if skin_obj is None:
            raise RuntimeError("C31 missing GNM skin component")
        attr=skin_obj.data.color_attributes.get("C31_FaceMask")
        if attr is None:
            attr=skin_obj.data.color_attributes.new(name="C31_FaceMask",type='FLOAT_COLOR',domain='POINT')
        mouth_center=sum(transformed_landmarks[48:60],Vector())/12
        mouth_left=transformed_landmarks[48]; mouth_right=transformed_landmarks[54]
        mouth_half=max(.018,abs(mouth_left.x-mouth_right.x)*.55)
        eye_l=sum(transformed_landmarks[36:42],Vector())/6
        eye_r=sum(transformed_landmarks[42:48],Vector())/6
        nose_tip=transformed_landmarks[30]
        cheek_z=(mouth_center.z+((eye_l.z+eye_r.z)*.5))*.5
        cheek_dx=max(.030,abs(eye_l.x-eye_r.x)*.74)
        forehead_z=((eye_l.z+eye_r.z)*.5)+.055
        def gmask(x,z,cx,cz,sx,sz):
            return math.exp(-0.5*(((x-cx)/sx)**2+((z-cz)/sz)**2))
        for v in skin_obj.data.vertices:
            p=v.co
            lip=min(1.0,1.18*gmask(p.x,p.z,mouth_center.x,mouth_center.z,mouth_half,.0105))
            cheek=0.42*(
                gmask(p.x,p.z,mouth_center.x+cheek_dx,cheek_z,.030,.032)+
                gmask(p.x,p.z,mouth_center.x-cheek_dx,cheek_z,.030,.032)
            )
            nose=0.32*gmask(p.x,p.z,nose_tip.x,nose_tip.z,.019,.030)
            eyelid=0.20*(
                gmask(p.x,p.z,eye_l.x,eye_l.z,.025,.015)+
                gmask(p.x,p.z,eye_r.x,eye_r.z,.025,.015)
            )
            blush=min(.46,cheek+nose+eyelid)
            tzone=min(1.0,
                .82*gmask(p.x,p.z,nose_tip.x,nose_tip.z,.018,.050)+
                .48*gmask(p.x,p.z,0.0,forehead_z,.042,.050)
            )
            attr.data[v.index].color=(lip,blush,tzone,1.0)
            c31_mask_vertex_count+=1

    if C29_GNM_PRESENTATION:
        for comp,pts in (("left_eye",transformed_landmarks[36:42]),("right_eye",transformed_landmarks[42:48])):
            eye_mesh=c28_gnm_objects.get(comp)
            if eye_mesh is None:
                raise RuntimeError(f"C29 missing GNM eye component: {comp}")
            ec=sum(pts,Vector())/len(pts)
            front_y=max(float(v.co.y) for v in eye_mesh.data.vertices)
            iy=front_y+.00020
            cylinder(f"DIGE_C29_{comp.upper()}_IRIS_RING",(ec.x,iy,ec.z),.00505,.00016,iris_ring)
            cylinder(f"DIGE_C29_{comp.upper()}_IRIS",(ec.x,iy+.00013,ec.z),.00445,.00014,iris)
            cylinder(f"DIGE_C29_{comp.upper()}_PUPIL",(ec.x,iy+.00026,ec.z),.00185,.00012,black)
            cylinder(f"DIGE_C29_{comp.upper()}_CORNEA",(ec.x,iy+.00039,ec.z),.00530,.00012,cornea)
            c29_iris_count+=1

    gnm_bbox_min=Vector(gm["bbox_min"])*head_scale+head_translation
    gnm_bbox_max=Vector(gm["bbox_max"])*head_scale+head_translation
    c28_body_cut_z=float(gnm_bbox_min.z+.018)
    bm=bmesh.new(); bm.from_mesh(body.data)
    kill=[v for v in bm.verts if v.co.z>c28_body_cut_z]
    if len(kill)<100:
        raise RuntimeError(f"C28 body-head cut selected too few vertices: {len(kill)} cut_z={c28_body_cut_z}")
    bmesh.ops.delete(bm,geom=kill,context='VERTS')
    bm.to_mesh(body.data); bm.free(); body.data.update()

    eye_obj.hide_render=True
    brow_obj.hide_render=True
    lash_obj.hide_render=True
    for ob in list(bpy.data.objects):
        if ob.name.startswith(("DIGE_V8_MOUTH_","DIGE_V8_UPPER_LIP_","DIGE_V8_LOWER_LIP_","NOSTRIL_","DIGE_V8_EYE_WETLINES","DIGE_C20_","DIGE_C21_","DIGE_C22_","DIGE_C23_","DIGE_C24_","DIGE_C26_")):
            ob.hide_render=True

    brow_top=max(p.z for p in gnm_brow_left+gnm_brow_right)
    target_hairline_z=brow_top+.043
    front=[]
    for v in hair_obj.data.vertices:
        wp=hair_obj.matrix_world@v.co
        if wp.y>gnm_eye_mid.y-.035 and abs(wp.x-gnm_eye_mid.x)<.105 and wp.z>brow_top:
            front.append(wp.z)
    if len(front)<20:
        raise RuntimeError(f"C28 insufficient frontal hair samples: {len(front)}")
    front.sort()
    current_hairline_z=front[max(0,int(len(front)*.06)-1)]
    c28_hairline_delta=max(-.050,min(.012,target_hairline_z-current_hairline_z))
    for v in hair_obj.data.vertices:
        wp=hair_obj.matrix_world@v.co
        if wp.y<=gnm_eye_mid.y-.050 or abs(wp.x-gnm_eye_mid.x)>.120 or wp.z<brow_top:
            continue
        central=max(0.0,1.0-abs(wp.x-gnm_eye_mid.x)/.120)
        front_w=max(0.0,min(1.0,(wp.y-(gnm_eye_mid.y-.050))/.105))
        upper_guard=max(0.0,min(1.0,(brow_top+.140-wp.z)/.140))
        w=(central**1.25)*(front_w**1.10)*upper_guard
        if w<=0: continue
        v.co.z+=c28_hairline_delta*w
        v.co.y-=.0025*max(0.0,-c28_hairline_delta/.050)*w
        c28_hairline_warp_vertices+=1
    hair_obj.data.update()

    grng=random.Random(20262828)
    brow_fibers=[]
    lash_fibers=[]
    for pts in (gnm_brow_left,gnm_brow_right):
        ordered=sorted(pts,key=lambda p:p.x)
        for i in range(72):
            u=(i+grng.uniform(-.30,.30))/71.0
            u=max(0.0,min(1.0,u))
            seg=min(len(ordered)-2,int(u*(len(ordered)-1)))
            lu=u*(len(ordered)-1)-seg
            root=ordered[seg].lerp(ordered[seg+1],lu)+Vector((0,.00115 if C31_GNM_FACE_APPEARANCE else .00065,grng.uniform(-.0004,.0004)))
            side=1.0 if root.x>=gnm_eye_mid.x else -1.0
            length=grng.uniform(.0026,.0048)
            brow_fibers.append([
                root,
                root+Vector((side*length*.25,.00035,length*.45)),
                root+Vector((side*length*.58,.00065,length*.82)),
            ])
    for eye_pts in (transformed_landmarks[36:42],transformed_landmarks[42:48]):
        ec=sum(eye_pts,Vector())/len(eye_pts)
        upper=sorted([p for p in eye_pts if p.z>=ec.z-.0005],key=lambda p:p.x)
        if len(upper)<2:
            upper=sorted(eye_pts,key=lambda p:p.x)
        for i in range(28):
            u=(i+.5)/28.0
            seg=min(len(upper)-2,int(u*(len(upper)-1)))
            lu=u*(len(upper)-1)-seg
            root=upper[seg].lerp(upper[seg+1],lu)+Vector((0,.00105 if C31_GNM_FACE_APPEARANCE else .00055,.00025))
            side=1.0 if root.x>=gnm_eye_mid.x else -1.0
            length=grng.uniform(.0016,.0034)
            lash_fibers.append([
                root,
                root+Vector((side*.00010,length*.52,length*.14)),
                root+Vector((side*.00022,length,length*.26)),
            ])
    facial_hair_mat=principled("DIGE_C31_FACIAL_HAIR",(0.010,0.004,0.002),rough=.40,ior=1.50) if C31_GNM_FACE_APPEARANCE else hair
    curve_object("DIGE_C28_GNM_BROW_FIBERS",brow_fibers,.000082 if C31_GNM_FACE_APPEARANCE else .000060,facial_hair_mat)
    curve_object("DIGE_C28_GNM_LASH_FIBERS",lash_fibers,.000048 if C31_GNM_FACE_APPEARANCE else .000036,facial_hair_mat)
    c28_brow_fiber_count=len(brow_fibers)
    c28_lash_fiber_count=len(lash_fibers)
    if C31_GNM_FACE_APPEARANCE:
        wet_splines=[]
        for eye_pts in (transformed_landmarks[36:42],transformed_landmarks[42:48]):
            ec=sum(eye_pts,Vector())/len(eye_pts)
            lower=sorted(eye_pts,key=lambda p:(p.z,p.x))[:4]
            lower=sorted(lower,key=lambda p:p.x)
            wet_splines.append([Vector((p.x,p.y+.00105,p.z-.00010)) for p in lower])
        curve_object("DIGE_C31_GNM_EYE_WETLINES",wet_splines,.000038,wetline)
        c31_wetline_count=len(wet_splines)
        mc=sum(transformed_landmarks[48:60],Vector())/12
        ml=transformed_landmarks[48]; mr=transformed_landmarks[54]
        mouth_line=[
            Vector((ml.x,mc.y+.00125,mc.z)),
            Vector(((ml.x+mc.x)*.5,mc.y+.00135,mc.z-.00015)),
            Vector((mc.x,mc.y+.00138,mc.z-.00022)),
            Vector(((mr.x+mc.x)*.5,mc.y+.00135,mc.z-.00015)),
            Vector((mr.x,mc.y+.00125,mc.z)),
        ]
        curve_object("DIGE_C31_GNM_MOUTH_GAP",[mouth_line],.000045,mouth_dark)
        c31_mouth_gap_count=1

    baby=[]
    for i in range(104):
        if grng.random()<.28: continue
        u=(i+grng.uniform(-.40,.40))/103.0
        x=gnm_eye_mid.x-.083+.166*u
        temple=min(1.0,abs(x-gnm_eye_mid.x)/.083)
        z=target_hairline_z+.012*(temple**1.45)+grng.uniform(-.0017,.0017)
        root=Vector((x,gnm_eye_mid.y+.030+grng.uniform(-.001,.001),z))
        length=grng.uniform(.007,.015)
        side=1.0 if x>=gnm_eye_mid.x else -1.0
        baby.append([
            root,
            root+Vector((side*grng.uniform(-.0004,.0010),-.0035,length*.32)),
            root+Vector((side*grng.uniform(-.0007,.0016),-.0080,length*.70)),
            root+Vector((side*grng.uniform(-.0010,.0022),-.0130,length)),
        ])
    curve_object("DIGE_C28_GNM_HAIRLINE_FIBERS",baby,.000045,hair)
    c28_hairline_fiber_count=len(baby)

    c28_gnm={
        "enabled":True,
        "source_repo":gm["source_repo"],
        "source_commit":gm["source_commit"],
        "license":gm["license"],
        "model":gm["model"],
        "manifest_sha256":sha(manifest_path),
        "identity_source":gm.get("identity_source"),
        "semantic_identity_enabled":gm.get("semantic_identity_enabled"),
        "semantic_gender":gm.get("semantic_gender"),
        "semantic_ethnicity":gm.get("semantic_ethnicity"),
        "head_scale":head_scale,
        "head_translation":list(head_translation),
        "body_cut_z":c28_body_cut_z,
        "aligned_bbox_min":list(gnm_bbox_min),
        "aligned_bbox_max":list(gnm_bbox_max),
        "target_interocular_distance":tgt_dist,
        "source_interocular_distance":src_dist,
        "hairline_target_z":target_hairline_z,
        "hairline_before_z":current_hairline_z,
        "hairline_delta":c28_hairline_delta,
        "hairline_warp_vertices":c28_hairline_warp_vertices,
        "brow_fibers":c28_brow_fiber_count,
        "lash_fibers":c28_lash_fiber_count,
        "hairline_fibers":c28_hairline_fiber_count,
        "skin_contract":c28_skin_contract,
        "eye_contract":c28_eye_contract,
        "c29_presentation":C29_GNM_PRESENTATION,
        "c29_calibrated_iris_count":c29_iris_count,
        "c31_face_appearance":C31_GNM_FACE_APPEARANCE,
        "c31_mask_vertex_count":c31_mask_vertex_count,
        "c31_wetline_count":c31_wetline_count,
        "c31_mouth_gap_count":c31_mouth_gap_count,
        "components":{k:len(v.data.vertices) for k,v in c28_gnm_objects.items()},
    }

# C26 non-destructive frontal groom repair. C25 proved that face deletion creates
# a black temple wedge, so C26 moves vertices only: low fringe moves back/up away
# from the eye interface while the upper frontal mass is lowered toward the brow.
c26_fringe_clear_vertices=0
c26_hairline_warp_vertices=0
if C26_SAFE_GROOM:
    for v in hair_obj.data.vertices:
        p=v.co
        wp=hair_obj.matrix_world @ p
        if wp.y > .010 and wp.z < 1.615 and abs(wp.x) < .112:
            p.y -= .015
            p.z += .007
            c26_fringe_clear_vertices+=1
    hair_obj.data.update()
    for v in hair_obj.data.vertices:
        p=v.co
        wp=hair_obj.matrix_world @ p
        if wp.y <= -.030 or wp.z < 1.590 or wp.z > 1.690 or abs(wp.x) > .112:
            continue
        central=max(0.0,1.0-abs(wp.x)/.112)
        front=max(0.0,min(1.0,(wp.y+.030)/.085))
        upper_guard=max(0.0,min(1.0,(1.690-wp.z)/.100))
        w=(central**1.32)*(front**1.08)*upper_guard
        if w<=0.0:
            continue
        p.z -= .038*w
        p.y += .002*w
        c26_hairline_warp_vertices+=1
    hair_obj.data.update()
    pts=[hair_obj.matrix_world @ v.co for v in hair_obj.data.vertices]
    hair_fit["c26_fringe_clear_vertices"]=c26_fringe_clear_vertices
    hair_fit["c26_hairline_warp_vertices"]=c26_hairline_warp_vertices
    hair_fit["c26_postwarp_bbox_min"]=[min(p[i] for p in pts) for i in range(3)]
    hair_fit["c26_postwarp_bbox_max"]=[max(p[i] for p in pts) for i in range(3)]

# C25 mature groom cleanup: retain the official fitted short03 bulk and its authored
# UV flow, but remove only the low forward fringe polygons that C20-C24 proved
# occlude the eye/temple region. Then perform one bounded frontal placement pass.
c25_removed_fringe_faces=0
c25_hairline_warp_vertices=0
if C25_MATURE_STACK and C25_GROOM_CLIP and not C26_SAFE_GROOM:
    bm=bmesh.new(); bm.from_mesh(hair_obj.data)
    remove=[]
    for face in bm.faces:
        wc=hair_obj.matrix_world @ face.calc_center_median()
        if wc.y > .010 and wc.z < 1.615 and abs(wc.x) < .112:
            remove.append(face)
    c25_removed_fringe_faces=len(remove)
    if remove:
        bmesh.ops.delete(bm,geom=remove,context='FACES')
    bm.to_mesh(hair_obj.data); bm.free(); hair_obj.data.update()

    for v in hair_obj.data.vertices:
        p=v.co
        wp=hair_obj.matrix_world @ p
        if wp.y <= -.025 or wp.z < 1.590 or wp.z > 1.690 or abs(wp.x) > .112:
            continue
        central=max(0.0,1.0-abs(wp.x)/.112)
        front=max(0.0,min(1.0,(wp.y+.025)/.080))
        upper_guard=max(0.0,min(1.0,(1.690-wp.z)/.100))
        w=(central**1.35)*(front**1.10)*upper_guard
        if w<=0:
            continue
        p.z -= .030*w
        p.y += .003*w
        c25_hairline_warp_vertices+=1
    hair_obj.data.update()
    pts=[hair_obj.matrix_world @ v.co for v in hair_obj.data.vertices]
    hair_fit["c25_removed_fringe_faces"]=c25_removed_fringe_faces
    hair_fit["c25_hairline_warp_vertices"]=c25_hairline_warp_vertices
    hair_fit["c25_postwarp_bbox_min"]=[min(p[i] for p in pts) for i in range(3)]
    hair_fit["c25_postwarp_bbox_max"]=[max(p[i] for p in pts) for i in range(3)]

# C24 frontal mass placement. C23 still left a visibly oversized forehead.
# This pass is bounded to the forward short03 shell and lowers center more than temples.
c24_hairline_warp_vertices=0
if C24_HAIRLINE_REPAIR and not C25_MATURE_STACK:
    for v in hair_obj.data.vertices:
        p=v.co
        if p.y <= -.045 or p.z < 1.555 or p.z > 1.695 or abs(p.x) > .118:
            continue
        central=max(0.0,1.0-abs(p.x)/.118)
        front=max(0.0,min(1.0,(p.y+.045)/.110))
        upper_guard=max(0.0,min(1.0,(1.695-p.z)/.140))
        w=(central**1.18)*(front**1.05)*upper_guard
        if w<=0.0:
            continue
        p.z -= .0390*w
        p.y += .0060*w
        c24_hairline_warp_vertices+=1
    hair_obj.data.update()
    pts=[hair_obj.matrix_world @ v.co for v in hair_obj.data.vertices]
    hair_fit["c24_hairline_warp_vertices"]=c24_hairline_warp_vertices
    hair_fit["c24_postwarp_bbox_min"]=[min(p[i] for p in pts) for i in range(3)]
    hair_fit["c24_postwarp_bbox_max"]=[max(p[i] for p in pts) for i in range(3)]

# C23 stronger frontal hairline placement. C22 moved the shell but the hero audit
# still showed an oversized forehead. This second bounded pass only affects the
# frontal short03 mass and is intentionally stronger at the center than temples.
c23_hairline_warp_vertices=0
if C23_HAIRLINE_REPAIR and not C24_HAIRLINE_REPAIR:
    for v in hair_obj.data.vertices:
        p=v.co
        if p.y <= -.035 or p.z < 1.565 or p.z > 1.690 or abs(p.x) > .115:
            continue
        central=max(0.0,1.0-abs(p.x)/.115)
        front=max(0.0,min(1.0,(p.y+.035)/.095))
        crown_guard=max(0.0,min(1.0,(1.690-p.z)/.115))
        w=(central**1.30)*(front**1.10)*crown_guard
        if w<=0.0:
            continue
        p.z -= .0260*w
        p.y += .0050*w
        c23_hairline_warp_vertices+=1
    hair_obj.data.update()
    pts=[hair_obj.matrix_world @ v.co for v in hair_obj.data.vertices]
    hair_fit["c23_hairline_warp_vertices"]=c23_hairline_warp_vertices
    hair_fit["c23_postwarp_bbox_min"]=[min(p[i] for p in pts) for i in range(3)]
    hair_fit["c23_postwarp_bbox_max"]=[max(p[i] for p in pts) for i in range(3)]

# C22 frontal bulk-groom warp. C21 audit showed that the lawful short03 mass still
# left an oversized forehead. This bounded deformation only affects the frontal
# short03 shell and preserves the rest of the groom/topology.
c22_hair_mass_warp_vertices=0
if C22_HAIR_MASS_WARP and not C23_HAIRLINE_REPAIR:
    for v in hair_obj.data.vertices:
        p=v.co
        if p.y <= -0.010 or p.z < 1.585 or p.z > 1.685 or abs(p.x) > .112:
            continue
        central=max(0.0,1.0-abs(p.x)/.112)
        front=max(0.0,min(1.0,(p.y+.010)/.075))
        w=(central**1.55)*(front**1.25)
        if w <= 0.0:
            continue
        p.z -= .0185*w
        p.y += .0035*w
        c22_hair_mass_warp_vertices+=1
    hair_obj.data.update()
    # Keep provenance metrics but refresh the actual post-warp bbox for readback.
    pts=[hair_obj.matrix_world @ v.co for v in hair_obj.data.vertices]
    hair_fit["c22_mass_warp_vertices"]=c22_hair_mass_warp_vertices
    hair_fit["c22_postwarp_bbox_min"]=[min(p[i] for p in pts) for i in range(3)]
    hair_fit["c22_postwarp_bbox_max"]=[max(p[i] for p in pts) for i in range(3)]

# C21 natural-detail layer: sparse, irregular micro-hairs replace the C20
# continuous brow arches and comb-like hairline bridge. These are deterministic
# cosmetic strands bounded to the existing fitted anatomy/groom.
c21_brow_hair_count=0
c21_lash_hair_count=0
c21_hairline_baby_count=0
c21_temple_flyaway_count=0
if C21_NATURAL_DETAIL and not C22_LANDMARK_GROOM and not C23_HAIRLINE_REPAIR:
    nrng=random.Random(20262121)

    brow_hairs=[]
    for side in (-1,1):
        for i in range(44):
            t=(i+nrng.uniform(-.28,.28))/43.0
            t=max(0.0,min(1.0,t))
            x=side*(.014 + .040*t)
            arch=1.6035 + .0068*math.sin(math.pi*t)
            root=(x,.0470+nrng.uniform(-.00055,.00055),arch+nrng.uniform(-.0008,.0008))
            length=nrng.uniform(.0025,.0052)
            outward=side*(.22+.68*t)
            upward=.98-.55*t
            norm=math.sqrt(outward*outward+upward*upward)
            dx=outward/norm*length
            dz=upward/norm*length
            bend=nrng.uniform(-.00035,.00035)
            brow_hairs.append([
                root,
                (root[0]+dx*.48,root[1]+.00035,root[2]+dz*.48+bend),
                (root[0]+dx,root[1]+.00060,root[2]+dz),
            ])
    curve_object("DIGE_C21_NATURAL_BROW_HAIRS",brow_hairs,.000050,hair)
    c21_brow_hair_count=len(brow_hairs)

    lash_hairs=[]
    for side in (-1,1):
        for i in range(16):
            t=(i+.5)/16.0
            x=side*(.010+.037*t)
            z=1.5894 + .0035*math.sin(math.pi*t) + nrng.uniform(-.00025,.00025)
            root=(x,.0430+nrng.uniform(-.0002,.0002),z)
            length=nrng.uniform(.0018,.0038)*(0.75+0.35*math.sin(math.pi*t))
            lash_hairs.append([
                root,
                (x+side*.00025,root[1]+length*.55,z+length*.18),
                (x+side*.00055,root[1]+length,z+length*.30),
            ])
    curve_object("DIGE_C21_NATURAL_UPPER_LASHES",lash_hairs,.000042,hair)
    c21_lash_hair_count=len(lash_hairs)

    # Hairline baby hairs: intentionally sparse and irregular. Roots follow a
    # shallow center-to-temple profile and point back/up into the bulk groom.
    baby_hairs=[]
    bins=84
    for i in range(bins):
        if nrng.random() < .32:
            continue
        u=(i+nrng.uniform(-.45,.45))/(bins-1)
        x=-.078 + .156*u
        temple=min(1.0,abs(x)/.078)
        root_z=1.6325 + .0115*(temple**1.55) + nrng.uniform(-.0018,.0018)
        root_y=.0445 + nrng.uniform(-.0012,.0012)
        length=nrng.uniform(.0070,.0145)
        side=1.0 if x>=0 else -1.0
        side_bias=side*nrng.uniform(-.15,.22)
        back=nrng.uniform(.72,1.0)
        lift=nrng.uniform(.45,.85)
        norm=math.sqrt(side_bias*side_bias+back*back+lift*lift)
        dx=side_bias/norm*length
        dy=-back/norm*length
        dz=lift/norm*length
        baby_hairs.append([
            (x,root_y,root_z),
            (x+dx*.34,root_y+dy*.34,root_z+dz*.34+nrng.uniform(-.0004,.0004)),
            (x+dx*.70,root_y+dy*.70,root_z+dz*.70+nrng.uniform(-.0005,.0005)),
            (x+dx,root_y+dy,root_z+dz),
        ])
    curve_object("DIGE_C21_HAIRLINE_BABY_HAIRS",baby_hairs,.000048,hair)
    c21_hairline_baby_count=len(baby_hairs)

    flyaways=[]
    for side in (-1,1):
        for _ in range(4):
            x=side*nrng.uniform(.061,.078)
            z=nrng.uniform(1.642,1.668)
            y=nrng.uniform(.025,.043)
            length=nrng.uniform(.014,.025)
            flyaways.append([
                (x,y,z),
                (x+side*length*.22,y-length*.12,z+length*.30),
                (x+side*length*.46,y-length*.20,z+length*.68),
            ])
    curve_object("DIGE_C21_TEMPLE_FLYAWAYS",flyaways,.000040,hair)
    c21_temple_flyaway_count=len(flyaways)

# C20 deterministic hairline bridge. The C18/C19 bulk mesh solves scalp coverage,
# while these fine curves lower and break up the frontal edge without replacing
# the fitted short03 groom or letting long strands sweep into the face.
c20_hairline_curve_count=0
if C20_VISUAL_REPAIR and not C21_NATURAL_DETAIL:
    hairline_splines=[]
    hrng=random.Random(20262020)
    for i in range(151):
        u=i/150.0
        x=-.075 + .150*u
        temple=abs(x)/.075
        root_z=1.626 + .012*(temple**1.7) + hrng.uniform(-.0012,.0012)
        root_y=.0460 + hrng.uniform(-.0008,.0008)
        side=1.0 if x>=0 else -1.0
        sway=hrng.uniform(-.0022,.0022)
        hairline_splines.append([
            (x,root_y,root_z),
            (x+sway*.25, .0370, root_z+.007+hrng.uniform(-.001,.001)),
            (x+sway*.70+side*.0010, .0210, root_z+.019+hrng.uniform(-.001,.001)),
            (x+sway+side*.0018, .0030, root_z+.033+hrng.uniform(-.0015,.0015)),
        ])
    curve_object("DIGE_C20_HAIRLINE_BRIDGE",hairline_splines,.000060,hair)
    c20_hairline_curve_count=len(hairline_splines)

def build_c17_strand_groom(guide_obj, surface_obj, material):
    # C17.6 — authored multi-guide field.
    # Scar chain:
    # C17.1 fixed guide-shell roots; C17.2/3 falsified density-only repair;
    # C17.4 falsified stratified child roots + local heuristic flow;
    # C17.5 falsified nearest outer-shell endpoint targeting.
    #
    # The official short03 asset already contains authored hair-flow information in
    # its UV diffuse. C17.6 extracts local streak orientation, maps UV directions
    # through the fitted guide-face Jacobian into 3D tangents, resolves +/- direction
    # away from the crown, then K-neighbor interpolates that field onto true scalp
    # roots. Density remains frozen at C17.4/C17.5 for a causal A/B.
    guide_obj.data.update()
    surface_obj.data.update()
    rng=random.Random(20260920)

    mesh=guide_obj.data
    uv_layer=mesh.uv_layers.active
    if uv_layer is None:
        raise RuntimeError("C17.6 requires authored short03 UVs")

    guide_texture_path=system_dir/hair_asset["diffuse"]["runtime_name"]
    guide_texture_path=Path(guide_texture_path)
    if not guide_texture_path.is_absolute():
        guide_texture_path=ROOT/guide_texture_path
    if not guide_texture_path.exists():
        raise RuntimeError(f"C17.6 guide diffuse missing: {guide_texture_path}")
    guide_texture_sha=sha(guide_texture_path)
    if guide_texture_sha != hair_asset["diffuse"]["sha256"]:
        raise RuntimeError(
            f"C17.6 guide diffuse hash drift: expected={hair_asset['diffuse']['sha256']} got={guide_texture_sha}"
        )

    flow_image=bpy.data.images.load(str(guide_texture_path),check_existing=True)
    width,height=map(int,flow_image.size)
    if width < 64 or height < 64:
        raise RuntimeError(f"C17.6 guide texture unexpectedly small: {width}x{height}")
    rgba=np.empty(len(flow_image.pixels),dtype=np.float32)
    flow_image.pixels.foreach_get(rgba)
    rgba=rgba.reshape((height,width,4))
    gray=(rgba[:,:,0]*0.2126 + rgba[:,:,1]*0.7152 + rgba[:,:,2]*0.0722)
    alpha=rgba[:,:,3]

    guide_rot=guide_obj.matrix_world.to_3x3()
    guide_points=[guide_obj.matrix_world @ v.co for v in mesh.vertices]
    top_count=max(24,len(guide_points)//10)
    crown_points=sorted(guide_points,key=lambda p:p.z)[-top_count:]
    crown_center=Vector((0,0,0))
    for p in crown_points:
        crown_center+=p
    crown_center/=len(crown_points)

    flow_samples=[]
    coherence_values=[]
    alpha_values=[]
    for poly in mesh.polygons:
        loops=list(poly.loop_indices)
        if len(loops) < 3:
            continue
        uv_pts=[uv_layer.data[li].uv.copy() for li in loops]
        uc=sum(float(t.x) for t in uv_pts)/len(uv_pts)
        vc=sum(float(t.y) for t in uv_pts)/len(uv_pts)
        px=int(round(max(0.0,min(1.0,uc))*(width-1)))
        py=int(round(max(0.0,min(1.0,vc))*(height-1)))

        r=5
        x0=max(1,px-r); x1=min(width-1,px+r+1)
        y0=max(1,py-r); y1=min(height-1,py+r+1)
        if x1-x0 < 5 or y1-y0 < 5:
            continue
        patch=gray[y0:y1,x0:x1]
        apatch=alpha[y0:y1,x0:x1]
        gy,gx=np.gradient(patch)
        mask=apatch > 0.05
        if int(mask.sum()) < 12:
            continue
        weights=apatch[mask]
        gxv=gx[mask]; gyv=gy[mask]
        wsum=float(weights.sum())+1e-12
        jxx=float((gxv*gxv*weights).sum()/wsum)
        jyy=float((gyv*gyv*weights).sum()/wsum)
        jxy=float((gxv*gyv*weights).sum()/wsum)
        mean_alpha=float(weights.mean())
        trace=jxx+jyy
        anis=math.sqrt(max(0.0,(jxx-jyy)*(jxx-jyy)+4.0*jxy*jxy))
        coherence=anis/(trace+1e-12)

        # Blender image pixel rows follow UV bottom-up order. Gradient dominant
        # orientation is perpendicular to the fiber line orientation.
        theta_grad=0.5*math.atan2(2.0*jxy,jxx-jyy)
        theta_line=theta_grad+math.pi*0.5
        du=math.cos(theta_line)
        dv=math.sin(theta_line)
        if coherence < 0.20:
            # Preserve a source-bound fallback instead of returning to hard-coded
            # C17.3 back/down vectors.
            du=0.0; dv=1.0

        l0,l1,l2=loops[0],loops[1],loops[2]
        vi0=mesh.loops[l0].vertex_index
        vi1=mesh.loops[l1].vertex_index
        vi2=mesh.loops[l2].vertex_index
        p0=guide_obj.matrix_world @ mesh.vertices[vi0].co
        p1=guide_obj.matrix_world @ mesh.vertices[vi1].co
        p2=guide_obj.matrix_world @ mesh.vertices[vi2].co
        t0=uv_layer.data[l0].uv
        t1=uv_layer.data[l1].uv
        t2=uv_layer.data[l2].uv
        du1=float(t1.x-t0.x); dv1=float(t1.y-t0.y)
        du2=float(t2.x-t0.x); dv2=float(t2.y-t0.y)
        det=du1*dv2-dv1*du2
        if abs(det) < 1e-10:
            continue
        e1=p1-p0; e2=p2-p0
        dPdu=(e1*dv2-e2*dv1)/det
        dPdv=(-e1*du2+e2*du1)/det
        flow=dPdu*du+dPdv*dv
        if flow.length < 1e-8:
            continue

        center=Vector((0,0,0))
        for li in loops:
            center+=guide_obj.matrix_world @ mesh.vertices[mesh.loops[li].vertex_index].co
        center/=len(loops)
        normal=(guide_rot @ poly.normal).normalized()
        if normal.length < 1e-8:
            normal=Vector((0,0,1))
        flow=flow-normal*flow.dot(normal)
        if flow.length < 1e-8:
            continue
        flow.normalize()

        # Structure-tensor orientation is an unoriented line. Resolve sign by
        # flowing away from the fitted crown over the guide surface.
        outward=center-crown_center
        outward=outward-normal*outward.dot(normal)
        if outward.length > 1e-7 and flow.dot(outward) < 0:
            flow=-flow

        flow_samples.append((poly.index,center,normal,flow,coherence,mean_alpha))
        coherence_values.append(coherence)
        alpha_values.append(mean_alpha)

    if len(flow_samples) < 500:
        raise RuntimeError(f"C17.6 texture-flow field too sparse: {len(flow_samples)} samples")

    # Vectorized KNN arrays for deterministic guide interpolation.
    guide_centers=np.array([[s[1].x,s[1].y,s[1].z] for s in flow_samples],dtype=np.float64)
    guide_flows=np.array([[s[3].x,s[3].y,s[3].z] for s in flow_samples],dtype=np.float64)
    guide_coh=np.array([s[4] for s in flow_samples],dtype=np.float64)
    guide_alpha=np.array([s[5] for s in flow_samples],dtype=np.float64)

    surface_rot=surface_obj.matrix_world.to_3x3()
    scalp_candidates=[]
    if C28_GNM_HEAD:
        # C28 uses a new scan-learned head topology. Derive scalp bounds from the
        # aligned GNM contract and the measured brow/hairline instead of MakeHuman constants.
        _c28_bbox_min=Vector(c28_gnm["aligned_bbox_min"])
        _c28_bbox_max=Vector(c28_gnm["aligned_bbox_max"])
        _c28_eye_mid=(Vector(c28_gnm["head_translation"]) + Vector((0,0,0)))  # provenance-only origin
        _c28_hairline=float(c28_gnm["hairline_target_z"])
        _c28_z_min=_c28_hairline-(.105 if C32_GNM_DERMAL_HAIR else .010)
        _c28_z_max=float(_c28_bbox_max.z)+.004
        _c28_x_half=max(.115,min(.155,(float(_c28_bbox_max.x)-float(_c28_bbox_min.x))*.48))
        _c28_y_max=float(_c28_bbox_max.y)+.004
    for idx,v in enumerate(surface_obj.data.vertices):
        p=surface_obj.matrix_world @ v.co
        if C28_GNM_HEAD:
            if p.z < _c28_z_min or p.z > _c28_z_max:
                continue
            if abs(p.x) > _c28_x_half or p.y > _c28_y_max:
                continue
        else:
            if p.z < 1.540 or p.z > 1.706:
                continue
            if abs(p.x) > .130 or p.y > .065:
                continue
        # C19 keeps the C17.7 face-clearance scar but replaces its excessively
        # high/receded central hairline with an explicit center/temple profile.
        n=(surface_rot @ v.normal).normalized()
        if n.length < 1e-8:
            n=Vector((0,0,1))
        if C28_GNM_HEAD:
            if C32_GNM_DERMAL_HAIR:
                # C32.1: lower roots are permitted only on the temple/side/back
                # scalp. Expanding Z alone admitted forehead/face vertices in the
                # first C32 render, producing strands across the eyes/nose/mouth.
                # Keep the measured frontal hairline, but fail closed for lower
                # central/front-facing vertices.
                lower_root=(p.z < _c28_hairline-.004)
                if lower_root:
                    side_or_back=(abs(p.x) >= .070 or p.y <= -.030)
                    if not side_or_back:
                        continue
                    if p.y > -.010 and n.y > .05:
                        continue
                elif n.y > .72 and p.z < _c28_hairline+.010:
                    # Near the frontal hairline, preserve edge roots but reject
                    # strongly face-facing forehead samples.
                    continue
            else:
                # Pre-C32 gate retained for reproducibility.
                if n.y < -0.16 and p.z < _c28_hairline+.018:
                    continue
        elif C19_HUMANIZATION:
            frontal_hairline_z=C19_HAIRLINE_CENTER_Z + C19_HAIRLINE_TEMPLE_RISE*min(abs(p.x),.10)
            if p.y > .000:
                if p.z < frontal_hairline_z:
                    continue
                if n.z < 0.06 and p.z < frontal_hairline_z+.012:
                    continue
                if n.y < -0.10:
                    continue
            if p.z < 1.575 and abs(p.x) < .085:
                continue
        else:
            frontal_hairline_z=1.620-0.10*min(abs(p.x),.10)
            if p.y > .000 and p.z < frontal_hairline_z:
                continue
            if p.y > .000 and n.y < -0.05:
                continue
            if p.z < 1.585 and abs(p.x) < .085:
                continue
        scalp_candidates.append((idx,p,n))
    if len(scalp_candidates) < 350:
        raise RuntimeError(f"C17.6 scalp mask too sparse: {len(scalp_candidates)} roots")

    target_roots=min(1800,len(scalp_candidates))
    if len(scalp_candidates) > target_roots:
        roots=[]
        for i in range(target_roots):
            roots.append(scalp_candidates[min(len(scalp_candidates)-1,int(i*len(scalp_candidates)/target_roots))])
    else:
        roots=scalp_candidates

    k_neighbors=8
    root_guides=[]
    root_coherences=[]
    shell_lifts=[]
    for root_index,root,n in roots:
        rv=np.array([root.x,root.y,root.z],dtype=np.float64)
        delta=guide_centers-rv
        d2=np.einsum('ij,ij->i',delta,delta)
        ids=np.argpartition(d2,k_neighbors-1)[:k_neighbors]
        ids=ids[np.argsort(d2[ids])]
        anchor=guide_flows[ids[0]].copy()

        flows=guide_flows[ids].copy()
        dots=flows @ anchor
        flows[dots < 0] *= -1.0
        weights=np.exp(-d2[ids]/(2.0*.055*.055))
        weights*=np.maximum(.12,guide_coh[ids])*np.maximum(.25,guide_alpha[ids])
        wsum=float(weights.sum())
        if wsum < 1e-10:
            continue
        f=(flows*weights[:,None]).sum(axis=0)/wsum
        gc=(guide_centers[ids]*weights[:,None]).sum(axis=0)/wsum
        fc=float((guide_coh[ids]*weights).sum()/wsum)

        field_flow=Vector((float(f[0]),float(f[1]),float(f[2])))
        field_flow=field_flow-n*field_flow.dot(n)
        if field_flow.length < 1e-8:
            field_flow=Vector((float(anchor[0]),float(anchor[1]),float(anchor[2])))
            field_flow=field_flow-n*field_flow.dot(n)
        if field_flow.length < 1e-8:
            continue
        field_flow.normalize()

        guide_center=Vector((float(gc[0]),float(gc[1]),float(gc[2])))
        shell_vec=guide_center-root
        shell_len=max(.001,shell_vec.length)
        shell_lift=max(.006,min(.045,abs(shell_vec.dot(n))))
        root_guides.append((
            root_index,root,n,int(flow_samples[int(ids[0])][0]),
            guide_center,field_flow,shell_len,shell_lift,fc
        ))
        root_coherences.append(fc)
        shell_lifts.append(shell_lift)

    # C17.7 intentionally narrows the scalp mask to eliminate facial/forehead
    # intrusion. With 64 strands/root, 350 valid scalp roots already yields
    # >=22,400 rendered curves, so the old 1200-root gate became a false blocker.
    if len(root_guides) < 350:
        raise RuntimeError(f"C17.7 interpolated scalp field too sparse: {len(root_guides)} roots")
    c32_lower_central_root_count=0
    if C32_GNM_DERMAL_HAIR:
        for _ri,_root,_n,*_rest in root_guides:
            if _root.z < _c28_hairline-.004 and abs(_root.x) < .070 and _root.y > -.030:
                c32_lower_central_root_count += 1
        if c32_lower_central_root_count:
            raise RuntimeError(f"C32.1 lower-central face/scalp root leak: {c32_lower_central_root_count}")

    points_per_curve=12 if C32_GNM_DERMAL_HAIR else 8
    strands_per_root=HAIR_STRANDS_PER_ROOT
    curve_count=len(root_guides)*strands_per_root
    hair_data=bpy.data.hair_curves.new("DIGE_C17_STRAND_GROOM_DATA")
    hair_data.add_curves([points_per_curve]*curve_count)
    try:
        hair_data.set_types(type='CATMULL_ROM')
    except Exception:
        pass
    hair_data.surface=surface_obj
    hair_data.materials.append(material)

    positions=[]
    radii=[]
    base_radius=0.000042 if C32_GNM_DERMAL_HAIR else 0.000055
    tip_radius=0.0000065 if C32_GNM_DERMAL_HAIR else 0.000011
    down=Vector((0.0,0.0,-1.0))
    inv_world=surface_obj.matrix_world.inverted()
    surf_rot=surface_obj.matrix_world.to_3x3()

    for root_index,root,n,guide_index,guide_center,field_flow,shell_len,shell_lift,field_coherence in root_guides:
        tangent_flow=field_flow.copy()
        tangent_cross=n.cross(tangent_flow)
        if tangent_cross.length < 1e-8:
            tangent_cross=Vector((1,0,0))
        tangent_cross.normalize()

        cluster_phase=((guide_index*31 + root_index*7) % 97)/97.0*math.tau
        clump_bias=(tangent_cross*math.cos(cluster_phase) + tangent_flow*math.sin(cluster_phase)*.18)
        if clump_bias.length < 1e-8:
            clump_bias=tangent_cross.copy()
        clump_bias.normalize()

        # Density and 44/20 population split remain frozen from C17.4/C17.5.
        # Only the authored multi-guide direction + guide-derived lift change.
        frontal=max(0.0,min(1.0,(root.y+.010)/.060))
        envelope=max(.036,min(.066,shell_len*.50+.024))
        if frontal > .35:
            envelope=min(envelope,.042)
        under_lift=max(.004,min(.012,.004+shell_lift*.18))
        style_lift=max(.010,min(.026,.010+shell_lift*.42))

        grid=max(2,int(math.ceil(math.sqrt(strands_per_root))))
        undercoat_count=max(1,int(round(strands_per_root*(.58 if C32_GNM_DERMAL_HAIR else .75))))
        for k in range(strands_per_root):
            gx=k % grid
            gy=k // grid
            du=((gx+0.5)/grid-.5)*.0050 + rng.uniform(-.00016,.00016)
            dv=((gy+0.5)/grid-.5)*.0050 + rng.uniform(-.00016,.00016)
            proposed=root + tangent_flow*du + tangent_cross*dv
            local_proposed=inv_world @ proposed
            hit,loc_local,n_local,_poly=surface_obj.closest_point_on_mesh(local_proposed)
            if hit:
                root_j=surface_obj.matrix_world @ loc_local
                child_n=(surf_rot @ n_local).normalized()
                if root_j.z < 1.535 or root_j.z > 1.712 or root_j.y > .072:
                    root_j=root.copy()
                    child_n=n.copy()
            else:
                root_j=root.copy()
                child_n=n.copy()
            root_j += child_n*0.00065

            child_flow=tangent_flow-child_n*tangent_flow.dot(child_n)
            if child_flow.length < 1e-8:
                child_flow=field_flow.copy()
            child_flow.normalize()
            # Prevent front-scalp strands from flowing into the face. Blend them
            # laterally/backward while preserving authored texture-flow elsewhere.
            front_gate=max(0.0,min(1.0,(root_j.y+.004)/.050))
            if front_gate > 0.0:
                safe_dir=Vector((1.0 if root_j.x >= 0 else -1.0,-0.35,0.10))
                safe_dir=safe_dir-child_n*safe_dir.dot(child_n)
                if safe_dir.length > 1e-8:
                    safe_dir.normalize()
                    safe_w=max(0.0,min(0.98,HAIR_FRONT_SAFE_BLEND*front_gate))
                    child_flow=(child_flow*(1.0-safe_w)+safe_dir*safe_w)
                    child_flow.normalize()
            child_cross=child_n.cross(child_flow)
            if child_cross.length < 1e-8:
                child_cross=tangent_cross.copy()
            child_cross.normalize()

            undercoat=(k < undercoat_count)
            if undercoat:
                length=rng.uniform(.018,.034)*HAIR_ACCENT_LENGTH_SCALE if C32_GNM_DERMAL_HAIR else rng.uniform(.015,.027)*HAIR_ACCENT_LENGTH_SCALE
                lift=under_lift*rng.uniform(.78,1.08) if C32_GNM_DERMAL_HAIR else under_lift*rng.uniform(.82,1.02)
                tip_clear=rng.uniform(.0010,.0024) if C32_GNM_DERMAL_HAIR else rng.uniform(.0010,.0020)
                flow=(child_flow + child_cross*rng.uniform(-.065,.065)).normalized() if C32_GNM_DERMAL_HAIR else (child_flow + child_cross*rng.uniform(-.040,.040)).normalized()
                amp=rng.uniform(.00028,.00088) if C32_GNM_DERMAL_HAIR else rng.uniform(.00020,.00065)
            else:
                length=min(.058,envelope*1.12)*rng.uniform(.82,1.14)*HAIR_ACCENT_LENGTH_SCALE if C32_GNM_DERMAL_HAIR else min(.043,envelope)*rng.uniform(.78,.96)*HAIR_ACCENT_LENGTH_SCALE
                lift=style_lift*rng.uniform(.76,1.12) if C32_GNM_DERMAL_HAIR else style_lift*rng.uniform(.80,1.02)
                tip_clear=rng.uniform(.0016,.0042) if C32_GNM_DERMAL_HAIR else rng.uniform(.0016,.0032)
                flow=(child_flow + child_cross*rng.uniform(-.095,.095) + clump_bias*rng.uniform(.002,.012)).normalized() if C32_GNM_DERMAL_HAIR else (child_flow + child_cross*rng.uniform(-.060,.060) + clump_bias*rng.uniform(.0015,.0075)).normalized()
                amp=rng.uniform(.00050,.00155) if C32_GNM_DERMAL_HAIR else rng.uniform(.00035,.00105)

            lateral=(child_cross + child_flow*rng.uniform(-.14,.14)).normalized() if C32_GNM_DERMAL_HAIR else (child_cross + child_flow*rng.uniform(-.10,.10)).normalized()
            strand_phase=cluster_phase + k*0.713
            for j in range(points_per_curve):
                t=j/(points_per_curve-1)
                bend=math.sin(math.pi*t)
                sag=t*t
                p=(
                    root_j
                    + flow*(length*t)
                    + child_n*(lift*bend + tip_clear*t)
                    + lateral*(amp*bend)
                    + (child_cross*((.00024 if undercoat else .00058)*math.sin(math.tau*(1.35*t)+strand_phase)*bend) if C32_GNM_DERMAL_HAIR else Vector((0,0,0)))
                    + (child_n*((.00010 if undercoat else .00022)*math.sin(math.tau*(2.65*t)+strand_phase*1.73)*bend) if C32_GNM_DERMAL_HAIR else Vector((0,0,0)))
                    + down*(length*((.014 if undercoat else .022) if C32_GNM_DERMAL_HAIR else (.018 if undercoat else .026))*sag)
                )
                # C18 hybrid: the fitted bulk mesh owns coverage/style; curves are
                # bounded hairline/silhouette accents. Prevent accents from sweeping
                # into the central face even if source texture-flow is ambiguous.
                if root_j.y > -0.002:
                    max_forward=root_j.y+0.0045
                    if p.y > max_forward:
                        p.y=max_forward
                    if abs(p.x) < .100 and p.z < 1.600:
                        p.y=min(p.y,root_j.y-0.0015)
                positions.extend((p.x,p.y,p.z))
                taper=(base_radius*(1.0-t) + tip_radius*t)
                radius=taper*rng.uniform(.94,1.06)*(0.92 if undercoat else 1.0)
                radii.append(radius)

    pos=hair_data.attributes["position"]
    pos.data.foreach_set("vector",positions)
    radius_attr=hair_data.attributes.get("radius")
    if radius_attr is None:
        radius_attr=hair_data.attributes.new("radius",'FLOAT','POINT')
    radius_attr.data.foreach_set("value",radii)

    groom=bpy.data.objects.new("DIGE_C17_STRAND_GROOM",hair_data)
    bpy.context.collection.objects.link(groom)
    guide_obj.hide_render=not C18_HYBRID_BULK
    try:
        guide_obj.hide_set(not C18_HYBRID_BULK)
    except Exception:
        pass

    return groom,{
        "root_count":len(root_guides),
        "scalp_candidate_count":len(scalp_candidates),
        "guide_sample_count":len(flow_samples),
        "guide_mesh_vertices":len(mesh.vertices),
        "guide_mesh_polygons":len(mesh.polygons),
        "guide_field_version":"C17_6_SHORT03_UV_TEXTURE_FLOW_K8",
        "guide_field_source":"OFFICIAL_MAKEHUMAN_SHORT03_DIFFUSE_STRUCTURE_TENSOR_PLUS_UV_JACOBIAN",
        "guide_texture_sha256":guide_texture_sha,
        "guide_texture_size":[width,height],
        "guide_field_neighbors":k_neighbors,
        "guide_field_mean_sample_coherence":sum(coherence_values)/len(coherence_values),
        "guide_field_mean_root_coherence":sum(root_coherences)/len(root_coherences),
        "guide_field_mean_alpha":sum(alpha_values)/len(alpha_values),
        "guide_field_mean_shell_lift_m":sum(shell_lifts)/len(shell_lifts),
        "strands_per_root":strands_per_root,
        "curve_count":curve_count,
        "points_per_curve":points_per_curve,
        "point_count":curve_count*points_per_curve,
        "root_radius_m":base_radius,
        "tip_radius_m":tip_radius,
        "guide_mesh_rendered":C18_HYBRID_BULK,
        "blender_datablock":"HAIR_CURVES",
        "curve_type":"CATMULL_ROM",
        "surface_bound":True,
        "distribution":"SCALP_TEXTURE_FLOW_K8_STRATIFIED_UNDERCOAT_STYLE_C17_6",
        "coverage_mask":"SCALP_Z1P540_1P706_YLE0P065_FRONTAL_HAIRLINE",
        "density_frozen_from":"C17_4_C17_5",
        "seed":20260920,
        "c32_lower_central_root_count":c32_lower_central_root_count if C32_GNM_DERMAL_HAIR else None,
        "c32_root_domain":"MEASURED_HAIRLINE_PLUS_TEMPLE_SIDE_BACK_ONLY_V2" if C32_GNM_DERMAL_HAIR else None,
    }

groom_surface=(c28_gnm_objects.get("skin") if C28_GNM_HEAD else body)
if groom_surface is None:
    raise RuntimeError("C28 GNM skin surface missing for strand groom")
hair_groom,hair_curve_metrics=build_c17_strand_groom(hair_obj,groom_surface,hair)
if C29_GNM_PRESENTATION:
    hair_obj.hide_render=True
    try:
        hair_obj.hide_set(True)
    except Exception:
        pass
    hair_curve_metrics["guide_mesh_rendered"]=False
    hair_fit["c29_bulk_mesh_hidden"]=True
strands=[None]*hair_curve_metrics["curve_count"]
hair_surface_contract={
    "root_source":"SCALP_SURFACE_ROOTS_PLUS_OFFICIAL_SHORT03_UV_TEXTURE_FLOW_FIELD",
    "asset_key":HAIR_ASSET_KEY,
    "asset":HAIR_ASSET_KEY.replace("hair_",""),
    "asset_tags":hair_asset["tags"],
    "obj_sha256":hair_asset["obj"]["sha256"],
    "mhclo_sha256":hair_asset["mhclo"]["sha256"],
    "diffuse_sha256":hair_asset["diffuse"]["sha256"],
    "guide_vertices":hair_fit["vertices"],
    "guide_polygons":hair_fit["polygons"],
    "mass_mesh_rendered":hair_curve_metrics["guide_mesh_rendered"],
    "curve_count":hair_curve_metrics["curve_count"],
    "point_count":hair_curve_metrics["point_count"],
    "points_per_curve":hair_curve_metrics["points_per_curve"],
    "root_radius_m":hair_curve_metrics["root_radius_m"],
    "tip_radius_m":hair_curve_metrics["tip_radius_m"],
    "surface_bound":hair_curve_metrics["surface_bound"],
    "distribution":hair_curve_metrics["distribution"],
    "guide_field_version":hair_curve_metrics["guide_field_version"],
    "guide_field_source":hair_curve_metrics["guide_field_source"],
    "guide_texture_sha256":hair_curve_metrics["guide_texture_sha256"],
    "guide_field_neighbors":hair_curve_metrics["guide_field_neighbors"],
    "guide_field_mean_root_coherence":hair_curve_metrics["guide_field_mean_root_coherence"],
    "seed":hair_curve_metrics["seed"],
    "style":"C32_GNM_DERMAL_FIBER_GROOM_V1" if C32_GNM_DERMAL_HAIR else ("C29_GNM_STRAND_ONLY_PRESENTATION_V1" if C29_GNM_PRESENTATION else ("C27_OFFICIAL_ANATOMY_SURFACE_FIBERS_V1" if C27_SURFACE_FIBERS else ("C26_MPFB2_PHOTOMETRIC_SAFE_GROOM_V1" if C26_PHOTOMETRIC else ("MPFB2_ENHANCED_SKIN_EYES_CURATED_SHORT03_C25_V1" if C25_MATURE_STACK else ("SURFACE_EYES_SOURCE_ALBEDO_C24_V1" if (C24_SURFACE_EYES or C24_SOURCE_ALBEDO or C24_HAIRLINE_REPAIR) else ("CALIBRATED_EYES_FRONTAL_GROOM_C23_V1" if (C23_CALIBRATED_EYES or C23_HAIRLINE_REPAIR or C23_FACE_PLANES) else ("PHYSICAL_SKIN_LANDMARK_GROOM_C22_V1" if (C22_PHYSICAL_SKIN or C22_LANDMARK_GROOM or C22_HAIR_MASS_WARP) else ("HYBRID_BULK_PLUS_NATURAL_MICROHAIRS_C21_V1" if C21_NATURAL_DETAIL else ("HYBRID_BULK_PLUS_MICRO_HAIRLINE_BROW_CURVES_C20_V1" if C20_VISUAL_REPAIR else ("HYBRID_BULK_PLUS_HAIRLINE_CURVES_C19_V1" if C19_HUMANIZATION else ("HYBRID_BULK_PLUS_BOUNDED_CURVES_C18_V1" if C18_HYBRID_BULK else "HAIR_CURVES_GUIDE_INTERPOLATED_C17_V1"))))))))))),
}

# Fitted garment proxy from the deterministic canonical MakeHuman helper-tights group.
tights_path=RUNTIME/"dige_makehuman_tights_v8.obj"
bpy.ops.wm.obj_import(
    filepath=str(tights_path),
    forward_axis='Y',
    up_axis='Z',
    use_split_objects=False,
    use_split_groups=False,
)
garments=[o for o in bpy.context.selected_objects if o.type=='MESH']
if len(garments)!=1:
    raise RuntimeError(f"Expected one helper-tights garment mesh, got {len(garments)}")
tights=garments[0]
tights.name="DIGE_V8_FITTED_TIGHTS"
tights.data.materials.append(cloth)
bpy.context.view_layer.objects.active=tights
bpy.ops.object.shade_smooth()
gsub=tights.modifiers.new("DIGE_V8_TIGHTS_SUBDIV","SUBSURF"); gsub.levels=1; gsub.render_levels=2
solid=tights.modifiers.new("DIGE_V8_TIGHTS_THICKNESS","SOLIDIFY"); solid.thickness=.0030; solid.offset=1.0

bpy.ops.mesh.primitive_plane_add(size=20,location=(0,0,-.006))
floor=bpy.context.object; floor.data.materials.append(floor_mat)

def area(name,loc,energy,size,color,target=(0,0,1.25)):
    bpy.ops.object.light_add(type='AREA',location=loc)
    o=bpy.context.object; o.name=name; o.data.energy=energy; o.data.shape='DISK'; o.data.size=size; o.data.color=color
    d=Vector(target)-o.location; o.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    return o
if C26_PHOTOMETRIC:
    face_target=(0,.020,1.575)
    area("KEY",(1.45,1.90,2.22),235,1.45,(1.0,.95,.90),face_target)
    area("FILL",(-1.60,2.00,1.78),24,2.60,(.88,.93,1.0),face_target)
    area("RIM",(0,-2.10,2.28),58,1.35,(1.0,.88,.78),face_target)
    area("DETAIL",(-.95,1.10,1.72),22,.46,(.96,.98,1.0),face_target)
elif C20_VISUAL_REPAIR:
    face_target=(0,.020,1.575)
    area("KEY",(1.35,1.95,2.25),300,1.20,(1.0,.90,.82),face_target)
    area("FILL",(-1.70,2.10,1.82),28,2.40,(.80,.87,1.0),face_target)
    area("RIM",(0,-2.10,2.35),90,1.25,(1.0,.76,.58),face_target)
    area("DETAIL",(-1.05,1.10,1.74),42,.38,(.93,.96,1.0),face_target)
elif C19_PHOTO_LIGHTING:
    face_target=(0,.020,1.575)
    area("KEY",(1.65,2.35,2.45),650,1.70,(1.0,.90,.82),face_target)
    area("FILL",(-1.80,2.10,1.85),55,2.60,(.78,.86,1.0),face_target)
    area("RIM",(0,-2.20,2.40),150,1.50,(1.0,.76,.58),face_target)
    area("FACE",(.15,1.30,1.70),10,.85,(1.0,.93,.88),face_target)
    area("DETAIL",(-1.10,1.15,1.75),35,.45,(.92,.96,1.0),face_target)
else:
    area("KEY",(2.1,2.8,2.8),500,2.5,(1.0,.88,.78))
    area("FILL",(-2.0,2.1,1.8),110,3.0,(.72,.84,1.0))
    area("RIM",(0,-2.3,2.5),210,1.8,(1.0,.72,.50))
    area("FACE",(0,1.2,1.8),45,1.1,(1.0,.91,.84))

world=bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world=world
world.use_nodes=True
bg=world.node_tree.nodes.get("Background"); bg.inputs["Color"].default_value=(0.012,0.014,0.020,1); bg.inputs["Strength"].default_value=.022 if C26_PHOTOMETRIC else .055

bpy.ops.object.camera_add(); cam=bpy.context.object; bpy.context.scene.camera=cam; cam.data.sensor_width=36

def aim(loc,target,lens,fstop):
    cam.location=loc; d=Vector(target)-cam.location; cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
    cam.data.lens=lens; cam.data.dof.use_dof=True; cam.data.dof.focus_distance=d.length; cam.data.dof.aperture_fstop=fstop

def configure_cycles_device(scene):
    mode=os.environ.get("DIGE_CYCLES_DEVICE","CPU").upper()
    backend=os.environ.get("DIGE_CYCLES_BACKEND","OPTIX").upper()
    info={"requested_mode":mode,"requested_backend":backend,"enabled_devices":[]}
    if mode == "CPU":
        scene.cycles.device='CPU'
        info["actual_mode"]="CPU"
        return info
    if mode != "GPU":
        raise RuntimeError(f"Unsupported DIGE_CYCLES_DEVICE={mode}")
    addon=bpy.context.preferences.addons.get("cycles")
    if addon is None:
        raise RuntimeError("Cycles addon unavailable")
    prefs=addon.preferences
    try:
        prefs.compute_device_type=backend
    except Exception as exc:
        raise RuntimeError(f"Cannot select Cycles backend {backend}: {exc}")
    try:
        prefs.get_devices()
    except Exception:
        pass
    enabled=[]
    for dev in prefs.devices:
        rec={"name":dev.name,"type":dev.type,"id":getattr(dev,"id",None)}
        use=(dev.type == backend)
        dev.use=use
        if use:
            enabled.append(rec)
    if not enabled:
        raise RuntimeError(f"No usable {backend} device enumerated; CPU fallback forbidden")
    scene.cycles.device='GPU'
    info["actual_mode"]="GPU"
    info["enabled_devices"]=enabled
    return info

scene=bpy.context.scene
scene.render.engine='CYCLES'
# C17 close-up hair certification uses geometric strand cylinders so radius is physical.
try:
    scene.render.hair_type='CYLINDER'
    scene.render.hair_subdiv=1
except Exception:
    pass
device_info=configure_cycles_device(scene)
scene.cycles.samples=int(os.environ.get("DIGE_SAMPLES_PREVIEW","128"))
scene.cycles.seed=int(os.environ.get("DIGE_RENDER_SEED","20260919"))
scene.cycles.use_denoising=True
scene.cycles.use_adaptive_sampling=True
scene.cycles.adaptive_threshold=.015
scene.cycles.max_bounces=12
scene.cycles.diffuse_bounces=4
scene.cycles.glossy_bounces=4
scene.cycles.transmission_bounces=8
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
scene.render.resolution_percentage=100
scene.view_settings.look='AgX - Medium High Contrast'
if C26_PHOTOMETRIC:
    scene.view_settings.exposure=-0.62
elif C20_VISUAL_REPAIR:
    scene.view_settings.exposure=-0.35
vl=scene.view_layers[0]
vl.use_pass_normal=True; vl.use_pass_z=True; vl.use_pass_diffuse_color=True
vl.use_pass_glossy_direct=True; vl.use_pass_transmission_direct=True
if hasattr(vl,"cycles") and hasattr(vl.cycles,"use_pass_denoising_data"):
    vl.cycles.use_pass_denoising_data=True

# Distances inherit the latest provider-backed Drive sweep: V6C-122 fullbody=5.1m, hero=2.7m.
all_views=[
 ("01_FRONT50",(0,5.1,1.03),(0,0,.92),50,7.1,512,768),
 ("02_LEFT_PROFILE50",(5.1,0,1.08),(0,0,.98),50,7.1,512,768),
 ("03_THREE_QUARTER50",(3.60,3.60,1.10),(0,0,1.00),50,6.3,512,768),
 ("04_HERO85",(0,1.10,1.595),(0,.030,1.580),85,4.5,900,900),
 ("05_BACK_THREE_QUARTER50",(-3.60,-3.60,1.08),(0,0,1.00),50,6.3,512,768)
]
if RENDER_SET=="FULL":
    views=all_views
elif RENDER_SET=="HERO_ONLY":
    views=[v for v in all_views if v[0]=="04_HERO85"]
else:
    raise RuntimeError(f"Unsupported DIGE_RENDER_SET={RENDER_SET}")
outputs=[]
for vid,loc,target,lens,fstop,w,h in views:
    scene.render.resolution_x=w; scene.render.resolution_y=h
    aim(loc,target,lens,fstop)
    scene.render.image_settings.file_format='PNG'
    p=OUT/f"{vid}_V8.png"; scene.render.filepath=str(p)
    bpy.ops.render.render(write_still=True)
    outputs.append({"view":vid,"file":p.name,"sha256":sha(p),"lens_mm":lens,"fstop":fstop,"width":w,"height":h})

# Controlled same-seed hero A/B: RAW multilayer EXR vs denoised PNG at identical sample count.
hero_samples=int(os.environ.get("DIGE_SAMPLES_HERO","256"))
hero_seed=int(os.environ.get("DIGE_RENDER_SEED","20260919"))
aim((0,1.10,1.595),(0,.030,1.580),85,4.5)
scene.render.resolution_x=900; scene.render.resolution_y=900
scene.cycles.seed=hero_seed

scene.cycles.use_denoising=False; scene.cycles.samples=hero_samples
scene.render.image_settings.file_format='OPEN_EXR'; scene.render.image_settings.media_type='MULTI_LAYER_IMAGE'; scene.render.image_settings.color_depth='32'
raw=OUT/"04_HERO85_RAW_AOV_V8.exr"; scene.render.filepath=str(raw)
bpy.ops.render.render(write_still=True)

scene.cycles.use_denoising=True; scene.cycles.samples=hero_samples; scene.cycles.seed=hero_seed
scene.render.image_settings.media_type='IMAGE'; scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
denoised=OUT/"04_HERO85_DENOISED_V8.png"; scene.render.filepath=str(denoised)
bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"DIGE_V8_scene.blend"))
receipt={
 "pipeline":"DIGE_V8_MAKEHUMAN_CYCLES",
 "state":"PATH_TRACED_CANDIDATE_EXECUTED",
 "blender_version":bpy.app.version_string,
 "engine":"CYCLES","device":device_info["actual_mode"],"device_info":device_info,
 "identity_bound":False,
 "render_set":RENDER_SET,
 "output_tag":OUTPUT_TAG or None,
 "canon_execution_manifest_sha256":CANON_SHA256,
 "runtime_commit":os.environ.get("DIGE_RUNTIME_COMMIT") or os.environ.get("GITHUB_SHA"),
 "runner":{"name":os.environ.get("RUNNER_NAME"),"os":os.environ.get("RUNNER_OS"),"arch":os.environ.get("RUNNER_ARCH")},
 "geometry_manifest_sha256":sha(RUNTIME/"DIGE_V8_GEOMETRY_MANIFEST.json"),
 "geometry_source":"Google GNM Head scan-learned statistical model + MakeHuman body" if C28_GNM_HEAD else "MakeHuman bundled CC0 base mesh + CC0 asian-female-young morph target",
 "c28_gnm_head":c28_gnm,
 "garment_helper":geom["garment_helper"],
 "system_asset_pack":{
   "source_page":system_contract["source_page"],
   "pack_sha256":system_contract["pack_sha256"],
   "license":system_contract["license"],
   "probe_run":system_contract["probe_run"],
   "probe_artifact_id":system_contract["probe_artifact_id"]
 },
 "system_asset_fits":system_asset_fits,
 "fit_reference":{
   "vertices":fit_ref_meta["vertices"],
   "sha256":fit_ref_meta["sha256"],
   "body_prefix_overridden_vertices":len(body.data.vertices),
   "coordinate_system":fit_ref_meta["coordinate_system"]
 },
 "eye_helpers":geom["eye_helpers"],
 "landmark_binding_sha256":hashlib.sha256(json.dumps(geom["landmarks"],sort_keys=True).encode()).hexdigest(),
 "topology_metrics":topology,
 "craniofacial_runtime_deform":craniofacial_deform,
 "geometry_normalization":geom.get("normalization"),
 "hair_regime":hair_surface_contract["style"],
 "hair_surface_contract":hair_surface_contract,
 "appearance_candidate":(
   "C32_GNM_DERMAL_HAIR_REFINEMENT_V1" if C32_GNM_DERMAL_HAIR else
   "C31_GNM_REGIONAL_FACE_APPEARANCE_V1" if C31_GNM_FACE_APPEARANCE else
   "C30_GNM_SEMANTIC_FEMALE_ASIAN_V1" if C30_GNM_SEMANTIC_IDENTITY else
   "C29_GNM_PRESENTATION_REPAIR_V1" if C29_GNM_PRESENTATION else
   "C28_GNM_HIGH_FIDELITY_HEAD_V1" if C28_GNM_HEAD else
   "C27_OFFICIAL_ANATOMY_SURFACE_FIBERS_V1" if C27_SURFACE_FIBERS else
   "C26_PHOTOMETRIC_INTERFACE_V1" if C26_PHOTOMETRIC else
   "C25_MPFB2_ENHANCED_MATURE_STACK_V1" if C25_MATURE_STACK else
   "C24_SURFACE_EYES_SOURCE_ALBEDO_V1" if (C24_SURFACE_EYES or C24_SOURCE_ALBEDO or C24_HAIRLINE_REPAIR) else
   "C23_CALIBRATED_EYES_HAIRLINE_V1" if (C23_CALIBRATED_EYES or C23_HAIRLINE_REPAIR or C23_FACE_PLANES) else
   "C22_PHYSICAL_SKIN_LANDMARK_GROOM_V1" if (C22_PHYSICAL_SKIN or C22_LANDMARK_GROOM or C22_HAIR_MASS_WARP) else
   "C21_NATURAL_DETAIL_HYBRID_SKIN_GROOM_V1" if C21_NATURAL_DETAIL else
   "C20_VISUAL_REPAIR_HYBRID_SKIN_GROOM_V1" if C20_VISUAL_REPAIR else
   "C19_HUMANIZED_HYBRID_SKIN_GROOM_V1" if C19_HUMANIZATION else
   "C18_HYBRID_MATURE_GROOM_SKIN_V1" if C18_HYBRID_BULK else
   "C17_MATURE_STRAND_GROOM_OVER_C16_V1"
 ),
 "appearance_selection":{
   "skin_sss_weight":SKIN_SSS_WEIGHT,
   "skin_sss_scale":SKIN_SSS_SCALE,
   "skin_roughness_range":[SKIN_ROUGH_MIN,SKIN_ROUGH_MAX],
   "hair_regime":hair_surface_contract["style"],
   "hair_guide_sha256":geom["hair_guide"]["sha256"],
   "selection_basis":(
     "C32_AFTER_C31_VISUAL_AUDIT: KEEP_GNM_IDENTITY/CAMERA/PHOTOMETRY; REDUCE_WAXY_SSS_AND_COAT; INCREASE_MID/MICRO_DERMAL_VARIATION; EXPAND_GNM_SCALP_DOMAIN_TO_TEMPLES/SIDES; DOUBLE_FINE_STRAND_DENSITY; THINNER_RADIUS; LOWER_UNDERCOAT_RATIO; ADD_LOW_AMPLITUDE_MULTI_FREQUENCY_FIBER_VARIATION; SINGLE_TARGETED_FINALIST" if C32_GNM_DERMAL_HAIR else
     "C31_AFTER_C30_VISUAL_FAIL: KEEP_SEMANTIC_GNM_IDENTITY; ADD_GNM_LANDMARK_DRIVEN REGIONAL LIP/BLUSH/TZONE MASKS + STRONGER MULTISCALE PORE/MICRO NORMAL + FORWARD DARK BROW/LASH FIBERS + EYE WETLINES + SUBTLE MOUTH GAP; PRESERVE_CAMERA/PHOTOMETRY/GROOM" if C31_GNM_FACE_APPEARANCE else
     "C30_AFTER_C29_VISUAL_FAIL: KEEP_C29_PRESENTATION_REPAIR; REPLACE_UNCONSTRAINED_HEAD_PCA_SAMPLE_WITH_OFFICIAL_GNM_SEMANTIC_CVAE FEMALE+ASIAN IDENTITY; DETERMINISTIC_SEED; PRESERVE_GEOMETRY/PHOTOMETRY/GROOM FOR_CAUSAL_IDENTITY_ABLATION" if C30_GNM_SEMANTIC_IDENTITY else
     "C29_AFTER_C28_VISUAL_FAIL: KEEP_GNM_GEOMETRY; REPLACE_BROKEN_HEAD_MATERIAL_WITH_DIRECT_RANDOM_WALK_PROCEDURAL_SKIN; HIDE_SHORT03_BULK_MESH; RENDER_STRAND_GROOM_ONLY; CALIBRATED_IRIS_PUPIL_CORNEA_STACKS; PRESERVE_C26_PHOTOMETRY" if C29_GNM_PRESENTATION else
     "C28_AFTER_C27_VISUAL_FAIL: APACHE2_SCAN_LEARNED_GOOGLE_GNM_HEAD + INTERNAL_EYES_TEETH_TONGUE + EYE_ALIGNED_BODY_FIT + ADAPTIVE_HAIRLINE + GNM_LANDMARK_FIBERS; PRESERVE_C26_PHOTOMETRY" if C28_GNM_HEAD else
     "C27_AFTER_C26_VISUAL_FAIL: OFFICIAL_MAKEHUMAN_ANATOMY_TARGETS + SURFACE_ANCHORED_FIBER_GROOM + SUBTLE_NATIVE_MOUTH_INTERFACES; PRESERVE_C26_MPFB2_PHOTOMETRY" if C27_SURFACE_FIBERS else
     "C26_AFTER_C25_VISUAL_FAIL: PRESERVE_MPFB2_MATURE_SKIN_EYES + LOWER_ENERGY_NEGATIVE_EXPOSURE_PHOTOMETRY + NON_DESTRUCTIVE_FRONTAL_GROOM + LANDMARK_FIBER_BROWS_LASHES; SINGLE_TARGETED_FINALIST" if C26_PHOTOMETRIC else
     "C25_AFTER_C24_STOP_RULE: OFFICIAL_MPFB2_ENHANCED_SSS_AND_PROCEDURAL_EYES + ORIGINAL_CC0_SOURCE_ALBEDO + CURATED_SHORT03_FRINGE_REMOVAL + SINGLE_BOUNDED_HAIRLINE_PLACEMENT; NO_PARAMETER_SWEEP" if C25_MATURE_STACK else
     "C24_AFTER_C23_VISUAL_FAIL: EYE_APERTURES_CALIBRATED_TO_ACTUAL_FACE_SURFACE + SOURCE_ALBEDO_PRESERVED_WITH_MINIMAL_TINT + STRONGER_BOUNDED_FRONTAL_SHORT03_PLACEMENT; PRESERVE_OBJECT_METER_SKIN" if (C24_SURFACE_EYES or C24_SOURCE_ALBEDO or C24_HAIRLINE_REPAIR) else
     "C23_AFTER_C22_VISUAL_FAIL: REPLACE_MISFITTING_HIGH_POLY_EYE_ASSET_WITH_CALIBRATED_LANDMARK_EYES + STRONGER_FRONTAL_BULK_HAIRLINE_PLACEMENT + LANDMARK_BROW_LASH_FIBERS + TARGETED_FACE_PLANES; PRESERVE_OBJECT_METER_SKIN" if (C23_CALIBRATED_EYES or C23_HAIRLINE_REPAIR or C23_FACE_PLANES) else
     "C22_AFTER_C21_HUMAN_VISUAL_FAIL: PHYSICAL_OBJECT_SPACE_SKIN_SCALE + LANDMARK_ANCHORED_BROW_LASH_LID_INTERFACES + FRONTAL_BULK_GROOM_WARP; SINGLE_TARGETED_FINALIST" if (C22_PHYSICAL_SKIN or C22_LANDMARK_GROOM or C22_HAIR_MASS_WARP) else
     "C21_AFTER_C20_BREAKTHROUGH: REPLACE_COMB_HAIRLINE_AND_DRAWN_BROWS_WITH_SPARSE_IRREGULAR_MICROHAIRS; PRESERVE_C20_SKIN_DEPTH_BASELINE" if C21_NATURAL_DETAIL else
     "C20_AFTER_C19_VISUAL_FAIL: EXPLICIT_BROW_LASH_GEOMETRY + FRONTAL_HAIRLINE_BRIDGE + LOWER_EXPOSURE_DIRECTIONAL_FACE_LIGHT + STRONGER_MESO_MICRO_SKIN" if C20_VISUAL_REPAIR else
     "C19_HUMANIZATION_AFTER_C18_VISUAL_FAIL: LOWER_CENTER_HAIRLINE + STRONGER_BROW_LASH_READ + FACE_TARGETED_PHOTO_LIGHTING + LOWER_SSS_HIGHER_ROUGHNESS_MULTISCALE_SKIN" if C19_HUMANIZATION else
     "C18_MATURE_FIRST_HYBRID: FITTED_SHORT03_BULK_COVERAGE + BOUNDED_HAIR_CURVE_ACCENTS + FACE_CLEARANCE + SEPARATED_SKIN_CHANNELS" if C18_HYBRID_BULK else
     "C17_5_VISUAL_FAIL_NEAREST_SHELL_TARGET_FALSIFIED; OFFICIAL_SHORT03_UV_TEXTURE_FLOW_TO_3D_K8_FIELD; DENSITY_FROZEN_FOR_CAUSAL_AB"
   ),
   "skin_albedo_saturation":SKIN_ALBEDO_SAT,
   "skin_albedo_value":SKIN_ALBEDO_VALUE,
   "eye_texture_saturation":EYE_TEX_SAT,
   "eye_texture_value":EYE_TEX_VALUE,
   "hair_texture_saturation":HAIR_TEX_SAT,
   "hair_texture_value":HAIR_TEX_VALUE,
   "face_meso_scale":FACE_MESO_SCALE,
   "skin_tone_rgb":[SKIN_TONE_R,SKIN_TONE_G,SKIN_TONE_B],
   "skin_tone_mix":SKIN_TONE_MIX,
   "skin_micro_strength":SKIN_MICRO_STRENGTH,
   "hair_card_specular":0.16,
   "hair_card_coat":0.004,
   "hair_card_roughness":0.54,
   "hair_card_anisotropy":0.34,
   "hair_asset_key":HAIR_ASSET_KEY,
   "c19_humanization":C19_HUMANIZATION,
   "c19_photo_lighting":C19_PHOTO_LIGHTING,
   "c19_hairline_center_z":C19_HAIRLINE_CENTER_Z if C19_HUMANIZATION else None,
   "c19_hairline_temple_rise":C19_HAIRLINE_TEMPLE_RISE if C19_HUMANIZATION else None,
   "c20_visual_repair":C20_VISUAL_REPAIR,
   "c20_hairline_bridge_curves":c20_hairline_curve_count,
   "c20_brow_curves":c20_brow_curve_count,
   "c20_lash_curves":c20_lash_curve_count,
   "c21_natural_detail":C21_NATURAL_DETAIL,
   "c21_brow_hairs":c21_brow_hair_count,
   "c21_lash_hairs":c21_lash_hair_count,
   "c21_hairline_baby_hairs":c21_hairline_baby_count,
   "c21_temple_flyaways":c21_temple_flyaway_count,
   "c22_physical_skin":C22_PHYSICAL_SKIN,
   "c22_skin_coordinate_space":skin_asset.get("coordinate_space"),
   "c22_landmark_groom":C22_LANDMARK_GROOM,
   "c22_hair_mass_warp":C22_HAIR_MASS_WARP,
   "c22_hair_mass_warp_vertices":c22_hair_mass_warp_vertices,
   "c22_brow_fibers":c22_brow_fiber_count,
   "c22_lash_fibers":c22_lash_fiber_count,
   "c22_lid_margin_curves":c22_lid_margin_curve_count,
   "c23_calibrated_eyes":C23_CALIBRATED_EYES,
   "c23_eye_count":c23_eye_count,
   "c23_eye_contract":c23_eye_contract,
   "c23_face_planes":C23_FACE_PLANES,
   "c23_hairline_repair":C23_HAIRLINE_REPAIR,
   "c23_hairline_warp_vertices":c23_hairline_warp_vertices,
   "c23_brow_fibers":c23_brow_fiber_count,
   "c23_lash_fibers":c23_lash_fiber_count,
   "c23_hairline_fibers":c23_hairline_fiber_count,
   "c24_surface_eyes":C24_SURFACE_EYES,
   "c24_source_albedo":C24_SOURCE_ALBEDO,
   "c24_hairline_repair":C24_HAIRLINE_REPAIR,
   "c24_eye_count":c24_eye_count,
   "c24_eye_contract":c24_eye_contract,
   "c24_lid_curve_count":c24_lid_curve_count,
   "c24_hairline_warp_vertices":c24_hairline_warp_vertices,
   "c25_mature_stack":C25_MATURE_STACK,
   "c25_mpfb2_commit":C25_MPFB2_COMMIT or None,
   "c25_mpfb_skin":c25_mpfb_skin,
   "c25_mpfb_eyes":c25_mpfb_eyes,
   "c25_groom_clip":C25_GROOM_CLIP,
   "c25_removed_fringe_faces":c25_removed_fringe_faces,
   "c25_hairline_warp_vertices":c25_hairline_warp_vertices,
   "c26_photometric":C26_PHOTOMETRIC,
   "c26_safe_groom":C26_SAFE_GROOM,
   "c26_fiber_groom":C26_FIBER_GROOM,
   "c26_fringe_clear_vertices":c26_fringe_clear_vertices,
   "c26_hairline_warp_vertices":c26_hairline_warp_vertices,
   "c26_brow_fibers":c26_brow_fiber_count,
   "c26_lash_fibers":c26_lash_fiber_count,
   "c26_exposure":-0.62 if C26_PHOTOMETRIC else None,
   "c26_world_strength":0.022 if C26_PHOTOMETRIC else None,
   "c27_surface_fibers":C27_SURFACE_FIBERS,
   "c27_native_interfaces":C27_NATIVE_INTERFACES,
   "c27_official_anatomy":geom.get("c27_official_anatomy"),
   "c28_gnm_head":C28_GNM_HEAD,
   "c28_gnm_contract":c28_gnm,
   "c29_gnm_presentation":C29_GNM_PRESENTATION,
   "c29_calibrated_iris_count":c29_iris_count,
   "c29_bulk_hair_hidden":bool(C29_GNM_PRESENTATION),
   "c30_gnm_semantic_identity":C30_GNM_SEMANTIC_IDENTITY,
   "c30_identity_source":c28_gnm.get("identity_source"),
   "c30_semantic_gender":c28_gnm.get("semantic_gender"),
   "c30_semantic_ethnicity":c28_gnm.get("semantic_ethnicity"),
   "c31_gnm_face_appearance":C31_GNM_FACE_APPEARANCE,
   "c32_gnm_dermal_hair":C32_GNM_DERMAL_HAIR,
   "c31_mask_vertex_count":c31_mask_vertex_count,
   "c31_wetline_count":c31_wetline_count,
   "c31_mouth_gap_count":c31_mouth_gap_count
 },
 "scalp_shadow_polygons":scalp_shadow_polygons,
 "drive_compute_priors":geom["drive_compute_priors"],
 "skin_albedo":skin_asset,
 "skin_model":{"subsurface_method":"MPFB2_ENHANCED_SSS" if C25_MATURE_STACK else "RANDOM_WALK_SKIN","subsurface_weight":SKIN_SSS_WEIGHT if not C25_MATURE_STACK else None,"subsurface_scale":SKIN_SSS_SCALE if not C25_MATURE_STACK else None,"subsurface_anisotropy":SKIN_SSS_ANISO if not C25_MATURE_STACK else None,"roughness_range":[SKIN_ROUGH_MIN,SKIN_ROUGH_MAX] if not C25_MATURE_STACK else None,"micro_bump_scales":[SKIN_MESO_FREQ,SKIN_PORE_FREQ,SKIN_MICRO_FREQ] if not C25_MATURE_STACK else None,"bump_distance":SKIN_BUMP_DISTANCE if not C25_MATURE_STACK else None,"coat_weight":SKIN_COAT_WEIGHT if not C25_MATURE_STACK else None,"coat_roughness":SKIN_COAT_ROUGHNESS if not C25_MATURE_STACK else None,"coordinate_space":skin_asset.get("coordinate_space"),"c25_mpfb2":c25_mpfb_skin},
 "hair_curve_count":len(strands),
 "hair_guide":geom["hair_guide"],
 "hair_curve_metrics":hair_curve_metrics,
 "render_curve_shape":"CYLINDER",
 "provenance":{
   "source_pixels_used":False,
   "reference_pixels_read_by_renderer":False,
   "reference_images_composited":False,
   "reference_textures_used":False,
   "external_skin_texture_used":skin_asset["enabled"],
   "external_skin_texture_sha256":skin_asset["sha256"],
   "external_skin_texture_license":"CC0" if skin_asset["enabled"] else None,
   "external_skin_texture_pack_sha256":"7495ab99287053bd19ff1636114e64b608994d9f7437fea6cc75ea387f96dba9" if skin_asset["enabled"] else None,
   "external_system_asset_used":True,
   "external_system_asset_pack_sha256":system_contract["pack_sha256"],
   "external_system_asset_license":system_contract["license"],
   "external_guide_texture_flow_used":True,
   "external_guide_texture_flow_sha256":hair_curve_metrics["guide_texture_sha256"],
   "external_guide_texture_flow_method":hair_curve_metrics["guide_field_version"],
   "external_geometry_asset_used":True,
   "external_geometry_asset_license":"CC0-1.0",
   "image_model_calls":0,
   "renderer_network_calls":0
 },
 "outputs":outputs,
 "denoise_ab":{"seed":hero_seed,"samples":hero_samples,"raw_aov":{"file":raw.name,"sha256":sha(raw)},"denoised":{"file":denoised.name,"sha256":sha(denoised)}},
 "scene_sha256":sha(OUT/"DIGE_V8_scene.blend"),
 "evidence_boundary":{"gpu_claim_requires_actual_mode_gpu":True,"hyperreal_certified":False,"identity_bound":False},
 "claim_ceiling":"PRODUCTION_TOPOLOGY_PLUS_CYCLES_PATH_TRACED_CANDIDATE; HYPERREAL_CERTIFICATION_REQUIRES_VISUAL_AND_LHYPER_AUDIT; DEUS_IDENTITY_NOT_BOUND"
}
(OUT/"DIGE_V8_RENDER_RECEIPT.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
print(json.dumps(receipt,sort_keys=True))
