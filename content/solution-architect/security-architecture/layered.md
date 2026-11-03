## Quick

Kiến trúc bảo mật là cách xếp các lớp kiểm soát quanh tài sản cần bảo vệ: danh tính, mạng, ứng dụng, dữ liệu, phát hiện. [[defense-in-depth|Defense in depth]] nghĩa là các lớp độc lập nhau; [[zero-trust|zero trust]] nghĩa là không cho quyền chỉ vì request đến từ mạng nội bộ. **Giả định một lớp sẽ thủng ([[assume-breach|assume breach]]): mỗi danh tính chỉ với tới đúng thứ nó cần, mạng được chia để kẻ tấn công không đi ngang được, và việc dùng quyền nào cũng để lại dấu vết có người xem.**

## Interview

Tôi bắt đầu từ tài sản và đường tấn công, không bắt đầu từ danh sách sản phẩm. Dữ liệu nào nếu lộ là thảm hoạ, ai và cái gì đang với tới được nó, và nếu một máy bị chiếm thì kẻ tấn công đi tiếp tới đâu.

Lớp quan trọng nhất là danh tính. Với người: một [[identity-provider|IdP]] duy nhất, [[sso|SSO]] qua [[oidc|OIDC]] hoặc [[saml|SAML]] cho mọi công cụ, [[mfa|MFA]] chống phishing cho quyền quản trị, và cấp, thu hồi tài khoản tự động theo dữ liệu nhân sự. Với service: [[workload-identity|workload identity]] cấp credential ngắn hạn, không có access key dài hạn nằm trong biến môi trường.

Theo zero trust, mỗi request được xác thực và kiểm quyền theo danh tính, thiết bị và ngữ cảnh. Kết nối giữa service dùng [[mtls|mTLS]], nhưng mTLS chỉ trả lời "ai đang gọi"; service vẫn phải kiểm "người gọi này được làm gì".

Mạng vẫn cần chia vùng, như một lớp chứ không phải lớp duy nhất. Tách tài khoản cloud giữa production và dev, chia subnet theo tầng, mặc định chặn trong cluster rồi mở từng đường, chặn chiều ra internet. Mục tiêu là chặn [[lateral-movement|lateral movement]].

Dữ liệu nhạy cảm được mã hoá bằng khoá riêng trong [[kms|KMS]], chỉ role của service sở hữu được giải mã. Mọi thao tác quản trị và truy cập dữ liệu nhạy cảm vào audit log nằm ở tài khoản riêng, có cảnh báo.

Bẫy hay gặp: VPN vào là thấy mọi thứ; gateway kiểm [[jwt|JWT]] rồi service phía sau tin mọi request; lỗi [[ssrf|SSRF]] đọc được credential từ metadata service của máy; role của node quá rộng nên pod nào cũng dùng được; nhân viên nghỉ việc vẫn còn tài khoản ở công cụ không nối SSO. Và mua một sản phẩm "zero trust" rồi coi là xong.

## Deep

- **Defense in depth là các lớp độc lập**: mỗi bước của một cuộc tấn công nên có một lớp chặn hoặc phát hiện riêng. Ví dụ đường SSRF tới credential của máy: kiểm URL ở ứng dụng; chặn chiều ra tới metadata service ở mạng; IMDSv2 bắt buộc ở host; role tối thiểu; bucket chỉ nhận request qua VPC endpoint của mình; cảnh báo khi credential bị dùng từ nơi lạ. Các lớp dùng chung một giả định (chung một credential, chung một quản trị viên) thì không độc lập.
- **Zero trust theo NIST SP 800-207** (2020):
  - Quyết định truy cập nằm ở policy decision point (PDP, gồm policy engine quyết định và policy administrator mở hoặc cắt phiên), được thực thi ở [[policy-enforcement-point|policy enforcement point (PEP)]] đứng trước tài nguyên: proxy truy cập, gateway, sidecar.
  - Quyết định theo từng phiên, dựa trên danh tính, trạng thái thiết bị và ngữ cảnh, không dựa trên vị trí mạng.
  - Google BeyondCorp là ví dụ sớm: nhân viên vào ứng dụng nội bộ qua proxy kiểm danh tính và thiết bị, không qua VPN.
  - [[ztna|ZTNA]] là sản phẩm cho phần người dùng vào ứng dụng; nó không xử lý danh tính của service, quyền của role cloud hay phân vùng trong cluster.
  - Đi dần theo ứng dụng, bắt đầu từ thứ giá trị nhất, không đổi cả công ty trong một đêm.
- **Phân vùng mạng** ([[network-segmentation|network segmentation]]; CIDR, route table, security group ở bài Mạng máy tính cơ bản):
  - Ranh giới mạnh nhất trên cloud là tài khoản: production, dev, log, quản trị ở các tài khoản riêng, có guardrail chung (AWS Organizations SCP chặn tắt CloudTrail, chặn region không dùng).
  - Trong một VPC: subnet public chỉ có load balancer, subnet ứng dụng, subnet dữ liệu không có đường ra internet. [[security-group|Security group]] của database cho phép từ security group của service, không theo cả dải CIDR.
  - Chặn chiều ra: phần lớn service không cần gọi internet. Đi qua proxy egress có allowlist tên miền; dịch vụ cloud (S3, KMS, Secrets Manager) đi qua [[vpc-endpoint|VPC endpoint]] để không ra internet.
- **Kubernetes**:
  - Mặc định mọi pod gọi được mọi pod. [[network-policy|NetworkPolicy]] chỉ có luật cho phép, cộng dồn, và chỉ có hiệu lực khi CNI hỗ trợ.
  - Policy không khai `policyTypes` thì Ingress luôn được bật, Egress chỉ được bật khi policy có mục `egress`.
  - NetworkPolicy là L3/L4: không lọc theo tên miền (allowlist tên miền đi qua proxy egress), không áp cho pod `hostNetwork`. Trên EKS, VPC CNI phải bật hỗ trợ network policy.
  - Cách làm: mỗi namespace một policy mặc định chặn cả hai chiều, rồi mở từng đường cần, kể cả DNS.
  - [[microsegmentation|Microsegmentation]] theo danh tính service bằng [[service-mesh|service mesh]] (`AuthorizationPolicy` của Istio) ở bài API gateway, BFF & service mesh.
- **mTLS là xác thực, không phải phân quyền**: đã chạy trên JDK 27 với một CA thử và ba chứng chỉ mang SAN dạng [[spiffe|SPIFFE]] (`spiffe://shop.local/ns/prod/sa/<tên>`), server `payments` bắt buộc chứng chỉ client:
  - Client không có chứng chỉ: `SSLHandshakeException: (certificate_required)`.
  - Chỉ bật mTLS: cả `orders` lẫn `reports` tạo được hoàn tiền (201), vì cả hai có chứng chỉ hợp lệ của cùng CA.
  - Thêm allowlist theo SPIFFE ID: `orders` 201, `reports` 403.
  - Trong mesh, phần phân quyền này là `AuthorizationPolicy` (bài API gateway, BFF & service mesh).
- **Phân quyền ở đâu**: gateway kiểm thô (đã xác thực, có scope); service sở hữu tài nguyên kiểm chi tiết (đơn này của tenant nào, người này có quyền trên hồ sơ này không), vì chỉ nó có dữ liệu để quyết định. Truyền danh tính người dùng cuối xuống ([[token-relay|token relay]]) thay vì chỉ danh tính service, nếu không service phía sau thành "confused deputy" làm thay bất kỳ ai. Mô hình RBAC/ABAC/ReBAC ở bài Mô hình phân quyền.
- **Danh tính của người tập trung**:
  - Một IdP, mọi công cụ (cloud console, CI, Grafana, database admin) đăng nhập qua SSO. Công cụ nào còn tài khoản riêng là nơi tài khoản của người đã nghỉ việc sống sót.
  - Cấp và thu hồi theo dữ liệu nhân sự (vào, chuyển bộ phận, nghỉ), đẩy xuống ứng dụng bằng [[scim|SCIM]].
  - Quyền theo nhóm, không gán trực tiếp từng người.
  - MFA chống phishing (FIDO2, passkey) cho quản trị viên. OTP bị lừa nhập vào trang giả (SMS còn bị chiếm qua đổi SIM); push bị spam tới khi người dùng bấm duyệt.
  - Quyền cao chỉ cấp khi cần, có hạn và có người duyệt ([[just-in-time-access|just-in-time access]]); vài tài khoản [[break-glass-access|break-glass]] cho lúc IdP chết, khoá cứng, cảnh báo mỗi lần dùng, thử định kỳ.
  - Chi tiết giao thức ở bài OAuth2 & OpenID Connect và bài SSO doanh nghiệp & SAML.
- **Danh tính của workload**:
  - Thứ tự ưu tiên: credential ngắn hạn cấp theo danh tính (IAM role qua instance profile, EKS Pod Identity hoặc IRSA, Workload Identity của GCP) hơn secret được xoay vòng, hơn key tĩnh (bài Quản lý secret).
  - Pod không được dùng role của node; mỗi service một role, giới hạn tới đúng bucket, prefix, khoá KMS.
  - CI/CD lên cloud bằng OIDC federation thay vì access key. Trust policy phải giới hạn claim `sub` theo repo và nhánh hoặc môi trường; chỉ kiểm `aud` thì workflow của repo khác cũng có thể nhận role.
    - Với GitHub Actions, repo tạo sau 15/7/2026 (và repo đổi tên hay chuyển chủ sau ngày đó) có `sub` kèm id số của owner và repo, dạng `repo:octo-org@123456/octo-repo@456789:ref:refs/heads/main`, để người lấy lại tên tổ chức hay repo đã xoá không nhận được role. Repo cũ giữ dạng `repo:octo-org/octo-repo:...` cho tới khi bật trong cài đặt OIDC của repo hoặc tổ chức (UI hay REST API); sửa trust policy trước khi bật để deploy không vỡ. GitHub Enterprise Server chưa có dạng này.
    - Điều kiện viết theo dạng cũ như `repo:octo-org/*` không khớp dạng mới, nên role cho repo mới phải viết theo id.
- **SSRF và metadata service**: service nhận URL từ người dùng (tải ảnh, xem trước link, webhook) có thể bị dẫn tới `169.254.169.254` để đọc credential của máy. Vụ lộ dữ liệu Capital One năm 2019 đi đúng đường này: một WAF cấu hình sai trên EC2 bị SSRF tới metadata service, role của nó đọc được nhiều bucket S3. Chặn nhiều lớp:
  - Ứng dụng: allowlist scheme và host, phân giải DNS rồi chặn dải private và link-local, kiểm lại sau mỗi redirect (chi tiết ở bài OWASP Top 10 với Java/Spring).
  - Host: [[imds|IMDSv2]] bắt buộc (`HttpTokens=required`) để lấy token phải gửi `PUT` có header; hop limit 1 làm token không về tới container chạy trong network namespace riêng.
  - Mạng: NetworkPolicy có `Egress` cho phép `ipBlock` `0.0.0.0/0` với `except: [169.254.169.254/32]`. Vì chỉ có luật cho phép nên phải viết kiểu loại trừ, và pod bị chọn chỉ còn đi được theo các luật này (nhớ mở DNS).
  - Quyền: role tối thiểu ([[least-privilege|least privilege]]); bucket policy chỉ nhận request qua VPC endpoint của mình (`aws:SourceVpce`), nên credential bị đánh cắp không đọc được bucket đó từ ngoài VPC. Nó vẫn dùng được cho API khác và từ máy khác trong VPC; policy deny cũng cần ngoại lệ cho role quản trị và dịch vụ AWS truy cập thay. Mở rộng thành data perimeter bằng `aws:PrincipalOrgID`, `aws:ResourceAccount`.
- **Dữ liệu**: phân loại dữ liệu trước (công khai, nội bộ, nhạy cảm, bị quản lý như số thẻ, giấy tờ tùy thân). Mã hoá at rest bằng khoá KMS riêng cho dữ liệu nhạy cảm; key policy là lớp quyền thứ hai, vì đọc được object mà không giải mã được thì vô ích. TLS cả giữa các service nội bộ. Số thẻ thì tokenize để phần lớn hệ thống ra khỏi phạm vi PCI (bài Thiết kế hệ thống thanh toán). Cơ chế mã hoá và envelope encryption ở bài Mật mã cho kỹ sư.
- **Truy cập quản trị vào production**: không bastion SSH dùng chung khoá, không user database dùng chung. Vào qua công cụ gắn với IdP (AWS Systems Manager Session Manager, proxy truy cập), có ghi phiên; quyền database có hạn và gắn với người cụ thể. Mỗi service một user database với quyền tối thiểu.
- **Phát hiện và phản ứng**: [[audit-trail|audit log]] của cloud (CloudTrail cho cả tổ chức) ghi vào tài khoản log riêng, không xoá được (S3 Object Lock). Cảnh báo cho sự kiện tín hiệu cao: đăng nhập root, đổi policy IAM, tắt log, credential của máy dùng từ ngoài cloud (GuardDuty có loại cảnh báo này), đọc hàng loạt object nhạy cảm. Có runbook thu hồi credential và cô lập workload; tập dượt như với sự cố vận hành.
- **Nghĩ theo [[blast-radius|blast radius]]**: với mỗi credential, hỏi "lộ cái này thì với tới được gì". Role của node đọc mọi bucket, user database `admin` dùng chung, token CI có quyền admin là ba câu trả lời tệ nhất.
- **Trade-off**: mỗi lớp thêm ma sát (đăng nhập, xin quyền, mở từng đường mạng) và chi phí vận hành (cấp chứng chỉ, policy, log). Ưu tiên theo đường tấn công tới tài sản giá trị nhất; một tập lớn chính sách không ai hiểu sẽ bị mở toang ở sự cố đầu tiên. Threat modeling (STRIDE) ở bài Bảo mật trong quy trình phát triển; bảo mật trong buổi review kiến trúc ở bài AWS Well-Architected.
