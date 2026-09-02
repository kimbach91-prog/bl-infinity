# BL∞ Culture Chamber / Buồng Nuôi Cấy

**Namespace:** `BL-INF-CULTURE-CHAMBER`  
**Class:** incubator / reversible research sandbox / candidate-only surface  
**Canonical effect:** `NONE`  
**Promotion:** only through explicit review, evidence, Reality Veto and owner decision  
**Created:** 2026-09-02  
**Base public repository state when opened:** `0.5.5-mts-open-world-ingestion`  
**Base commit observed:** `975d8151ae05c1b65ab8bbb9dea9da28470ce979`

## Purpose

Buồng Nuôi Cấy là vùng để giữ các cấu kiện mới trước khi chúng đủ điều kiện trở thành doctrine, protocol, machine object hoặc runtime policy chính thức của BL∞.

Nó cho phép:

- bảo tồn ý tưởng thô và causal history;
- formalize nhiều biến thể cạnh tranh;
- chạy benchmark, adversarial test và prior-art check;
- giữ `UNKNOWN` thay vì ép kết luận;
- rollback hoặc quarantine một nhánh mà không làm mất lịch sử;
- promote chỉ các delta có bằng chứng và giá trị dương.

## Core invariants

```text
INCUBATED != CANONICAL
MODEL != EMPIRICAL FACT
SIMULATION != REAL-WORLD EXECUTION
PREDICTION != FUTURE KNOWLEDGE
DELEGATED EXECUTION != IDENTITY COLLAPSE
SECURITY != HISTORY ERASURE
CONSTRAINT NAVIGATION != CONSTRAINT EVASION
COURAGE != BLIND COMMITMENT
VIGILANCE != PARALYSIS
```

## Evidence rule

Mọi con số benchmark được nói trong hội thoại nhưng chưa có script/dataset/seed có thể tái lập phải mang trạng thái:

`UNVERIFIED_SESSION_RESULT`

Chúng không được dùng làm evidence canonical cho tới khi được chạy lại và lưu đủ:

- code/version;
- dataset hoặc generator;
- seed;
- metric definition;
- runtime/hardware context khi liên quan;
- output artifact;
- error/failure cases.

## Promotion gate

Một object trong chamber chỉ được đề nghị promote khi có tối thiểu:

1. identity + provenance rõ;
2. scope và non-claims;
3. typed dependencies;
4. falsifier / failure modes;
5. benchmark hoặc argument test phù hợp;
6. Reality Veto result;
7. compatibility check với BL-CONSERVE / BL-ADN;
8. explicit promotion decision.

Không có auto-promotion từ việc được ghi vào repository.
