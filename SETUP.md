# THEOLOI — Setup Windows hiện có

Checkout vẫn `D:\Workspace\AudioTP`; tên THEOLOI không yêu cầu đổi folder local. Không scaffold lại hoặc cài plugin cho dự án này.

## Dependencies

Python 3, Node/npm, Git. Dùng interpreter trực tiếp, không bắt buộc activation:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-sheets.txt
.\.venv\Scripts\python.exe -m pip install -r benchmarks/score-viewer/requirements.txt
npm.cmd ci --prefix apps/windows
npm.cmd ci --prefix workers/media-api
```

Rust/Cargo/MSVC/Windows SDK chỉ cần khi native build, xem apps/windows/README.md.

## Dữ liệu không có trong clone

Người quản lý cung cấp bộ inputs đã review/cấp quyền qua kênh riêng:

- source/snapshots/watv-vi-2026-10-10.audio.json và bookvn-vi-2026-10-12.sheets.json (chỉ metadata, không ảnh/PDF BookVN).
- catalog/catalog.vi.json, catalog/sheet-sources.vi.json.
- delivery/manifest.vi.json và sheet manifest/mapping hiện có.
- state/transfers.sqlite + state hợp lệ và media/audio theo localPath nếu chạy full integrity/playback.
- config/r2.json khi cần R2; config/r2.example.json chỉ placeholder.

Không tạo file rỗng/audio giả hoặc tự tải bù website. Prepare scripts pin baseline SHA; đổi baseline cần review riêng. Sau khi có inputs, chạy prepare-windows.py và prepare-worker.py, rồi lệnh preview/test ở README. Full regression dùng private datasets để kiểm tra mapping dù network/media commands đã mock; thiếu dữ liệu không phải PASS. Không tự chạy pipeline tải/upload khi setup.

## Secret

.env.example là template, không tự được load. CLI R2 đọc ignored .secrets/r2.env theo tùy chọn hiện có; dùng đúng field names trong script. Worker secrets chỉ cấu hình ở bước deploy riêng; không nhúng R2 key vào client hoặc yêu cầu dán key qua chat.

## Bootstrap chung (tham khảo lịch sử, chỉ áp dụng cho dự án mới)

# Project Bootstrap Protocol

File này định nghĩa quy trình khởi tạo một project mới.

Mục tiêu là để người dùng chỉ cần cung cấp:

1. `AGENTS.md`
2. `SETUP.md`
3. Một prompt mô tả ý tưởng

Sau đó agent phải tự:

- hiểu ý tưởng;
- xác định phạm vi V1;
- tạo tài liệu project;
- tạo roadmap và tasks;
- khởi tạo cấu trúc project;
- kiểm tra Git;
- kiểm tra tools / skills / plugins / MCP hiện có;
- đề xuất những tool phù hợp;
- cài những tool được chấp thuận;
- kiểm tra project;
- tạo Git repository / remote nếu được yêu cầu;
- bắt đầu implementation.

---

# 1. First Action

Khi bắt đầu một project mới:

1. Đọc toàn bộ `AGENTS.md`.
2. Đọc toàn bộ `SETUP.md`.
3. Đọc prompt của người dùng.
4. Kiểm tra thư mục hiện tại.
5. Kiểm tra xem project đã tồn tại hay đang bắt đầu từ đầu.

Không bắt đầu viết feature ngay trước khi hoàn thành bootstrap.

---

# 2. Understand The Idea

Từ prompt của người dùng, hãy tự xác định:

- Project là gì?
- Dành cho ai?
- Giải quyết vấn đề gì?
- Platform là gì?
- Web / App / Bot / CLI / API / Tool?
- Những tính năng chính là gì?
- Tính năng nào thuộc V1?
- Những gì chưa cần làm?
- Có UI hay không?
- Có backend hay không?
- Có database hay không?
- Có authentication hay không?
- Có API bên ngoài hay không?
- Có yêu cầu deploy hay không?

Nếu thông tin có thể suy luận hợp lý với rủi ro thấp:

> Tự đưa ra giả định và tiếp tục.

Không hỏi người dùng về những chi tiết nhỏ có thể quyết định sau.

Chỉ hỏi khi thiếu thông tin ảnh hưởng lớn đến:

- kiến trúc;
- dữ liệu;
- security;
- chi phí;
- platform;
- scope chính;
- deployment;
- Git repository;
- hành động irreversible.

Nếu phải hỏi, gom các câu hỏi quan trọng thành **một lần hỏi**, không hỏi từng câu một.

---

# 3. Create `PROJECT.md`

Sau khi hiểu ý tưởng, tạo:

```text
PROJECT.md
```

File này là nguồn thông tin chính về sản phẩm.

Cấu trúc:

```md
# Project

## Overview

Project này là gì?

## Target Users

Ai sẽ sử dụng?

## Problem

Project giải quyết vấn đề gì?

## Goals

Các mục tiêu chính.

## Core Features

Những chức năng chính.

## V1 Scope

Những gì phải có trong phiên bản đầu tiên.

## Non-Goals

Những thứ chưa làm trong V1.

## Main User Flows

Các flow quan trọng của người dùng.

## Tech Stack

Stack được chọn và lý do ngắn gọn.

## External Services

API / database / third-party services nếu có.

## Security Considerations

Secrets, authentication, permissions và dữ liệu nhạy cảm.

## Deployment

Môi trường deploy dự kiến.

## Definition of Done

Điều kiện để project hoặc V1 được coi là hoàn thành.
```

Không tạo tài liệu dài không cần thiết.

`PROJECT.md` phải đủ rõ để một coding agent mới đọc vào có thể hiểu project.

---

Tài liệu tiến độ phải được tạo trong thư mục `docs/`: `docs/ROADMAP.md` và `docs/TASKS.md`. Tạo `docs/` trước khi ghi file; không tạo bản trùng ở root. `PROJECT.md`, `AGENTS.md` và `SETUP.md` vẫn ở root.

# 4. Create `docs/ROADMAP.md`

Tạo:

```text
docs/ROADMAP.md
```

Không chia thành hàng trăm task ngay.

Chia project thành các milestone có ý nghĩa.

Ví dụ:

```md
# Roadmap

## Milestone 1 — Foundation

- project structure
- environment
- configuration
- basic application

## Milestone 2 — Core Feature A

...

## Milestone 3 — Core Feature B

...

## Milestone 4 — Testing & Polish

...

## Milestone 5 — Deployment

...
```

Roadmap phải theo nguyên tắc:

```text
Foundation
→ Core functionality
→ Integration
→ Quality
→ Deployment
```

Ưu tiên xây vertical slice hoạt động end-to-end sớm.

---

# 5. Create `docs/TASKS.md`

Từ roadmap, tạo:

```text
docs/TASKS.md
```

Mỗi task phải:

- đủ nhỏ để agent có thể hoàn thành;
- có kết quả kiểm chứng được;
- không quá phụ thuộc vào task chưa làm;
- tránh thay đổi quá nhiều phần của codebase cùng lúc.

Ví dụ:

```md
# Tasks

## Current Milestone

### Task 1

- [ ] Implementation
- [ ] Tests
- [ ] Verification

### Task 2

- [ ] Implementation
- [ ] Tests
- [ ] Verification
```

Sử dụng:

```text
[ ] chưa làm
[x] hoàn thành
```

Cập nhật `docs/TASKS.md` trong quá trình development.

Không đánh dấu hoàn thành nếu chưa verify.

---

# 6. Optional Documentation

Không tự tạo hàng loạt file documentation.

Chỉ tạo thêm nếu project thực sự cần.

Có thể gồm:

```text
DESIGN.md
ARCHITECTURE.md
DECISIONS.md
API.md
DATABASE.md
```

Quy tắc:

### Có UI đáng kể

Tạo:

```text
DESIGN.md
```

### Kiến trúc phức tạp

Tạo:

```text
ARCHITECTURE.md
```

### Có quyết định kỹ thuật quan trọng

Tạo:

```text
DECISIONS.md
```

### Project nhỏ

Không cần tạo các file trên nếu không mang lại giá trị.

---

# 7. Initialize Project Structure

Sau khi tài liệu cơ bản hoàn thành:

1. Kiểm tra stack phù hợp.
2. Khởi tạo project nếu chưa tồn tại.
3. Tạo cấu trúc folder hợp lý.
4. Cài dependency cơ bản cần thiết.
5. Không thêm dependency chỉ vì "có thể hữu ích".

Luôn ưu tiên:

```text
simple
+
maintainable
+
few dependencies
```

---

# 8. Environment & Secrets

Nếu project cần secrets:

Tạo:

```text
.env.example
```

và đảm bảo:

```text
.env
```

được ignore.

Không bao giờ:

- commit token;
- commit API key;
- commit password;
- commit private key;
- ghi secret trực tiếp vào source code.

Nếu `.gitignore` chưa tồn tại:

Tạo `.gitignore` phù hợp với stack.

---

# 9. Tool Audit

Sau khi biết loại project và stack, kiểm tra những tool hiện đang có.

Chia tool thành bốn nhóm.

---

## A. PROJECT TOOL

Tool tạo cấu trúc hoặc workflow trực tiếp trong repository.

Ví dụ:

```text
Spec Kit
```

Dùng khi project có:

- nhiều feature liên quan nhau;
- requirement phức tạp;
- architecture đáng kể;
- nhiều milestone;
- cần spec formal.

Không thêm Spec Kit chỉ vì nó tồn tại.

Project nhỏ có thể chỉ dùng:

```text
PROJECT.md
docs/ROADMAP.md
docs/TASKS.md
```

---

## B. CODEX PLUGIN / SKILL

Tool nâng khả năng làm việc của Codex.

Ví dụ:

```text
Superpowers
UI/UX Pro Max
```

### Superpowers

Nên đề xuất cho phần lớn software project.

Mục đích:

- planning;
- implementation workflow;
- testing discipline;
- debugging;
- code review;
- verification.

### UI/UX Pro Max

Chỉ đề xuất khi project có:

- website;
- application UI;
- dashboard;
- frontend;
- design-heavy interface.

Không đề xuất cho:

```text
Telegram bot thuần
CLI tool
backend service thuần
```

trừ khi project cũng có frontend.

---

# 10. MCP Audit

Kiểm tra MCP hiện đã được cấu hình cho Codex.

Không cài lại tool đã tồn tại và hoạt động.

Các MCP thường cân nhắc:

---

## Context7

Đề xuất khi project sử dụng:

- framework;
- library;
- external API;
- SDK;
- services có documentation thay đổi thường xuyên.

Ví dụ:

```text
Astro
React
Telegram API
Supabase
Cloudflare
Stripe
PixiJS
```

Mục đích:

```text
current documentation
→ less API hallucination
```

---

## Serena

Đề xuất khi:

- codebase đã tương đối lớn;
- cần semantic code navigation;
- có nhiều symbol/reference;
- việc tìm code bằng text search bắt đầu không hiệu quả.

Không cần thiết cho project rất nhỏ.

---

## Playwright MCP

Đề xuất khi project có:

```text
website
web application
admin dashboard
browser interaction
```

Mục đích:

```text
AI code
→ open browser
→ use application
→ verify flow
→ find problems
→ fix
```

Không cần cho Telegram bot thuần không có web UI.

---

# 11. DEV TOOL Audit

Kiểm tra các development/security/testing tool phù hợp.

Ví dụ:

```text
Gitleaks
pytest
vitest
eslint
prettier
ruff
mypy
Playwright tests
```

Chỉ đề xuất tool phù hợp với stack.

---

## Gitleaks

Ưu tiên đề xuất khi project:

- dùng API key;
- dùng token;
- dùng `.env`;
- kết nối cloud;
- kết nối Telegram;
- có repository public hoặc remote.

Mục tiêu:

```text
detect secrets before commit
```

---

## Test Framework

Phải có testing strategy phù hợp với stack.

Ví dụ:

Python:

```text
pytest
```

JavaScript / TypeScript:

```text
Vitest
```

Web E2E:

```text
Playwright
```

Không cài nhiều framework test giải quyết cùng một vấn đề nếu không cần.

---

# 12. Recommend Tools Based On Project

Sau khi audit:

Tạo đề xuất ngắn.

Ví dụ project Telegram Bot:

```text
Recommended:

✓ Superpowers
✓ Context7
✓ Gitleaks
✓ pytest

Optional later:

○ Serena — khi codebase lớn hơn

Not needed now:

✗ UI/UX Pro Max
✗ Playwright MCP
✗ Spec Kit
```

Ví dụ web application:

```text
Recommended:

✓ Superpowers
✓ Context7
✓ UI/UX Pro Max
✓ Playwright MCP
✓ Gitleaks

Consider:

○ Spec Kit
○ Serena
```

---

# 13. Tool Installation Approval

Không hỏi từng tool riêng lẻ.

Sau khi audit, hỏi một lần:

```text
Dựa trên project này, tôi đề xuất:

1. Superpowers — Recommended
2. Context7 — Recommended
3. Gitleaks — Recommended
4. Serena — Optional
5. UI/UX Pro Max — Not needed
6. Playwright MCP — Not needed

Bạn muốn:

A. Cài tất cả tool Recommended
B. Chọn thủ công
C. Không cài thêm
```

Nếu prompt ban đầu của người dùng đã nói rõ:

```text
auto_install_recommended_tools = true
```

thì không cần hỏi lại đối với các tool local/reversible được phép cài.

Nếu tool yêu cầu:

- login;
- OAuth;
- API key;
- global system modification;
- paid service;

thì dừng đúng tại bước cần user interaction.

Sau khi user hoàn thành interaction, tiếp tục setup.

---

# 14. Installation Rules

Mỗi loại tool phải được cài đúng cách.

Không clone tất cả GitHub repo vào source project.

### PROJECT TOOL

Cài/scaffold vào repository khi tool yêu cầu.

### CODEX PLUGIN / SKILL

Cài vào Codex/plugin/skill environment phù hợp.

### MCP

Cấu hình trong Codex MCP configuration.

Ưu tiên project-scoped MCP configuration khi phù hợp và project được trusted.

### DEV TOOL

Cài dưới dạng:

```text
dev dependency
```

hoặc local development tool khi có thể.

Tránh global install nếu local install đáp ứng được yêu cầu.

---

# 15. Verify Tools

Sau khi cài một tool:

Không mặc định coi installation thành công.

Verify:

```text
installed
↓
available
↓
agent can access it
↓
basic test works
```

Nếu tool yêu cầu restart Codex hoặc tạo thread mới:

Thông báo rõ cho người dùng.

Không tiếp tục giả định tool đã được load trong session hiện tại nếu cần restart.

---

# 16. Baseline Verification

Trước khi bắt đầu feature development:

Chạy baseline phù hợp với stack.

Ví dụ:

```text
tests
typecheck
lint
build
```

Mục đích:

> Biết project đang ở trạng thái tốt trước khi AI bắt đầu thay đổi code.

Nếu baseline đang fail:

Ghi lại lỗi.

Phân biệt rõ:

```text
pre-existing failure
```

và:

```text
failure introduced by current task
```

---

# 17. Git Initialization

Kiểm tra Git.

Nếu chưa có repository:

```text
git init
```

Sử dụng branch mặc định:

```text
main
```

trừ khi project yêu cầu khác.

Kiểm tra trước khi commit:

```text
.env
secrets
generated files
dependencies
build artifacts
```

không bị commit nhầm.

Nếu Gitleaks có sẵn:

Chạy Gitleaks trước initial commit.

---

# 18. Initial Commit

Khi bootstrap hoàn thành và baseline ổn:

Tạo commit:

```text
chore: bootstrap project
```

Commit gồm:

```text
AGENTS.md
SETUP.md
PROJECT.md
docs/ROADMAP.md
docs/TASKS.md
project skeleton
configuration
tests
```

Không commit secrets.

---

# 19. Git Remote

Thông tin Git có thể được truyền trong prompt ban đầu.

Ví dụ:

```text
Git provider: GitHub
Repository: username/project-name
Visibility: private
Remote: <remote-url>
```

Nếu remote đã tồn tại:

Kiểm tra:

```text
git remote -v
```

Không thay remote đang tồn tại nếu chưa được phép.

Nếu remote chưa tồn tại nhưng prompt đã cung cấp đầy đủ thông tin và quyền tạo repository:

Có thể tạo remote và push.

Nếu thiếu:

```text
repository name
visibility
authentication
```

hãy hỏi một lần.

Không:

```text
force push
delete branch
overwrite remote
rewrite history
```

nếu chưa có explicit approval.

Sau khi remote được cấu hình:

```text
git push -u origin main
```

Verify push thành công.

---

# 20. Bootstrap Completion Check

Setup chỉ được coi là hoàn thành khi:

```text
[ ] AGENTS.md đã đọc
[ ] PROJECT.md đã tạo
[ ] docs/ROADMAP.md đã tạo
[ ] docs/TASKS.md đã tạo
[ ] Project structure đã sẵn sàng
[ ] .gitignore đã đúng
[ ] Secrets đã được bảo vệ
[ ] Tool audit đã hoàn thành
[ ] Recommended tools đã được xử lý
[ ] Baseline tests đã chạy
[ ] Git đã được init
[ ] Initial commit đã tạo
[ ] Remote đã được cấu hình nếu yêu cầu
[ ] Initial push đã thành công nếu yêu cầu
```

Sau đó:

> Không dừng để hỏi "Bạn có muốn tôi bắt đầu code không?"

Chuyển trực tiếp sang Development Mode.

---

# 21. Development Mode

Sau bootstrap:

1. Đọc `PROJECT.md`.
2. Đọc `docs/ROADMAP.md`.
3. Đọc `docs/TASKS.md`.
4. Xác định milestone hiện tại.
5. Chọn task chưa hoàn thành tiếp theo.
6. Implement.
7. Test.
8. Verify.
9. Update `docs/TASKS.md`.
10. Commit checkpoint hợp lý.
11. Chuyển sang task tiếp theo.

Flow:

```text
TASK
↓
INSPECT
↓
PLAN
↓
IMPLEMENT
↓
TEST
↓
VERIFY
↓
FIX IF NEEDED
↓
RETEST
↓
UPDATE TASKS
↓
COMMIT
↓
NEXT TASK
```

---

# 22. Autonomous Execution

Sau khi setup hoàn thành:

Agent phải sở hữu công việc end-to-end.

Không dừng sau:

- planning;
- tạo skeleton;
- implement lần đầu;
- test lần đầu;
- build pass;
- một milestone nhỏ.

Không hỏi:

```text
Should I continue?
Would you like me to implement the next task?
Should I run the tests?
Should I fix this issue?
Would you like me to proceed?
```

Nếu hành động đó rõ ràng cần thiết để hoàn thành project:

> Tự làm.

Khi gặp lỗi:

```text
investigate
↓
fix
↓
test
↓
continue
```

Không báo lỗi cho user rồi dừng nếu agent có khả năng tự sửa.

---

# 23. When To Stop

Chỉ dừng khi:

### Project hoàn thành

Definition of Done đã đạt.

### Genuine blocker

Ví dụ:

- cần secret;
- cần OAuth/login;
- cần account permission;
- cần quyết định product lớn;
- cần chi tiền;
- external service unavailable.

### Irreversible / high-risk action

Ví dụ:

- production database migration;
- delete data;
- delete repository;
- force push;
- production deployment có impact lớn.

### Platform hard limit

Agent không thể tiếp tục vì:

- quota;
- tool unavailable;
- environment limitation.

Trong trường hợp này:

1. cập nhật `docs/TASKS.md`;
2. ghi rõ task hiện tại;
3. ghi những gì đã hoàn thành;
4. ghi bước tiếp theo;
5. đảm bảo working tree ở trạng thái dễ tiếp tục.

Không để session kết thúc trong trạng thái không rõ project đang ở đâu.

---

# 24. Tool Re-Evaluation

Không chỉ audit tool một lần duy nhất.

Khi project thay đổi đáng kể, đánh giá lại.

Ví dụ:

```text
Telegram Bot
```

ban đầu không cần Playwright.

Nhưng sau này thêm:

```text
Web Admin Dashboard
```

thì agent phải nhận ra:

```text
Playwright MCP
UI/UX skill
```

bắt đầu có giá trị.

Tương tự:

```text
20 files
```

có thể chưa cần Serena.

Nhưng:

```text
300 files
```

thì nên đề xuất Serena.

---

# 25. Principle

Không cài tool vì tool đang nổi tiếng.

Chỉ cài khi:

```text
problem exists
+
tool solves that problem
+
benefit > complexity
```

Mục tiêu không phải:

> Có nhiều AI tool nhất.

Mục tiêu là:

> Tạo một development system để agent có thể tự làm việc chính xác, nhanh, có kiểm chứng và ít cần người dùng can thiệp nhất.

---

# Final Bootstrap Flow

```text
USER PROMPT
     │
     ▼
READ AGENTS.md
     │
     ▼
READ SETUP.md
     │
     ▼
UNDERSTAND IDEA
     │
     ▼
PROJECT.md
     │
     ▼
docs/ROADMAP.md
     │
     ▼
docs/TASKS.md
     │
     ▼
PROJECT SKELETON
     │
     ▼
TOOL AUDIT
     │
     ├── Project Tools
     ├── Codex Plugins / Skills
     ├── MCP
     └── Dev Tools
     │
     ▼
ONE INSTALLATION DECISION
     │
     ▼
INSTALL + VERIFY
     │
     ▼
BASELINE TEST
     │
     ▼
GIT INIT
     │
     ▼
SECURITY CHECK
     │
     ▼
INITIAL COMMIT
     │
     ▼
REMOTE + PUSH
     │
     ▼
SETUP COMPLETE
     │
     ▼
AUTONOMOUS DEVELOPMENT
     │
     ▼
TASK → CODE → TEST → FIX → VERIFY
     │
     ▼
NEXT TASK
     │
     ↺
```
