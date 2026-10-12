# AGENTS.md — THEOLOI monorepo

## Quy trình riêng

- Đọc SETUP.md, PROJECT.md, README.md, docs/MASTER_ROADMAP.md, docs/ROADMAP.md, docs/CURRENT_PHASE.md, docs/TASKS.md và báo cáo phase trước; kiểm tra Git/branch và blocker, không bootstrap lại dự án.
- Phạm vi tự chủ là phase/task người dùng giao. Hoàn thành plan → implement → test → fix → review → document → Git trong phạm vi đó; không dừng giữa các task nhỏ. Sau nghiệm thu, đề xuất 3–5 công việc tiếp theo và DỪNG tại ranh giới phase, trừ khi người dùng đã yêu cầu làm hết/nhiều phase. Không tự hiểu roadmap dài hạn là quyền triển khai toàn bộ.
- Khi người dùng nói “Tiếp tục”, đọc CURRENT_PHASE/ROADMAP: tiếp tục phần chưa xong của phase hiện hành; nếu đã hoàn tất, bắt đầu phase được đề xuất gần nhất. Phê duyệt phase không thay phê duyệt production/chi phí/quyền nội dung.
- Trạng thái phase: NOT STARTED / IN PROGRESS / BLOCKED / READY FOR REVIEW / DONE. Chỉ DONE khi acceptance có bằng chứng; phân biệt unit/integration/browser/Windows native/live Cloudflare/user acceptance. Cập nhật CURRENT_PHASE, TASKS, CHANGELOG, DECISIONS/BACKLOG khi phù hợp, không tạo hệ thống roadmap trùng.
- Windows tại apps/windows, backend tại workers/media-api; pipeline giữ scripts/tests và metadata namespaces root. Không tạo package mobile/shared rỗng.
- Không đọc/in/commit .secrets, env thật, cookie, token/credential/session. Operational datasets, snapshots, generated production catalogs là local-only theo .gitignore. Audit index trước push.
- Không sửa 983 media, catalog/manifest gốc, assetId/objectKey hoặc Cloudflare config trong task source thông thường; không tự download/upload/live B10/deploy.
- Clone source cần private inputs do người quản lý cung cấp để chạy full regression/playback. Không fake audio hoặc tải bù để làm test pass.
- Context7 cho cú pháp library/framework/API/CLI; không cần cho refactor thuần hoặc logic nghiệp vụ.
- Không force-push/destructive reset/ghi đè remote. Cập nhật TASKS/audit bằng kết quả thực tế; phân biệt offline/local với native/live.

Các nguyên tắc chung bên dưới tiếp tục áp dụng khi không xung đột yêu cầu người dùng.

# Universal Project Rules

Tài liệu này quy định cách coding agent làm việc trong repository.

File này được thiết kế để có thể tái sử dụng cho nhiều loại project:

- Web
- App
- Telegram/Discord Bot
- CLI
- API
- Automation
- Python tool
- JavaScript/TypeScript project
- Project có hoặc không có UI

Các yêu cầu riêng của từng project phải nằm trong:

```text
PROJECT.md
SPEC.md
docs/ROADMAP.md
docs/TASKS.md
DESIGN.md
ARCHITECTURE.md
```

nếu các file đó tồn tại.

`AGENTS.md` chỉ chứa **nguyên tắc làm việc chung**.

---

# 1. Thứ tự đọc context

Trước khi bắt đầu làm việc:

1. Đọc `AGENTS.md`.
2. Nếu đang bootstrap project và có `SETUP.md`, đọc và làm theo `SETUP.md`.
3. Đọc `PROJECT.md` hoặc `SPEC.md` nếu tồn tại.
4. Đọc `docs/ROADMAP.md` nếu tồn tại.
5. Đọc `docs/TASKS.md` nếu tồn tại.
6. Đọc các tài liệu liên quan khác khi task thực sự cần.

Không giả định requirement nếu project đã có tài liệu mô tả.

Ưu tiên thông tin cụ thể của project hơn các rule chung trong file này.

---

# 2. Nguyên tắc quan trọng nhất

Ưu tiên:

> **smallest correct solution**

Giải pháp tốt nhất không phải giải pháp:

- nhiều code nhất;
- nhiều abstraction nhất;
- nhiều package nhất;
- trông "enterprise" nhất.

Giải pháp tốt là giải pháp:

- đúng;
- nhỏ;
- rõ ràng;
- dễ kiểm tra;
- dễ sửa;
- dễ bảo trì.

---

# 3. Ponytail Principle

Triết lý tham chiếu:

```text
DietrichGebert/ponytail
```

Tinh thần:

> Code tốt nhất đôi khi là code không cần viết.

Trước khi tạo code mới, đi lần lượt theo ladder sau:

```text
1. Functionality này có thực sự cần tồn tại không?
        ↓
2. Codebase đã có thứ giải quyết nó chưa?
        ↓
3. Standard library có giải quyết được không?
        ↓
4. Platform/native API có giải quyết được không?
        ↓
5. Dependency hiện tại có giải quyết được không?
        ↓
6. Một đoạn code nhỏ, trực tiếp có đủ không?
        ↓
7. Chỉ sau đó mới cân nhắc dependency hoặc abstraction mới.
```

Không sử dụng simplicity như lý do để bỏ:

- security;
- validation tại trust boundary;
- accessibility;
- error handling quan trọng;
- bảo vệ dữ liệu;
- correctness.

Phải hiểu vấn đề trước rồi mới tối giản.

Không "đơn giản hóa" bằng cách bỏ requirement.

---

# 4. Ponytail Integration

Project không được phụ thuộc vào việc Ponytail plugin có được cài hay không.

Các rule cốt lõi đã được định nghĩa trong `AGENTS.md`.

Nếu Ponytail skill/plugin tồn tại trong coding environment:

- có thể sử dụng nó khi phù hợp;
- có thể dùng review/audit để phát hiện over-engineering;
- có thể sử dụng các workflow bổ sung của nó.

Nếu Ponytail không tồn tại:

> Tiếp tục làm việc bình thường theo các rule trong file này.

Không tự clone Ponytail source vào repository chỉ để sử dụng các nguyên tắc trên.

---

# 5. YAGNI

Không xây functionality chỉ vì:

> "Sau này có thể cần."

Chỉ xây những gì:

- requirement hiện tại cần;
- milestone hiện tại cần;
- hoặc cần thiết để implementation hiện tại đúng và an toàn.

Không tự thêm:

- backend;
- database;
- authentication;
- account system;
- API server;
- caching layer;
- queue;
- plugin system;
- microservices;
- state-management library;
- abstraction framework;
- analytics;
- cloud service;

nếu project chưa thực sự cần.

---

# 6. Scope

Chỉ sửa những phần liên quan đến task.

Không:

- refactor toàn project khi đang sửa một feature nhỏ;
- đổi architecture chỉ vì thích cách khác;
- đổi framework;
- rewrite code đang chạy tốt;
- format hàng loạt file không liên quan;
- đổi dependency không liên quan;
- tự thêm feature ngoài scope.

Nếu phát hiện improvement ngoài scope:

Ghi nhận nó.

Không tự triển khai trừ khi:

- cực nhỏ;
- rõ ràng cần thiết;
- ít rủi ro;
- trực tiếp hỗ trợ task hiện tại.

---

# 7. Technology Stack

Không có stack mặc định trong file này.

Stack phải được xác định từ:

```text
PROJECT.md
package.json
pyproject.toml
requirements.txt
Cargo.toml
go.mod
pom.xml
build.gradle
```

hoặc các file cấu hình tương đương.

Không đổi framework hoặc language nếu người dùng không yêu cầu.

Ưu tiên công nghệ project đang sử dụng.

---

# 8. Dependencies

Trước khi thêm dependency mới, kiểm tra:

1. Có thực sự cần không?
2. Platform có solution native không?
3. Standard library có solution không?
4. Project đã có dependency giải quyết việc này chưa?
5. Một đoạn code nhỏ có đơn giản hơn không?

Nếu một trong các cách trên đủ tốt:

> Không thêm dependency.

Nếu cần dependency mới:

- chọn dependency phổ biến và còn được maintain;
- tránh package quá lớn cho functionality nhỏ;
- kiểm tra compatibility;
- không thêm nhiều library giải quyết cùng một việc.

---

# 9. Architecture

Không tạo abstraction trước khi có vấn đề thực tế.

Không tự tạo các pattern như:

```text
Repository
Factory
Manager
Adapter
Service Layer
Event Bus
Plugin System
Generic Engine
```

nếu project chưa cần.

Không tạo:

- custom hook chỉ dùng một lần;
- utility file cho vài dòng logic;
- wrapper quanh API đơn giản;
- config system cho vài giá trị;
- component chỉ để bọc JSX/HTML nhỏ.

Chỉ abstraction khi:

- pattern thực sự lặp lại;
- domain boundary rõ ràng;
- abstraction làm code dễ hiểu hơn;
- abstraction giảm complexity thực tế.

Duplication nhỏ và dễ hiểu đôi khi tốt hơn abstraction quá sớm.

---

# 10. State & Data

Ưu tiên state đơn giản nhất phù hợp với stack.

Thứ tự suy nghĩ:

```text
derived value
↓
local state
↓
shared state hiện có
↓
project-native solution
↓
state library mới
```

Không duplicate state nếu có thể derive.

Không thêm database nếu:

- local file;
- local storage;
- memory;
- existing persistence;

đã đủ đáp ứng requirement.

Việc lựa chọn persistence phải dựa vào requirement của project.

---

# 11. UI/UX — chỉ áp dụng khi project có UI

Nếu project không có UI:

> Bỏ qua section này.

Nếu project có UI:

Ưu tiên:

- clarity;
- usability;
- visual hierarchy;
- responsive behavior;
- accessibility;
- consistency.

Không hy sinh usability để đổi lấy hiệu ứng.

Tránh UI AI-generic như:

- quá nhiều card;
- gradient vô nghĩa;
- excessive shadow;
- excessive rounded container;
- badge ở mọi nơi;
- dashboard layout khi sản phẩm không phải dashboard;
- animation không phục vụ interaction.

Nếu environment có UI/UX skill phù hợp:

- sử dụng nó như design guidance;
- không biến skill đó thành runtime dependency;
- không copy nguyên branding/assets/UI của sản phẩm khác.

Nếu project có `DESIGN.md`:

> `DESIGN.md` là nguồn chính cho visual direction.

---

# 12. Accessibility

Nếu project có user interface:

Không bỏ accessibility chỉ để giảm code.

Ưu tiên:

- semantic elements;
- keyboard navigation;
- visible focus;
- readable contrast;
- proper labels;
- ARIA khi semantic HTML không đủ;
- touch targets hợp lý.

Accessibility là correctness, không phải decoration.

---

# 13. Performance

Không premature optimization.

Nhưng tránh những vấn đề rõ ràng như:

- unnecessary repeated work;
- unnecessary re-render;
- duplicate network calls;
- event listener leak;
- unbounded loop;
- unnecessary large assets;
- dependency lớn cho task nhỏ.

Chỉ tối ưu sâu khi:

- có benchmark;
- có profiling;
- hoặc bottleneck rõ ràng.

---

# 14. Trước khi code

Trước mỗi task:

1. Hiểu requirement.
2. Kiểm tra `git status`.
3. Đọc code liên quan.
4. Trace flow hiện tại.
5. Kiểm tra functionality tương tự đã tồn tại chưa.
6. Xác định root của thay đổi.
7. Chọn smallest correct solution.
8. Sau đó mới sửa code.

Không bắt đầu bằng việc tạo file mới.

Bắt đầu bằng việc hiểu code hiện có.

---

# 15. Autonomous Execution

Khi được giao một implementation task:

> Own it end-to-end.

Không dừng sau:

- analysis;
- planning;
- skeleton;
- implementation đầu tiên;
- test đầu tiên;
- build pass.

Tiếp tục qua:

```text
inspect
↓
plan
↓
implement
↓
test
↓
verify
↓
fix
↓
retest
↓
complete
```

Không hỏi:

```text
Should I continue?
Should I implement the next step?
Should I test it?
Should I fix this?
Would you like me to proceed?
```

nếu đó rõ ràng là bước cần thiết để hoàn thành task.

Tự đưa ra quyết định kỹ thuật nhỏ nếu:

- hợp lý;
- ít rủi ro;
- dễ hoàn tác;
- không thay đổi requirement.

---

# 16. Khi nào phải hỏi

Chỉ hỏi khi thực sự cần quyết định của người dùng.

Ví dụ:

- requirement có nhiều cách hiểu quan trọng;
- thay đổi architecture đáng kể;
- đổi framework/language;
- thêm backend/database lớn;
- sử dụng paid service;
- cần credentials;
- breaking change;
- nguy cơ mất dữ liệu;
- production-impacting action;
- security-sensitive decision;
- thay đổi behavior người dùng mong muốn;
- quyết định scope sản phẩm lớn.

Nếu có nhiều câu hỏi:

> Gom thành một lần hỏi.

Không hỏi từng câu nhỏ liên tục.

---

# 17. Fix Bug

Khi sửa bug:

```text
reproduce
↓
trace
↓
find root cause
↓
fix root cause
↓
test
↓
regression check
```

Không:

- che lỗi bằng workaround nếu root cause có thể sửa;
- suppress exception chỉ để test pass;
- xóa validation chỉ để code chạy;
- thay đổi unrelated code.

Nếu không reproduce được:

Ghi rõ điều đó.

Không giả vờ đã xác nhận root cause.

---

# 18. External Documentation

Khi làm việc với:

- framework;
- library;
- API;
- SDK;
- cloud service;
- tool có version thay đổi nhanh;

không đoán API nếu documentation có thể kiểm tra.

Nếu Context7 hoặc documentation tool tương đương có sẵn:

> Sử dụng khi cần.

Ưu tiên:

```text
current project version
+
official documentation
```

hơn memory của model.

Không tự cài tool chỉ để tra một thông tin nếu web/docs hiện tại đủ giải quyết.

---

# 19. Skills / Plugins / MCP

Skills, plugins và MCP là khả năng bổ sung cho coding agent.

Chúng không phải mặc định là dependency của project.

Trước khi sử dụng:

1. Kiểm tra tool có tồn tại không.
2. Kiểm tra nó có thực sự phù hợp task không.
3. Chỉ sử dụng nếu benefit rõ ràng.

Ví dụ:

```text
Context7
→ documentation

Serena
→ semantic codebase navigation

Playwright MCP
→ browser interaction / QA

UI/UX skill
→ design guidance

Ponytail
→ simplicity / over-engineering review
```

Nếu tool hữu ích nhưng chưa tồn tại:

- có thể đề xuất;
- hoặc để `SETUP.md` xử lý trong tool audit.

Không tự clone repository vào source code chỉ vì đó là một development tool.

---

# 20. Testing

Sau mỗi thay đổi có ý nghĩa:

Chạy validation phù hợp với project.

Có thể bao gồm:

```text
unit tests
integration tests
typecheck
lint
build
```

Không giả định tất cả project đều có tất cả các command trên.

Đọc project scripts/config trước.

Không tạo test framework lớn chỉ để test một logic rất nhỏ.

Nhưng business logic quan trọng phải có verification đáng tin cậy.

---

# 21. Test như người dùng thật

Nếu project có interface hoặc executable flow:

Không chỉ chứng minh:

```text
code compiles
```

Phải chứng minh behavior hoạt động.

Ví dụ web:

```text
open
navigate
click
type
reload
responsive check
console check
```

Ví dụ API:

```text
request
response
validation
failure case
```

Ví dụ bot:

```text
command
input
response
persistence
restart when relevant
```

Ví dụ CLI:

```text
run command
valid input
invalid input
exit code
output
```

Nếu Playwright/browser automation có sẵn và project là web:

Sử dụng khi hợp lý.

---

# 22. Verification Before Completion

Không báo task hoàn thành chỉ vì:

```text
build passed
```

Trước khi báo Done, tự kiểm tra:

- requirement đã được đáp ứng chưa?
- có bỏ sót edge case quan trọng không?
- test phù hợp đã pass chưa?
- có regression rõ ràng không?
- có complexity không cần thiết không?
- có dependency không cần thiết không?
- có debug code không?
- có secret không?
- có file thừa không?
- working tree có thay đổi ngoài scope không?

Nếu phát hiện vấn đề có thể tự sửa:

> Sửa rồi verify lại.

---

# 23. Security

Không bao giờ:

- hard-code secrets;
- commit `.env`;
- commit token;
- commit API key;
- commit password;
- commit private key;
- log secret.

Secrets phải dùng mechanism phù hợp như:

```text
environment variables
secret manager
CI/CD secret
```

Nếu `.env` được sử dụng:

Nên có:

```text
.env.example
```

không chứa secret thật.

Khi project có secret-scanning tool như Gitleaks:

Sử dụng trước các checkpoint quan trọng khi phù hợp.

---

# 24. Git Safety

Không:

```text
force push
rewrite history
reset destructive
delete branch
delete repository
overwrite remote
revert user changes
```

nếu chưa có explicit approval.

Không commit:

- secrets;
- generated junk;
- debug files;
- dependency directory;
- build artifacts không cần track.

Trước checkpoint quan trọng:

```bash
git status
git diff
```

Commit nên nhỏ và có ý nghĩa.

Ví dụ:

```text
feat: add recurring reminders
fix: handle invalid reminder time
test: cover reminder scheduling
```

---

# 25. Không ghi đè công việc của người khác

Repository có thể chứa thay đổi chưa commit của:

- người dùng;
- agent khác;
- collaborator.

Không mặc định những thay đổi đó là rác.

Trước khi sửa:

```text
git status
```

Nếu gặp thay đổi không liên quan:

Tránh ghi đè.

Không tự revert.

---

# 26. Documentation

Không tạo documentation chỉ để có documentation.

Tài liệu phải có mục đích.

Các file phổ biến:

```text
PROJECT.md
docs/ROADMAP.md
docs/TASKS.md
DESIGN.md
ARCHITECTURE.md
DECISIONS.md
```

chỉ tồn tại khi chúng mang lại giá trị.

Không tự tạo thêm hàng loạt docs nếu project nhỏ.

README nên đủ để developer mới biết:

- project là gì;
- cách setup;
- cách chạy;
- cách test;
- cách build nếu relevant.

---

# 27. Task Tracking

Nếu `docs/TASKS.md` tồn tại:

Cập nhật nó trong quá trình làm việc.

Không đánh dấu:

```text
[x]
```

trước khi task được verify.

Khi task hoàn thành:

```text
implement
↓
test
↓
verify
↓
mark done
```

Nếu session phải dừng vì blocker:

Cập nhật task để session sau hiểu:

- đã làm gì;
- đang ở đâu;
- còn gì;
- blocker là gì.

---

# 28. Definition of Done

Một task chỉ hoàn thành khi:

```text
requested behavior implemented
+
relevant tests pass
+
affected flow verified
+
no known blocking regression
+
no accidental scope changes
```

Nếu project có Definition of Done riêng trong `PROJECT.md` hoặc `SPEC.md`:

> Sử dụng definition cụ thể đó.

---

# 29. Trước khi báo hoàn thành

Tự hỏi:

```text
Có làm thứ user không yêu cầu không?

Có thể reuse thay vì viết mới không?

Có abstraction không cần thiết không?

Có dependency mới không cần thiết không?

Có thể dùng native solution không?

Có file không cần thiết không?

Có unresolved test failure không?

Có console/runtime error không?

Có secret/debug code không?

Có behavior nào chưa verify không?
```

Nếu có thể đơn giản hóa mà không làm mất correctness:

> Đơn giản hóa trước khi hoàn thành.

---

# 30. Báo cáo cuối task

Trả lời ngắn gọn.

Không kể lại toàn bộ quá trình suy nghĩ.

Format mặc định:

```md
### Đã làm

- Những thay đổi chính.

### Validation

- Test/build/check đã chạy.
- Kết quả.

### Lưu ý

- Chỉ ghi khi còn limitation hoặc điều user cần biết.

### Git

- Commit message đề xuất nếu phù hợp.
```

Nếu không có lưu ý:

Không cần tạo section trống.

---

# 31. Nguyên tắc cuối cùng

> Đọc nhiều hơn trước khi viết nhiều hơn.

> Reuse trước khi rebuild.

> Native trước dependency.

> Concrete trước abstraction.

> Evidence trước claims.

> Correctness trước cleverness.

> Simplicity không được đánh đổi security hoặc usability.

Và quan trọng nhất:

> **Hãy tạo giải pháp nhỏ nhất nhưng vẫn đúng, an toàn, dễ hiểu, dễ test và dễ bảo trì.**
