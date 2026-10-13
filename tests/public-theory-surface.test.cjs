"use strict";
// B∞ public philosophy reopening acceptance. This scans only deliberately
// selected public HTML pages, never confidential Drive or repository material.
const fs=require("node:fs");
const assert=require("node:assert/strict");
const editions=[
 {path:"theory.html",lang:"vi",title:"BL∞: Vô hạn khả năng",boundary:"Ranh giới công bố"},
 {path:"en/theory/index.html",lang:"en",title:"BL∞: The reach of possibility",boundary:"Publication boundary"},
 {path:"zh/theory/index.html",lang:"zh-CN",title:"BL∞：可达的未来",boundary:"公开范围"}
];
for(const e of editions){
 const html=fs.readFileSync(e.path,"utf8");
 const main=html.match(/<main[^>]*id="theory-content"[\s\S]*?<\/main>/)?.[0]||"";
 assert(html.startsWith("<!doctype html>"),e.path+" not standalone HTML");
 assert(html.includes('<html lang="'+e.lang+'">'),e.path+" bad language");
 assert(html.includes(e.title),e.path+" title missing");
 assert(html.includes(e.boundary),e.path+" scope disclaimer missing");
 assert(html.includes("PUBLIC_B_INFINITY_THEORY_OVERVIEW_V1"),e.path+" missing admitted public-scope marker");
 assert(html.includes('data-bl-public-header="1.2"'),e.path+" shared navigation missing");
 assert(html.includes("site-navigation.js?v=20261013-theory1"),e.path+" missing versioned navigation");
 assert(html.includes('hreflang="vi"')&&html.includes('hreflang="en"')&&html.includes('hreflang="zh-Hans"'),e.path+" international links missing");
 assert(html.includes("UNKNOWN"),e.path+" unknown boundary missing");
 assert(!/http-equiv\s*=\s*["']refresh["']/i.test(html),e.path+" still redirects");
 assert((main.match(/class="section"/g)||[]).length===6,e.path+" missing philosophy sections");
 assert((main.match(/<h2>/g)||[]).length===6,e.path+" public outline incomplete");
 assert(main.length>(e.lang==="zh-CN"?2600:3500),e.path+" too short");
 assert(!/<\s*(?:code|pre|script|iframe|form|input|textarea)\b/i.test(main),e.path+" executable or reconstructive section present");
 assert(!/data:text\/|javascript:|gdrive:\/\//i.test(main),e.path+" unsupported egress content");
 assert(!/\b(?:[A-Z]{3,}_[A-Z0-9]{3,}){2,}\b/.test(main.replaceAll("PUBLIC_B_INFINITY_THEORY_OVERVIEW_V1","")),e.path+" unreviewed internal identifier");
 const links=[...main.matchAll(/<a\s+[^>]*href="([^"]+)"/g)].map(x=>x[1]);
 assert(links.every(href=>href.startsWith("../")||href.startsWith("./")||/^[a-z0-9-]+(?:\/[a-z0-9-]+)*(?:\/|\.html)$/i.test(href)),e.path+" unknown external link");
 assert(links.length>=4,e.path+" review and bibliography links missing");
 console.log("B_INFINITY_PUBLIC_THEORY_DISCLOSURE_PASS",e.lang,html.length,links.length);
}
