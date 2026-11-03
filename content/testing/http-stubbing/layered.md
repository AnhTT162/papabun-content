## Quick

[[wiremock|WireMock]] chạy một HTTP server thật trên cổng ngẫu nhiên ngay trong test và trả response dựng sẵn cho request khớp với [[test-stub|stub]]. Nhờ vậy test được **toàn bộ HTTP client của bạn qua mạng thật**: URL, header, JSON, xử lý mã lỗi, timeout, retry, kết nối bị cắt, những thứ mock một interface Java bỏ qua. **Stub chỉ kiểm cách bạn hiểu API; provider có thật sự trả như vậy không thì cần [[consumer-driven-contract|contract test]].**

## Interview

**Vì sao không mock client**: mock `PaymentClient` bỏ qua đúng phần hay hỏng nhất: URL, header, mapping JSON, xử lý 4xx/5xx, timeout, connection pool. WireMock là stub ở tầng HTTP: code chạy y như production, chỉ đổi base URL.

**Cách dùng**: `WireMockExtension` của JUnit 5 với `dynamicPort()`; khai báo `stubFor(post("/payments").withHeader(...).withRequestBody(equalToJson(...)).willReturn(okJson(...)))`; đưa base URL cho ứng dụng qua `@DynamicPropertySource` hoặc thư viện `wiremock-spring-boot`. Request không khớp stub nào nhận `404` kèm bảng "Closest stub" chỉ đúng chỗ lệch.

**Test đường lỗi**: mã lỗi (500, 503, 429 kèm `Retry-After`); chậm (`withFixedDelay` cho header đến muộn, `withChunkedDribbleDelay` cho body nhỏ giọt) để kiểm timeout của client, như [[read-timeout|read timeout]]; lỗi mạng bằng [[fault-injection|fault injection]] (`Fault.CONNECTION_RESET_BY_PEER`, `EMPTY_RESPONSE`); scenario (lần đầu 503, lần sau 200) để kiểm retry. Với mỗi loại lỗi, kiểm client trả gì cho code gọi nó: exception nghiệp vụ nào, có thử lại không, thử lại bao nhiêu lần. Đó là hợp đồng giữa client và phần còn lại của service, và là chỗ bug production hay nằm.

**Verify số request**: `verify(3, postRequestedFor(urlEqualTo("/payments")))` đếm request thật đã tới, kèm header và body. Đây là cách duy nhất thấy retry gửi bao nhiêu lần và gửi gì.

**Bẫy hay gặp**: chỉ test happy path; stub viết theo trí nhớ, lệch với API thật; test timeout bằng delay dài làm suite chậm (đặt timeout nhỏ cho client trong test); retry `POST` không có [[idempotency-key|idempotency key]], hoặc sinh key mới mỗi lần thử.

## Deep

- **Đo trên ví dụ thật** (WireMock 3.13.2, `java.net.http.HttpClient` của JDK 27): client timeout 1 giây, retry 3 lần khi timeout, stub trả sau 1,5 giây. Cổng thanh toán nhận 3 request `POST /payments`, mỗi request một `Idempotency-Key` khác nhau. Timeout ở client không huỷ việc phía server: cả ba lần đều được xử lý xong. Cách làm key đúng ở bài Idempotency.
- **Fault và exception phía client** (JDK 27): `CONNECTION_RESET_BY_PEER` ra `IOException: Connection reset`; `EMPTY_RESPONSE` ra `IOException: EOF reached while reading`; `MALFORMED_RESPONSE_CHUNK` và `RANDOM_DATA_THEN_CLOSE` cũng ra `IOException` với message khác. Code phân loại lỗi để retry nên dựa vào kiểu exception (và `HttpTimeoutException` là lớp con của `IOException`), không dựa vào message.
- **Timeout của JDK `HttpClient`**: không có timeout mặc định cho request; `HttpRequest.timeout(...)` là thời hạn cho cả response, nên với `BodyHandlers.ofString()` nó cắt cả khi header đến chậm lẫn khi body nhỏ giọt (đo: body 1.000 byte rải trong 3 giây bị cắt sau khoảng 1 giây). Client dùng timeout theo từng lần đọc socket (`responseTimeout` của Apache HttpClient 5, `readTimeout` của OkHttp) thì khác: body nhỏ giọt chỉ bị cắt khi một khoảng trống giữa hai lần nhận vượt timeout, nên chọn `withChunkedDribbleDelay` cho khớp với kiểu timeout cần kiểm. Mặc định của Apache HttpClient 5 và cách đặt pool, timeout ở bài Tuning server & HTTP client.
- **Connect timeout** khó test bằng WireMock, vì server luôn nhận kết nối; thường dùng một địa chỉ không định tuyến được, phụ thuộc mạng của máy chạy test nên chỉ giữ rất ít test kiểu này.
- **Khớp request**: `urlEqualTo` so cả query string theo đúng thứ tự; `urlPathEqualTo` cộng `withQueryParam` linh hoạt hơn. `equalToJson(json, true, true)` bỏ qua thứ tự mảng và trường thừa; `matchingJsonPath` kiểm từng trường. Nhiều stub cùng khớp thì stub khai báo sau thắng, trừ khi đặt `atPriority`.
- **Scenario**: `inScenario("flaky").whenScenarioStateIs(STARTED).willSetStateTo("recovered")` cho máy trạng thái nhỏ (đo: 503, rồi 200, 200). Dùng để test retry hồi phục, hoặc [[circuit-breaker|circuit breaker]]: trả 500 liên tục rồi `verify` rằng sau ngưỡng mở mạch không còn request nào tới (bài Timeout, retry, circuit breaker, bulkhead).
- **Record và playback**: chạy WireMock làm proxy tới sandbox của provider để ghi lại mapping JSON. Nhanh có stub giống thật, nhưng bản ghi cũ dần và chứa header thừa; review và rút gọn trước khi commit, không để lộ token.
- **Trong Spring**: `wiremock-spring-boot` (4.4.3, dùng `wiremock-jetty12` 3.13.2) có `@EnableWireMock` và `@ConfigureWireMock(baseUrlProperties = "payment.base-url")` để tự đặt property base URL. `MockRestServiceServer` của Spring mock ở tầng `RestTemplate`/`RestClient`, không đi qua mạng, nên không kiểm được timeout hay connection pool.
- **Chỉ kiểm phía bạn**: stub cho thấy client xử lý đúng response mà bạn tin provider sẽ trả. Khi provider đổi tên trường, test vẫn xanh. Dùng contract test, hoặc sinh stub từ contract (stub runner của Spring Cloud Contract) để stub và provider không lệch nhau (bài Contract testing).
- **Phiên bản** (11/2026): WireMock 3.x là bản ổn định (3.13.2); 4.x vẫn đang beta (4.0.0-beta.41). Lựa chọn khác: MockWebServer của OkHttp (nhẹ, xếp hàng response theo thứ tự), MockServer, Hoverfly.
- **Chạy riêng ngoài JVM**: WireMock standalone (jar hoặc Docker) với mapping JSON trong thư mục `mappings/`, dùng làm downstream giả cho môi trường test nhiều service; khi đó stub thành tài sản dùng chung, cần có người sở hữu và cập nhật theo API thật.
