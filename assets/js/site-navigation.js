/* B∞ public menu v1.2. Accessible, no tracking, no network. */
(()=>{"use strict";const b=document.querySelector(".bl-toggle"),d=document.querySelector(".bl-drawer"),o=document.querySelector(".bl-overlay"),x=document.querySelector(".bl-close");if(!b||!d||!o||!x)return;let prior=null;
function set(open,restore=true){if(open===!d.hidden)return;d.hidden=!open;o.hidden=!open;b.setAttribute("aria-expanded",String(open));document.body.classList.toggle("bl-scroll-lock",open);if(open){prior=document.activeElement;x.focus()}else if(restore)(prior instanceof HTMLElement?prior:b).focus()}
b.addEventListener("click",()=>set(d.hidden));x.addEventListener("click",()=>set(false));o.addEventListener("click",()=>set(false));d.querySelectorAll("a").forEach(a=>a.addEventListener("click",()=>set(false,false)));document.addEventListener("keydown",e=>{if(d.hidden)return;if(e.key==="Escape"){e.preventDefault();set(false);return}if(e.key!=="Tab")return;const a=[...d.querySelectorAll("button,a[href]")].filter(el=>!el.disabled);if(!a.length)return;if(e.shiftKey&&document.activeElement===a[0]){e.preventDefault();a[a.length-1].focus()}else if(!e.shiftKey&&document.activeElement===a[a.length-1]){e.preventDefault();a[0].focus()}})})();

/* B∞ language routing v1.0. All translations are static, no external translation API. */
(()=>{"use strict";
const script=document.querySelector('script[src*="assets/js/site-navigation.js"]');
if(!script)return;
const root=new URL("../../",script.src);
const prefix=root.pathname;
const path=location.pathname.startsWith(prefix)?location.pathname.slice(prefix.length):"";
const normalize=p=>p.replace(/index\.html$/,"").replace(/^\/+/,"");
const clean=normalize(path);
const map={
home:{vi:"",en:"en/",zh:"zh/"},
essay:{vi:"kien-truc-su-he-thong/",en:"en/architect-of-intelligence/",zh:"zh/architect-of-intelligence/"},
theory:{vi:"theory.html",en:"en/theory/",zh:"zh/theory/"},
publication:{vi:"publication-gate.html",en:"en/publication-gate/",zh:"zh/publication-gate/"}
};
const key=Object.keys(map).find(k=>Object.values(map[k]).some(v=>normalize(v)===clean))||null;
const pathLanguage=clean.startsWith("en/")?"en":clean.startsWith("zh/")?"zh":null;
const supported=new Set(["vi","en","zh"]);
const query=new URLSearchParams(location.search);
const requested=query.get("lang");
let stored=null;
try{stored=localStorage.getItem("bl-public-language-v1")}catch(_){}
const browserLanguage=(()=>{
  const list=Array.isArray(navigator.languages)&&navigator.languages.length?navigator.languages:[navigator.language||"vi"];
  for(const candidate of list){
    const tag=String(candidate||"").toLowerCase();
    if(tag.startsWith("vi"))return"vi";
    if(tag.startsWith("en"))return"en";
    if(tag.startsWith("zh"))return"zh";
  }
  return"en";
})();
let language=supported.has(requested)?requested:(pathLanguage||(supported.has(stored)?stored:browserLanguage));
if(key&&normalize(map[key][language])!==clean){
  const destination=new URL(map[key][language],root);
  const preserved=new URLSearchParams(location.search);preserved.delete("lang");
  destination.search=preserved.toString();
  destination.hash=location.hash;
  location.replace(destination.href);
  return;
}
const words={
vi:{"Trang chủ":"Trang chủ","Sách sống":"Sách sống","Tiểu thuyết":"Tiểu thuyết","Bài luận":"Bài luận","Hệ thống":"Hệ thống","Tác giả":"Tác giả","Kiến trúc sư hệ thống":"Kiến trúc sư trí tuệ","Kiến trúc sư trí tuệ":"Kiến trúc sư trí tuệ","Thư viện sách sống":"Thư viện sách sống","Từ Hai Bàn Tay Trắng Đến Một Nhà Nước":"Từ Hai Bàn Tay Trắng Đến Một Nhà Nước","Biểu tượng và Bản chất":"Biểu tượng và Bản chất","Lần Hồi Quy Thứ Một Triệu":"Lần Hồi Quy Thứ Một Triệu","Phát triển con người":"Phát triển con người","Tự do Học thuật":"Tự do Học thuật","Dân chủ Học thuật":"Dân chủ Học thuật","Lâm Kim Bách":"Lâm Kim Bách","Dự án công khai":"Dự án công khai","Điều hướng":"Điều hướng","Tác phẩm":"Tác phẩm","Nghiên cứu":"Nghiên cứu","Tác giả & dự án":"Tác giả & dự án","Khám phá B∞":"Khám phá B∞","Danh mục":"Danh mục","Mở danh mục":"Mở danh mục","Đóng danh mục":"Đóng danh mục","Học thuyết BL∞":"Học thuyết BL∞","Cổng công bố BL∞":"Cổng công bố BL∞"},
en:{"Trang chủ":"Home","Sách sống":"Living books","Tiểu thuyết":"Fiction","Bài luận":"Essay","Hệ thống":"Systems","Tác giả":"Author","Kiến trúc sư hệ thống":"Architect of Intelligence","Kiến trúc sư trí tuệ":"Architect of Intelligence","Thư viện sách sống":"Living books library","Từ Hai Bàn Tay Trắng Đến Một Nhà Nước":"From Empty Hands to a Nation","Biểu tượng và Bản chất":"Symbols and Essence","Lần Hồi Quy Thứ Một Triệu":"The Millionth Return","Phát triển con người":"Human development","Tự do Học thuật":"Academic Freedom","Dân chủ Học thuật":"Academic Democracy","Lâm Kim Bách":"Lâm Kim Bách","Dự án công khai":"Public projects","Điều hướng":"Navigation","Tác phẩm":"Works","Nghiên cứu":"Research","Tác giả & dự án":"Author and projects","Khám phá B∞":"Explore B∞","Danh mục":"Menu","Mở danh mục":"Open menu","Đóng danh mục":"Close menu","Học thuyết BL∞":"BL∞ Theory","Cổng công bố BL∞":"Publication gateway"},
zh:{"Trang chủ":"首页","Sách sống":"持续更新的书籍","Tiểu thuyết":"小说","Bài luận":"随笔","Hệ thống":"系统","Tác giả":"作者","Kiến trúc sư hệ thống":"智慧架构师","Kiến trúc sư trí tuệ":"智慧架构师","Thư viện sách sống":"动态书库","Từ Hai Bàn Tay Trắng Đến Một Nhà Nước":"从白手起家到建立一个国家","Biểu tượng và Bản chất":"符号与本质","Lần Hồi Quy Thứ Một Triệu":"第一百万次回归","Phát triển con người":"人的发展研究","Tự do Học thuật":"学术自由","Dân chủ Học thuật":"学术民主","Lâm Kim Bách":"林金百（Lâm Kim Bách）","Dự án công khai":"公开项目","Điều hướng":"导航","Tác phẩm":"作品","Nghiên cứu":"研究","Tác giả & dự án":"作者与项目","Khám phá B∞":"探索 B∞","Danh mục":"菜单","Mở danh mục":"打开菜单","Đóng danh mục":"关闭菜单","Học thuyết BL∞":"BL∞ 学说","Cổng công bố BL∞":"科学公开入口"}
};
if(document.body)document.body.classList.add("bl-public-site");
const header=document.querySelector(".bl-site-header"),drawer=document.querySelector(".bl-drawer");
if(!header||!drawer)return;
function addPublicTheoryLink(nav,beforeFragment){
  if(!nav)return;
  const existing=Array.from(nav.querySelectorAll("a")).some(a=>(a.getAttribute("href")||"").includes("theory.html")||(a.getAttribute("href")||"").includes("/theory/"));
  if(existing)return;
  const a=document.createElement("a");
  a.href=new URL(map.theory.vi,root).href;
  a.textContent="Học thuyết BL∞";
  if(key==="theory")a.setAttribute("aria-current","page");
  const before=Array.from(nav.querySelectorAll("a")).find(link=>(link.getAttribute("href")||"").includes(beforeFragment));
  nav.insertBefore(a,before||null);
}
addPublicTheoryLink(header.querySelector("nav.bl-horizontal"),"projects.html");
addPublicTheoryLink(drawer.querySelector("nav.bl-links"),"kien-truc-su-he-thong");
function addPublicationLink(){
 const nav=drawer.querySelector("nav.bl-links");if(!nav)return;
 const url=new URL(map.publication.vi,root).href;
 if([...nav.querySelectorAll("a")].some(a=>a.href===url))return;
 const a=document.createElement("a");a.href=url;a.textContent="Cổng công bố BL∞";
 const theory=[...nav.querySelectorAll("a")].find(z=>z.href===new URL(map.theory.vi,root).href);
 if(theory)theory.insertAdjacentElement("afterend",a);else nav.appendChild(a);
}
addPublicationLink();
const remember=(value)=>{try{localStorage.setItem("bl-public-language-v1",value)}catch(_){}};
const textFor=(source)=>words[language][source]||source;
const snapshot=new WeakMap();
function original(el){if(!snapshot.has(el))snapshot.set(el,el.textContent.trim());return snapshot.get(el)}
const navNodes=[...header.querySelectorAll("nav a"),...drawer.querySelectorAll("nav a")];
const navOrigins=navNodes.map(a=>({el:a,word:a.textContent.trim(),originalHref:a.href}));
const groupNodes=[...drawer.querySelectorAll(".bl-group"),drawer.querySelector(".bl-drawer-head strong"),header.querySelector(".bl-toggle span")].filter(Boolean);
const groupOrigins=groupNodes.map(el=>({el,word:el.textContent.trim()}));
const menuButton=header.querySelector(".bl-toggle"),closeButton=drawer.querySelector(".bl-close");
const sideFoot=drawer.querySelector(".bl-drawer-foot"),footVI=sideFoot?sideFoot.textContent:"";

/* Shared public footer: keep editorial footers, add consistent route affordances. */
function createPublicFooter(){
  const main=document.querySelector("body > main");
  if(!main)return null;
  let foot=main.querySelector("footer:last-of-type");
  if(!foot){foot=document.createElement("footer");main.appendChild(foot)}
  foot.classList.add("bl-unified-footer");
  if(foot.querySelector(".bl-footer-links"))return foot;
  const navigation=document.createElement("nav");
  navigation.className="bl-footer-links";navigation.setAttribute("aria-label","B∞ site footer");
  for(const [type,source] of [["home","Trang chủ"],["theory","Học thuyết BL∞"],["publication","Cổng công bố BL∞"],["essay","Kiến trúc sư trí tuệ"]]){
    const a=document.createElement("a");a.dataset.blLink=type;a.dataset.blLabel=source;
    a.href=new URL(map[type].vi,root).href;a.textContent=source;navigation.appendChild(a);
  }
  const note=document.createElement("small");note.className="bl-footer-custody";
  note.textContent="B∞ · Lâm Kim Bách · Tri thức công khai có nguồn và ranh giới";
  foot.append(navigation,note);return foot;
}
const unifiedFooter=createPublicFooter();
function updatePublicFooter(){
 if(!unifiedFooter)return;
 for(const a of unifiedFooter.querySelectorAll("[data-bl-link]")){
  const type=a.dataset.blLink,source=a.dataset.blLabel;
  a.href=new URL(map[type][language],root).href;a.textContent=textFor(source);
 }
 const note=unifiedFooter.querySelector(".bl-footer-custody");
 if(note)note.textContent=language==="en"?"B∞ · Lâm Kim Bách · Public knowledge, provenance and boundaries":
 language==="zh"?"B∞ · Lâm Kim Bách · 公开知识、来源与边界":
 "B∞ · Lâm Kim Bách · Tri thức công khai có nguồn và ranh giới";
}

const note=document.createElement("div");note.className="bl-i18n-notice";note.hidden=true;note.setAttribute("role","status");header.insertAdjacentElement("afterend",note);
const holder=document.createElement("div");holder.className="bl-language-wrap";
const label=document.createElement("label");label.textContent="🌐";label.setAttribute("for","bl-public-language");
const select=document.createElement("select");select.id="bl-public-language";select.setAttribute("aria-label","Website language / Ngôn ngữ / 语言");
for(const [value,title] of [["vi","VI"],["en","EN"],["zh","中文"]]){const option=document.createElement("option");option.value=value;option.textContent=title;select.appendChild(option)}
holder.append(label,select);header.querySelector(".bl-header-inner").insertBefore(holder,menuButton);
function update(){
  select.value=language;
  header.lang=language==="zh"?"zh-CN":language;drawer.lang=header.lang;
  for(const {el,word,originalHref} of navOrigins){
    el.textContent=textFor(word);
    const resolved=new URL(originalHref);
    let kind=null;
    if(resolved.origin===root.origin&&resolved.pathname===root.pathname)kind="home";
    else if(resolved.origin===root.origin&&resolved.pathname===new URL(map.essay.vi,root).pathname)kind="essay";
    else if(resolved.origin===root.origin&&resolved.pathname===new URL(map.theory.vi,root).pathname)kind="theory";
    else if(resolved.origin===root.origin&&resolved.pathname===new URL(map.publication.vi,root).pathname)kind="publication";
    if(kind){el.href=new URL(map[kind][language],root).href;}
  }
  for(const {el,word} of groupOrigins)el.textContent=textFor(word);
  if(sideFoot)sideFoot.textContent=language==="vi"?footVI:language==="en"?"B∞ · Public reading library. Every work has its own disclosure boundary.":"B∞ · 公共阅读图书馆。每部作品均有独立的公开范围。";
  if(menuButton)menuButton.setAttribute("aria-label",textFor("Mở danh mục"));
  if(closeButton)closeButton.setAttribute("aria-label",textFor("Đóng danh mục"));
  updatePublicFooter();
  if(language!=="vi"&&!key){
    note.hidden=false;note.lang=header.lang;
    const msg=language==="en"?"This work has not yet been translated. The original Vietnamese text is shown. ":"本篇作品尚未翻译，以下保留越南语原文。";
    const go=language==="en"?"Go to the translated homepage":"返回已翻译的首页";
    note.replaceChildren(document.createTextNode(msg));
    const link=document.createElement("a");link.href=new URL(map.home[language],root).href;link.textContent=go;note.appendChild(link);
  }else{note.hidden=true;note.replaceChildren();}
}
select.addEventListener("change",()=>{
  const next=select.value;
  if(!supported.has(next))return;
  language=next;remember(next);
  if(key){
    const dest=new URL(map[key][next],root);
    if(dest.pathname!==location.pathname){location.assign(dest.href);return;}
  }
  update();
});
update();
})();
