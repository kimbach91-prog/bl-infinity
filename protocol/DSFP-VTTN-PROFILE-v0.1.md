# DSFP–VTTN Profile v0.1

## Mục tiêu

DSFP là fabric vận chuyển/quyền; VTTN là lớp ngữ nghĩa. Profile này định nghĩa ranh giới giữa hai lớp để DEUS có thể hoạt động qua cloud, relay, LAN hoặc disconnected mode mà không buộc bên trung gian phải nhìn thấy source text hay ontology lõi.

## 1. Nguyên tắc

```text
Domain != Identity
Relay != Authority
Transport != Meaning
Reachable != Authorized
Readable envelope != readable payload
```

Danh tính đến từ khóa/chứng thư/capability đã xác thực. Domain chỉ là locator có thể thay thế.

## 2. Envelope tối thiểu

Relay được phép thấy tối đa:

```text
protocol_version
message_id
sender_public_id
recipient_public_id_or_group
capability_class
coarse_workload_class
expiry
delivery_priority
payload_length
cipher_suite_id
```

Relay không cần thấy:

```text
VTTN source
VTTN-IR
private concept IDs
prompt/context
raw reasoning
private topology
secrets
payload provenance contents
```

## 3. Payload

Payload logic:

```text
VTTN Source (optional at endpoint)
 -> typed VTTN-IR
 -> canonical encoding
 -> optional compartment split
 -> end-to-end encryption
 -> DSFP envelope
```

Endpoint nhận giải mã và kiểm tra capability trước khi render/execute.

## 4. Hai chế độ vận hành

### Federated Online

Có thể dùng DNS/CDN/Vercel/Cloudflare/other relays làm adapter. Adapter không là root of trust. Node có thể đổi relay mà không đổi identity hoặc semantic state.

### Sovereign / Disconnected

Không cần DNS công cộng, cloud control plane hay vendor account. Locator có thể là local discovery, static peer map, removable signed bundle hoặc private overlay. Cùng identity, capability, VTTN-IR và audit semantics được giữ nguyên.

## 5. Compartmentation

Một workload lớn có thể chia thành các compartment độc lập. Mỗi compartment có capability riêng và chỉ nhận phần VTTN-IR cần thiết. Không node trung gian nào mặc định nhận toàn bộ ontology hoặc task context.

## 6. Audit

Audit record chỉ giữ digest/correlation cần thiết ở lớp fabric. Semantic audit chi tiết thuộc endpoint hoặc trust domain có quyền. Không ghi source/payload plaintext vào relay logs mặc định.

## 7. Tương thích

- Crypto primitive là pluggable profile nhưng phải dùng primitive đã được đánh giá độc lập.
- VTTN version được ghi trong encrypted payload header.
- Concept package được content-addressed/signed.
- Relay upgrade không được làm thay đổi nghĩa VTTN.
- Vendor adapter có thể mất hoàn toàn mà sovereign mode vẫn giữ được dữ liệu, danh tính và khả năng biên dịch.

## 8. Black-core boundary

Profile công khai mô tả cơ chế. Những thứ sau thuộc private DEUS profile:

```text
private concept dictionary
routing utility function
private capability taxonomy
model-specific semantic lowering
protected ontology graph
private evaluator semantics
```

Do đó người ngoài có thể triển khai VTTN/DSFP hữu ích mà không suy ra được lõi DEUS.
