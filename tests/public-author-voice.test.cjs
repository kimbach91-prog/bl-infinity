"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const checked=[
["index.html","Tôi không dựng thư viện này"],
["theory.html","Tôi không chấp nhận lấy giới hạn"],
["academic-freedom.html","Tôi không cho rằng một người phải"],
["academic-democracy.html","chân lý không được biểu quyết bằng số đông"],
["author.html","Tôi là Lâm Kim Bách."],
["authors-promise.html","Tôi sẽ tiếp tục công bố"],
["projects.html","Tôi làm nhiều loại công trình"],
["publication-gate.html","Tôi sẽ không công bố toán tử gốc"],
["books/index.html","Tôi không xem một cuốn sách"],
["books/bieu-tuong-va-ban-chat/index.html","Tôi nghi ngờ những cái tên"],
["books/ho-chi-minh/index.html","Tôi viết về Chủ tịch Hồ Chí Minh"],
["books/ho-chi-minh/sources.html","Tôi muốn người đọc có thể lần ngược"],
["books/kevin-intellectual-map/index.html","Tôi viết bản đồ này"],
["research/human-development/index.html","Điều khiến tôi quan tâm"],
["research/human-development/kevin-nt/index.html","Tôi muốn nghiên cứu năng lực phát triển"],
["research/human-development/kevin-nt/tien-hoa-luong-cuc.html","Tôi gọi"],
["research/human-development/kevin-nt/attribution-benchmark.html","Tôi không chấp nhận lấy sự tương đồng"],
["research/human-development/kevin-nt/studio/index.html","Tôi không nghiên cứu Kevin để"],
["kien-truc-su-he-thong/index.html","Tôi không quan tâm ai đưa ra được nhiều câu trả lời nhất"],
["en/architect-of-intelligence/index.html","I care less about who can produce the most answers"],
["zh/architect-of-intelligence/index.html","我并不关心谁能生成最多答案"]
];
for(const [path,anchor] of checked){
 const html=fs.readFileSync(path,"utf8");
 assert(html.includes(anchor),path+": author viewpoint anchor missing");
 assert(html.includes('data-bl-public-header="1.2"'),path+": shared header lost");
 assert(!/(?:CORE_PRIMARY_SOLVER|COMMAND_TEXT|ARGS_JSON|WORKING_CAPSULE|raw_bearer_token)/.test(html),path+": protected material pattern");
}
for(const path of ["kien-truc-su-he-thong/index.html","en/architect-of-intelligence/index.html","zh/architect-of-intelligence/index.html"]){
 const html=fs.readFileSync(path,"utf8");
 assert(!html.includes("\u2014"),path+": essay-long-dash regression");
 for(let i=1;i<=11;i++)assert(html.includes('id="ref-'+i+'"'),path+": evidence source "+i+" missing");
 assert(html.includes('<details class="essay-references">'),path+": science bibliography lost");
}
const book=fs.readFileSync("books/bieu-tuong-va-ban-chat/chapters/00-loi-mo.md","utf8");
assert(book.includes("Tôi từng nghĩ con người nhìn thấy thế giới rồi mới đặt tên cho nó."),"distinctive original book voice must be preserved");
const history=fs.readFileSync("books/ho-chi-minh/chapters/00-loi-mo.md","utf8");
assert(history.includes("Tôi kính ngưỡng Chủ tịch Hồ Chí Minh."),"historical research author positioning must be preserved");
console.log("B_INFINITY_AUTHOR_VOICE_AND_BOUNDARY_PASS",checked.length,"edited public prose pages");
