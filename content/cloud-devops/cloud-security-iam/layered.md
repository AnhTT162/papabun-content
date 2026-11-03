## Quick

IAM của AWS trả lời một câu: **request này có được phép không**, bằng cách xét mọi policy liên quan. Mặc định là từ chối, một `Deny` tường minh ở bất kỳ đâu thắng mọi `Allow`, và với request khác tài khoản thì **cả hai phía** đều phải cho phép. [[least-privilege|Least privilege]] trên cloud được làm bằng ba tầng: tài khoản tách theo môi trường và mức nhạy cảm, guardrail của tổ chức ([[service-control-policy|SCP]]) chặn những việc không ai được làm, và role nhỏ cho từng service.

## Interview

Khi một request tới AWS, IAM gom mọi policy áp vào nó: [[identity-based-policy|identity-based policy]] gắn vào user hay role, [[resource-based-policy|resource-based policy]] như bucket policy hay [[key-policy|key policy]] của KMS, SCP và [[resource-control-policy|RCP]] của AWS Organizations, permissions boundary, session policy. Đầu tiên tìm `Deny` tường minh: có là từ chối. Sau đó SCP và RCP phải cho phép; rồi cần ít nhất một `Allow` ở identity hoặc resource policy, và không bị boundary hay session policy chặn. Không ai cho phép thì từ chối ngầm định.

Request khác tài khoản được đánh giá ở cả tài khoản gọi lẫn tài khoản sở hữu tài nguyên: role phải có identity policy cho phép, và bucket hay khoá phải có resource policy cho phép tài khoản hay role đó. KMS chặt hơn nữa: key policy là nguồn quyền chính; nếu key policy không cho phép tài khoản dùng IAM policy, thì IAM policy cho quyền gì cũng vô hiệu.

Tôi tổ chức theo tài khoản vì đó là ranh giới mạnh nhất: tài khoản quản trị tổ chức gần như trống, tài khoản log và audit riêng mà người vận hành không xoá được, tài khoản cho prod, staging, dev của từng nhóm hệ thống. SCP chặn ở mức tổ chức: không rời Organizations, không tắt CloudTrail hay GuardDuty, chỉ dùng các region được phép, không tạo access key cho user. Người dùng đăng nhập qua IAM Identity Center với SSO của công ty, nhận credential tạm thời theo permission set; không có IAM user dài hạn.

Mỗi service một role, giới hạn tới đúng bucket, prefix, khoá KMS, queue nó cần; role ([[iam-role|IAM role]]) được nhận qua instance profile, task role hay EKS Pod Identity. IAM Access Analyzer tìm quyền không dùng và tài nguyên chia sẻ ra ngoài tổ chức.

Bẫy hay gặp: policy dùng `"Resource": "*"` và `s3:*` cho nhanh; quên `kms:Decrypt` khi bucket mã hoá bằng khoá riêng; trust policy cho phép cả một tài khoản khác assume role mà không có điều kiện; và quản trị bằng root user.

## Deep

- **Cấu trúc một statement**: `Effect`, `Action`, `Resource`, `Condition` (và `Principal` với resource policy). Bẫy:
  - Hành động trên bucket và trên object có ARN khác nhau: `s3:ListBucket` trên `arn:aws:s3:::invoices`, `s3:GetObject` trên `arn:aws:s3:::invoices/*`. Sai ARN là AccessDenied dù "đã cho quyền".
  - `NotAction` với `Allow` cho mọi hành động trừ danh sách, kể cả các dịch vụ ra đời sau này; dùng với `Deny` thì hợp lý hơn.
  - Điều kiện hay dùng: `aws:SourceVpce` (chỉ qua VPC endpoint của mình), `aws:PrincipalOrgID` (chỉ principal trong tổ chức), `aws:SecureTransport`, `aws:RequestedRegion`, tag của principal và tài nguyên cho ABAC.
- **Thứ tự đánh giá** (tài liệu IAM): từ chối ngầm định; tìm `Deny` tường minh trong mọi loại policy; RCP phải có `Allow` áp dụng (RCP chỉ giới hạn, không cấp quyền); SCP tương tự; resource-based policy; identity-based policy; permissions boundary; session policy. Quyền thực tế là phần giao của các giới hạn (SCP, RCP, boundary, session) với phần được cấp (identity hay resource policy). Ngoại lệ trong cùng tài khoản: resource policy cấp thẳng cho ARN của IAM user hay của role session không bị boundary giới hạn; cấp cho ARN của role thì vẫn bị. Ngoại lệ trong cùng tài khoản: resource policy cấp thẳng cho ARN của IAM user hay của role session không bị boundary giới hạn; cấp cho ARN của role thì vẫn bị.
- **SCP và RCP**:
  - SCP giới hạn những gì principal trong tài khoản thành viên được làm; RCP (từ 2024) giới hạn những gì có thể làm với tài nguyên của tài khoản thành viên, kể cả bởi principal bên ngoài. Cả hai không áp vào tài khoản quản trị tổ chức, nên đừng chạy workload ở đó.
  - RCP là nền của data perimeter: chặn mọi principal ngoài tổ chức đọc S3, KMS, Secrets Manager của bạn, dù một bucket policy lỡ mở public.
- **Role và [[trust-policy|trust policy]]**:
  - Role có hai policy: trust policy (ai được assume) và permission policy (assume xong làm được gì). Cho phép `"AWS": "arn:aws:iam::<tài khoản khác>:root"` nghĩa là bất kỳ principal nào trong tài khoản đó mà được tài khoản đó cho phép `sts:AssumeRole`.
  - Bên thứ ba (SaaS giám sát) assume role trong tài khoản của bạn: bắt buộc điều kiện `sts:ExternalId` do bên đó cấp riêng cho bạn để chống [[confused-deputy|confused deputy]]. Dịch vụ AWS truy cập tài nguyên thay bạn: dùng `aws:SourceArn`, `aws:SourceAccount` trong resource policy.
  - CI đăng nhập bằng OIDC: trust policy phải giới hạn `sub` theo repo và nhánh, nếu không mọi repo trên cùng nền tảng CI đều assume được (bài Kiến trúc bảo mật).
- **[[permissions-boundary|Permissions boundary]]**: trần quyền gắn vào user hay role; dùng khi cho đội dự án tự tạo role mà không leo được quyền cao hơn mức cho phép (role họ tạo phải mang boundary).
- **[[kms|KMS]]**:
  - Mỗi khoá có đúng một key policy; không ai, kể cả root, có quyền với khoá nếu không được key policy, IAM policy hay grant cho phép, và IAM policy chỉ có hiệu lực khi key policy cho phép tài khoản dùng IAM.
  - Khác tài khoản: key policy cho phép tài khoản hay role bên kia, và role bên kia có identity policy cho `kms:Decrypt`. Khoá do AWS quản lý (`aws/s3`) không đổi được key policy nên không chia sẻ khác tài khoản được.
  - Tách quyền quản trị khoá khỏi quyền dùng khoá; `kms:ViaService` giới hạn khoá chỉ được dùng qua một dịch vụ (ví dụ chỉ qua S3). Envelope encryption và xoay khoá ở bài Mật mã cho kỹ sư.
- **Tài khoản và landing zone**: Control Tower hay mẫu tự dựng tạo tổ chức với OU (Security, Infrastructure, Workloads/Prod, Workloads/Non-prod, Sandbox), tài khoản log tập trung (CloudTrail cả tổ chức, Config), tài khoản audit (GuardDuty, Security Hub ở chế độ quản trị tập trung). Tài khoản mới sinh từ quy trình tự động có sẵn guardrail, mạng, logging.
- **Danh tính người**: IAM Identity Center nối với IdP công ty, permission set theo vai trò, quyền cao qua just-in-time có duyệt và có hạn; vài tài khoản break-glass có MFA phần cứng, được giám sát mỗi lần dùng. Root user chỉ dùng cho vài việc bắt buộc, có MFA, không có access key.
- **Phát hiện**: CloudTrail ghi mọi lời gọi API (ai, khi nào, từ đâu); GuardDuty phát hiện hành vi bất thường (credential của EC2 dùng từ ngoài AWS, truy vấn tới tên miền đào coin); Config ghi lịch sử cấu hình và kiểm luật; Access Analyzer tìm quyền không dùng, tài nguyên chia sẻ ra ngoài, và kiểm policy trước khi deploy. Phản ứng sự cố bảo mật ở bài Kiến trúc bảo mật.
- **Phân vùng mạng** chỉ là một lớp: tài khoản, VPC, subnet, security group tham chiếu nhau, egress có kiểm soát (bài Network trên cloud). Danh tính là lớp quan trọng nhất vì API của cloud gọi được từ bất cứ đâu có credential.
