from __future__ import annotations
import argparse, hashlib, json, os, re

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
    digest=sha256(args.input)
    with open(args.input,encoding='utf-8') as f:r=json.load(f)
    errors=[]
    if digest!='874fc9b46cd8147184eb906857ed2f7a6cf5a988514fbad52323aaf5d5422915':errors.append('heldout_json_sha_mismatch')
    if r.get('truth_boundary')!='PUBLIC_SOURCEFREE_P5P9_FROZEN_NO_RETRAIN_HELDOUT_ONLY':errors.append('truth_boundary')
    model=r.get('model_source',{})
    if model.get('source_method_commit')!='86206804f93371eb249d2c5a50871bb39bae2c42':errors.append('source_method_commit')
    if model.get('source_run')!=35873876012:errors.append('source_run')
    if model.get('fit_evidence',{}).get('loto_correct')!=861 or model.get('fit_evidence',{}).get('loto_checked')!=861:errors.append('fit_evidence')
    expected_cycle=['065dffac4c588d19','cac698dcf6fb6b76','62a0851c5747bb6e','58498753074a2cd7','b0a3a987438be855','eb1fb214319d2bd3','758df3c6a8125ac1']
    if model.get('phase_cycle')!=expected_cycle:errors.append('phase_cycle')
    if model.get('cursor_delta_mod5')!={'ACTION3':4,'ACTION4':1}:errors.append('cursor_rule')
    rows=r.get('results',[])
    files=[x.get('file') for x in rows]
    if len(rows)!=5 or len(set(files))!=5:errors.append('five_unique_results')
    expected={f'tr87-cd924810_p{i}_events.jsonl' for i in range(5,10)}
    if set(files)!=expected:errors.append('file_set')
    sums={'checked':0,'predicted':0,'correct':0,'abstain':0,'mismatch_count':0}
    safe=0
    per=[]
    for x in rows:
        v=x.get('verification',{});p=x.get('plan',{})
        for k in sums:sums[k]+=int(v.get(k,0))
        if v.get('mismatch_count')!=0:errors.append('per_trace_mismatch:'+str(x.get('file')))
        if v.get('abstain')!=0:errors.append('per_trace_abstain:'+str(x.get('file')))
        if v.get('predicted')!=v.get('checked') or v.get('correct')!=v.get('predicted'):errors.append('per_trace_incomplete:'+str(x.get('file')))
        if p.get('exists') and p.get('final_matches_target') and p.get('under_128'):safe+=1
        else:errors.append('plan_fail:'+str(x.get('file')))
        per.append({'file':x.get('file'),'checked':v.get('checked'),'correct':v.get('correct'),'n_actions':p.get('n_actions'),'offsets':p.get('offsets')})
    agg=r.get('aggregate',{})
    for k,v in sums.items():
        if agg.get(k)!=v:errors.append('aggregate_recompute:'+k)
    if sums!={'checked':713,'predicted':713,'correct':713,'abstain':0,'mismatch_count':0}:errors.append('expected_totals')
    if agg.get('accuracy')!=1.0 or agg.get('coverage')!=1.0:errors.append('aggregate_rates')
    if safe!=5 or agg.get('safe_plan_exists_traces')!=5 or agg.get('total_traces')!=5:errors.append('safe_plan_count')
    audit={'audit':'R335_P5P9_HELDOUT_ARTIFACT_INDEPENDENT_AUDIT_V1','input_sha256':digest,'independent_recomputed_totals':sums,'safe_plan_count':safe,'per_trace':per,'errors':errors,'verdict':'PASS' if not errors else 'FAIL','promotion_boundary':'PUBLIC_OFFLINE representation/action-mechanism audit only; no whole-game/provider/Kaggle promotion'}
    with open(args.out,'w',encoding='utf-8') as f:json.dump(audit,f,indent=2,sort_keys=True)
    print(json.dumps({'verdict':audit['verdict'],'totals':sums,'safe_plan_count':safe,'errors':errors},sort_keys=True))
    if errors:raise SystemExit(2)

if __name__=='__main__':main()
