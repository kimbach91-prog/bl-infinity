#!/usr/bin/env python3
import json, os
from pathlib import Path
home=Path(os.getenv('BL_HC_HOME',Path(__file__).resolve().parents[2])).resolve()
required=['00_BOOT_IDENTITY/IDENTITY.json','00_BOOT_IDENTITY/CURRENT.json','02_CONSTITUTION_REASONING/COGNITIVE_CONSTITUTION.md','01_MEMORY_CANON/MEMORY_POLICY.md','04_RUNTIME_ADAPTERS/RUNTIME_CONTRACT.json','05_DEUS_BRIDGE_TASKBUS/BRIDGE_CONTRACT.json','06_EVAL_SHADOW_TEST/EVAL_PROTOCOL.md']
missing=[x for x in required if not (home/x).exists()]
secretish=[]
for p in home.rglob('*'):
 if p.is_file() and any(x in p.name.lower() for x in ('secret','credential','.env')) and p.name!='config.example.env': secretish.append(str(p.relative_to(home)))
print(json.dumps({'agent_id':'BL-HC-01','home':str(home),'required_missing':missing,'secret_like_files':secretish,'model_endpoint_configured':bool(os.getenv('BL_HC_MODEL_ENDPOINT')),'model_name_configured':bool(os.getenv('BL_HC_MODEL_NAME')),'local_token_configured':bool(os.getenv('BL_HC_API_TOKEN')),'ready_for_service_start':not missing},indent=2))
raise SystemExit(0 if not missing else 2)
