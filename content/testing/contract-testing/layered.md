## Quick

Contract test kiểm **hai service có hiểu nhau không** mà không cần dựng cả hai cùng lúc. Với [[consumer-driven-contract|consumer-driven contract]], consumer ghi kỳ vọng của mình (request nó gửi, phần response nó thật sự dùng) thành contract; provider chạy contract đó với code thật trong CI của mình. **Contract kiểm hình dạng của giao tiếp, không kiểm nghiệp vụ của provider**, và chỉ thật sự có giá trị khi gắn vào quyết định deploy ([[can-i-deploy|`can-i-deploy`]]).

## Interview

**Vấn đề nó giải**: e2e giữa chục service chậm và chập chờn; còn stub HTTP do consumer tự viết có thể lệch với provider thật mà không ai biết, cho tới production.

**Luồng [[pact|Pact]]**:
1. Test của consumer chạy với mock server của Pact, sinh pact file JSON gồm các interaction và matcher.
2. CI publish pact lên [[pact-broker|Pact Broker]] kèm version (git SHA) và branch.
3. CI của provider lấy các pact cần kiểm theo consumer version selector (`mainBranch`, `deployedOrReleased`), phát lại từng request vào provider thật và so response với matcher. Dữ liệu cần cho mỗi interaction được dựng qua [[provider-state|provider state]] (`given(...)` phía consumer, `@State` phía provider).
4. Trước khi deploy, `can-i-deploy` hỏi broker: phiên bản này đã được kiểm tương thích với các phiên bản đang chạy ở môi trường đích chưa. Deploy xong thì `record-deployment`.

**Matcher**: kiểm theo kiểu (`stringType`, `integerType`, regex) thay vì giá trị cụ thể. Provider thêm trường mới vẫn qua; đổi tên hay bỏ trường mà consumer dùng thì fail.

**Spring Cloud Contract**: contract (Groovy, YAML) nằm ở repo provider; plugin sinh test cho provider và sinh stub WireMock đóng gói thành jar để consumer chạy bằng stub runner. Hợp khi cả hai phía dùng JVM và provider làm chủ hợp đồng; Pact đa ngôn ngữ và đúng nghĩa consumer-driven hơn.

**Không dùng cho**: kiểm nghiệp vụ của provider (việc của test riêng provider); API public có nhiều client không biết trước, khi đó so [[openapi|OpenAPI]] giữa hai phiên bản và versioning hợp hơn.

## Deep

- **Đo trên ví dụ thật** (Pact JVM 4.7.6, JUnit 6.1.3): consumer `order-service` khai báo `stringType("sku")`, `integerType("available")`; pact file sinh ra theo spec 4.0 có `matchingRules` `$.sku: type` và `$.available: integer`. Provider trả thêm trường `warehouse`: verify qua. Provider đổi `available` thành `availableQty`: "has a matching body (FAILED)", kèm "Actual map is missing the following keys: available" và diff hai body.
- **Contract không phải functional test**: chỉ khai báo trường consumer dùng, mỗi interaction độc lập, không viết chuỗi "tạo đơn rồi huỷ đơn". Đưa luật nghiệp vụ của provider vào pact (như "số lượng âm phải bị từ chối với thông báo X") làm pact giòn và chồng lấn test của provider.
- **Provider state là hợp đồng giữa hai đội**: đặt tên theo nghiệp vụ ("SKU PHO-01 có 12 sản phẩm trong kho"), không theo bảng hay id nội bộ. Provider cài handler dựng dữ liệu (insert vào database test hoặc stub tầng repository) nhưng vẫn chạy controller, serialize, filter thật; verify với controller bị mock thì mất phần lớn giá trị.
- **Consumer version selector khuyên dùng**: `{ "mainBranch": true }` và `{ "deployedOrReleased": true }`; khi hai đội làm tính năng chung trên nhánh cùng tên thì thêm `{ "matchingBranch": true }`. Provider kiểm đúng các phiên bản consumer có thể gặp ở production, không kiểm mọi pact từng có.
- **Pending pact và WIP pact**: pact mới mà provider chưa từng kiểm qua không làm đỏ build của provider (chỉ báo) cho tới lần đầu pass; WIP pact cho provider tự lấy pact từ nhánh đang phát triển của consumer. Hai cơ chế này để consumer thêm kỳ vọng mới mà không chặn pipeline của đội khác; chúng chỉ chạy đúng khi provider publish kết quả verify kèm branch của mình.
- **Webhook**: broker gọi CI của provider khi có pact mới cần verify (sự kiện `contract_requiring_verification_published`), để consumer biết kết quả trong vài phút thay vì chờ lần build sau của provider.
- **`can-i-deploy` cần dữ liệu deploy**: broker là ma trận phiên bản consumer × provider × kết quả verify. Thiếu `record-deployment` ở một phía thì broker không biết phiên bản nào đang chạy ở môi trường nào, và câu trả lời mất ý nghĩa. Lệnh này nên là một bước chặn trong pipeline deploy của **cả hai** phía.
- **Contract cho message**: Pact có message pact cho payload event (Kafka, RabbitMQ): consumer khai báo event nó đọc, provider kiểm hàm sinh event. Bổ sung cho [[schema-registry|schema registry]] (bài Event schema evolution): registry kiểm tương thích schema nói chung, contract cho biết consumer cụ thể nào dùng trường nào, nên biết bỏ trường nào là an toàn.
- **Bi-directional contract testing** (PactFlow): provider đưa OpenAPI đã tự kiểm bằng công cụ của mình, PactFlow (bản thương mại, không có trong Pact Broker mã nguồn mở) so pact của consumer với spec thay vì phát lại request. Triển khai nhanh cho provider không muốn viết state handler, nhưng chỉ đáng tin bằng mức spec khớp với code.
- **Spring Cloud Contract chi tiết**: bản 5.0.x đi cùng Spring Cloud 2025.1 cho Spring Boot 4 (Boot 3 dùng dòng 4.x). Contract viết bằng Groovy, YAML, Java hoặc Kotlin DSL trong `src/test/resources/contracts`; base class dựng `RestAssuredMockMvc` với controller thật; stub jar (classifier `stubs`) được publish lên kho Maven; consumer dùng `@AutoConfigureStubRunner(ids = "shop:inventory:+:stubs", stubsMode = StubsMode.REMOTE, repositoryRoot = "...")`, vì mặc định `CLASSPATH` chỉ tìm stub trên classpath. Muốn consumer-driven thì đội consumer mở pull request thêm contract vào repo provider. Service không chạy JVM chỉ dùng được qua Docker image và Stub Runner Boot, kém tự nhiên hơn thư viện Pact cho từng ngôn ngữ.
- **Message pact với Avro hay Protobuf**: message pact so nội dung dạng JSON; event nhị phân phải kiểm qua biểu diễn JSON của record hoặc qua plugin của Pact cho định dạng đó.
- **Enum và giá trị mới**: matcher theo kiểu (`stringType`) cho qua mọi chuỗi, nên provider thêm giá trị enum mới không làm verify fail. Muốn bắt điều đó, consumer khai báo regex liệt kê giá trị nó hiểu, và provider state phải sinh ra giá trị mới thì verify mới thấy.
- **Consumer test phải đi qua HTTP client thật** của consumer (cùng cấu hình URL, header, serialize), không tự gọi mock server bằng một client khác; nếu không pact mô tả request mà code thật không gửi. Phía provider, xác thực khi verify thường xử lý bằng request filter gắn token test.
- **Bẫy của `can-i-deploy`**: hai bên chưa có pact nào thì lệnh trả pass; provider chưa kịp verify thì kết quả là chưa biết (dùng `--retry-while-unknown`); môi trường phải được khai báo trước trong broker; app di động hay thư viện không deploy liên tục thì dùng `record-release` thay `record-deployment`.
- **Bẫy khi triển khai**: chỉ chạy verify mà không gắn `can-i-deploy` (vẫn deploy được phiên bản phá vỡ); version pact theo số tự tăng thay vì git SHA; một pact khổng lồ do một người viết cho mọi consumer; xoá hết e2e. Giữ vài smoke test sau deploy cho hành trình sống còn (bài Test pyramid & chiến lược test).
- **Khi nào không đáng**: hai service do cùng một đội sở hữu, deploy cùng lúc; hoặc chỉ một consumer và một provider ít đổi. Chi phí vận hành broker, state handler và kỷ luật versioning khi đó lớn hơn lợi ích; integration test với stub và OpenAPI diff là đủ.
