# Việt Văn Minh Stack v0.1

Mục tiêu: xây một lớp hạ tầng tri thức – ngôn ngữ – chứng minh – quyền – giáo dục – lưu trữ – khoa học – kinh tế – văn hóa có thể chạy độc lập khi cần, nhưng vẫn liên thông an toàn qua DSFP và biểu đạt ngữ nghĩa bằng VTTN.

## Nguyên tắc nền

1. **Ngữ nghĩa trước giao diện**: mọi nền tảng dùng concept ID và VTTN-IR, không phụ thuộc một nhà cung cấp hay một kiểu chữ cụ thể.
2. **Nguồn gốc bắt buộc**: dữ kiện lịch sử, ngôn ngữ, văn hóa, luật, khoa học phải có provenance; không hợp thức hóa suy đoán thành sự thật.
3. **Nhiều truyền thống, không một bản chất bất biến**: di sản Việt Nam được mô hình như mạng theo thời đại, vùng miền, cộng đồng, trường phái, nguồn và độ chắc chắn.
4. **Public/Common != DEUS Core**: tài nguyên có ích cho xã hội có thể mở; compiler profile, routing semantics, private ontology, eval/failure corpus và protected prompts của DEUS không được công khai.
5. **Offline-first khả dụng**: các nền tảng trọng yếu phải có snapshot, export, kiểm chứng hash và chế độ local/sovereign không cần Vercel, Cloudflare hoặc một cloud cụ thể.
6. **Interoperability, không lock-in**: adapter tới web/cloud chỉ là ngoại vi; identity, quyền, bằng chứng và canonical state không phụ thuộc DNS hay account của nhà cung cấp.
7. **Reality gate**: phân biệt OBS / INFER / ASSUME / NORM / HYPOTHESIS; không được dùng văn phong trang trọng để che độ bất định.

## Chín nền tảng

### 1. Việt Ngữ Platform — VNG
Từ điển concept Việt/Hán–Việt/Việt lịch sử; alias, nghĩa, thời kỳ, vùng, nguồn, quan hệ ngữ nghĩa; compiler vào VTTN-IR.

### 2. Việt Tri Thức Platform — VKT
Knowledge graph có provenance; claim, evidence, counterevidence, uncertainty, temporal validity và version lineage.

### 3. Việt Chứng Platform — VC
Proof/evidence ledger cho toán, logic, khoa học, chính sách và kiểm chứng tài liệu; tách chứng minh hình thức, bằng chứng thực nghiệm và lập luận triết học.

### 4. Việt Quyền Platform — VQ
Quyền, nghĩa vụ, capability, consent, revocation, delegation và audit. Không đồng nhất luật mô tả với luật thực định; mọi corpus pháp lý phải chỉ rõ thẩm quyền và thời điểm hiệu lực.

### 5. Việt Học Platform — VHOC
Curriculum graph theo prerequisite, mục tiêu năng lực, nguồn học, bài kiểm chứng và nhiều lộ trình; dùng tiếng Việt như ngôn ngữ tri thức bậc cao chứ không chỉ làm bản dịch.

### 6. Việt Ký Platform — VKY
Kho lưu trữ văn bản, âm thanh, hình ảnh, bản đồ, từ điển, bia ký, sách, tư liệu dân gian và metadata; ưu tiên format mở, checksum, replication và quyền truy cập rõ ràng.

### 7. Việt Khoa Platform — VKHOA
Lab notebook, hypothesis registry, experiment/eval records, negative results, reproducibility bundle và scientific lineage.

### 8. Việt Kinh Platform — VKINH
Sổ đóng góp, chi phí, compute, license, quyền lợi, settlement và provenance giá trị; không biến điểm tín dụng nội bộ thành tuyên bố tài chính nếu chưa có cơ sở pháp lý.

### 9. Việt Văn Platform — VVAN
Di sản văn hóa và sáng tạo: tác phẩm, thể loại, biểu tượng, phương ngữ, nghi lễ, nghề, tri thức dân gian, lịch sử diễn giải; mỗi mục phải tách nguồn gốc, diễn giải và sáng tạo mới.

## Bốn dịch vụ nền dùng chung

- **Concept Registry**: định danh nghĩa ổn định.
- **Provenance Ledger**: nguồn, tác giả, thời gian, giấy phép, hash và chuỗi dẫn xuất.
- **Evidence Ledger**: claim/evidence/counterevidence/status.
- **Disclosure Boundary**: PUBLIC / COMMON / RESTRICTED / BLACK_CORE.

## Quan hệ với DEUS

```text
Human / Institution
      ↓
VTTN semantic layer
      ↓
Việt Văn Minh Stack
      ↓
Canonical records + evidence + rights
      ↓
DSFP envelopes / local sovereign transport
      ↓
DEUS interfaces and authorized compute
```

DEUS được phép sử dụng các nền tảng này qua interface đã định danh; không được suy diễn rằng dữ liệu COMMON hay PUBLIC cho phép đọc BLACK_CORE.

## Thành công tối thiểu của v1

- cùng một record có thể tạo, kiểm chứng, export và đọc offline;
- mỗi claim có nguồn hoặc trạng thái `UNSOURCED` rõ ràng;
- mỗi khái niệm có concept ID bền vững và alias tiếng Việt;
- mỗi artifact có hash, license, provenance và disclosure class;
- một node độc lập có thể dựng lại canonical subset từ snapshot mà không cần nhà cung cấp trung gian;
- public corpus có thể tồn tại và phát triển tách khỏi DEUS private implementation.
