"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const close=(a,b,eps=1e-10)=>Math.abs(a-b)<eps;
const n=Math.pow(3,4),tree=[0,1,2,3,4].reduce((a,i)=>a+Math.pow(3,i),0);
assert.equal(n,81);assert.equal(tree,121);
const M=[[0,1,0],[0,0,1],[0,0,0]];
const sq=(i,j)=>[0,1,2].reduce((sum,k)=>sum+M[i][k]*M[k][j],0);
assert.equal(sq(0,2),1);
const posterior=(.8*.2)/(.8*.2+.1*.8);
assert(close(posterior,2/3));
const ent=p=>-p*Math.log2(p)-(1-p)*Math.log2(1-p);
assert(close(ent(.5),1));assert(close(ent(2/3),.9182958340544896));
for(const [path,markers] of [
  ["theory.html",["3⁴ = 81","= 121","P(H | E)","0,918"]],
  ["en/theory/index.html",["3⁴ = 81","= 121","P(H | E)","0.918"]],
  ["zh/theory/index.html",["3⁴ = 81","= 121","P(H | E)","0.918"]]
]){
 const html=fs.readFileSync(path,"utf8");
 for(const marker of markers)assert(html.includes(marker),path+" illustrated calculation missing "+marker);
 assert(html.includes("publication-gate") && html.includes("UNKNOWN"),path+" context missing");
}
console.log("B_INFINITY_PUBLIC_PRETHEORY_CALCULATIONS_PASS",n,tree,posterior,ent(2/3));
