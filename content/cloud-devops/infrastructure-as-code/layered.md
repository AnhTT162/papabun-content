## Quick

[[infrastructure-as-code|IaC]] mô tả hạ tầng bằng code có review và lịch sử; [[terraform|Terraform]] so code với [[terraform-state|state]] và thực tế rồi tính ra kế hoạch thay đổi. **Đọc kỹ `plan` trước khi `apply`, giữ state ở backend chung có khoá, và nhớ rằng đổi địa chỉ tài nguyên trong code có thể có nghĩa là xoá và tạo lại.** [[gitops|GitOps]] đưa cùng ý tưởng vào Kubernetes: agent trong cluster liên tục kéo git về và sửa lệch.

## Interview

Không có IaC thì hạ tầng là kết quả của hàng trăm cú click không ai nhớ: không dựng lại được môi trường, không review được thay đổi, staging và prod lệch nhau. IaC cho hạ tầng cùng quy trình như code: pull request, review, CI, lịch sử.

Terraform làm việc theo ba nguồn: code mô tả trạng thái mong muốn, state ghi lại tài nguyên nào trong code ứng với tài nguyên thật nào (theo ID), và API của cloud cho trạng thái thật. `terraform plan` làm mới state từ thực tế, so với code, rồi in ra tạo, sửa tại chỗ, thay thế (xoá rồi tạo) hay xoá. Một số thuộc tính không sửa tại chỗ được, như tên queue hay CIDR của subnet, nên đổi nó là thay thế cả tài nguyên.

State là thứ quý nhất: mất state thì Terraform không biết mình quản lý gì; hai người apply cùng lúc thì hỏng state. Tôi đặt state ở backend chung (S3 có bật versioning và mã hoá, khoá bằng `use_lockfile`), mỗi môi trường và mỗi phạm vi một state nhỏ (mạng, database, từng service) để plan nhanh và lỗi không lan. Code dùng chung đóng thành [[terraform-module|module]] có phiên bản.

Quy trình: pull request chạy `fmt`, `validate`, policy check, và `plan` với kết quả đăng vào pull request; merge thì pipeline apply đúng plan đã duyệt. Không ai sửa tay trên console; nếu có, plan định kỳ phát hiện [[configuration-drift|drift]].

Với Kubernetes, tôi dùng GitOps: [[argo-cd|Argo CD]] trong cluster đọc repo cấu hình, đồng bộ manifest, tự sửa khi có người `kubectl edit`. CI chỉ build image và mở pull request đổi digest; cluster tự kéo, không cần cấp quyền cluster cho CI.

Bẫy hay gặp: `count` theo danh sách, xoá một phần tử ở giữa là đánh số lại và thay thế mọi thứ phía sau; secret nằm dạng rõ trong state; một state khổng lồ cho cả công ty mà plan mất 20 phút.

## Deep

- **Plan đọc thế nào**: `+` tạo, `~` sửa tại chỗ, `-/+` thay thế (xoá rồi tạo, dòng có `# forces replacement` cho biết thuộc tính gây ra), `-` xoá. Dòng tổng `Plan: X to add, Y to change, Z to destroy` là thứ đầu tiên phải nhìn: một thay đổi tưởng nhỏ mà có `destroy` là phải dừng lại. `create_before_destroy` trong `lifecycle` đảo thứ tự cho tài nguyên chịu được hai bản cùng lúc.
- **Địa chỉ tài nguyên**:
  - `count` đánh số theo vị trí: danh sách `[a, b, c]` bỏ `b` thì `[1]` đổi từ `b` thành `c` (thay thế nếu thuộc tính đó là ForceNew) và `[2]` bị xoá. `for_each` theo map hay set gắn mỗi tài nguyên với một khoá ổn định, nên thêm bớt không ảnh hưởng phần còn lại.
  - Đổi tên resource, chuyển vào module, đổi `count` sang `for_each`: khai báo khối `moved` để Terraform hiểu đây là cùng một tài nguyên thay vì xoá rồi tạo. `import` (khối trong code) đưa tài nguyên đã có vào quản lý; `removed` (kèm `lifecycle { destroy = false }`) bỏ khỏi state mà không xoá tài nguyên thật.
  - `lifecycle { prevent_destroy = true }` cho tài nguyên có dữ liệu (database, bucket, queue): plan nào muốn xoá sẽ báo lỗi.
- **State**:
  - Backend S3: bật versioning để khôi phục state cũ, mã hoá, chặn public; khoá bằng `use_lockfile = true` (file khoá trong chính bucket, có từ Terraform 1.10). Khoá bằng DynamoDB đã deprecated. Khoá kẹt sau khi pipeline chết thì `terraform force-unlock` sau khi chắc không ai đang chạy.
  - File plan và state đều chứa giá trị dạng rõ; `sensitive = true` chỉ che khi in ra màn hình. Lưu file plan có mã hoá, giới hạn quyền và xoá sau khi apply.
  - `-target` chỉ để chữa cháy, không dùng thường xuyên; `.terraform.lock.hcl` ghim phiên bản provider và phải commit.
  - State chứa giá trị thuộc tính dạng rõ, kể cả password database nếu bạn truyền vào. Hạn chế ai đọc được bucket state; dùng ephemeral resource và đối số write-only (Terraform 1.10/1.11 trở lên, khi provider hỗ trợ) để secret không bị ghi vào state, hoặc để dịch vụ tự sinh và quản lý password (RDS tích hợp Secrets Manager).
  - Chia state theo vòng đời và người sở hữu: mạng (ít đổi) tách khỏi app (đổi thường); prod tách khỏi dev. Đọc output của state khác qua data source hoặc tham số, tránh phụ thuộc chéo vòng tròn.
- **Module**: đóng gói một mẫu có quyết định sẵn (VPC chuẩn ba tầng, service ECS với alarm mặc định). Ghim phiên bản khi gọi module; module quá chung chung với hàng chục biến cho mọi trường hợp thì khó dùng hơn viết thẳng. Module không thay được việc hiểu tài nguyên bên dưới.
- **Drift**: ai đó sửa security group trên console thì lần `plan` sau đề xuất đưa về như code và `apply` sẽ hoàn tác thay đổi đó (với luật khai báo trong khối `ingress` của chính `aws_security_group`; luật quản lý bằng resource riêng thì luật mở tay nằm ngoài tầm Terraform). Chạy `terraform plan -refresh-only` hay plan định kỳ trong CI để phát hiện; với thay đổi khẩn cấp, sửa code ngay sau đó. Thuộc tính do hệ thống khác quản lý (số task do autoscaling chỉnh) thì đặt `ignore_changes`.
- **[[policy-as-code|Policy as code]]**: kiểm plan bằng OPA/Conftest, Checkov, Sentinel: chặn bucket public, security group mở 0.0.0.0/0 cho cổng quản trị, thiếu tag chi phí, và chặn plan có `destroy` cho loại tài nguyên được bảo vệ.
- **Công cụ**: Terraform đổi giấy phép sang BSL năm 2023; OpenTofu là nhánh mã nguồn mở dưới Linux Foundation, tương thích phần lớn. CloudFormation và CDK là của AWS, state do AWS giữ, có rollback khi stack lỗi. Pulumi viết bằng ngôn ngữ lập trình thông thường.
- **GitOps** (bốn nguyên tắc OpenGitOps v1.0.0): trạng thái mong muốn khai báo; lưu có phiên bản, bất biến; agent tự kéo về; liên tục đối soát.
  - Argo CD: mỗi Application trỏ tới một đường dẫn trong repo (YAML thuần, Kustomize hoặc Helm); `selfHeal` hoàn tác sửa tay, `prune` xoá tài nguyên đã bỏ khỏi git; sync wave và hook để sắp thứ tự (migration trước, app sau). Flux là lựa chọn tương tự.
  - So với push từ CI: CI không cần credential của cluster, cluster tự hồi phục về git, rollback là revert commit. Giá: thêm một hệ thống phải vận hành, và secret phải có cách riêng (External Secrets Operator, Sealed Secrets; bài Helm, Kustomize & cấu hình nhiều môi trường).
  - Hạ tầng cloud (VPC, RDS) vẫn thường dùng Terraform qua pipeline; có thể quản lý từ Kubernetes bằng Crossplane hay AWS Controllers for Kubernetes khi muốn một mô hình GitOps cho tất cả.
- **Immutable infrastructure**: thay máy chứ không vá máy: image (AMI, container) dựng sẵn từ pipeline, thay cả instance khi đổi; không SSH vào sửa. Đi cùng IaC để môi trường dựng lại được từ đầu, điều kiện của DR (bài High availability & disaster recovery).
