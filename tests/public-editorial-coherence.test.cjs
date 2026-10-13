"use strict";
const fs=require("node:fs");
const assert=require("node:assert/strict");
const root="https://kimbach91-prog.github.io/bl-infinity/";
const pages=[
"index.html","theory.html","academic-freedom.html","academic-democracy.html","author.html","authors-promise.html","projects.html",
"books/index.html","books/bieu-tuong-va-ban-chat/index.html","books/ho-chi-minh/index.html","books/ho-chi-minh/sources.html","books/kevin-intellectual-map/index.html",
"novel/index.html","novel/chapter-001.html","research/human-development/index.html",
"research/human-development/kevin-nt/index.html","research/human-development/kevin-nt/studio/index.html",
"research/human-development/kevin-nt/tien-hoa-luong-cuc.html","research/human-development/kevin-nt/attribution-benchmark.html",
"kien-truc-su-he-thong/index.html","en/index.html","en/theory/index.html","en/architect-of-intelligence/index.html",
"zh/index.html","zh/theory/index.html","zh/architect-of-intelligence/index.html"
];
const canonicals=new Set();
for(const path of pages){
 const html=fs.readFileSync(path,"utf8");
 const head=html.split("</head>")[0];
 const suffix=path==="index.html"?"":path.endsWith("/index.html")?path.slice(0,-10):path;
 const canonical=root+suffix;
 const meta=(rx)=>(head.match(rx)||[]).length;
 assert(html.includes('data-bl-editorial="1"'),path+": editorial style marker missing");
 assert(head.includes("editorial-unified.css?v=20261013-public2"),path+": shared design stylesheet missing");
 assert(html.includes('data-bl-public-header="1.2"'),path+": shared header missing");
 assert(meta(/rel="canonical"/g)===1,path+": canonical duplicate or missing");
 assert(head.includes('rel="canonical" href="'+canonical+'"'),path+": incorrect canonical");
 assert(!canonicals.has(canonical),path+": duplicate canonical identity");
 canonicals.add(canonical);
 for(const field of ['property="og:title"','property="og:description"','property="og:url"','name="twitter:card"','name="description"','name="bl-evidence-status"']){
  assert(meta(new RegExp(field,"g"))===1,path+": bad metadata "+field);
 }
 assert(head.includes("application/ld+json"),path+": structured metadata absent");
 assert(html.includes("<footer"),path+": missing footer");
 assert(!html.includes("SENSITIVE_ROOT_OPERATOR_SOURCE"),path+": unsafe symbol");
 const pathLang=path.startsWith("en/")?"en":path.startsWith("zh/")?"zh-CN":"vi";
 assert(html.includes('<html lang="'+pathLang+'">'),path+": wrong document language");
 if(path.includes("/theory/")||path==="theory.html")assert(!html.includes('http-equiv="refresh"'),path+": theory must not redirect");
}
for(const path of ["deus/index.html","public-compute/gate.html","public-compute/webgpu-s0.html"]){
 const html=fs.readFileSync(path,"utf8");
 assert(!html.includes("editorial-unified.css"),path+": application was inadvertently restyled");
}
console.log("B_INFINITY_EDITORIAL_META_AND_DESIGN_PASS "+pages.length+" pages, "+canonicals.size+" unique canonicals");
