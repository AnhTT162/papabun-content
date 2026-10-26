## Quick

Service nói chuyện với nhau theo hai kiểu. **Đồng bộ** (REST, [[grpc|gRPC]], [[graphql|GraphQL]]): bên gọi chờ kết quả, nên phụ thuộc vào việc bên kia đang sống. **Bất đồng bộ** (message qua Kafka, RabbitMQ): bên gửi không chờ, hai bên tách nhau về thời gian. Chọn đồng bộ khi **cần câu trả lời ngay để đi tiếp**, bất đồng bộ khi chỉ cần báo rằng việc gì đó đã xảy ra. [[service-discovery|Service discovery]] cho bên gọi biết instance nào đang sống để gọi tới.

## Interview

**REST (HTTP + JSON)**: dễ debug, mọi ngôn ngữ và trình duyệt đều dùng được, cache được với `GET`. Hợp cho API công khai và phần lớn API nội bộ. Hợp đồng mô tả bằng OpenAPI.

**gRPC**: [[protobuf|Protobuf]] (nhị phân, có schema), chạy trên HTTP/2 với [[multiplexing|multiplexing]] và streaming hai chiều, sinh client cho nhiều ngôn ngữ. Hợp cho gọi nội bộ tần suất cao và hợp đồng chặt. Đổi lại: khó debug bằng `curl`, trình duyệt cần gRPC-Web, và cân bằng tải phức tạp hơn (xem Deep).

**GraphQL**: client chọn đúng trường cần, gom nhiều nguồn trong một request. Hợp cho tầng [[bff|BFF]] (backend for frontend) phục vụ app di động và web. Bẫy: resolver gọi lẻ từng bản ghi gây N+1 (gom bằng [[dataloader|DataLoader]]), cache HTTP khó hơn vì phần lớn là `POST`, và cần giới hạn độ sâu và chi phí query.

**Đồng bộ làm khả dụng nhân với nhau**: một request đi qua 3 service, mỗi service sẵn sàng 99,9%, thì tổng chỉ còn khoảng 99,7% (thời gian lỗi tăng gấp ba). Chuỗi gọi đồng bộ dài còn cộng dồn latency và timeout.

**Bất đồng bộ đổi lấy gì**: bên nhận chết thì message chờ trong broker; nhưng phải chấp nhận [[eventual-consistency|eventual consistency]], message trùng ([[idempotent-consumer|consumer idempotent]]), thứ tự chỉ trong phạm vi [[kafka-partition|partition]], và khó trả lời ngay cho người dùng.

**Service discovery**:
- Phía server: Kubernetes Service có DNS ổn định (`payment.default.svc.cluster.local`), kube-proxy chuyển tới pod đang sẵn sàng. Bên gọi không cần thư viện gì.
- Phía client: client hỏi registry (Eureka, Consul) danh sách instance rồi tự cân bằng tải, như Spring Cloud LoadBalancer.

## Deep

- **gRPC và cân bằng tải L4**: HTTP/2 giữ một kết nối lâu dài và gửi mọi request qua đó. Sau một Kubernetes Service thường (L4, theo kết nối), toàn bộ request của một client dồn vào một pod dù có 10 pod. Sửa bằng cân bằng tải phía client ([[headless-service|headless Service]] cùng chính sách `round_robin`; gRPC Java mặc định là `pick_first` nên phải cấu hình tường minh, và đặt `maxConnectionAge` ở server để client phân giải lại DNS và thấy pod mới), proxy L7 (Envoy, service mesh), hoặc đặt tuổi tối đa cho kết nối.
- **Deadline của gRPC**: client đặt deadline, và deadline được truyền theo các lời gọi tiếp theo, nên service ở giữa biết còn bao nhiêu thời gian và bỏ việc khi đã quá hạn. REST không có sẵn cơ chế này; phải tự truyền qua header.
- **Tương thích của Protobuf**: field được nhận diện bằng số, không bằng tên. Thêm field mới với số mới là tương thích; không bao giờ dùng lại số của field đã xoá (đánh dấu `reserved`). Đổi kiểu của field là phá hợp đồng.
- **Client HTTP trong Spring**: `RestTemplate` ở chế độ bảo trì từ 6.1, và Spring đã công bố kế hoạch deprecate nó ở 7.1, gỡ ở 8.0; Spring 6.1 có `RestClient` (đồng bộ, API kiểu fluent) và HTTP interface (`@HttpExchange` trên interface, Spring tạo cài đặt). `WebClient` cho code reactive. Dù dùng cái nào, phải cấu hình connection pool và timeout của HTTP client bên dưới.
- **Request-reply qua message broker**: gửi message rồi chờ reply trên một queue tạm là đồng bộ trá hình: vẫn phụ thuộc bên kia đang sống, lại thêm độ phức tạp của broker. Cần câu trả lời ngay thì gọi đồng bộ với timeout rõ ràng.
- **Chọn theo luồng nghiệp vụ, không chọn một kiểu cho cả hệ thống**: giữ hàng khi đặt đơn cần trả lời ngay (đồng bộ); gửi email xác nhận, cộng điểm, cập nhật báo cáo thì không (event). Một service thường có cả hai.
- **Mã lỗi**: REST dùng HTTP status và [[problem-detail|`ProblemDetail`]]; gRPC có bộ status riêng (`UNAVAILABLE`, `DEADLINE_EXCEEDED`, `INVALID_ARGUMENT`...). Chỉ retry lỗi tạm thời như `UNAVAILABLE`, và chỉ khi thao tác idempotent hoặc có idempotency key: server có thể đã xử lý xong trước khi client nhận lỗi (bài Idempotency). Không retry `INVALID_ARGUMENT`.
- **Versioning**: API công khai version trong URL (`/v2/orders`) hoặc header; API nội bộ ưu tiên thay đổi tương thích ngược để khỏi chạy hai version song song.
- **Xem thêm**: cân bằng tải L4/L7 ở bài Load balancing; timeout, retry, circuit breaker ở bài Resilience patterns; outbox ở bài Transactional outbox & CDC; BFF và gateway ở bài API gateway, BFF & service mesh.
