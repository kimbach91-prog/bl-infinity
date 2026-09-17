# ∞ DEUS · ARC-AGI-3 / LS20

## Nhật ký kết quả công khai · Public execution log

**7/7 màn hoàn thành · 348 hành động replay · Trạng thái cuối `WIN`.**

Bản trích kết quả của lượt xác minh ngày **17/09/2026**, phục vụ đối chiếu các số liệu DEUS trong bài công bố LS20. Nội dung dưới đây được lấy từ hai tệp `receipt.json` của cùng một workflow; bảng đối chiếu được tính lại từ hai tệp `transcript.json`.

English: Selected execution-receipt fields for the September 17, 2026 LS20 verification run. The cross-run comparison was recomputed from both retained transcripts. This document publishes results, not solver code or action sequences.

## 1. Kết quả và điều kiện đo · Results and configuration

| Trường / Field | ONLINE | NORMAL |
|---|---:|---:|
| Game | `ls20` | `ls20` |
| Seed | `0` | `0` |
| Màn hoàn thành / Levels completed | **7/7** | **7/7** |
| Trạng thái cuối / Final state | **WIN** | **WIN** |
| Hành động replay / Replay actions | **348** | **348** |
| Kết quả kiểm tra / Verification result | `PASS` | `PASS` |
| Giá trị `scorecard_score` trong receipt | `100.0` | `100.0` |
| Thời gian replay, giây / Replay seconds | `27.743752285` | `0.7031317139999942` |
| ARC toolkit | `arc-agi 0.9.9` | `arc-agi 0.9.9` |
| ARC engine | `arcengine 0.9.3` | `arcengine 0.9.3` |

**Định nghĩa phép đo:** 348 là độ dài đường giải thực thi lại sau khám phá; không bao gồm thử sai và reset trước đó. Thời gian trên là thời gian replay đã có đường giải, không phải thời gian tìm lời giải. `100.0` là giá trị scorecard ghi trong receipt của lượt LS20 này.

Measurement: post-exploration route replay. Earlier exploration/reset attempts are excluded; replay duration is not solution-discovery time.

## 2. Mốc hoàn thành từng màn · Per-level completion

Số hành động từng màn được tính bằng hiệu giữa hai mốc hoàn thành liên tiếp trong receipt. Hai môi trường có cùng các mốc dưới đây.

| Màn / Level | Hành động của màn / Actions | Lũy kế / Cumulative | Đã hoàn thành / Completed | Trạng thái sau mốc / State |
|---|---:|---:|---:|---|
| L1 | 13 | 13 | 1/7 | `NOT_FINISHED` |
| L2 | 45 | 58 | 2/7 | `NOT_FINISHED` |
| L3 | 49 | 107 | 3/7 | `NOT_FINISHED` |
| L4 | 53 | 160 | 4/7 | `NOT_FINISHED` |
| L5 | 63 | 223 | 5/7 | `NOT_FINISHED` |
| L6 | 72 | 295 | 6/7 | `NOT_FINISHED` |
| L7 | 53 | 348 | 7/7 | `WIN` |

**L1–L5: 223 hành động. L6: 72. L7: 53. Tổng: 348.**

## 3. Trích receipt ONLINE · ONLINE receipt excerpt

Các tên trường và giá trị trong khối JSON được giữ nguyên từ artifact gốc; những trường ngoài phạm vi công bố đã được lược bỏ.

```json
{
  "result": "PASS",
  "mode": "ONLINE",
  "game": "ls20",
  "seed": 0,
  "toolkit": "arc-agi 0.9.9",
  "engine": "arcengine 0.9.3",
  "run_id": "35225319065",
  "started_at": "2026-09-17T13:09:43.807523+00:00",
  "completed_at": "2026-09-17T13:10:11.551280+00:00",
  "actions_executed": 348,
  "prefix_actions": 223,
  "l6_actions": 72,
  "l7_actions": 53,
  "levels_completed": 7,
  "state": "WIN",
  "scorecard_score": 100.0,
  "exploration_actions_included": false
}
```

## 4. Trích receipt NORMAL · NORMAL receipt excerpt

```json
{
  "result": "PASS",
  "mode": "NORMAL",
  "game": "ls20",
  "seed": 0,
  "toolkit": "arc-agi 0.9.9",
  "engine": "arcengine 0.9.3",
  "run_id": "35225319065",
  "started_at": "2026-09-17T13:09:41.813189+00:00",
  "completed_at": "2026-09-17T13:09:42.516318+00:00",
  "actions_executed": 348,
  "prefix_actions": 223,
  "l6_actions": 72,
  "l7_actions": 53,
  "levels_completed": 7,
  "state": "WIN",
  "scorecard_score": 100.0,
  "exploration_actions_included": false
}
```

## 5. Đối chiếu từng bản ghi · Record-by-record comparison

Bảng này là kết quả kiểm tra lại dữ liệu đã lưu, không phải một lượt chơi mới. Với mỗi vị trí từ 1 đến 348, so sánh hai bản ghi tương ứng của ONLINE và NORMAL.

| Trường / Field | Khớp / Matched | Không khớp / Mismatched |
|---|---:|---:|
| `i` — thứ tự bản ghi / record index | 348/348 | 0 |
| `a` — hành động / action | 348/348 | 0 |
| `levels_completed` — số màn hoàn thành | 348/348 | 0 |
| `state` — trạng thái game / game state | 348/348 | 0 |
| `frame_sha256` — hash ảnh quan sát / observation hash | 348/348 | 0 |

Không công bố chuỗi hành động hoặc ảnh quan sát thô trong mục này. Chỉ công bố số lượng bản ghi khớp và định danh kiểm chứng.

## 6. Định danh nguồn · Evidence identifiers

| Thành phần / Item | Định danh / Identifier |
|---|---|
| GitHub workflow run | `35225319065` |
| ONLINE job | `105215286907` |
| NORMAL job | `105215286513` |
| Commit đã được runner sử dụng / Tested source commit | `33eddfc9a1f076f5652b1043f19db5f8dc529165` |
| ONLINE artifact | `10498008321` · `arc3-seven-level-verification-ONLINE` |
| NORMAL artifact | `10498118099` · `arc3-seven-level-verification-NORMAL` |
| Scorecard ID ghi trong ONLINE receipt | `fbff3d4d-ba23-46d9-900a-0a6f2a4293e9` |

SHA-256 của các gói artifact gốc, đã đối chiếu với metadata GitHub:

```text
ONLINE ZIP
1ad8f960e7a58d709ae83849af840a8befe3d95f22feb93c5dc7331f29e0b361

NORMAL ZIP
23cd54d086a90b26756eb3388111c149e42ee1ac43a3897787ae332f40b76d84
```

SHA-256 của hai tệp `receipt.json` gốc trước khi trích trường:

```text
ONLINE receipt.json
bbdac845a9347869079b90fb804be12a03636ae6b91d01738efe1e491fb62640

NORMAL receipt.json
e590a181e5f3b7b02281ed49e469aea69e52c0b2afb578fca468bd213994d528
```

## 7. Phạm vi công bố · Publication scope

Mục này chỉ trích nhật ký kết quả LS20 liên quan đến bài đăng: kết quả 7/7, độ dài replay, các mốc từng màn, thông số thực thi và đối chiếu hai môi trường. Không kèm mã bộ giải, công thức, chuỗi lệnh, prompt, dữ liệu lõi riêng tư hoặc nhật ký ngoài LS20.

Các số liệu của GPT-6 Astra trong bài đăng đến từ nguồn ARC Prize riêng; chúng không phải đầu ra của workflow DEUS và không được đưa vào đây dưới dạng nhật ký DEUS.

This extract is scoped to DEUS LS20 execution evidence. It does not republish solver implementation, action sequences, private prompts, or unrelated logs. Astra results are external comparison data, not output from this DEUS workflow.
