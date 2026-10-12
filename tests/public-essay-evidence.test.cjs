"use strict";
const fs = require("node:fs");
const assert = require("node:assert/strict");

const pages = [
  { path: "kien-truc-su-he-thong/index.html", language: "vi", min: 35000, title: "Kiến trúc sư trí tuệ", refs: "Nguồn và ranh giới bằng chứng", conceptual: "Dị số: điểm kỳ dị" },
  { path: "en/architect-of-intelligence/index.html", language: "en", min: 33000, title: "Architect of Intelligence", refs: "Sources and evidentiary boundaries", conceptual: "Dị số" },
  { path: "zh/architect-of-intelligence/index.html", language: "zh-CN", min: 18000, title: "智慧架构师", refs: "参考来源与证据边界", conceptual: "异数" }
];
for (const p of pages) {
  const html = fs.readFileSync(p.path, "utf8");
  assert(html.length >= p.min, p.path + ": too short to be the long-form evidence edition");
  assert(html.includes('<html lang="' + p.language + '">'), p.path + ": wrong language");
  assert(html.includes('data-bl-public-header="1.2"'), p.path + ": navigation missing");
  assert(html.includes('itemscope itemtype="https://schema.org/ScholarlyArticle"'), p.path + ": article identity missing");
  assert(html.includes(p.title) && html.includes(p.refs) && html.includes(p.conceptual), p.path + ": claims or references missing");
  assert((html.match(/<h2>/g) || []).length >= 13, p.path + ": argument depth removed");
  assert((html.match(/<p>/g) || []).length >= 48, p.path + ": evidence narrative truncated");
  assert(!html.includes("\u2014"), p.path + ": long dash reintroduced");
  assert(!html.includes("CORE_PRIMARY_SOLVER") && !html.includes("COMMAND_TEXT") && !html.includes("ARGS_JSON"), p.path + ": private operational token detected");
  for (let i = 1; i <= 11; i++) {
    assert(html.includes('href="#ref-' + i + '"'), p.path + ": uncited reference " + i);
    assert(html.includes('id="ref-' + i + '"'), p.path + ": bibliography gap " + i);
  }
  for (const source of ["10.1126/science.adh2586", "10.1038/s41562-024-02024-1", "10.1038/s41586-024-07566-y"]) {
    assert(html.includes(source), p.path + ": source missing " + source);
  }
  console.log("B_INFINITY_ESSAY_EVIDENCE_SOURCE_PASS", p.language, html.length);
}
