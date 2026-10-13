"use strict";
/* Audit ONLY the explicit, staged B∞ public website (_site).
   Never crawl Drive or confidential repository files. No network requests. */
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict");
const root=path.resolve(process.argv[2]||"_site");
const origin="https://kimbach91-prog.github.io";
const sitePrefix="/bl-infinity/";
assert(fs.existsSync(path.join(root,"index.html")),"staged public homepage missing");
const all=[];
function walk(dir){for(const item of fs.readdirSync(dir,{withFileTypes:true})){
  const abs=path.join(dir,item.name);
  if(item.isDirectory())walk(abs);
  else if(item.isFile())all.push(abs);
}}
walk(root);
const files=new Set(all.map(f=>path.relative(root,f).split(path.sep).join("/")));
const htmlFiles=all.filter(f=>/\.html$/i.test(f));
const missing=[],badRoot=[],duplicateIds=[],missingFragments=[],unsafeHref=[],accessibility=[],external=[];
const clean=s=>String(s||"").replace(/&amp;/g,"&").replace(/&quot;/g,'"').replace(/&#39;/g,"'").trim();
function convertRef(raw,from,kind){
 raw=clean(raw);
 if(!raw||raw.startsWith("#")&&kind==="meta")return null;
 if(/^(data:|blob:|mailto:|tel:|sms:)/i.test(raw))return null;
 if(/^javascript:/i.test(raw)){unsafeHref.push({from,raw:raw.slice(0,80)});return null;}
 let u;try{u=new URL(raw,origin+sitePrefix+from)}catch{return null;}
 if(u.origin!==origin){external.push(u.origin);return null;}
 if(!u.pathname.startsWith(sitePrefix)){
   // A fully-qualified page on a different GitHub Pages project is external.
   // Its public availability cannot be inferred from this repository's artifact.
   if(/^https?:\/\//i.test(raw) && u.pathname.startsWith("/Theory-Group/")){
      external.push(u.origin+"/Theory-Group/");return null;
   }
   badRoot.push({from,raw:raw.slice(0,100),resolved:u.pathname});
   return null;
 }
 let relative;
 try{relative=decodeURIComponent(u.pathname.slice(sitePrefix.length));}catch{relative=u.pathname.slice(sitePrefix.length)}
 let target=relative;
 if(!target || target.endsWith("/"))target+="index.html";
 if(!files.has(target) && !path.extname(target) && files.has(target+"/index.html"))target+="/index.html";
 if(!files.has(target)){missing.push({from,raw:raw.slice(0,115),target,kind});return null;}
 return {target,fragment:u.hash.slice(1),kind};
}
function attribute(tag,name){const re=new RegExp("(?:^|\\s)"+name+"\\s*=\\s*([\"'])([\\s\\S]*?)\\1","i");return tag.match(re)?.[2]||"";}
let htmlReferences=0,cssReferences=0,imageCount=0,navCount=0;
for(const file of htmlFiles){
 const from=path.relative(root,file).split(path.sep).join("/");
 const html=fs.readFileSync(file,"utf8");
 // Strip inline CSS/JS to avoid false HTML tags embedded in executable strings.
 const markup=html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,"").replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,"");
 const ids=[...markup.matchAll(/\bid=(["'])([^"']+)\1/gi)].map(m=>m[2]);
 for(const id of new Set(ids))if(ids.filter(x=>x===id).length>1)duplicateIds.push({from,id});
 if(markup.includes('class="bl-site-header"'))navCount++;
 for(const match of markup.matchAll(/<(a|img|link|script|source|video|audio|iframe|form|use|meta|object)\b[^>]*>/gi)){
   const tag=match[0],type=match[1].toLowerCase();
   if(type==="img"){imageCount++;if(!/\balt\s*=/i.test(tag))accessibility.push({from,issue:"image missing alt",tag:tag.slice(0,100)});}
   if(type==="a" && /\btarget\s*=\s*["']_blank["']/i.test(tag) &&
      !/\brel\s*=\s*["'][^"']*\bnoopener\b/i.test(tag))accessibility.push({from,issue:"new tab missing noopener",tag:tag.slice(0,120)});
   const names=type==="meta"?["content"]:["href","src","poster","action","data-src","srcset"];
   for(const attr of names){
     const raw=attribute(tag,attr);if(!raw)continue;
     const urls=attr==="srcset"?raw.split(",").map(x=>x.trim().split(/\s+/)[0]):[raw];
     for(const item of urls){
       if(type==="meta"&&!/^https?:|^\//.test(item))continue;
       const target=convertRef(item,from,type);htmlReferences++;
       if(!target||!target.fragment||!target.target.endsWith(".html"))continue;
       const fileContent=fs.readFileSync(path.join(root,target.target),"utf8");
       let frag=target.fragment;try{frag=decodeURIComponent(frag)}catch{}
       if(!fileContent.includes('id="'+frag+'"')&&!fileContent.includes("id='"+frag+"'")&&!fileContent.includes('name="'+frag+'"'))missingFragments.push({from,target:target.target,fragment:frag});
     }
   }
 }
}
for(const file of all.filter(f=>/\.css$/i.test(f))){
 const from=path.relative(root,file).split(path.sep).join("/");
 const css=fs.readFileSync(file,"utf8");
 for(const match of css.matchAll(/url\(\s*(['"]?)([^)'"]+)\1\s*\)/gi)){
   convertRef(match[2],from,"css");cssReferences++;
 }
}
const issues=[...missing.map(e=>({...e,issue:"missing published file"})),...badRoot.map(e=>({...e,issue:"site-root mismatch"}))];
const uniq=a=>[...new Set(a)];
const compact=(a,n=30)=>a.slice(0,n);
const stats={htmlFiles:htmlFiles.length,stagedFiles:files.size,htmlReferences,cssReferences,images:imageCount,publicNavigationPages:navCount,missing:missing.length,badRoot:badRoot.length,unsafeHref:unsafeHref.length,duplicateIds:duplicateIds.length,missingFragments:missingFragments.length,accessibilityWarnings:accessibility.length,externalDomains:uniq(external).length};
console.log("B_INFINITY_STAGED_SITE_AUDIT_COUNTS",JSON.stringify(stats));
if(issues.length)console.error("B_INFINITY_STAGED_SITE_BROKEN_LINKS",JSON.stringify(compact(issues,80),null,2));
if(unsafeHref.length)console.error("B_INFINITY_STAGED_SITE_UNSAFE_LINKS",JSON.stringify(compact(unsafeHref),null,2));
if(duplicateIds.length)console.warn("B_INFINITY_STAGED_SITE_DUPLICATE_IDS",JSON.stringify(compact(duplicateIds),null,2));
if(missingFragments.length)console.warn("B_INFINITY_STAGED_SITE_FRAGMENT_WARNINGS",JSON.stringify(compact(missingFragments),null,2));
if(accessibility.length)console.warn("B_INFINITY_STAGED_SITE_ACCESSIBILITY_WARNINGS",JSON.stringify(compact(accessibility),null,2));
if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
 "## B∞ Staged Public Site Crawl\n\n\`\`\`json\n"+JSON.stringify(stats,null,2)+"\n\`\`\`\n");
assert.equal(issues.length,0,"Public site has internal broken or misrooted links");
assert.equal(unsafeHref.length,0,"Public site has javascript: links");
console.log("B_INFINITY_STAGED_SITE_LINKS_PASS",htmlFiles.length,htmlReferences+cssReferences);
