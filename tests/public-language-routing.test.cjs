// Public B∞ language-routing regression tests. No external dependencies or network.
"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const full=fs.readFileSync("assets/js/site-navigation.js","utf8");
const start=full.indexOf("/* B∞ language routing v1.0.");
assert(start>=0,"public localization code missing");
const code=full.slice(start);
const root="https://kimbach91-prog.github.io/bl-infinity/";
let count=0;
function verify({path="",browser=["vi-VN"],saved=null,search=""},expected){
 const redirects=[];
 const location={
  pathname:"/bl-infinity/"+path,
  href:root+path+search,
  search,hash:"",
  replace(url){redirects.push(url)},
  assign(url){redirects.push(url)}
 };
 const document={
  querySelector(selector){
   if(selector.includes('script[src*='))return {src:root+"assets/js/site-navigation.js?v=20261013-unified1"};
   return null;
  }
 };
 const localStorage={getItem(k){assert.equal(k,"bl-public-language-v1");return saved}};
 vm.runInNewContext(code,{document,location,navigator:{languages:browser,language:browser[0]},localStorage,URL,URLSearchParams,Set});
 assert.deepEqual(redirects,expected?[root+expected]:[],JSON.stringify({path,browser,saved,search,expected,redirects}));
 count++;
}
verify({path:"",browser:["en-US"]},"en/");
verify({path:"kien-truc-su-he-thong/",browser:["zh-CN"]},"zh/architect-of-intelligence/");
verify({path:"",saved:"zh",browser:["vi-VN"]},"zh/");
verify({path:"",search:"?lang=en",browser:["vi-VN"]},"en/");
verify({path:"en/",browser:["vi-VN"]},null);
verify({path:"zh/architect-of-intelligence/",browser:["en-US"]},null);
verify({path:"books/",browser:["en-US"]},null);
verify({path:"",browser:["de-DE"]},"en/");
verify({path:"",saved:"en",search:"?lang=vi",browser:["de-DE"]},null);
verify({path:"theory.html",browser:["en-US"]},"en/theory/");
verify({path:"theory.html",browser:["zh-CN"]},"zh/theory/");
verify({path:"en/theory/",browser:["vi-VN"]},null);
verify({path:"zh/theory/",browser:["en-US"]},null);
verify({path:"theory.html",search:"?lang=vi",browser:["en-US"]},null);
verify({path:"publication-gate.html",browser:["en-US"]},"en/publication-gate/");
verify({path:"publication-gate.html",browser:["zh-CN"]},"zh/publication-gate/");
verify({path:"en/publication-gate/",browser:["vi-VN"]},null);
verify({path:"zh/publication-gate/",browser:["en-US"]},null);
verify({path:"publication-gate.html",search:"?lang=vi",browser:["en-US"]},null);
assert(code.includes("localStorage.setItem("),"manual language persistence missing");
assert(code.includes('select.addEventListener("change"'),"manual locale selector missing");
assert(code.includes("bl-i18n-notice"),"untranslated work disclosure missing");
assert(!/translate\.googleapis|translate\.google\.com|fetch\(/i.test(code),"unreviewed external translation request");
console.log("B_INFINITY_I18N_ROUTE_TESTS_PASS "+count+" scenarios");
