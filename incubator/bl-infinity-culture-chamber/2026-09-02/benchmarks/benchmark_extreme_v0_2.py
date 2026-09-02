#!/usr/bin/env python3
"""BL∞ Culture Chamber Extreme Benchmark v0.2

Synthetic, reproducible stress test. This is NOT evidence of consciousness,
biological reflexes, physical retrocausality, or real-world safety.
"""
import json, time
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

TRAIN_SEEDS=[11,29,47,83]
TEST_SEEDS=[131,197,251,313]
OOD_SEEDS=[401,409,419,431]
N=100_000
ENV_NAMES=["stable","sensor_spoof","hidden_toxin","causal_drift","delayed_harm","false_safe","resource_exhaustion","compound_trap"]

def sigmoid(x):
    return 1/(1+np.exp(-np.clip(x,-30,30)))

def generate(seed,n=N):
    rng=np.random.default_rng(seed); env=rng.integers(0,8,size=n); context=rng.normal(size=(n,4)); base=rng.normal(size=n)
    novelty=rng.beta(2,5,size=n); hidden=rng.normal(size=n); resource=np.clip(rng.normal(0.62,0.18,size=n),0,1)
    z=1.1*base+0.65*context[:,0]-0.45*context[:,1]+0.55*novelty+0.25*hidden
    z+=np.where(env==2,1.15*(hidden>0.4),0); z+=np.where(env==3,-1.1*context[:,0]+0.9*context[:,2],0)
    z+=np.where(env==4,0.65*context[:,3],0); z+=np.where(env==5,1.25*(base<-0.3),0)
    z+=np.where(env==6,0.7*(resource<0.35),0); z+=np.where(env==7,0.8*(hidden>0)+0.8*(context[:,2]>0.2)-0.55*context[:,1],0)
    p=sigmoid(z-0.2); danger=rng.random(n)<p
    obs=z+rng.normal(0,0.8,size=n); obs+=np.where(env==1,rng.normal(0,1.5,size=n),0)
    obs+=np.where(env==2,-0.9*danger,0); obs+=np.where(env==5,-1.35*danger,0); obs+=np.where(env==7,rng.normal(-0.25,1.0,size=n),0)
    asymmetric=danger & np.isin(env,[2,7])
    return dict(env=env,context=context,base=base,novelty=novelty,hidden=hidden,resource=resource,z=z,p_danger=p,danger=danger.astype(int),obs=obs,asymmetric=asymmetric.astype(int),outcome_u=rng.random(n))

def generate_ood(seed,scenario,n=80_000):
    rng=np.random.default_rng(seed); context=rng.normal(size=(n,4)); base=rng.normal(size=n); novelty=rng.beta(2.3,4.5,size=n); hidden=rng.normal(size=n); resource=np.clip(rng.normal(0.50,0.22,size=n),0,1)
    env=np.full(n,7 if scenario in ("silent_poison","compound_new") else (3 if scenario=="rule_flip" else 1),dtype=int)
    if scenario=="silent_poison":
        z=0.35*base+0.15*context[:,0]+1.8*(hidden>0.15)+0.6*novelty-0.2; danger=rng.random(n)<sigmoid(z); obs=0.25*base+rng.normal(-0.9*danger,0.55,size=n); asymmetric=danger&(hidden>0.15)
    elif scenario=="rule_flip":
        z=-0.9*base-0.95*context[:,0]+0.75*context[:,1]-0.65*context[:,2]+0.7*novelty; danger=rng.random(n)<sigmoid(z); obs=0.8*base+0.55*context[:,0]+rng.normal(0,0.7,size=n); asymmetric=danger&(rng.random(n)<0.12)
    elif scenario=="sensor_blackout":
        z=0.45*base+0.95*context[:,2]+0.7*context[:,3]+0.5*novelty; danger=rng.random(n)<sigmoid(z); obs=rng.normal(0,0.18,size=n); asymmetric=danger&(rng.random(n)<0.10)
    elif scenario=="compound_new":
        z=0.6*base-0.4*context[:,0]+0.8*context[:,3]+1.0*(hidden>0.5)+0.9*(resource<0.3)+0.5*novelty; danger=rng.random(n)<sigmoid(z); obs=0.35*z+rng.normal(-0.7*danger,1.15,size=n); asymmetric=danger&((hidden>0.5)|(resource<0.25))
    else: raise ValueError(scenario)
    return dict(env=env,context=context,base=base,novelty=novelty,hidden=hidden,resource=resource,z=z,p_danger=sigmoid(z),danger=danger.astype(int),obs=obs,asymmetric=asymmetric.astype(int),outcome_u=rng.random(n))

def slice_data(d,sl):
    n=len(d["danger"]); return {k:(v[sl] if isinstance(v,np.ndarray) and v.shape[0]==n else v) for k,v in d.items()}

def evaluate(d,policy):
    action,conf=policy(d); y=d["danger"]; env=d["env"]; res=d["resource"]; asym=d["asymmetric"]; u=d["outcome_u"]
    success=np.zeros(len(y),dtype=bool); cat=np.zeros(len(y),dtype=bool); cost=np.where(action==1,0.06,np.where(action==2,0.13,0.0)); safe=y==0; danger=y==1; success[safe]=True
    p0=np.where(asym==1,0.92,0.72); p0=np.where(env==4,np.maximum(p0,0.78),p0); p0=np.where(env==7,np.maximum(p0,0.88),p0)
    m=danger&(action==0); f=m&(u<p0); success[m]=~f[m]; cat|=f&((asym==1)|(env==7)|(env==4))
    p1=np.where(asym==1,0.80,0.88); p1=np.where(env==1,p1-0.05,p1); p1=np.where(env==7,p1-0.08,p1)
    m=danger&(action==1); s=m&(u<p1); success[m]=s[m]; cat|=m&~s&(asym==1)&(u>0.97)
    p2=np.where(asym==1,0.97,0.95); p2=np.where((env==6)&(res<0.25),0.88,p2)
    m=danger&(action==2); s=m&(u<p2); success[m]=s[m]; cat|=m&~s&(asym==1)&(u>0.995)
    exhaustion=(env==6)&(res<0.18)&(action==2)&(u<0.10); success[exhaustion]=False
    reward=success.astype(float)-0.6*cost-4.0*cat.astype(float); oracle=np.where(y==0,0,np.where(asym==1,2,1)); oracle_cost=np.where(oracle==1,0.06,np.where(oracle==2,0.13,0)); regret=(np.ones(len(y))-0.6*oracle_cost)-reward
    pred=(action>0).astype(int); tp=((pred==1)&(y==1)).sum(); tn=((pred==0)&(y==0)).sum(); fp=((pred==1)&(y==0)).sum(); fn=((pred==0)&(y==1)).sum(); precision=tp/max(tp+fp,1); recall=tp/max(tp+fn,1); f1=2*precision*recall/max(precision+recall,1e-12)
    return dict(success_rate=float(success.mean()),loss_rate=float(1-success.mean()),catastrophic_rate=float(cat.mean()),protective_accuracy=float((tp+tn)/len(y)),f1=float(f1),mean_regret=float(regret.mean()),mean_cost=float(cost.mean()),probe_rate=float((action==1).mean()),defend_rate=float((action==2).mean()),safe_intervention_rate=float((action[safe]>0).mean()),danger_inaction_rate=float((action[danger]==0).mean()),mean_conf=float(np.mean(conf)))

def p_r0(d):
    s=d["obs"]; return np.where(s>1.2,2,np.where(s>0.55,1,0)),sigmoid(np.abs(s))
def p_r1(d):
    s=0.9*d["obs"]+0.45*d["context"][:,0]-0.2*d["context"][:,1]+0.25*d["novelty"]; return np.where(s>1.35,2,np.where(s>0.45,1,0)),sigmoid(np.abs(s))
def p_r2(d):
    c=d["context"]; s=0.72*d["obs"]+0.40*c[:,0]-0.15*c[:,1]+0.32*c[:,2]+0.20*c[:,3]+0.42*d["novelty"]+0.48*np.exp(-np.abs(d["obs"]))*d["novelty"]; return np.where(s>1.25,2,np.where(s>0.30,1,0)),sigmoid(np.abs(s)+0.2*d["novelty"])
def p_r3(d):
    c=d["context"]; obs=d["obs"]; nov=d["novelty"]; res=d["resource"]; base=0.62*obs+0.28*c[:,0]-0.10*c[:,1]+0.26*c[:,2]+0.15*c[:,3]+0.35*nov; ss=((obs<0)&(nov>0.45)).astype(float); trap=0.75*nov+0.55*np.abs(c[:,2])+0.75*ss+0.45*(res<0.3); score=base+0.65*trap; dt=np.where(res<0.22,1.75,1.35); pt=np.where(res<0.22,0.65,0.35); return np.where(score>dt,2,np.where(score>pt,1,0)),sigmoid(np.abs(score)+0.3*trap)
def r4_components(d):
    c=d["context"]; obs=d["obs"]; nov=d["novelty"]; res=d["resource"]; expected=0.5*c[:,0]-0.2*c[:,1]+0.25*c[:,2]; mismatch=np.abs(obs-expected); fs=((obs<0.15)&(nov>0.35)&(mismatch>0.8)).astype(float); base=0.55*obs+0.22*c[:,0]-0.08*c[:,1]+0.28*c[:,2]+0.18*c[:,3]+0.30*nov; trap=0.55*mismatch+0.65*fs+0.40*nov+0.30*(res<0.28); return base+0.82*trap,trap,mismatch
def p_r4(d):
    causal,trap,mis=r4_components(d); res=d["resource"]; nov=d["novelty"]; dt=1.45+0.45*(res<0.20); pt=0.22-0.12*(nov>0.65)+0.20*(res<0.12); a=np.where(causal>dt,2,np.where(causal>pt,1,0)); a=np.where((a==0)&(nov>0.70)&(res>0.10),1,a); return a,sigmoid(np.abs(causal)+0.35*trap)
def features(d):
    c=d["context"]; obs=d["obs"]; nov=d["novelty"]; res=d["resource"]; expected=0.5*c[:,0]-0.2*c[:,1]+0.25*c[:,2]; mismatch=np.abs(obs-expected); fs=((obs<0.15)&(nov>0.35)&(mismatch>0.8)).astype(float); return np.column_stack([obs,c,nov,res,mismatch,fs])
def train_model():
    ds=[generate(s) for s in TRAIN_SEEDS]; X=np.vstack([features(d) for d in ds]); y=np.concatenate([d["danger"] for d in ds]); rng=np.random.default_rng(20260902); idx=rng.choice(len(y),250_000,replace=False); m=HistGradientBoostingClassifier(max_iter=180,learning_rate=0.08,max_leaf_nodes=31,l2_regularization=0.2,random_state=20260902); m.fit(X[idx],y[idx]); return m,X,y
def ml_policy(model,t1=0.45,t2=0.55):
    def pol(d):
        p=model.predict_proba(features(d))[:,1]; return np.where(p>=t2,2,np.where(p>=t1,1,0)),np.maximum(p,1-p)
    return pol
def fused_policy(model,alpha=0.5,t1=0.48,t2=0.58,tp=1.0,td=1.8):
    def pol(d):
        p=model.predict_proba(features(d))[:,1]; causal,trap,mis=r4_components(d); structural=sigmoid(causal-0.3); risk=alpha*p+(1-alpha)*structural; t2v=t2+0.08*(d["resource"]<0.18); a=np.where((risk>=t2v)|((trap>=td)&(p>=0.42)),2,np.where((risk>=t1)|((trap>=tp)&(p>=0.32)),1,0)); a=np.where((a==0)&(d["novelty"]>0.78)&(mis>1.15)&(d["resource"]>0.12),1,a); return a,np.maximum(risk,1-risk)
    return pol
def mean_metrics(rows):
    return {k:float(np.mean([r[k] for r in rows])) for k in rows[0]}
def main():
    model,X,y=train_model(); policies={"R0_reflex":p_r0,"R1_conditioned":p_r1,"R2_superreflex":p_r2,"R3_survival_radar":p_r3,"R4_full_candidate":p_r4,"ML_HGB_balanced":ml_policy(model),"R5_fused_balanced":fused_policy(model)}
    in_dist={name:mean_metrics([evaluate(generate(seed),pol) for seed in TEST_SEEDS]) for name,pol in policies.items()}
    ood={}
    for sc in ["silent_poison","rule_flip","sensor_blackout","compound_new"]:
        ood[sc]={name:mean_metrics([evaluate(generate_ood(seed,sc),policies[name]) for seed in OOD_SEEDS]) for name in ["R0_reflex","R4_full_candidate","ML_HGB_balanced","R5_fused_balanced"]}
    rng=np.random.default_rng(909); old_idx=rng.choice(len(X),60_000,replace=False); Xold,yold=X[old_idx],y[old_idx]; adaptation={}
    for sc in ["silent_poison","rule_flip","sensor_blackout","compound_new"]:
        fixed=[]; adapted=[]
        for seed in OOD_SEEDS:
            d=generate_ood(seed,sc); first=slice_data(d,slice(0,2500)); rest=slice_data(d,slice(2500,None)); am=HistGradientBoostingClassifier(max_iter=120,learning_rate=0.08,max_leaf_nodes=31,l2_regularization=0.25,random_state=seed); am.fit(np.vstack([Xold,features(first)]),np.concatenate([yold,first["danger"]])); fixed.append(evaluate(rest,policies["R5_fused_balanced"])); adapted.append(evaluate(rest,fused_policy(am)))
        adaptation[sc]={"fixed":mean_metrics(fixed),"adapted_2500":mean_metrics(adapted)}
    print(json.dumps({"benchmark_id":"BL-INF-CC-BENCH-EXTREME-V0.2","status":"REPRODUCIBLE_SYNTHETIC_BENCHMARK","seeds":{"train":TRAIN_SEEDS,"test":TEST_SEEDS,"ood":OOD_SEEDS},"sample_sizes":{"in_distribution_per_seed":N,"ood_per_seed":80000,"adaptation_window":2500},"in_distribution":in_dist,"ood":ood,"adaptation":adaptation},indent=2,ensure_ascii=False))
if __name__=="__main__": main()
