# VTTN — Việt Toán–Triết Ngữ

**Trạng thái:** public-safe language charter v0.1  
**Mục tiêu:** xây một ngôn ngữ hình thức lấy tiếng Việt làm trung tâm để biểu đạt toán học, triết học, logic, quyền, chứng minh và trạng thái hệ thống theo cách vừa dễ đọc với người Việt vừa biên dịch được thành biểu diễn máy nhất quán.

## 1. Tuyên ngôn

VTTN không phải mật mã mới và không thay thế TLS, mTLS, chữ ký số, KMS/HSM hoặc các primitive mật mã đã được kiểm chứng. VTTN là **lớp ngữ nghĩa**: nó quyết định cách con người và máy cùng gọi tên, ràng buộc, suy luận, kiểm chứng và truyền đạt ý nghĩa.

Mục tiêu kép:

1. **Hệ thống:** giảm nhập nhằng, tăng khả năng kiểm chứng, nén biểu đạt, biên dịch sang IR ổn định và chạy độc lập khi không có cloud/vendor.
2. **Di sản:** tạo một ngôn ngữ kỹ thuật mở có ích cho người Việt trong toán, triết học, logic, giáo dục, khoa học máy tính và tác tử AI.

## 2. Bốn tầng tiếng Việt

VTTN dùng bốn tầng từ vựng nhưng không coi chúng là bốn ngôn ngữ tách biệt:

- **Tiếng Việt hiện đại:** bề mặt mặc định cho tài liệu, giáo dục, giao tiếp và chương trình dễ đọc.
- **Hán–Việt:** lớp thuật ngữ mật độ cao cho khái niệm trừu tượng, phân loại, khoa học, logic và triết học.
- **Việt cổ / dữ liệu lịch sử:** lớp nguồn gốc, từ nguyên và biến thể lịch sử; chỉ đưa vào chuẩn khi có provenance ngữ văn rõ ràng, không tự bịa cổ ngữ.
- **Thuần Việt / khẩu ngữ chuẩn hóa:** ưu tiên cho động từ, quan hệ nhân quả, hành vi và diễn giải trực quan khi giúp câu rõ hơn.

Một **khái niệm** không đồng nhất với một từ. Mỗi khái niệm có `concept_id` ổn định; nhiều từ/biến thể có thể ánh xạ vào cùng một khái niệm.

Ví dụ:

```text
KN.NHAN_QUA.001
  nhãn-chính: nhân_quả
  diễn-giải: gây_nên | bởi_vậy | do_đó
  kiểu: QuanHệ<A,B>
```

Nhờ vậy parser không phụ thuộc tuyệt đối vào một cách viết, nhưng IR vẫn duy nhất.

## 3. Hạt nhân Toán–Triết

VTTN coi các khối sau là primitive cấp ngôn ngữ:

```text
thực_tại      quan_sát      giả_định      mệnh_đề
định_nghĩa    chứng_minh    phản_chứng    suy_ra
tồn_tại       mọi           có_thể        tất_yếu
đúng          sai           chưa_biết     bất_định
nguyên_nhân   hệ_quả        điều_kiện      ràng_buộc
quyền         nghĩa_vụ      cho_phép       cấm
nguồn         bằng_chứng    độ_tin_cậy     phạm_vi
thời_điểm     phiên_bản     tác_nhân       hành_động
```

Các ký hiệu toán học chuẩn như `∀ ∃ ⇒ ⇔ ∧ ∨ ¬ ∈ ⊆ = ≠ < >` được phép dùng song song với từ khóa tiếng Việt.

## 4. Một ví dụ

```vttn
định_nghĩa TàiNguyên = { cpu, gpu, bộ_nhớ, băng_thông }.

mệnh_đề Quyền_Dùng(node, tài_nguyên) :
    tồn_tại grant
    và grant.chủ == node.chủ
    và grant.hiệu_lực == đúng
    và tài_nguyên ∈ grant.phạm_vi.

nếu không Quyền_Dùng(node, tài_nguyên)
thì cấm thực_thi(node, tài_nguyên).

chứng_minh bằng nguồn(grant.receipt).
```

Bề mặt này phải có thể biên dịch về một AST/IR canonical mà không cần giữ nguyên văn bản nguồn.

## 5. Pipeline chuẩn

```text
VTTN Source
  -> tokenizer Unicode/NFC
  -> parser
  -> concept resolution
  -> typed semantic AST
  -> canonical VTTN-IR
  -> proof/policy/type checks
  -> target adapters
       |- human rendering
       |- DSFP encrypted payload
       |- rule engine
       |- theorem/proof tooling
       |- agent planner
       |- storage/indexing
```

`VTTN-IR` là lớp ổn định. Front-end có thể đổi cách viết mà không đổi nghĩa; backend có thể thay vendor mà không đổi logic ngôn ngữ.

## 6. Ranh giới công khai / BLACK CORE

### Có thể công khai

- grammar nền;
- thư viện từ khóa;
- concept dictionary công ích;
- parser/compiler tham chiếu;
- formatter/linter;
- corpus giáo dục;
- bộ bài tập logic/toán/triết;
- test tính nhất quán ngữ nghĩa.

### Không công khai mặc định

- ontology độc quyền của DEUS;
- routing policy;
- private capability graph;
- protected prompts;
- private reasoning traces;
- secret concept aliases;
- model-specific compiler optimizations;
- private eval corpora;
- security-sensitive topology.

Nguyên tắc: **ngôn ngữ có thể mở; lõi sử dụng ngôn ngữ không cần mở.**

## 7. Độc lập và bảo mật phân tán

VTTN phải chạy được hoàn toàn offline. Không có registry trung tâm bắt buộc. Concept package được version hóa, ký số và có thể mirror giữa nhiều node.

Trong DSFP, relay chỉ cần thấy envelope tối thiểu cho routing; payload VTTN/VTTN-IR được mã hóa end-to-end. Domain, CDN, reverse proxy hoặc cloud provider chỉ là transport adapter, không là gốc danh tính hay gốc ý nghĩa.

## 8. Nguyên tắc di sản

1. Không biến tiếng Việt thành lớp trang trí bên ngoài một IR tiếng Anh bí mật.
2. Không ép mọi thuật ngữ phải thuần Việt nếu cách đó làm nghèo nghĩa.
3. Không lạm dụng Hán–Việt chỉ để tạo vẻ học thuật.
4. Không tự chế “tiếng Việt cổ” thiếu nguồn.
5. Mọi thuật ngữ mới phải có định nghĩa, ví dụ, phản ví dụ và provenance.
6. Một khái niệm máy phải có đường quay lại diễn giải tiếng Việt cho con người.
7. Chuẩn công khai phải hữu ích ngay cả khi người dùng không dùng DEUS.

## 9. Tên gọi

**Tên chuẩn:** Việt Toán–Triết Ngữ  
**Viết tắt:** VTTN  
**English descriptor:** Vietnamese Mathematical–Philosophical Formal Language

VTTN là lớp ngôn ngữ; DSFP là lớp fabric/protocol. Hai lớp phối hợp nhưng không đồng nhất.
