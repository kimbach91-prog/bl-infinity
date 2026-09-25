"""Optional CPU backend acceptance. Synthetic project tests, no network data or grants."""
from __future__ import annotations
import hashlib,json,os,platform,statistics,time
from pathlib import Path
import numpy as np
import scipy.sparse as sp
from scipy.optimize import milp,Bounds,LinearConstraint
from ortools.sat.python import cp_model
import graphblas as gb
from egglog import EGraph,Expr,i64Like,StringLike,vars_,i64,rewrite,ruleset,eq

OUT=Path(os.environ.get('PORTFOLIO_OUT','.deus/operator-portfolio'));OUT.mkdir(parents=True,exist_ok=True)
receipts=[]
def timed(names,check,repeats=7):
    raw={k:[] for k in names}
    for fn in names.values(): assert check(fn())
    for i in range(repeats):
        for name in (list(names) if i%2==0 else list(reversed(names))):
            t=time.perf_counter_ns();value=names[name]();u=time.perf_counter_ns();assert check(value);v=time.perf_counter_ns()
            raw[name].append({'call_ns':u-t,'verify_ns':v-u,'end_to_end_ns':v-t})
    return {'raw':raw,'median_ms':{k:statistics.median(x['call_ns'] for x in v)/1e6 for k,v in raw.items()},'median_e2e_ms':{k:statistics.median(x['end_to_end_ns'] for x in v)/1e6 for k,v in raw.items()},'rounds':repeats}

# Same sparse matrix and output; build/import cost separately visible.
rng=np.random.default_rng(913);n=4096;rows=rng.integers(0,n,32768);cols=rng.integers(0,n,32768);values=rng.normal(size=len(rows));x=rng.normal(size=n)
t=time.perf_counter();a=sp.coo_matrix((values,(rows,cols)),shape=(n,n)).tocsr();csr_setup=(time.perf_counter()-t)*1000
expected=a@x
t=time.perf_counter();g=gb.io.from_scipy_sparse(a);vx=gb.Vector.from_dense(x);gb_setup=(time.perf_counter()-t)*1000
try:gb.ss.config['nthreads']=2
except (AttributeError,KeyError,TypeError):pass
b=timed({'scipy_csr':lambda:a@x,'graphblas_mxv':lambda:g.mxv(vx).new().to_dense(fill_value=0)},lambda o:bool(np.allclose(o,expected,rtol=1e-11,atol=1e-11)))
receipts.append({'family':'GRAPHBLAS','state':'EXECUTED_CPU_SCOPED','shape':[n,n],'nnz':int(a.nnz),'csr_setup_ms':csr_setup,'graphblas_import_ms':gb_setup,'benchmark':b,'output_sha256':hashlib.sha256(expected.tobytes()).hexdigest()})

# Independent job assignment, same makespan objective; no real scheduler action.
durations=[3,3,2,2,2,9,9,7,7,5,5,4];m=3;nj=len(durations)
def greedy():
    loads=[0]*m;assignment=[0]*nj
    for j in sorted(range(nj),key=lambda j:-durations[j]):
        i=min(range(m),key=lambda i:loads[i]);assignment[j]=i;loads[i]+=durations[j]
    return {'assignment':assignment,'makespan':max(loads),'optimal':False}
def cpsat():
    model=cp_model.CpModel();xx=[[model.new_bool_var(f'x{j}_{i}') for i in range(m)] for j in range(nj)]
    for row in xx:model.add_exactly_one(row)
    c=model.new_int_var(max(durations),sum(durations),'makespan')
    for i in range(m):model.add(sum(durations[j]*xx[j][i] for j in range(nj))<=c)
    model.minimize(c);solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=2;solver.parameters.num_search_workers=2;solver.parameters.random_seed=913
    status=solver.solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return {**greedy(),'fallback':True,'status':int(status)}
    return {'assignment':[next(i for i in range(m) if solver.value(xx[j][i])) for j in range(nj)],'makespan':solver.value(c),'optimal':status==cp_model.OPTIMAL,'status':int(status)}
def verify_schedule(o):
    return bool(len(o['assignment'])==nj and all(type(i)is int and 0<=i<m for i in o['assignment']) and o['makespan']==max(sum(d for d,i in zip(durations,o['assignment']) if i==k) for k in range(m)))
b=timed({'greedy':greedy,'cp_sat':cpsat},verify_schedule)
receipts.append({'family':'CP_SAT','state':'EXECUTED_CPU_SCOPED','benchmark':b,'greedy':greedy(),'cp_sat':cpsat(),'actual_resource_grants':0})

# Restricted exact integer rewrite equality; distinguish backend execution from speedup.
class Num(Expr):
    def __init__(self,value:i64Like)->None: ...
    @classmethod
    def var(cls,name:StringLike)->Num: ...
    def __add__(self,other:Num)->Num: ...
    def __mul__(self,other:Num)->Num: ...
a0,b0,c0=vars_('a b c',Num);i,j=vars_('i j',i64)
rules=ruleset(rewrite(a0+b0).to(b0+a0),rewrite(a0*(b0+c0)).to(a0*b0+a0*c0),rewrite(Num(i)+Num(j)).to(Num(i+j)),rewrite(Num(i)*Num(j)).to(Num(i*j)))
def eggcheck():
    graph=EGraph();lhs=Num(2)*(Num.var('x')+Num(3));rhs=Num(6)+Num(2)*Num.var('x');graph.register(lhs,rhs);graph.run(rules*10);graph.check(eq(lhs).to(rhs));return True
b=timed({'egglog_construct_saturate_check':eggcheck},lambda v:v is True)
receipts.append({'family':'EGGLOG','state':'EXECUTED_CPU_SCOPED','benchmark':b,'scope':'fixed integer rewrite congruence; no global optimizer/performance claim'})

import importlib.metadata as md
payload={'schema':'deus-scientific-backend-acceptance/1','state':'PASS_FOR_THREE_BOUNDED_BACKENDS','python':platform.python_version(),'versions':{k:md.version(k) for k in ['numpy','scipy','ortools','python-graphblas','egglog']},'receipts':receipts,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'gpu_executed':False,'production_adopted':False,'limitations':['Synthetic finite contracts; not a real Internet recrawl','GraphBLAS imports are included only in setup measurements','CP-SAT solves independent assignment, not a live multi-host schedule','No native Differential Dataflow, CUDA or whole-system capacity claim']}
(OUT/'scientific-backends.json').write_text(json.dumps(payload,indent=2));print(json.dumps(payload))
