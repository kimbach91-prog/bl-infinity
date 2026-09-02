# BL-NOVEL · Social Language & Literary Era Atlas

**Object:** `BL-NOVEL-ERA-LANGUAGE-ATLAS`  
**Series:** *Bách Lâm · Lần Hồi Quy Thứ Một Triệu*  
**Class:** worldbuilding constraint / sociolinguistic timeline / literary-style registry  
**Status:** `ADOPTED · REALITY-ANCHORED · OPEN-TO-PATCH`  
**Origin:** Lâm Kim Bách / Bách Lâm  
**Version:** `1.0`  
**Date:** `2026-09-02`

---

## 0. Mục đích

Một nhân vật không được nói như năm 2026 chỉ vì người viết đang sống ở năm 2026.

Một cảnh lịch sử tốt phải giải đồng thời ít nhất sáu câu hỏi:

```text
WHEN?
WHERE?
WHO SPEAKS TO WHOM?
THROUGH WHICH MEDIUM?
UNDER WHICH SOCIAL RELATION?
IN WHICH LITERARY/NARRATIVE MODE?
```

Atlas này không ép toàn bộ truyện thành văn cổ hoặc một kiểu "phục dựng bảo tàng". Nó tạo constraint để mỗi cảnh có **giọng thời đại** nhưng vẫn dễ đọc đối với độc giả hiện đại.

```text
PeriodAuthenticity != ArchaicOverload
LiteraryEra != AuthorImitation
DialogueRegister != NarratorRegister
HistoricalVocabulary != TimelessVocabulary
OneYear != OneUniformVoice
Region != NationAsMonolith
```

Không bắt chước giọng riêng của một tác giả cụ thể. Chỉ dùng đặc trưng cấp **giai đoạn, trường phái, thể loại, môi trường truyền thông và bối cảnh xã hội**.

---

## 1. Era Resolver

Mỗi scene có thể resolve bằng vector:

```text
S(y,r,a,c,m,q,g) -> {
  lexicon,
  pronouns,
  politeness,
  sentence_rhythm,
  taboo_surface,
  media_constraints,
  information_speed,
  narrator_distance,
  literary_pressure,
  historical_unknowns
}
```

Trong đó:

- `y`: năm hoặc khoảng năm;
- `r`: vùng/địa điểm;
- `a`: tuổi/thế hệ;
- `c`: tầng lớp/nghề/học vấn/môi trường;
- `m`: medium — trực tiếp, thư, báo, điện thoại, SMS, chat, forum, social platform...;
- `q`: quan hệ xã hội — gia đình, ngang hàng, cấp bậc, người lạ, thân mật, nghi lễ...;
- `g`: literary mode / genre.

Nếu scene không khóa được năm chính xác, resolver phải trả về `ERA_BAND`, không được bịa một từ lóng hay thiết bị chỉ vì “nghe hợp thời”.

---

## 2. Bản đồ văn học – xã hội theo giai đoạn

### E0 — Dân gian / truyền khẩu / lớp nền xuyên thời kỳ

**Không phải một giai đoạn khép kín.** Các dạng truyền khẩu sống song song với văn học viết qua nhiều thế kỷ.

Các mode quan trọng:

- thần thoại, truyền thuyết;
- cổ tích;
- truyện cười;
- ngụ ngôn;
- tục ngữ;
- câu đố;
- ca dao, dân ca, lời ru;
- truyện kể gia đình, ký ức làng/xóm;
- tích, giai thoại, lời truyền miệng.

Constraint: lời kể truyền khẩu có thể biến thể theo người kể; **variation là một phần của provenance**, không tự xem là lỗi continuity.

### E1 — Thế kỷ X–XIV: văn học trung đại sớm

- văn học viết gắn mạnh với chữ Hán và tầng lớp học thuật/chính trị;
- văn học ghi nhận, tái tạo và chuyển hóa motif dân gian;
- các hình thức truyện kỳ dị, thần tích, lịch sử, Phật giáo/Thiền và thơ phát triển trong môi trường văn hóa bác học;
- tiếng nói đời thường không được suy trực tiếp từ văn bản bác học.

### E2 — Thế kỷ XV–XVII: Nôm mở rộng năng lực biểu đạt tiếng Việt

- thơ Nôm và văn Nôm phát triển;
- ngôn ngữ dân tộc đi sâu hơn vào sáng tác;
- văn chương bác học và lời ăn tiếng nói thường ngày vẫn không đồng nhất;
- có thể dùng nhịp cân đối, hình ảnh cô đọng, điển tích ở narrator hoặc nhân vật có học, nhưng không bắt mọi người dân nói như văn bản khoa cử.

### E3 — Thế kỷ XVIII–nửa đầu XIX: truyện thơ Nôm, ngâm khúc, ca trù và đời tư cảm xúc

- truyện Nôm/lục bát, song thất lục bát, ngâm khúc, ca trù và nhiều dạng thơ Nôm đạt vị trí nổi bật;
- số phận cá nhân, tình yêu, phẩm giá, bất công xã hội có không gian biểu đạt lớn hơn;
- lời kể có thể nhạc tính cao, nhưng cảnh hội thoại phải vẫn phân biệt địa vị, tuổi tác, giới, quan hệ thân–sơ và vùng văn hóa.

### E4 — Cuối thế kỷ XIX–1931: Quốc ngữ, báo chí và văn xuôi hiện đại chuyển tiếp

- báo chí Quốc ngữ và văn xuôi Quốc ngữ mở rộng;
- tiểu thuyết văn xuôi hiện đại hình thành trong quá trình chuyển từ truyện thơ Nôm, văn xuôi Hán/Nôm và bản dịch;
- cấu trúc câu, nhịp kể và từ vựng có thể mang dấu quá độ giữa văn biền ngẫu/cổ và văn xuôi hiện đại;
- đô thị, trường học, nhà in, báo chí, quảng cáo, thư từ và đời sống thuộc địa làm thay đổi tốc độ lưu thông ngôn ngữ.

### E5 — 1932–1945: hiện đại hóa tăng tốc

Các dòng không được trộn thành một giọng duy nhất:

- **Thơ mới**: cái tôi trữ tình, nhịp điệu và cảm xúc cá nhân đổi mạnh;
- **lãng mạn**: cá nhân, tình yêu, giải phóng khỏi một số ràng buộc gia đình/xã hội;
- **hiện thực**: đời sống xã hội, nghèo đói, bất bình đẳng, mâu thuẫn giai tầng;
- **phóng sự**: quan sát xã hội, điều tra, tốc độ báo chí;
- **tiểu thuyết Quốc ngữ**: hiện đại hóa kết cấu, nhân vật, đời tư;
- **truyền kỳ/kỳ án tiếp biến**: thể loại cũ tiếp tục biến đổi trong môi trường mới;
- thơ, truyện ngắn, kịch, dịch thuật và báo chí cùng tạo một trường văn học đa dòng.

Constraint: năm 1935 ở Hà Nội, Huế, Sài Gòn hay nông thôn không có cùng register.

### E6 — 1945–1954: cách mạng, kháng chiến và tái cấu trúc công chúng

- thơ, ký, truyện ngắn, bút ký, ký sự và văn xuôi kháng chiến có vai trò lớn;
- giọng cộng đồng, hành động, chiến trường, lao động, quê hương và lịch sử tăng trọng;
- ngôn ngữ công cộng/chính trị mạnh hơn, nhưng nhật ký, thư nhà và hội thoại đời thường vẫn có lớp riêng.

### E7 — 1954–1975: bắt buộc resolve theo vùng và hệ sinh thái văn hóa

Không được ghi `VIETNAM_1954_1975_STYLE` như một giọng đồng nhất.

#### E7-N — Miền Bắc

- văn học cách mạng, chiến tranh, xây dựng xã hội mới;
- thơ, truyện, ký, trường ca, văn xuôi chiến trường;
- khuynh hướng sử thi–lãng mạn và cái chung có trọng lượng lớn, nhưng tác giả/nhân vật vẫn có khác biệt.

#### E7-S — Đô thị miền Nam

- hệ sinh thái báo chí, xuất bản, dịch thuật và văn chương đô thị đa dạng;
- thơ tình, phản chiến, hiện sinh, tiểu thuyết mới, truyện ngắn, biên khảo–hư cấu và nhiều khuynh hướng khác cùng tồn tại;
- ảnh hưởng dịch thuật Pháp, Nga và các nguồn quốc tế tạo các register khác nhau.

#### E7-R — Nông thôn / chiến khu / vùng giao tranh

- lời nói và trải nghiệm không thể suy trực tiếp từ văn học đô thị hoặc văn bản tuyên truyền;
- medium liên lạc, an ninh, di chuyển và quan hệ cộng đồng tác động trực tiếp tới cách nói và mức thông tin một nhân vật có thể biết.

### E8 — 1975–1985: hậu chiến và giai đoạn chuyển giọng

- đời sống hậu chiến, tái thiết, gia đình, ký ức và tổn thương đi vào văn học;
- truyện ngắn cho thấy giọng tranh biện/đối thoại, suy luận–triết lý, xót xa–thương cảm;
- nhân vật cá nhân và tâm lý đời thường ngày càng tạo áp lực lên mô hình kể thuần sử thi.

### E9 — 1986–2000: Đổi Mới và đa giọng

- nhu cầu nói thật/nhận thức lại lịch sử và xã hội tăng;
- tiểu thuyết/truyện ngắn mở rộng con người cá nhân và đời sống thế sự;
- các giọng suy tư–triết lý, giễu nhại, trung tính/khách quan cùng tồn tại;
- dòng ý thức, kết cấu phi tuyến, liên văn bản và các kỹ thuật hiện đại được sử dụng rộng hơn;
- văn hóa dân gian tiếp tục tái sinh trong motif, biểu tượng, không gian và ngôn ngữ;
- kinh tế thị trường, di cư, đô thị hóa, nghề nghiệp và hàng hóa mới làm từ vựng đời thường đổi nhanh.

### E10 — 2001–2006: Internet còn có “địa điểm”

- dial-up/ADSL, máy tính để bàn, quán Internet, forum/chat tạo medium mới;
- 2003 ADSL mở ra băng rộng rõ hơn; Internet Việt Nam có khoảng 3,1 triệu người dùng theo VNNIC;
- “lên mạng” thường vẫn là một hành động có thời điểm/địa điểm rõ hơn so với smartphone era;
- lời thoại trực tiếp trong gia đình không tự động nhiễm ngôn ngữ chat;
- viết tắt, không dấu, biểu tượng và register nhóm trẻ có thể xuất hiện trong SMS/chat nhưng chỉ khi scene/nhân vật/medium cho phép.

### E11 — 2007–2012: hội nhập sâu hơn, 3G và chuyển từ PC sang mobile

Mốc nền:

- Việt Nam gia nhập WTO ngày 11/01/2007;
- 3G khai trương năm 2009;
- VNNIC ghi nhận xu hướng lớn năm 2009 là dịch thói quen Internet từ PC sang mobile;
- 2010–2012: cáp quang, smartphone/tablet và Internet băng rộng tăng mạnh;
- đến khoảng quý III/2012 có hơn 31 triệu người dùng Internet theo báo cáo VNNIC.

Worldbuilding consequence:

- thông tin đi vào đời sống nhanh hơn;
- người trẻ có nhiều register theo medium hơn: mặt đối mặt, SMS, chat, forum, blog, mạng xã hội;
- tiếng Anh, viết tắt và biến thể mạng có thể tăng nhưng phải gắn đúng cộng đồng sử dụng;
- khoảng cách ngôn ngữ giữa thế hệ và giữa online/offline dễ thấy hơn.

### E12 — 2013–2019: smartphone hóa và platform hóa

- online dần bớt là “nơi đi tới”, trở thành trạng thái mang theo người;
- camera, chat nhóm, notification, comment, meme và feed làm nhịp hội thoại ngắn hơn và context-switch dày hơn;
- một người có thể có nhiều giọng: gia đình, công việc, nhóm bạn, public post, private chat;
- quote, screenshot và context collapse trở thành yếu tố cốt truyện khả dụng.

Không gán slang cụ thể cho một năm nếu chưa có corpus/source phù hợp.

### E13 — 2020–2026: video ngắn, social language và lai mã tăng tốc

- social media và digital communication là nguồn đổi mới từ vựng quan trọng ở giới trẻ;
- slang, từ mới và English loanwords có mức sử dụng cao trong nhiều nhóm trẻ, nhưng phụ thuộc nền tảng, thân–sơ và ngữ cảnh;
- cùng một người có thể nói chuẩn trong họp, dùng slang với bạn, và quay về hệ xưng hô kinship trong gia đình trong cùng một ngày;
- ngôn ngữ nền tảng không được viết như “tiếng Việt mới” duy nhất.

### E14 — Tương lai

Không dự đoán từ lóng tương lai như fact.

Future dialogue dùng:

```text
KnownLanguageState(t0)
+ Social/TechPressures
+ BranchingLanguageDrift
+ InWorldCorpusEvidence
-> CandidateFutureRegister
```

Nếu chưa có in-world corpus hoặc historical bridge, giữ `FUTURE_REGISTER_OPEN`.

---

## 3. Genre Atlas — kho thể loại dùng làm “bút pháp áp lực”, không phải costume

Không thể khẳng định một danh sách hữu hạn là “tất cả thể loại từng tồn tại”. Atlas dùng **open registry**; khi phát hiện thể loại/nhánh mới, bổ sung với provenance.

### Oral / Folk

- thần thoại;
- truyền thuyết;
- cổ tích;
- ngụ ngôn;
- truyện cười;
- giai thoại;
- tục ngữ;
- câu đố;
- ca dao;
- dân ca/lời ru;
- truyện kể gia đình và ký ức cộng đồng.

### Medieval / Classical written

- thơ chữ Hán;
- thơ Nôm;
- văn biền ngẫu;
- chiếu/biểu/hịch/cáo như historical textual forms;
- sử truyện / ký;
- truyền kỳ;
- chí quái / truyện kỳ dị;
- truyện thơ Nôm;
- lục bát;
- song thất lục bát;
- ngâm khúc;
- ca trù / hát nói;
- diễn ca;
- văn tế.

### Modern transition / colonial-era

- báo chí Quốc ngữ;
- tiểu thuyết chương hồi chuyển tiếp;
- tiểu thuyết hiện đại;
- truyện ngắn;
- phóng sự;
- du ký;
- bút ký;
- tùy bút;
- kịch;
- thơ mới;
- lãng mạn;
- hiện thực;
- trào phúng;
- truyền kỳ/kỳ án hiện đại hóa;
- trinh thám, phiêu lưu và dịch thuật đại chúng.

### War / revolutionary / divided literary ecologies

- thơ cách mạng;
- thơ chiến tranh;
- trường ca;
- ký sự chiến trường;
- bút ký;
- truyện ký;
- nhật ký;
- thư;
- tiểu thuyết chiến tranh;
- truyện ngắn;
- thơ tình;
- phản chiến;
- văn chương đô thị;
- hiện sinh;
- tiểu thuyết mới / phản tiểu thuyết;
- biên khảo hòa vào hư cấu.

### Postwar / Doi Moi / contemporary

- truyện ngắn đời tư–thế sự;
- tiểu thuyết sự kiện;
- tiểu thuyết tâm lý;
- dòng ý thức;
- phi tuyến;
- đa thanh;
- giễu nhại;
- lịch sử xét lại / memory fiction;
- trinh thám / tình báo / phản gián;
- thiếu nhi;
- khoa học viễn tưởng;
- giả tưởng / kỳ ảo;
- horror;
- romance;
- family saga;
- autofiction-like forms nhưng không tự đồng nhất với tự truyện;
- speculative fiction;
- documentary fiction;
- mạng/blog/forum fiction;
- serialized web fiction;
- microfiction/platform-native writing;
- transmedia narrative.

Registry luôn mở.

---

## 4. Luật lời thoại theo medium

### Face-to-face

Ưu tiên quan hệ xưng hô, tuổi, vai vế, cảm xúc và không gian. Không bê cú pháp chat vào miệng nhân vật nếu không có lý do.

### Thư tay / nhật ký

Cho phép câu dài hơn, khoảng dừng dài, self-edit và khoảng cách thời gian giữa viết–đọc.

### Điện thoại bàn

Không có visual context; mở/đóng cuộc gọi và xác nhận người nghe quan trọng hơn.

### SMS

Độ dài, chi phí, bàn phím và tốc độ tạo pressure lên viết tắt. Không áp cùng kiểu viết cho mọi thế hệ.

### Chat / forum / blog

Nickname, quote, reply delay, emoticon, typo, viết không dấu và in-group code có thể quan trọng. Nhưng public forum != private chat.

### Social/mobile

Screenshot, forwarded context, voice note, emoji, meme, link, seen/read state và notification có thể là phần của hành động chứ không chỉ decoration.

---

## 5. Hệ xưng hô là state machine xã hội

Tiếng Việt dùng mạnh kin terms và relational terms ngoài quan hệ huyết thống.

Một nhân vật có thể chuyển:

```text
anh/em <-> tôi/bạn <-> cô/cháu <-> chú/cháu <-> bác/cháu <-> con/bố/mẹ...
```

khi thay đổi:

- tuổi tương đối được nhận thức;
- mức thân mật;
- vai trò nghề nghiệp;
- cảm xúc;
- quan hệ quyền lực;
- bối cảnh gia đình/công việc;
- vùng và tập quán nhóm.

Do đó dialogue engine phải lưu **relationship state**, không chỉ character name.

---

## 6. Year Override Ledger tối thiểu cho original timeline Việt Nam

| Năm | Reality anchor | Story-language consequence |
|---|---|---|
| 1986 | Đổi Mới | bắt đầu một chu kỳ biến đổi kinh tế–xã hội lớn; ký ức thế hệ trước/sau lệch nhau rõ |
| 1997 | Internet Việt Nam chính thức kết nối toàn cầu 19/11 | Internet tồn tại nhưng chưa ambient; lời nói về mạng còn mới với nhiều gia đình |
| 2002–2003 | chương trình/SGK mới triển khai theo lộ trình; ADSL xuất hiện | trẻ em gặp đồng thời cải cách giáo dục và Internet nhanh hơn |
| 2007 | WTO 11/01 | từ vựng hội nhập/thị trường/ngoại ngữ đi vào TV, báo chí và mâm cơm qua các hậu quả đời thường |
| 2009 | 3G; chuyển thói quen từ PC sang mobile | “online” bắt đầu rời khỏi địa điểm cố định |
| 2010–2012 | smartphone/tablet, cáp quang, hơn 31 triệu người dùng Internet vào 2012 | nhiều register online/offline cùng tồn tại; tốc độ truyền tin tăng |
| 2016+ | 4G và mobile broadband mở rộng | media-rich mobile communication trở thành bình thường hơn |
| 2020–2026 | social/video platform và slang/loanword đổi nhanh | phải resolve theo tuổi, platform, group và formal/informal context |

Các năm không có override kế thừa `ERA_BAND` + evidence cục bộ.

---

## 7. Cơ chế chọn bút pháp cho một scene

```text
Scene
-> ResolveYear/Era
-> ResolveRegion
-> ResolveSocialRelation
-> ResolveMedium
-> ResolveCharacterGeneration
-> ChooseNarrativePressure(genre registry)
-> CheckLexicalAvailability
-> CheckPronoun/Politeness State
-> CheckInformationAvailabilityAtThatYear
-> Write
-> Anachronism Audit
-> Reality Anchor Audit
```

`NarrativePressure` chỉ điều chỉnh:

- khoảng cách người kể;
- độ nén câu;
- nhạc tính;
- mức nội tâm;
- mức tài liệu/biên khảo;
- mức giễu nhại;
- cấu trúc tuyến tính/phi tuyến;
- mật độ sensory detail.

Nó không được copy fingerprint của một tác giả cụ thể.

---

## 8. Anachronism Audit

Mỗi scene lịch sử phải tự hỏi:

1. Từ này đã phổ biến trong nghĩa này vào năm đó chưa?
2. Thiết bị/medium này đã có trong cộng đồng này chưa?
3. Nhân vật này có lý do biết thông tin đó chưa?
4. Cách xưng hô có đúng quan hệ hiện thời không?
5. Người kể đang “giải thích hộ” nhân vật bằng khái niệm của tương lai không?
6. Có đang lấy một trend đô thị làm cả Việt Nam không?
7. Có đang lấy văn phong một tác giả làm văn phong cả thời đại không?
8. Có đang dùng historical pain như decoration không?

Nếu không chắc:

```text
SPECIFICITY DOWN
PROVENANCE UP
UNKNOWN PRESERVED
```

---

## 9. Sources / reality anchors used for this atlas

- HNUE / Khoa Ngữ văn — *Chữ Nôm và văn học chữ Nôm*: https://nguvan.hnue.edu.vn/Nghi%C3%AAn-c%E1%BB%A9u/p/987
- Đinh Thị Khang — nghiên cứu Truyện Nôm như thể loại trung đại: https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002284434
- HCMUE Journal — Western acceptance/localization in early twentieth-century Vietnamese literature: https://journal.hcmue.edu.vn/index.php/hcmuejos/article/view/3591?lang=en_US
- USSH VNU — Thơ lục bát trong phong trào Thơ mới 1932–1945: https://ussh.vnu.edu.vn/vi/dao-tao/luan-van/ttlv-tho-luc-bat-viet-nam-trong-phong-trao-tho-moi-1932-1945-7563.html
- Tạp chí Hội Nhà văn Việt Nam — thi pháp thể loại 1945–1975: https://vanvn.vn/dien-mao-van-hoc-viet-nam-tu-1945-1975-nhin-tu-thi-phap-the-loai/
- HCMUE Journal — dấu ấn Tiểu thuyết mới trong văn chương đô thị miền Nam 1954–1975: https://journal.hcmue.edu.vn/index.php/hcmuejos/article/view/2972
- HCMUE Journal — thơ tình/văn học đô thị miền Nam 1954–1975: https://journal.hcmue.edu.vn/index.php/hcmuejos/article/view/5041
- Tạp chí KH ĐH Cần Thơ — truyện ngắn nữ Việt Nam 1975–1985 nhìn từ giọng điệu trần thuật: https://ctujsvn.ctu.edu.vn/index.php/ctujsvn/issue/view/149
- VJOL / HCMUE — giọng điệu trần thuật tiểu thuyết Việt Nam 1986–2000: https://vjol.info.vn/sphcm/vi/article/view/23445/
- VJOL / HCMUE — cốt truyện sự kiện trong tiểu thuyết Việt Nam 1986–2000: https://vjol.info.vn/sphcm/vi/article/view/33419/
- Tạp chí KH ĐH Cần Thơ 2026 — văn học Việt Nam sau Đổi Mới: https://ctujsvn.ctu.edu.vn/index.php/ctujsvn/article/view/7988
- VJOL — văn học mạng trong tiến trình văn học Việt Nam: https://vjol.info.vn/khcn/vi/article/view/70034/
- VNNIC — Báo cáo 25 năm Internet Việt Nam: https://archive.vnnic.vn/sites/default/files/whitebook/BaoCaoTainguyenInternet2022.pdf
- VNNIC — Báo cáo tài nguyên Internet 2012: https://www.vnnic.vn/sites/default/files/2025-07/baocaotainguyeninternet2012.pdf
- Vietnamese person reference / kinship terms (Sidnell & Shohet, 2013): https://doi.org/10.1111/1467-9655.12053
- Recent youth-language variation under digital/social media pressure: https://doi.org/10.60087/ijls.v2.n3.003

---

## 10. Canon effect

Atlas này **không khóa plot tương lai**. Nó khóa phương pháp phục dựng:

```text
ExactYear -> YearOverride if available
otherwise -> EraBand
then -> Region + Relation + Medium + Generation
then -> LiteraryPressure
then -> AnachronismAudit
```

Một scene có thể được patch về từ ngữ/nhịp/cách xưng hô nếu audit tốt hơn xuất hiện, miễn không silent-retcon event đã khóa.
