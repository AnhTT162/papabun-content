## Quick

Phân quyền trả lời "**người này** được làm **hành động này** trên **tài nguyên này** không". [[rbac|RBAC]] gán quyền theo vai trò, [[abac|ABAC]] quyết theo thuộc tính (của người, của tài nguyên, của ngữ cảnh), [[rebac|ReBAC]] suy quyền từ quan hệ (chủ sở hữu, thành viên nhóm, được chia sẻ). Hệ thật thường kết hợp: role cho quyền chức năng, quan hệ hoặc thuộc tính cho quyền trên từng bản ghi. **Kiểm ở server, trên đúng bản ghi được đọc hay ghi, mặc định từ chối.**

## Interview

**RBAC**: user → role → permission. Dễ hiểu và dễ kiểm toán ("ai có quyền duyệt chi?"). Nhưng role không diễn tả được "chỉ đơn của chi nhánh mình", nên số role nhân lên theo chi nhánh × chức năng ([[role-explosion|role explosion]]). Cách chữa phổ biến là gán role kèm phạm vi: "quản lý kho tại chi nhánh Huế".

**ABAC**: luật trên thuộc tính, ví dụ cùng chi nhánh, số tiền dưới hạn mức duyệt, trong giờ làm việc. Linh hoạt, nhưng khó trả lời ngược "ai xem được hồ sơ này", và thuộc tính phải tươi.

**ReBAC**: quyền suy từ đồ thị quan hệ: ai xem được thư mục thì xem được tài liệu trong đó, thành viên nhóm thừa hưởng quyền của nhóm. Hợp với chia sẻ kiểu Google Drive. Mô hình [[zanzibar|Zanzibar]] của Google, bản mở là OpenFGA, SpiceDB.

**Ở đâu**: [[policy-enforcement-point|PEP]] (filter, [[method-security|`@PreAuthorize`]], gateway) hỏi [[policy-decision-point|PDP]], có thể là code trong service hay engine như [[opa|OPA]], Cedar, OpenFGA. Gateway kiểm thô: đã đăng nhập, có scope. Service sở hữu dữ liệu kiểm chi tiết, vì chỉ nó biết bản ghi thuộc về ai.

**Bẫy hay gặp**: [[bola|BOLA]] (tên khác của [[idor|IDOR]] trong OWASP API Top 10), kể cả kiểu kiểm id trên URL nhưng ghi theo id trong body; danh sách và tìm kiếm không lọc theo quyền; nhét quyền chi tiết vào [[jwt|JWT]] nên đổi quyền không có hiệu lực tới khi token hết hạn; cache quyết định với khoá thiếu người dùng; engine phân quyền lỗi thì cho qua; quên lọc tenant.

**Cách làm đúng**: đưa điều kiện quyền vào truy vấn (`WHERE id = ? AND tenant_id = ? AND owner_id = ?`) thay vì tải rồi kiểm; mọi quyết định đi qua một chỗ có unit test; test truy cập chéo tự động cho mọi endpoint nhận id; log mọi lần từ chối.

## Deep

- **Từ vựng**: subject (ai), action (làm gì), resource (trên cái gì), context (giờ, IP, mức xác thực). Permission là cặp action + loại tài nguyên (`invoice:approve`); role là một gói permission. Code nên kiểm permission, không kiểm tên role: `hasAuthority("invoice:approve")` sống sót khi đổi cấu trúc role, `hasRole("CHIEF_ACCOUNTANT")` thì không.
- **RBAC chi tiết**:
  - Chuẩn NIST/ANSI có các mức: core, phân cấp role (`ADMIN` kế thừa `STAFF`), ràng buộc ([[separation-of-duties|tách nhiệm]]). Spring: `RoleHierarchyImpl.fromHierarchy("ROLE_ADMIN > ROLE_STAFF")`.
  - Role explosion: 30 chi nhánh × 6 chức năng là 180 role, mỗi lần mở chi nhánh thêm 6 role. Gán role theo phạm vi (role assignment = người + role + scope, cách Azure RBAC làm) giữ 6 role và đưa chi nhánh thành dữ liệu.
  - Tách nhiệm động là luật trên bản ghi, không phải role: người tạo phiếu chi không được duyệt chính phiếu đó dù có role duyệt.
- **ABAC chi tiết**:
  - NIST SP 800-162 (2014). Chuẩn cũ XACML 3.0 (OASIS 2013) viết policy bằng XML, nay ít dùng; thay bằng Rego (OPA) hay Cedar.
  - Thuộc tính lấy từ đâu: token (chỉ thứ ít đổi), database của service, hoặc PIP (policy information point) mà PDP gọi thêm. Thuộc tính cũ là quyết định sai: người vừa chuyển chi nhánh vẫn mang chi nhánh cũ trong token còn hạn.
  - Khó kiểm toán: muốn liệt kê ai xem được hồ sơ X phải chạy policy trên mọi người.
- **ReBAC và Zanzibar**:
  - Bài báo Zanzibar (USENIX ATC 2019): lưu [[relationship-tuple|relation tuple]] dạng `document:42#viewer@user:alice`, `folder:7#viewer@group:kho-hue#member`. Model định nghĩa quyền dẫn xuất: `viewer` của tài liệu = `editor` ∪ `viewer` trực tiếp ∪ `viewer` của thư mục cha. Check là duyệt đồ thị.
  - [[new-enemy-problem|New enemy problem]]: gỡ Bob khỏi thư mục rồi thêm tài liệu mật vào đó. Nếu check đọc từ bản sao hay cache cũ, Bob vẫn thấy tài liệu mới. Zanzibar dùng zookie: token nhất quán mà app lưu cùng nội dung khi sửa nó, để lần check sau dùng dữ liệu ACL ít nhất mới bằng thời điểm đó. SpiceDB có ZedToken; OpenFGA có chế độ `HIGHER_CONSISTENCY` (bỏ qua cache; cache của OpenFGA mặc định tắt).
  - Dữ liệu quan hệ nằm ở hai nơi: database của app và store của engine. Ghi kép là lệch dữ liệu; dùng outbox hay CDC để đồng bộ tuple, và có job đối soát.
  - Liệt kê ("Alice xem được tài liệu nào") là truy vấn ngược đắt: `ListObjects` (OpenFGA), `LookupResources` (SpiceDB) hợp với tập nhỏ, không thay được lọc trong database cho hàng triệu bản ghi.
  - Điều kiện theo ngữ cảnh (quyền hết hạn sau 30 ngày): OpenFGA conditions, SpiceDB caveats.
- **OPA và Cedar**:
  - OPA (CNCF graduated) là engine policy chung: nhận `input` JSON, trả quyết định theo policy Rego, dữ liệu nạp qua bundle. Chạy như sidecar hay thư viện, nên quyết định không cần gọi mạng. Mạnh ở hạ tầng (admission controller Kubernetes, kiểm Terraform, bài Enterprise architecture nhắc [[policy-as-code|policy as code]]) và ABAC trong service; không phải nơi lưu hàng triệu quan hệ.
  - Partial evaluation của OPA biến policy thành điều kiện còn lại khi chưa biết tài nguyên, có thể dịch sang `WHERE` để lọc danh sách.
  - Cedar (AWS, 2023; dịch vụ Amazon Verified Permissions): ngôn ngữ thiết kế để phân tích được, `forbid` luôn thắng `permit`, mặc định từ chối.
- **Lọc danh sách**: kiểm từng bản ghi là N lần gọi. Tải 1.000 bản ghi rồi lọc trong bộ nhớ thì phân trang hỏng (trang 20 dòng còn 3) và đếm tổng làm lộ số bản ghi. Spring `@PostFilter` làm đúng kiểu này (bài Kiến trúc Spring Security). Cách đúng, theo thứ tự ưu tiên:
  - Điều kiện quyền thành cột trong truy vấn (tenant, owner, chi nhánh); [[row-level-security|RLS]] làm lớp chặn thứ hai (bài Multi-tenancy).
  - Bảng ACL tính sẵn hoặc trường `allowed_groups` trong search index; đổi quyền phải cập nhật lại index.
  - Engine trả tập id được phép khi tập đó nhỏ (các dự án của người dùng), rồi lọc theo tập đó trong database.
- **Quyền trong token**: token mang danh tính, tenant, scope và role thô. Quyền chi tiết tra lúc kiểm. Token có thời hạn nên đổi quyền chỉ có hiệu lực khi token hết hạn; thao tác nhạy cảm (chuyển tiền, xuất dữ liệu) tra quyền mới nhất. Giới hạn kích thước token: bài JWT chuyên sâu.
- **Cache quyết định**: khoá phải gồm subject, action, resource, và phiên bản policy hay dữ liệu quan hệ; TTL ngắn; xoá khi đổi quyền. Khoá chỉ theo id tài nguyên là trả quyết định của người này cho người khác. Engine lỗi thì từ chối ([[fail-open|fail closed]], bài OWASP Top 10 với Java/Spring).
- **Các dạng BOLA hay sót** (OWASP API Security Top 10 2023: API1 BOLA, API3 lỗi cấp thuộc tính gồm [[mass-assignment|mass assignment]], API5 lỗi cấp chức năng):
  - Id trên path được kiểm, lệnh ghi dùng id trong body (lab bên dưới).
  - Tài nguyên lồng nhau `/orders/{orderId}/items/{itemId}`: kiểm quyền trên đơn nhưng không kiểm item có thuộc đơn đó.
  - Endpoint theo lô `?ids=1,2,3`, job xuất báo cáo, link tải file theo key trong object storage, GraphQL `node(id)`, kênh WebSocket đặt theo id.
  - UUID khó đoán không phải phân quyền: id lộ qua log, link chia sẻ, response khác.
  - Trả `404` thay vì `403` để không lộ bản ghi tồn tại: bài OWASP Top 10 với Java/Spring.
- **Cấp quyền cũng là quyền**: ai được gán role? Người gán không được cấp quyền lớn hơn mình có; tenant admin tạo role tuỳ biến chỉ chọn trong permission của tenant, không chọn được permission của nền tảng. Mọi thay đổi gán quyền ghi [[audit-log|audit log]]; gán quyền quản trị cần người thứ hai duyệt.
- **Cô lập tenant** ([[multi-tenancy|multi-tenancy]]) là bộ lọc đầu tiên, trước mọi role: tenant lấy từ token đã xác thực, không từ header. Chi tiết (RLS, tenant context, support impersonation): bài Multi-tenancy.
- **Gọi thay người dùng**: service phía sau nhận danh tính người dùng gốc (token exchange, bài OAuth2 & OpenID Connect), nếu không nó thành [[confused-deputy|confused deputy]], làm thay bất kỳ ai gọi tới.
- **Spring Security**:
  - `@PreAuthorize("@orderAuthz.canEdit(#id, authentication)")` gọi bean; tên tham số `#id` cần biên dịch với `-parameters` (Spring Boot bật sẵn), chạy `java File.java` hay build tự cấu hình thì thiếu.
  - `AuthorizationManager<T>` là giao diện chung cho cả URL lẫn method; viết một `AuthorizationManager` riêng khi cần gọi engine ngoài.
  - Từ 6.3: `@AuthorizeReturnObject` bọc object trả về để annotation phân quyền trên method của nó có hiệu lực, `@HandleAuthorizationDenied` thay exception bằng giá trị che (ví dụ ẩn số tài khoản).
  - Module `spring-security-acl` (bảng ACL theo từng object) có từ lâu, nặng và ít được chọn cho hệ mới.
- **Test**:
  - Ma trận role × endpoint sinh từ danh sách route, để endpoint mới không có rule thì test hỏng.
  - Fixture hai người dùng ở hai tenant; với mỗi endpoint nhận id, gọi bằng người kia và chờ `403`/`404`. Thêm biến thể id trong body, trong query, trong item lồng nhau.
  - Policy viết bằng Rego thì có `opa test`; với OpenFGA/SpiceDB có file assertion cho model.
  - Đổi engine thì chạy [[shadow-mode|shadow mode]]: engine mới quyết song song, log chỗ lệch với code cũ, chưa chặn.
