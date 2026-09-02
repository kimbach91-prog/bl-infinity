# 56 · BL-MTS — Nhánh Thống Hợp Học Thuyết Trưởng Thành

**Working name:** `BL Mature-Theory Synthesis Branch`  
**Code:** `BL-MTS`  
**Parent:** `BL∞`  
**Class:** external-theory preservation + cross-lineage synthesis + emergent-lineage compiler  
**Status:** `PUBLIC ARCHITECTURE · OPEN-ENDED · NON-EXHAUSTIVE`  
**Date:** `2026-09-02`

## 1. Mục tiêu

BL-MTS tạo một nhánh riêng để BL∞ có thể dùng các học thuyết, formalism và framework khoa học trưởng thành của nhân loại mà không xóa nguồn gốc của chúng.

```text
BL∞
└── BL-MTS
    ├── PRESERVED EXTERNAL THEORY FAMILIES
    ├── INTERSECTION MAP
    ├── HARMONIZATION MAP
    ├── DISAGREEMENT / NON-MERGE MAP
    └── BL-EMERGENT LINEAGE
```

BL-MTS không tuyên bố một danh sách hữu hạn có thể chứa “toàn bộ khoa học”. Nó là một registry mở có schema để tiếp tục hấp thụ theory family mới khi provenance và maturity đủ rõ.

## 2. Luật phả hệ

```text
ExternalTheory ∉ BL genealogy
ExternalTheory + BL bridge ≠ BL authorship
Similarity ≠ identity
Intersection ≠ proof
Synthesis ≠ historical ownership
```

Một object ngoài BL luôn giữ:

- tên chuẩn và phả hệ lịch sử;
- domain và phạm vi hiệu lực;
- maturity/evidence status;
- nguồn tham chiếu;
- các giới hạn hoặc open problems đã biết.

Chỉ object **mới sinh từ phép giao giữa nhiều lineage** mới có thể vào `BL-EMERGENT-LINEAGE`, và vẫn phải ghi đầy đủ cha mẹ bên ngoài + cha mẹ BL.

## 3. Năm quan hệ tổng hợp bắt buộc

### `INTERSECTS_WITH`
Có cấu trúc, câu hỏi, phương pháp hoặc constraint giao nhau.

### `HARMONIZES_WITH`
Hai object có thể cùng tồn tại trong scope rõ mà không cần đồng nhất ontology.

### `DISAGREES_WITH`
Prediction, assumption, ontology hoặc phạm vi áp dụng xung đột; phải giữ conflict thay vì ép hòa.

### `CANNOT_MERGE_WITH`
Giao nhau nhưng merge sẽ làm sai lineage, mất scope hoặc tạo claim mạnh hơn evidence.

### `GENERATES_CANDIDATE`
Va chạm tạo một cấu trúc BL-local mới. Candidate chưa phải truth và chưa phải novelty claim toàn cầu.

## 4. Compiler

Với mỗi theory family `T` ngoài BL:

```text
Preserve(T)
  ↓
Scope(T) + Evidence(T) + Lineage(T)
  ↓
Intersect(T, BL∞)
  ↓
{Agreement, Harmony, Disagreement, NonMerge}
  ↓
Collision
  ↓
CandidateEmergence
  ↓
Prior-art + Reality Veto + Provenance Gate
  ↓
BL-emergent lineage OR HOLD/REJECT
```

Không có transition `Imported → BL-owned`.

## 5. Các họ trưởng thành được nạp ở bản đầu

Bản khởi tạo bao phủ các family cốt lõi của:

- classical mechanics, electromagnetism, thermodynamics/statistical mechanics;
- special/general relativity;
- quantum mechanics, quantum field theory, Standard Model, Bell/entanglement, quantum information;
- cosmology, dark-sector inference, condensed matter;
- chemistry, chemical thermodynamics/kinetics, crystallography, 2D materials, quasicrystals, MOFs;
- plate tectonics, Earth-system/climate science;
- evolution, genetics, molecular biology, gene regulation, genomics, CRISPR, developmental biology;
- microbiology/infection, prions, protein structure, neuroscience;
- computability, complexity, information/coding, cryptography, control, probabilistic inference, statistical learning, neural networks;
- game/network/decision/causal frameworks với nhãn phạm vi phù hợp.

Registry machine-readable là nguồn chi tiết; danh sách này cố ý không được coi là exhaustive closure.

## 6. Điểm giao lớn với BL∞

### Scope-bounded validity
Nhiều theory trưởng thành cực mạnh trong một miền nhưng không tự nhận là ontology cuối cùng. Điểm giao với BL∞ là khả năng giữ `local closure` mà không suy thành `total closure`.

### Instrument-expanded reality surface
LIGO, genome sequencing, neurotechnology, collider và các measurement system cho thấy capability mới có thể mở phần Reality trước đó không quan sát trực tiếp được.

### Representation → prediction → intervention
Genomics, protein prediction, CRISPR và engineering cho thấy ba tầng này liên quan nhưng không đồng nhất.

### Negative knowledge
Một theory/claim bị bác, thu hẹp hoặc supersede vẫn tạo constraint cho successor. BL-MTS giữ cả failure lineage.

## 7. Điểm bất đồng / không được hòa giả

- Quantum entanglement không được đổi thành bằng chứng cho signalling ngược thời gian.
- Dark matter/dark energy không được đổi tên thành `UNKNOWN` của BL.
- Theory of computation không chứng minh mọi physical reality là computation.
- Neural networks không phải bằng chứng rằng biological brain và ANN là cùng ontology.
- Evolutionary processes không cho phép suy rằng mọi optimization system phải có biological fitness semantics.
- Statistical association không được merge thành causal mechanism nếu thiếu identification/evidence.
- Mature scientific consensus không phải absolute truth; nhưng outsider status cũng không làm một claim có xác suất đúng cao hơn.

## 8. BL-emergent lineage

Một candidate mới sinh từ va chạm phải có tối thiểu:

```text
EmergentObject = {
  BL_ID,
  BL_parent,
  external_parents[],
  collision_description,
  inherited_constraints[],
  new_delta,
  prior_art_status,
  falsifier_or_attack_surface,
  state
}
```

`new_delta` là bắt buộc. Không có delta thì đó chỉ là bridge/summary, không phải object mới của phả hệ BL.

## 9. Luật bảo toàn lịch sử

```text
Synthesis(x,y) does not erase x or y
Supersession does not erase ancestor
Rejection does not erase negative knowledge
New BL object does not retroactively own parent discoveries
```

## 10. Trạng thái nhận thức

BL-MTS phân biệt:

- `ESTABLISHED_DOMAIN_THEORY`
- `MATURE_FORMAL_FRAMEWORK`
- `STRONG_EMPIRICAL_FRAMEWORK`
- `OPEN_FRONTIER_WITH_MATURE_CORE`
- `REVISED_OR_SCOPE_LIMITED`
- `BL_EMERGENT_CANDIDATE`

Maturity không đồng nghĩa infallibility; open frontier không đồng nghĩa vô giá trị.

## 11. Quan hệ với External Science Constellation

`External Science Constellation` là atlas world-build và evidence surface. `BL-MTS` là compiler tổng hợp có bảo toàn lineage.

```text
External Science Constellation
        ↓ supplies preserved external objects
BL-MTS
        ↓ intersection/harmonization/disagreement/non-merge
BL-emergent candidates
        ↓ Reality Veto + prior-art + provenance
BL∞ lineage (chỉ khi đủ gate)
```

## 12. Hard invariants

1. `External science remains external by origin.`
2. `BL may synthesize without appropriating.`
3. `Agreement does not erase disagreement.`
4. `Intersection does not imply identity.`
5. `Emergence requires a demonstrable delta.`
6. `Every emergent object carries parent lineage.`
7. `Reality Veto outranks synthesis elegance.`
8. `Registry remains open-ended and non-exhaustive.`
