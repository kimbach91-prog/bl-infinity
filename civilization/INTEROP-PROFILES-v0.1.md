# Interoperability Profiles v0.1

Việt Văn Minh Stack giữ canonical state riêng bằng VTTN/concept IDs, nhưng phải xuất được sang chuẩn mở để dữ liệu tồn tại và hữu dụng ngoài DEUS.

## Nguyên tắc

- Adapter không được trở thành gốc chân lý.
- Round-trip phải giữ được `conceptId`, provenance refs, epistemic class và disclosure class.
- Trường nào chuẩn ngoài không biểu đạt được phải nằm trong extension namespace có version, không bị lặng lẽ bỏ.
- Export PUBLIC/COMMON chỉ lấy dữ liệu đã qua Disclosure Boundary. RESTRICTED/BLACK_CORE không được xuất chỉ vì adapter hỗ trợ.

## Hồ sơ chuẩn

### PROV-O adapter
Áp dụng cho: VKT, VC, VKHOA, VKY.

Mapping tối thiểu:
- artifact/record -> `prov:Entity`
- tác giả/quản thủ/phần mềm -> `prov:Agent`
- thu thập/chuyển đổi/kiểm chứng -> `prov:Activity`
- `derivedFrom` -> derivation relation
- generation / use / attribution giữ thời gian và agent khi có.

Canonical provenance vẫn nằm trong schema Việt Văn Minh; PROV-O là interchange view.

### CIDOC CRM adapter
Áp dụng cho: VKY, VVAN và các phần lịch sử của VNG.

Dùng cho quan hệ giữa vật thể/tác phẩm/sự kiện/người/nơi/thời kỳ và chuỗi tư liệu văn hóa. Mọi mapping phải giữ `sourceRef` và không biến diễn giải đang tranh luận thành fact canonical.

### TEI P5 adapter
Áp dụng cho: VNG, VKY, VVAN.

Dùng để xuất/nhập văn bản nhân văn, bản chép, chú giải, biến thể văn bản và metadata textual. VTTN concept IDs phải được giữ bằng identifier/annotation extension thích hợp; không dùng TEI làm compiler IR.

### RO-Crate 1.3 adapter
Áp dụng cho: VKHOA, VC và snapshot nghiên cứu của VKT.

Mỗi research package có thể xuất thành RO-Crate JSON-LD chứa dữ liệu, metadata, phần mềm, người/tổ chức và quan hệ tạo lập. `SnapshotManifest` của Việt Văn Minh đóng vai trò integrity layer bổ sung; RO-Crate không thay thế root hash/checksum policy của sovereign snapshot.

## Round-trip test bắt buộc

```text
Canonical Record
 -> external adapter
 -> external representation
 -> import adapter
 -> canonical candidate
 -> semantic diff
```

PASS khi:
- concept IDs không mất;
- provenance không bị hạ cấp;
- epistemic class không bị đổi ngầm;
- disclosure class không rộng hơn;
- nội dung có thể khác encoding nhưng semantic diff = 0 hoặc có loss report rõ ràng.
