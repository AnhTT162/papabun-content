## Quick

[[continuous-integration|CI]] là mọi người tích hợp vào nhánh chính ít nhất mỗi ngày và mỗi lần đều được build, test tự động; [[continuous-delivery|continuous delivery]] là main luôn ở trạng thái deploy được, [[continuous-deployment|continuous deployment]] là mọi commit xanh tự lên production. **Build một [[build-artifact|artifact]] một lần rồi đưa chính nó qua mọi môi trường**, test nhanh chạy trước, và tách *deploy* (đưa code lên) khỏi *release* (bật cho người dùng) bằng [[feature-flag|feature flag]].

## Interview

[[deployment-pipeline|Pipeline]] của tôi chia stage theo chi phí và tốc độ phản hồi.

Stage commit chạy trên mọi pull request, mục tiêu dưới 10 phút: compile, unit test, kiểm tĩnh (format, ArchUnit, quét secret và dependency), đóng gói image để test sớm. Image dùng để promote được build đúng một lần trên commit thật sự vào main (sau merge queue hay squash merge thì đó là commit mới): tag bằng commit SHA đó, tham chiếu bằng digest, từ đây không build lại nữa.

Stage tích hợp: integration test với database thật qua Testcontainers, contract test (`can-i-deploy` của Pact), quét lỗ hổng image. [[merge-queue|Merge queue]] chạy lại trên kết quả gộp để main không đỏ vì hai pull request xanh riêng nhưng xung đột khi gộp.

Stage deploy: cùng artifact lên staging, [[smoke-test|smoke test]] và vài kịch bản e2e quan trọng, rồi lên production bằng rolling hay canary, có kiểm tra tự động sau deploy (tỉ lệ lỗi, latency so với bản cũ) và tự quay lại khi xấu đi. Có cần người duyệt hay không tuỳ rủi ro, nhưng người duyệt nhìn vào dữ liệu của pipeline, không deploy bằng tay.

Feature flag tách deploy khỏi release: code chưa xong vẫn merge vào main mỗi ngày nhưng ẩn sau flag; bật dần theo phần trăm người dùng; có sự cố thì tắt flag thay vì rollback cả bản. Cái giá là nợ flag: mỗi flag release phải có ngày gỡ.

Tôi đo bằng các chỉ số [[dora-metrics|DORA]]: lead time từ commit tới production, tần suất deploy, thời gian khôi phục sau deploy lỗi, tỉ lệ deploy cần xử lý gấp, tỉ lệ deploy ngoài kế hoạch do sự cố. Nghiên cứu của DORA nhiều năm cho thấy nhanh và ổn định thường đi cùng nhau chứ không phải đánh đổi.

Bẫy hay gặp: build lại artifact cho từng môi trường; pipeline 60 phút khiến mọi người gộp thay đổi lớn; test chập chờn bị rerun cho qua; và secret của cloud lưu cứng trong CI thay vì OIDC.

## Deep

- **CI thật sự là gì**: không phải "có Jenkins". Theo định nghĩa của Martin Fowler, mỗi người tích hợp vào mainline ít nhất mỗi ngày, mỗi lần tích hợp được build tự động kiểm chứng, và main đỏ thì sửa ngay trước mọi việc khác. Nhánh feature sống hai tuần có CI chạy trên nhánh vẫn không phải CI (bài Git bên trong & quy trình nhánh).
- **Trunk-based là nền**: CI chỉ có nghĩa khi nhánh sống ngắn; thay đổi lớn đi bằng [[trunk-based-development|trunk-based]] với feature flag hoặc branch by abstraction thay vì nhánh dài.
- **Delivery khác deployment**: continuous delivery giữ mọi commit trên main ở trạng thái lên production được, việc bấm nút có thể còn là quyết định nghiệp vụ; continuous deployment bỏ bước bấm nút. Ứng dụng mobile, phần mềm cài tại khách thường chỉ đạt delivery.
- **Một artifact, nhiều môi trường**:
  - Cấu hình theo môi trường nằm ngoài artifact (bài Twelve-Factor App); promote bằng cách đổi digest image trong cấu hình của môi trường sau (bài Helm, Kustomize & cấu hình nhiều môi trường).
  - Build có thể tái lập (cố định phiên bản plugin, dependency, base image theo digest) để điều tra được sau này; ký image và sinh provenance, SBOM (bài Bảo mật trong quy trình phát triển).
- **Giữ pipeline nhanh**:
  - Cache dependency Maven/Gradle giữa các lần chạy; build image dùng cache layer và cache mount của BuildKit (bài Docker & container).
  - Chạy song song các job độc lập, chia bộ test lớn thành nhiều mảnh.
  - Monorepo: chỉ build và test phần bị ảnh hưởng (Gradle, Bazel, Nx hiểu đồ thị phụ thuộc).
  - Test chậm và e2e dời sang stage sau hoặc chạy theo lịch; giữ stage commit dưới 10 phút. Phân bổ test giữa các tầng ở bài Test pyramid & chiến lược test.
- **Test chập chờn**: rerun tự động làm pipeline xanh giả và che bug thật về race condition; cách cách ly, đo tỉ lệ chập chờn và sửa ở bài Test chập chờn.
- **Migration database trong pipeline**: chạy migration như một bước trước deploy (Job dùng cùng image), và chỉ dùng thay đổi tương thích ngược để bản cũ và mới cùng chạy được trong lúc rollout; mẫu expand/contract ở bài Rolling, blue-green, canary.
- **Kiểm tra sau deploy và tự rollback**: so tỉ lệ 5xx, latency p99, lỗi nghiệp vụ của bản mới với bản cũ trong vài phút đầu (Argo Rollouts, Flagger, CodeDeploy); vượt ngưỡng thì quay lại không cần người. Rollback chỉ an toàn khi schema và message vẫn tương thích với bản cũ.
- **Feature flag** (phân loại theo bài Feature Toggles của Pete Hodgson trên martinfowler.com):
  - Release toggle (ẩn tính năng dở, sống ngắn), experiment toggle (A/B), ops toggle (kill switch, tắt tính năng nặng khi quá tải), permission toggle (tính năng cho nhóm khách hàng).
  - Flag sống lâu thì số tổ hợp cần test tăng theo cấp số; mỗi release toggle có chủ và ngày gỡ, CI cảnh báo flag quá hạn.
  - Phần trăm rollout phải ổn định theo người dùng (băm `user_id` vào bucket), nếu không một người dùng thấy tính năng lúc có lúc không; test cả hai trạng thái của flag.
  - Đánh giá flag phải nhanh và không phụ thuộc mạng ở mỗi request: SDK giữ bản sao cấu hình trong bộ nhớ và cập nhật nền; dịch vụ flag sập thì dùng giá trị mặc định an toàn. OpenFeature là API chuẩn trung lập nhà cung cấp.
  - Flag không thay được tương thích dữ liệu: bật flag ghi định dạng mới rồi tắt đi thì dữ liệu đã ghi vẫn ở định dạng mới.
- **Bảo mật pipeline**: OIDC thay access key, job từ fork không có secret, ghim action theo commit SHA; chi tiết ở bài Bảo mật trong quy trình phát triển.
- **Pipeline as code**: định nghĩa trong repo (GitHub Actions, GitLab CI, Jenkinsfile), review như code, tái dùng bằng template của platform team. Pipeline sửa tay trên giao diện là cấu hình không ai review và không tái lập được.
- **DORA**: năm chỉ số chia hai nhóm: throughput (change lead time, deployment frequency, failed deployment recovery time) và instability (change fail rate, deployment rework rate). Đo theo từng service và xu hướng, không dùng để xếp hạng hay thưởng phạt team, vì chỉ số bị biến thành mục tiêu thì mất ý nghĩa.
