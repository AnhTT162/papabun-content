## Quick

[[evolutionary-architecture|Kiến trúc tiến hoá]] là kiến trúc hỗ trợ thay đổi từng bước, có định hướng, trên nhiều chiều (kỹ thuật, dữ liệu, bảo mật, vận hành). Định hướng đến từ [[fitness-function|fitness function]]: kiểm tra khách quan, thường tự động, cho biết một đặc tính kiến trúc còn đạt không. **Biến mỗi đặc tính quan trọng thành fitness function chạy trong pipeline hoặc trên production; thay đổi bằng các bước nhỏ mà sau mỗi bước hệ thống vẫn chạy; với hệ thống cũ thì đóng băng vi phạm hiện có và chặn vi phạm mới ([[ratchet|ratchet]]), thay vì viết lại.**

## Interview

Ford, Parsons, Kua và Sadalage định nghĩa kiến trúc tiến hoá là kiến trúc hỗ trợ thay đổi có định hướng, từng bước, trên nhiều chiều. Ý chính: không ai đoán đúng hệ thống sẽ cần gì sau ba năm, nên thay vì vẽ kiến trúc đích rồi hy vọng code giữ được, ta làm cho thay đổi rẻ và an toàn, và kiểm liên tục những đặc tính không được mất.

Công cụ chính là [[fitness-function|fitness function]]. Mỗi đặc tính quan trọng có một kiểm tra khách quan: quy tắc phụ thuộc giữa module bằng [[archunit|ArchUnit]] hay [[spring-modulith|Spring Modulith]], tương thích API bằng [[contract-test|contract test]] hoặc so [[openapi|OpenAPI]], p99 bằng load test có ngưỡng, độ sẵn sàng bằng [[slo|SLO]] trên production, [[cve|CVE]] và license bằng quét dependency. Cái chạy nhanh đặt ở bước commit, cái chậm chạy theo lịch, cái chỉ đo được trên production thì theo dõi liên tục. Fitness function đỏ phải chặn build hoặc có người chịu trách nhiệm xử lý; báo cáo không ai đọc thì không định hướng được gì.

Với hệ thống cũ, bật quy tắc mới thường ra cả nghìn vi phạm. Tôi dùng ratchet: `FreezingArchRule` của ArchUnit lưu vi phạm hiện có, chỉ báo vi phạm mới, và vi phạm đã sửa thì tự rời khỏi danh sách, nên số vi phạm chỉ giảm.

Thay đổi lớn tôi chia thành bước nhỏ đảo ngược được: tách deploy khỏi release bằng [[feature-flag|feature flag]], [[expand-contract|expand-contract]] cho schema và API, [[branch-by-abstraction|branch by abstraction]] trong code, [[strangler-fig|strangler fig]] cho cả hệ thống. Viết lại từ đầu hiếm khi đúng, vì hệ thống cũ vẫn thay đổi trong lúc bản mới đuổi theo.

Bẫy hay gặp: viết fitness function đo thứ dễ đo thay vì thứ quan trọng; ngưỡng không ai dám chặn; và dùng chế độ refreeze để làm build xanh, tức nuốt luôn vi phạm mới.

## Deep

- **Ba ý trong định nghĩa** (*Building Evolutionary Architectures*, Ford, Parsons, Kua 2017; bản 2 năm 2022 thêm Pramod Sadalage):
  - *Từng bước*: thay đổi nhỏ đi qua [[deployment-pipeline|deployment pipeline]] nhiều lần mỗi ngày, cộng với cách triển khai cho phép chạy song song cũ và mới.
  - *Có định hướng*: fitness function cho biết thay đổi có làm mất đặc tính quan trọng không. Không có phần này, "tiến hoá" chỉ là trôi dạt.
  - *Nhiều chiều*: kỹ thuật (ngôn ngữ, framework), dữ liệu (schema), bảo mật, vận hành (khả năng quan sát, chi phí). Kiến trúc dễ đổi code nhưng chung một database với năm hệ thống khác thì vẫn không tiến hoá được.
- **[[fitness-function|Fitness function]]**: tên mượn từ thuật toán di truyền, nơi hàm fitness đo một lời giải gần mục tiêu tới đâu. Các cách phân loại trong sách:
  - Atomic (kiểm một đặc tính trong một bối cảnh, như quy tắc phụ thuộc) và holistic (kiểm nhiều đặc tính cùng lúc, như bật mã hoá rồi xem latency còn trong ngân sách không).
  - Triggered (chạy khi có sự kiện: commit, merge, deploy) và continual (chạy liên tục trên production: SLO, [[chaos-engineering|chaos engineering]]).
  - Static (ngưỡng cố định: p99 ≤ 300 ms) và dynamic (ngưỡng theo bối cảnh: cho phép latency cao hơn khi tải gấp ba).
  - Automated và manual (review pháp lý, pentest định kỳ vẫn là fitness function nếu có tiêu chí rõ).
  - Temporal: nhắc theo thời gian, như "6 tháng sau khi có bản LTS mới thì build đỏ nếu chưa nâng".
- **Ví dụ theo đặc tính**:
  - Module và phụ thuộc: ArchUnit (`layeredArchitecture()`, `slices().matching("com.shop.(*)..").should().beFreeOfCycles()`), Spring Modulith `verify()` (bài Modular monolith), [[jdeps|jdeps]]. So sơ đồ component với code bằng ArchUnit, xem lab ở bài ADR, C4 model & tài liệu kiến trúc: rule cấu hình hẹp sẽ bỏ sót package mới.
  - Tương thích API và event: [[consumer-driven-contract|consumer-driven contract test]], so OpenAPI giữa hai phiên bản để chặn breaking change (bài Thiết kế REST API), kiểm [[schema-registry|schema registry]] ở chế độ tương thích.
  - Hiệu năng: load test có ngưỡng chạy theo lịch hoặc trước release (bài Load & performance testing).
  - Độ sẵn sàng và khả năng phục hồi: SLO và [[burn-rate|burn rate]] trên production (bài Metrics, tracing & SLO), chaos engineering có stop condition (bài Độ tin cậy & SRE).
  - Bảo mật và license: [[software-composition-analysis|software composition analysis]] chặn build khi có CVE từ mức High trở lên chưa có ngoại lệ; chặn AGPL trong service mà người ngoài dùng qua mạng, vì AGPL áp dụng cả khi không phân phối bản build (bài Build hay buy).
  - Dữ liệu: linter cho migration chặn đổi tên hay xoá cột trong cùng release với code dùng nó (expand-contract, bài Migration không downtime).
  - Chi phí: báo chênh lệch chi phí IaC trên pull request (bài Ước tính chi phí & FinOps).
- **Đặt ở đâu trong pipeline**: kiểm vài giây (ArchUnit, quét license) ở bước commit; vài phút (contract test) ở bước merge; hàng giờ (load test, quét image đầy đủ) chạy theo lịch hoặc trước release; còn lại trên production. Fitness function chậm và hay đỏ giả sẽ bị tắt; mỗi cái cần một chủ và một hành động rõ khi đỏ.
- **Ratchet cho hệ thống cũ bằng `FreezingArchRule`** (đã chạy với ArchUnit 1.5.1 trên JDK 27):
  - `FreezingArchRule.freeze(rule)` lưu vi phạm lần chạy đầu vào thư mục `archunit_store` (một file `stored.rules` và một file cho mỗi rule), các lần sau chỉ báo vi phạm mới.
  - Mặc định không được tạo store mới: lần chạy đầu ném `StoreInitializationFailedException: Creating new violation store is disabled`. Bật `freeze.store.default.allowStoreCreation=true` trong `archunit.properties` trên máy dev, chạy một lần, commit thư mục store.
  - Mặc định bỏ qua số dòng: thêm ba dòng phía trên đoạn vi phạm cũ, vi phạm vẫn được coi là đã ghi.
  - Vi phạm đã sửa tự bị xoá khỏi store (`allowStoreUpdate` mặc định `true`). Đưa vi phạm đó trở lại thì build đỏ: đây là ratchet, số vi phạm chỉ đi xuống.
  - Trên CI nên đặt `freeze.store.default.allowStoreUpdate=false`: khi ai đó sửa bớt vi phạm mà không commit store đã thu gọn, build ném `StoreUpdateFailedException`, buộc họ commit store. Nếu không, store trong repo vẫn giữ vi phạm cũ và người sau có thể đưa nó trở lại mà không bị chặn.
  - `freeze.refreeze=true` ghi lại toàn bộ vi phạm hiện tại và báo thành công. Chạy thử: một class mới vi phạm rule vẫn PASSED và bị ghi vào store. Chỉ dùng khi chủ động chấp nhận vi phạm hoặc format vi phạm đổi, không dùng để làm build xanh.
  - Cùng ý tưởng áp được cho chỉ số khác: số cảnh báo tĩnh, số phụ thuộc vòng, kích thước bundle: lưu mức hiện tại, chặn khi tăng, hạ mức khi giảm.
- **Đo đúng thứ cần đo**: [[goodharts-law|Goodhart's law]]: khi một chỉ số thành mục tiêu, nó không còn là chỉ số tốt. Coverage 80% đạt được bằng test không assert gì (bài Refactoring & nợ kỹ thuật có [[mutation-testing|mutation testing]]). Fitness function nên kiểm thẳng đặc tính (module A không gọi module B, p99 dưới ngưỡng), không kiểm đại lượng thay thế.
- **Bước nhỏ đảo ngược được**:
  - Tách deploy khỏi release: code mới lên production nhưng tắt sau [[feature-flag|feature flag]], bật dần theo phần trăm.
  - [[expand-contract|Expand-contract]] (còn gọi parallel change) cho schema, API, event: thêm cái mới bên cạnh cái cũ, chuyển người dùng, rồi mới bỏ cái cũ (bài Migration không downtime).
  - [[branch-by-abstraction|Branch by abstraction]]: đặt interface trước phần cần thay, viết bản mới phía sau, chuyển dần (bài Refactoring & nợ kỹ thuật).
  - [[strangler-fig|Strangler fig]] cho mức hệ thống, cùng [[parallel-run|parallel run]] khi cần so kết quả (bài Migration & hiện đại hoá).
- **Viết lại hay tiến hoá**: bản viết lại thường bị [[second-system-effect|second-system effect]] (Fred Brooks, *The Mythical Man-Month*: hệ thống thứ hai bị nhồi mọi thứ bản đầu đã kiềm chế), phải đuổi theo hệ thống cũ vẫn đang thay đổi, và đánh mất quy tắc nghiệp vụ ngầm. Joel Spolsky dùng Netscape làm ví dụ trong "Things You Should Never Do, Part I" (2000): viết lại trình duyệt mất khoảng ba năm, trong lúc đối thủ chiếm thị trường. Viết lại hợp lý khi phần đó nhỏ, hiểu rõ, có test bao hành vi, hoặc nền tảng thật sự không chạy tiếp được.
- **[[sacrificial-architecture|Sacrificial architecture]]** (Martin Fowler, 2014): chủ động thiết kế một phần để thay khi quy mô đổi hẳn, như hệ thống đầu tiên của một sản phẩm chưa biết có ai dùng. Điểm khác với viết lại vì bế tắc: biết trước nó sẽ bị thay, nên giữ ranh giới module và dữ liệu sạch để thay được từng phần.
- **Coupling quyết định khả năng tiến hoá**:
  - [[architecture-quantum|Architecture quantum]] là đơn vị deploy độc lập có độ gắn kết cao (bài Chọn kiểu kiến trúc). Chung database thì nhiều service vẫn là một quantum.
  - [[connascence|Connascence]] (Meilir Page-Jones): hai phần connascent khi đổi một phần buộc phải đổi phần kia. Dạng tĩnh (cùng tên, cùng kiểu, cùng ý nghĩa của giá trị, cùng thứ tự tham số, cùng thuật toán) dễ phát hiện hơn dạng động (cùng thứ tự thực thi, cùng thời điểm, cùng giá trị, cùng một đối tượng). Quy tắc: connascence càng mạnh thì càng phải ở gần nhau (trong một module); giữa các service chỉ nên là dạng yếu như cùng tên trường trong hợp đồng.
- **Dữ liệu là chiều khó nhất**: tích hợp qua database dùng chung làm schema không đổi được nếu không phối hợp mọi bên. Refactoring database (Ambler và Sadalage) dùng giai đoạn chuyển tiếp có cả cấu trúc cũ và mới, đồng bộ bằng trigger hoặc ghi kép, rồi bỏ cái cũ khi mọi bên đã chuyển.
- **Tiến hoá không có nghĩa là không thiết kế trước**: quyết định một chiều (mô hình dữ liệu cốt lõi, kiểu kiến trúc, vendor lõi) vẫn cần cân nhắc sớm; quyết định hai chiều để tới [[last-responsible-moment|last responsible moment]] (bài Ra quyết định & trade-off). Cặp tốt: ADR nói quy tắc, fitness function giữ quy tắc đó, để ADR không chỉ là tài liệu.
- **Ai giữ fitness function**: platform team cung cấp thư viện rule chung và template pipeline; mỗi team sở hữu rule của module mình và quyết khi nào nới ngưỡng, ghi lý do. Gom kết quả vào một dashboard theo team giúp thấy xu hướng (số vi phạm đóng băng giảm bao nhiêu mỗi quý).
