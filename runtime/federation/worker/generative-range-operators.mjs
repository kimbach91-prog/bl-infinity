/** Public integer arithmetic progression example, not a private kernel or a
 * universal accelerator. Eight explicit lanes, bounded sparse exceptions.
 * No network, filesystem, eval, dense arrays, physical resource claims or imports.
 */
const LIMIT=1000000000000n;
function integer(x){if(typeof x!=='string'||! /^-?(0|[1-9][0-9]*)$/.test(x)||x.length>64)throw Error('INTEGER_STRING_REQUIRED');return BigInt(x);}
function onlyKeys(x,keys){if(!x||typeof x!=='object'||Array.isArray(x)||Object.keys(x).some(k=>!keys.includes(k)))throw Error('UNSUPPORTED_DESCRIPTOR');}
export function decodeRange(d){
 onlyKeys(d,['schema','start','count','lanes','exceptions']);if(d.schema!=='affine-integer-range/1')throw Error('UNSUPPORTED_DESCRIPTOR');
 const start=integer(d.start),count=integer(d.count);if(start<0n||count<1n||start+count>LIMIT)throw Error('RANGE_LIMIT');
 if(!Array.isArray(d.lanes)||d.lanes.length!==8)throw Error('EIGHT_LANES_REQUIRED');
 const lanes=d.lanes.map(x=>{onlyKeys(x,['a','b']);return {a:integer(x.a),b:integer(x.b)};});
 if(!Array.isArray(d.exceptions)||d.exceptions.length>64)throw Error('SPARSE_EXCEPTION_LIMIT');const seen=new Set();
 const exceptions=d.exceptions.map(x=>{onlyKeys(x,['index','lane','value']);const index=integer(x.index);if(index<start||index>=start+count||!Number.isInteger(x.lane)||x.lane<0||x.lane>=8)throw Error('EXCEPTION_RANGE');const key=index+'|'+x.lane;if(seen.has(key))throw Error('DUPLICATE_EXCEPTION');seen.add(key);return {index,lane:x.lane,value:integer(x.value)};});
 return {start,count,lanes,exceptions};
}
export function reconstructCell(d,index){const p=decodeRange(d),i=integer(index);if(i<p.start||i>=p.start+p.count)throw Error('CELL_OUTSIDE_RANGE');const values=p.lanes.map(x=>x.a*i+x.b);for(const e of p.exceptions)if(e.index===i)values[e.lane]=e.value;return values.map(String);}
export function affineRangeSummary(input){
 const {start,count,lanes,exceptions}=decodeRange(input.value);const ordinal=count*(2n*start+count-1n)/2n;
 const sums=lanes.map(x=>x.a*ordinal+x.b*count);for(const e of exceptions)sums[e.lane]+=e.value-(lanes[e.lane].a*e.index+lanes[e.lane].b);
 return {schema:'affine-range-summary/1',start:String(start),count:String(count),laneSums:sums.map(String),sum:String(sums.reduce((a,b)=>a+b,0n)),semantics:'EXACT_INTEGER_AFFINE_PLUS_SPARSE_EXCEPTIONS_NOT_DENSE_ARBITRARY_STATE'};
}
export function reduceAffineRanges(input){
 const v=Object.values(input.upstream);if(!v.length||v.length>64)throw Error('BOUNDED_CHILDREN_REQUIRED');
 const normalized=v.map(x=>{if(x.schema!=='affine-range-summary/1'||x.semantics!=='EXACT_INTEGER_AFFINE_PLUS_SPARSE_EXCEPTIONS_NOT_DENSE_ARBITRARY_STATE')throw Error('SUMMARY_CONTRACT');const start=integer(x.start),count=integer(x.count);if(start<0n||count<1n||start+count>LIMIT||!Array.isArray(x.laneSums)||x.laneSums.length!==8)throw Error('SUMMARY_RANGE');const sums=x.laneSums.map(integer);if(sums.reduce((a,b)=>a+b,0n)!==integer(x.sum))throw Error('SUMMARY_SUM_MISMATCH');return {start,count,sums};}).sort((a,b)=>a.start<b.start?-1:a.start>b.start?1:0);
 const first=normalized[0];let end=first.start;const sums=Array(8).fill(0n);
 for(const x of normalized){if(x.start!==end)throw Error('OVERLAP_OR_GAP');end+=x.count;for(let i=0;i<8;i++)sums[i]+=x.sums[i];}
 return {schema:'affine-range-summary/1',start:String(first.start),count:String(end-first.start),laneSums:sums.map(String),sum:String(sums.reduce((a,b)=>a+b,0n)),semantics:'EXACT_INTEGER_AFFINE_PLUS_SPARSE_EXCEPTIONS_NOT_DENSE_ARBITRARY_STATE'};
}
