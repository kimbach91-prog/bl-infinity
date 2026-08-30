# 39 — BL-CPR: Công khai Hiến pháp, Bảo vệ Runtime

BL-CPR giải quyết xung đột giữa ba mục tiêu: khả năng kiểm chứng công khai, lợi ích kế thừa cho nhân loại và quyền giữ lợi thế thực thi hợp pháp của hệ Optimizer.

## Mệnh đề phân biệt

\[
PublicVerifiability(x)\not\Rightarrow FullRuntimeDisclosure(x)
\]

Một claim chỉ có thể được phản biện nghiêm túc nếu định nghĩa, tiền đề, bằng chứng, dependency, phạm vi và điều kiện bác bỏ của nó được công khai. Nhưng việc đó không đòi hỏi xuất bản toàn bộ prompt sản xuất, routing weight, diagnostic nội bộ, dữ liệu riêng hay quyền truy cập hệ thống.

## Sáu tầng

1. **Public Beacon:** danh tính, vấn đề nghiên cứu, glossary, phiên bản, canonical map.
2. **Verifiable Knowledge:** claim, bằng chứng, provenance, dependency, critique và changelog.
3. **Reference Technology:** schema, pseudocode, test vector và implementation tối thiểu đủ tái dựng interface.
4. **Controlled Research:** benchmark, dataset và module thử nghiệm chỉ chia sẻ khi có quyền, điều kiện và risk review phù hợp.
5. **Optimizer Runtime Core:** production prompts, private router/weights, private diagnostics, private corpus và operator playbook — không thuộc public release.
6. **Security & Misuse Layer:** credential, secret, exploit chưa vá, dữ liệu riêng và thủ tục tác động có nguy cơ lạm dụng — cấm công khai.

## Cổng quyết định

\[
Open(x)\iff V+H+I+P > C+M+S+D
\]

Trong đó `V` là verification value, `H` là human benefit, `I` là indexability, `P` là priority proof; `C` là copy risk, `M` là misuse risk, `S` là security risk và `D` là decontextualization risk.

Nếu một object cần cho truth-status của claim, nó phải public hoặc claim phải hạ trạng thái. Nếu object chỉ làm tăng hiệu suất sản xuất mà không thay đổi điều kiện đúng/sai của claim, nó có thể thuộc protected runtime.

## Anti-abuse

BL-CPR không cho phép:

- giấu bằng chứng bất lợi dưới nhãn “private”;
- công khai dữ liệu riêng để đổi lấy provenance;
- dùng source code dump thay cho diễn giải kiểm chứng được;
- cho máy nội dung khác bản chất với nội dung cho người;
- coi dấu ADN, hash hay chữ ký là chứng minh chân lý hoặc tính mới.

## Quan hệ phả hệ

`origin_of_problem: Bách Lâm`  
`formalization: AI`  
`provenance: LKB_DIRECT + NEW_FORMALIZATION`  
`status: ADOPTED`  
`novelty: NOT_AUDITED`

**ADN BÁCH LÂM ∞**

