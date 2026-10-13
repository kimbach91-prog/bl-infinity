"use strict";
// Curated B∞ public editorial pages only. No private or protected repository scan.
const fs=require("node:fs"),assert=require("node:assert/strict");
const paths=["index.html","theory.html","publication-gate.html","academic-freedom.html","academic-democracy.html","author.html","authors-promise.html","projects.html","books/index.html","books/bieu-tuong-va-ban-chat/index.html","books/ho-chi-minh/index.html","books/ho-chi-minh/sources.html","books/kevin-intellectual-map/index.html","novel/index.html","novel/chapter-001.html","research/human-development/index.html","research/human-development/kevin-nt/index.html","research/human-development/kevin-nt/studio/index.html","research/human-development/kevin-nt/tien-hoa-luong-cuc.html","research/human-development/kevin-nt/attribution-benchmark.html","kien-truc-su-he-thong/index.html","en/index.html","en/theory/index.html","en/publication-gate/index.html","en/architect-of-intelligence/index.html","zh/index.html","zh/theory/index.html","zh/publication-gate/index.html","zh/architect-of-intelligence/index.html"];
const seen=new Set();
const root="https://kimbach91-prog.github.io/bl-infinity/";
for(const path of paths){
 const html=fs.readFileSync(path,"utf8");
 const head=html.split("</head>")[0];
 const lang=path.startsWith("en/")?"en":path.startsWith("zh/")?"zh-CN":"vi";
 assert(html.includes('<html lang="'+lang+'">'),path+" language tag mismatched");
 assert((html.match(/data-bl-public-header="1\.2"/g)||[]).length===1,path+" header absent or duplicate");
 assert(html.includes('bl-drawer'),path+" mobile menu absent");
 assert(head.includes('site-navigation.css?v=20261013-unified1'),path+" design CSS release missing");
 assert(head.includes('site-navigation.js?v=20261013-unified1'),path+" locale/menu script release missing");
 for(const marker of ['name="bl-design-version"','name="description"','rel="canonical"','property="og:title"','property="og:description"','property="og:url"','property="og:site_name"','property="og:locale"','name="twitter:card"','name="twitter:title"']){
   assert(head.includes(marker),path+" metadata missing "+marker);
 }
 assert(head.includes('PUBLIC_SITE_UNIFIED_V1'),path+" design provenance missing");
 assert(head.includes('application/ld+json'),path+" structured page metadata missing");
 const canon=head.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
 assert(canon&&canon.startsWith("https://"),path+" canonical absent or relative");
 assert(!seen.has(canon),path+" canonical collision: "+canon);
 seen.add(canon);
 assert(!/(?:CORE_PRIMARY_SOLVER|COMMAND_TEXT|ARGS_JSON|WORKING_CAPSULE|raw_bearer_token)/.test(html),path+" private value pattern");
}

const map=JSON.parse(fs.readFileSync("public-content-map.json","utf8"));
assert.equal(map.schema,"b-infinity-public-content-map/1");
assert.equal(map.scientificDisclosure.originalOperators,"WITHHELD");
assert.equal(map.scientificDisclosure.automaticUnlock,false);
assert(map.canonicalSections.length>=12,"missing canonical subject hubs");
assert.equal(map.duplicatePolicy.redirectsImplemented.length,0,"unsanctioned semantic redirects");
for(const path of ["publication-gate.html","en/publication-gate/index.html","zh/publication-gate/index.html"]){
 const html=fs.readFileSync(path,"utf8");
 assert(html.includes('data-publication-gateway="BL_INFINITY_PUBLICATION_GATE_V1"'),path+" lacks formal release boundary");
 assert(html.includes("OWNER_RELEASE = NOT_GRANTED"),path+" must not imply automatic release");
 const main=html.match(/<main[\s\S]*?<\/main>/)?.[0]||"";
 assert(!/<form\b|<input\b|<textarea\b|<pre\b|<code\b/i.test(main),path+" public sensitive submission/input interface");
}
console.log("B_INFINITY_PUBLIC_RELEASE_POLICY_PASS",map.canonicalSections.length,"subjects");

console.log("B_INFINITY_PUBLIC_METADATA_UNIFIED_PASS",paths.length,"pages",seen.size,"unique canonicals");
