## Quick

[[serverless|Serverless]] là không quản lý server: nền tảng tự tạo môi trường chạy khi có việc, scale tới 0 khi không có, tính tiền theo lượng dùng. Với [[faas|FaaS]] như AWS Lambda (kiểu mặc định), **mỗi môi trường chỉ xử lý một lời gọi tại một thời điểm, có thể bị tạo mới bất cứ lúc nào ([[cold-start|cold start]]), và bị giới hạn 15 phút**. Hợp với tải theo sự kiện, thất thường; đắt và khó chịu với tải đều, lớn, cần latency ổn định.

## Interview

Lambda chạy code trong một execution environment (micro VM Firecracker). Lời gọi đầu tiên phải qua pha Init: tải code, khởi động runtime, chạy phần khởi tạo ngoài handler; đó là cold start. Sau đó môi trường được giữ lại và tái dùng cho lời gọi tiếp theo, nên kết nối database, client SDK nên tạo một lần ngoài handler. Với Lambda mặc định, mỗi môi trường xử lý một lời gọi tại một thời điểm: 200 lời gọi đồng thời là 200 môi trường, và 200 kết nối database nếu mỗi môi trường mở một kết nối.

Với Java, cold start là điểm yếu: JVM khởi động, nạp class, rồi framework dựng context, có thể vài giây với Spring. Cách giảm: SnapStart chụp môi trường sau Init và khôi phục từ ảnh chụp; provisioned concurrency giữ sẵn số môi trường đã khởi tạo (tính tiền cả lúc rảnh); bớt framework nặng; hoặc native image. Bộ nhớ quyết định cả CPU: 1.769 MB tương đương một vCPU, nên tăng bộ nhớ thường làm cold start và thời gian chạy ngắn lại.

Giới hạn cần nhớ: timeout tối đa 15 phút; payload đồng bộ 6 MB; concurrency mặc định 1.000 mỗi region cho cả tài khoản, mỗi function thêm tối đa 1.000 môi trường mỗi 10 giây.

Tôi dùng Lambda cho việc theo sự kiện: xử lý file mới trên S3, đọc SQS, webhook, job định kỳ, API ít traffic hay traffic rất thất thường. Không dùng cho service tải đều hàng nghìn request mỗi giây (container rẻ hơn nhiều), xử lý dài hơn 15 phút, hay API cần p99 ổn định dưới vài chục mili giây mà không trả tiền giữ sẵn môi trường.

Bẫy hay gặp: Lambda scale nhanh làm cạn connection của RDS (dùng RDS Proxy hoặc giới hạn concurrency); lời gọi bất đồng bộ được retry tự động nên handler phải idempotent; và một function gọi đồng bộ function khác là trả tiền cho cả hai lúc chờ.

## Deep

- **Vòng đời môi trường**: Init (tối đa 10 giây; quá thì Lambda khởi tạo lại trong lời gọi đầu với timeout của function; với provisioned concurrency, SnapStart, Managed Instances thì Init được chạy tới 15 phút), Invoke, Shutdown. Thời gian Init cũng bị tính tiền. Môi trường bị đóng băng giữa các lời gọi: thread nền, timer, kết nối có thể bị ngắt quãng; đừng dựa vào việc nền chạy sau khi handler trả về.
- **Giới hạn** (tài liệu Lambda 11/2026):
  - Timeout 900 giây; bộ nhớ 128–10.240 MB; `/tmp` 512–10.240 MB.
  - Payload: 6 MB mỗi chiều cho gọi đồng bộ, 200 MB cho response stream, 1 MB cho gọi bất đồng bộ.
  - Concurrency 1.000 mỗi region, xin tăng được tới hàng chục nghìn; tốc độ scale mỗi function 1.000 môi trường mỗi 10 giây.
- **Giảm cold start cho Java**:
  - SnapStart (Java 11 trở lên, Python 3.12 trở lên, .NET 8 trở lên): Lambda chạy Init khi publish phiên bản, chụp bộ nhớ và đĩa, rồi khôi phục cho mỗi môi trường mới. Bẫy giống [[crac|CRaC]] (bài Khởi động nhanh: CDS, CRaC, GraalVM native): seed ngẫu nhiên, ID, token giống nhau giữa các bản khôi phục; kết nối mở lúc Init đã chết khi khôi phục. Dùng hook trước chụp, sau khôi phục (API `org.crac` hay `Lifecycle` của Spring) để đóng và mở lại.
  - SnapStart chỉ dùng cho phiên bản đã publish (không cho `$LATEST`), không dùng chung với provisioned concurrency, EFS hay `/tmp` lớn hơn 512 MB; cold start của nó đo bằng `Restore Duration` thay vì `Init Duration`. Có thể chạy trước đường code nóng trong hook trước khi chụp (priming) để ảnh chụp có class đã nạp sẵn.
  - [[provisioned-concurrency|Provisioned concurrency]] (lựa chọn thay cho SnapStart, không phải dùng cùng): giữ sẵn N môi trường đã Init, không cold start trong giới hạn N, tính tiền theo giờ dù không có lời gọi. Kết hợp auto scaling theo lịch cho giờ cao điểm.
  - Bớt việc lúc khởi tạo: framework nhẹ hơn hoặc Spring Cloud Function với AOT, ít reflection, chọn arm64 (rẻ hơn, thường nhanh hơn), tăng bộ nhớ để có thêm CPU lúc Init.
- **Concurrency**: [[reserved-concurrency|reserved concurrency]] vừa giữ chỗ vừa là trần cho một function (đặt 0 là tắt function); bảo vệ dependency phía sau. Khi đọc SQS, giới hạn bằng maximum concurrency của event source mapping (bài Dịch vụ managed của AWS).
- **Kết nối database**: mỗi môi trường một kết nối, scale tới hàng trăm môi trường thì PostgreSQL hết `max_connections`. RDS Proxy gom kết nối; hoặc dùng database hợp mô hình này (DynamoDB, Aurora Data API).
- **Gọi bất đồng bộ**: S3, SNS, EventBridge gọi Lambda bất đồng bộ; lỗi thì Lambda tự thử lại 2 lần, sự kiện giữ tối đa 6 giờ, sau đó đưa tới destination khi thất bại hoặc DLQ. Vì có retry, handler phải idempotent (Powertools for AWS Lambda có module idempotency dùng DynamoDB).
- **Chi phí**: tính theo số lời gọi cộng GB-giây (làm tròn theo mili giây). Tải thấp và thất thường thì rẻ hơn hẳn máy chạy 24/7; tải đều cao thì container trên Fargate hay EC2 rẻ hơn nhiều lần. Lambda Managed Instances chạy function trên instance EC2 do Lambda quản lý: một môi trường xử lý nhiều lời gọi cùng lúc (code phải an toàn với thread), scale theo CPU, không cold start nhưng cũng không về 0; giá là giá EC2 cộng 15% phí quản lý, phần EC2 được giảm bằng Savings Plans. Hợp với tải lớn và đều mà vẫn giữ mô hình lập trình của Lambda. So sánh chi phí có số liệu ở bài Ước tính chi phí & FinOps.
- **Việc dài và nhiều bước**: một lời gọi tối đa 15 phút. Quy trình nhiều bước, có chờ: Step Functions, hoặc Lambda durable functions (checkpoint tự động, chờ không tính tiền, chạy tới một năm); cùng ý tưởng [[durable-execution|durable execution]] ở bài Thiết kế job scheduler phân tán. Hàm durable được chạy lại từ đầu và bỏ qua các bước đã checkpoint, nên code ngoài các bước phải tất định: không sinh UUID, đọc giờ hay gọi mạng ở ngoài một bước. Chia việc lớn thành nhiều phần qua SQS.
- **Chuỗi gọi đồng bộ**: function A gọi đồng bộ function B thì A trả tiền thời gian chờ B, và lỗi, timeout cộng dồn. Nối bằng queue hay event, hoặc Step Functions.
- **Serverless không chỉ là FaaS**: Fargate (container không quản lý máy), Aurora Serverless v2, DynamoDB on-demand, S3, SQS đều là mô hình trả theo dùng, scale tự động. Kiến trúc serverless là ghép các dịch vụ đó; chọn kiến trúc tổng thể ở bài Chọn kiểu kiến trúc.
- **Phát triển và test**: chạy handler như hàm Java bình thường trong unit test; SAM CLI hay LocalStack giả lập cục bộ nhưng không đúng quota, IAM, cold start; giữ test tích hợp trên tài khoản AWS thật. Observability: log có cấu trúc, trace X-Ray hay OpenTelemetry, metric `Duration`, `Throttles`, `ConcurrentExecutions`, và `Init Duration` trong dòng log `REPORT` để đếm cold start.
