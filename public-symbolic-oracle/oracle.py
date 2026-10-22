"""Bounded exact polynomial and affine-system verification, standard library only."""
import ast,json,re
from fractions import Fraction as Q
OPS={'expand_expression','differentiate','integrate_expression','factor_polynomial','solve_linear_system'}
def need(x,c):
    if not x:raise ValueError(c)
class Algebra:
    def __init__(self,variables):
        need(type(variables)is list and 1<=len(variables)<=32 and len(set(variables))==len(variables) and all(type(v)is str and re.fullmatch('[a-z][a-z0-9_]{0,7}',v) and '__'not in v for v in variables),'VARIABLES_BOUND')
        self.variables=variables;self.zero=(0,)*len(variables);self.cost=0
    def clean(self,p):
        p={k:v for k,v in p.items() if v};need(len(p)<=256 and all(sum(k)<=8 and max(k)<=8 and v.numerator.bit_length()<=512 and v.denominator.bit_length()<=512 for k,v in p.items()),'POLYNOMIAL_WORK_BOUND');return p
    def add(self,a,b):
        out=a.copy()
        for k,v in b.items():out[k]=out.get(k,Q(0))+v
        return self.clean(out)
    def mul(self,a,b):
        self.cost+=len(a)*len(b);need(self.cost<=65536,'ORACLE_OPERATION_BOUND');out={}
        for ka,va in a.items():
            for kb,vb in b.items():k=tuple(x+y for x,y in zip(ka,kb));out[k]=out.get(k,Q(0))+va*vb
        return self.clean(out)
    def poly(self,text):
        need(type(text)is str and 1<=len(text)<=4096,'EXPRESSION_LENGTH');tree=ast.parse(text,mode='eval');need(len(list(ast.walk(tree)))<=2048,'AST_BOUND')
        def go(n):
            if isinstance(n,ast.Constant) and type(n.value)is int:
                need(n.value.bit_length()<=128,'INTEGER_BIT_BOUND');return self.clean({self.zero:Q(n.value)})
            if isinstance(n,ast.Name) and n.id in self.variables:
                e=list(self.zero);e[self.variables.index(n.id)]=1;return {tuple(e):Q(1)}
            if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.USub,ast.UAdd)):
                p=go(n.operand);return {k:(-v if isinstance(n.op,ast.USub) else v) for k,v in p.items()}
            if isinstance(n,ast.BinOp):
                a=go(n.left)
                if isinstance(n.op,ast.Pow):
                    need(isinstance(n.right,ast.Constant) and type(n.right.value)is int and 0<=n.right.value<=8,'EXPONENT_BOUND');out={self.zero:Q(1)}
                    for _ in range(n.right.value):out=self.mul(out,a)
                    return out
                b=go(n.right)
                if isinstance(n.op,ast.Add):return self.add(a,b)
                if isinstance(n.op,ast.Sub):return self.add(a,{k:-v for k,v in b.items()})
                if isinstance(n.op,ast.Mult):return self.mul(a,b)
                if isinstance(n.op,ast.Div):
                    need(set(b)=={self.zero} and b[self.zero]!=0,'CONSTANT_DIVISOR');return self.clean({k:v/b[self.zero] for k,v in a.items()})
            raise ValueError('POLYNOMIAL_AST_ONLY')
        return go(tree.body)
    def diff(self,p,var):
        need(var in self.variables,'DIFFERENTIATION_VARIABLE');i=self.variables.index(var);out={}
        for k,v in p.items():
            if k[i]:e=list(k);e[i]-=1;out[tuple(e)]=v*k[i]
        return self.clean(out)
    def affine(self,text,variables):
        p=self.poly(text);need(all(sum(k)<=1 for k in p),'LINEAR_ONLY');row=[]
        for v in variables:
            e=list(self.zero);e[self.variables.index(v)]=1;row.append(p.pop(tuple(e),Q(0)))
        const=p.pop(self.zero,Q(0));need(not p,'UNDECLARED_SYSTEM_UNKNOWNS');return row,const
def full_column_rank(matrix,n):
    a=[row.copy() for row in matrix];rank=0
    for j in range(n):
        pivot=next((i for i in range(rank,len(a)) if a[i][j]),None)
        if pivot is None:continue
        a[rank],a[pivot]=a[pivot],a[rank];v=a[rank][j];a[rank]=[x/v for x in a[rank]]
        for i in range(rank+1,len(a)):
            v=a[i][j]
            if v:a[i]=[x-v*y for x,y in zip(a[i],a[rank])]
            need(all(x.numerator.bit_length()<=512 and x.denominator.bit_length()<=512 for x in a[i]),'RANK_WORK_BOUND')
        rank+=1
    return rank==n
def prepare(variables,name,args):
    a=Algebra(variables);need(name in OPS and type(args)is dict,'SUPPORTED_OPERATION')
    if name=='solve_linear_system':
        need(set(args)=={'system','variables'} and type(args['variables'])is list and 1<=len(args['variables'])<=16 and len(set(args['variables']))==len(args['variables']) and set(args['variables']).issubset(variables),'SYSTEM_VARIABLES')
        need(type(args['system'])is list and len(args['variables'])<=len(args['system'])<=32,'SYSTEM_ROWS');rows=[a.affine(x,args['variables']) for x in args['system']];need(full_column_rank([r for r,c in rows],len(args['variables'])),'UNIQUE_SOLUTION_REQUIRED');need(not full_column_rank([r+[-c] for r,c in rows],len(args['variables'])+1),'CONSISTENT_SYSTEM_REQUIRED')
    else:
        key='poly' if name=='factor_polynomial' else 'expr';expected={key,'variable'} if name in ['differentiate','integrate_expression'] else {key};need(set(args)==expected,'EXACT_ARGUMENT_FIELDS');a.poly(args[key]);need('variable'not in args or args['variable']in variables,'DECLARED_VARIABLE')
    need(len(json.dumps(args))<=12000,'REQUEST_ARGUMENT_BOUND');return True
def verify(variables,name,args,value):
    prepare(variables,name,args);a=Algebra(variables)
    if name=='solve_linear_system':
        need(type(value)is list and len(value)==1 and type(value[0])is str,'UNIQUE_SYSTEM_RESULT_SHAPE');tree=ast.parse(value[0],mode='eval');need(isinstance(tree.body,(ast.Tuple,ast.List)) and len(tree.body.elts)==len(args['variables']),'SYSTEM_VECTOR_LENGTH');vec=[]
        for n in tree.body.elts:
            p=a.poly(ast.unparse(n));need(set(p).issubset({a.zero}),'CONSTANT_SYSTEM_RESULT');vec.append(p.get(a.zero,Q(0)))
        for text in args['system']:
            row,c=a.affine(text,args['variables']);need(sum((v*x for v,x in zip(row,vec)),c)==0,'EXACT_LINEAR_RESIDUAL')
        return {'state':'PASS_EXACT_UNIQUE_AFFINE_SYSTEM','coordinates':len(vec),'zero_residuals':len(args['system'])}
    key='poly' if name=='factor_polynomial' else 'expr';original=a.poly(args[key]);returned=a.poly(value)
    if name=='differentiate':need(returned==a.diff(original,args['variable']),'EXACT_DERIVATIVE')
    elif name=='integrate_expression':need(a.diff(returned,args['variable'])==original,'EXACT_ANTIDERIVATIVE')
    else:need(returned==original,'EXACT_POLYNOMIAL_IDENTITY')
    return {'state':'PASS_EXACT_POLYNOMIAL_ORACLE','operation':name,'input_terms':len(original),'output_terms':len(returned),'factor_irreducibility_proven':False}
