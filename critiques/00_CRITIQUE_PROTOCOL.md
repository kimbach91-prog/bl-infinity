# Giao thức phản biện BL∞ / BLOK

## Một phản biện tối thiểu nên có

1. **Target:** Claim ID hoặc đoạn canonical cụ thể.
2. **Type:** R1–R12.
3. **Attack:** premise/inference/evidence/definition nào bị đánh.
4. **Argument:** chuỗi lý do đủ để người khác kiểm tra.
5. **Evidence/model:** nguồn, computation, counterexample hoặc countermodel nếu cần.
6. **Requested status:** reject, revise, narrow scope, add evidence, mark speculative, no change.

## Mẫu

```yaml
critique_id: BL-R-XXXX
target: BL-P-XXX
type: R2-invalid-inference
summary: "..."
attack_surface: "premise P2 -> conclusion C"
argument: "..."
evidence: []
proposed_resolution: "revise"
author: "..."
date: "..."
```

## Trạng thái

- `OPEN`
- `UNDER_REVIEW`
- `UPHELD`
- `PARTIALLY_UPHELD`
- `REJECTED_WITH_REASON`
- `INCORPORATED`
- `DUPLICATE`
- `SUPERSEDED`

Một critique bị reject không bị xóa; reason được lưu để người ngoài audit.
