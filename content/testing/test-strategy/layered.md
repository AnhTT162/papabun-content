## Quick

Chiến lược test là chọn kiểm mỗi rủi ro ở mức nào, sao cho CI **phản hồi nhanh** mà kết quả **đáng tin**. [[test-pyramid|Test pyramid]] khuyên nhiều [[unit-test|unit test]], ít [[integration-test|integration test]], rất ít [[end-to-end-test|end-to-end test]]; [[testing-trophy|testing trophy]] dồn trọng tâm vào integration. Hình dạng là phụ. **Mỗi rủi ro nên được bắt ở mức rẻ nhất bắt được nó, và test kiểm hành vi chứ không kiểm cách cài đặt.**

## Interview

**Ba mức**: unit test kiểm một đơn vị hành vi trong bộ nhớ, chạy mili giây, không I/O. Integration test kiểm code của mình với hạ tầng thật như database, Kafka, HTTP, mất vài giây. End-to-end test kiểm cả hệ thống đã deploy qua UI hoặc API, mất vài phút và có nhiều thành phần có thể hỏng.

**Pyramid** (Mike Cohn, 2009): càng lên cao, test càng chậm, đắt, dễ chập chờn và khó chỉ ra chỗ hỏng, nên càng ít. Google Testing Blog năm 2015 gợi ý tỉ lệ 70/20/10 làm điểm khởi đầu.

**Trophy** (Kent C. Dodds) và [[testing-honeycomb|honeycomb]] (Spotify): service chủ yếu đọc ghi database và gọi service khác thì unit test mock hết mọi thứ kiểm được rất ít. Integration test với database thật cho nhiều tự tin hơn trên mỗi phút chạy. Hai mô hình không mâu thuẫn: nhiều logic tính toán thì nhiều unit test, nhiều code nối hạ tầng thì nhiều integration test.

**Phản mẫu** [[ice-cream-cone|ice cream cone]]: phần lớn là e2e và test tay. Suite chạy hàng giờ, đỏ vì môi trường, và team dần quen bỏ qua màu đỏ.

**Nên test**: logic nghiệp vụ và nhánh biên (tiền, quyền, chuyển trạng thái), câu SQL tự viết, mapping và serialize JSON, cấu hình bảo mật, hợp đồng với service khác. **Không cần test**: getter/setter, code của chính framework, method private gọi trực tiếp (test qua API public), chi tiết cài đặt như "gọi repository đúng một lần" khi kết quả mới là thứ cần kiểm.

**Đo chiến lược bằng**: thời gian CI cho mỗi commit (quy tắc ten-minute build của XP: dưới 10 phút), tỉ lệ [[flaky-test|test chập chờn]], và loại bug lọt ra production. Coverage chỉ là số phụ.

## Deep

- **"Unit" là gì**: trường phái classical (Detroit) coi unit là một hành vi, có thể gồm nhiều class, chỉ thay các phụ thuộc chậm hoặc dùng chung như database, mạng. Trường phái mockist (London) coi unit là một class và mock mọi class nó gọi. Theo cách gọi của Jay Fields mà Martin Fowler dùng lại, đó là [[sociable-test|sociable và solitary]] test. Test solitary dễ vỡ khi refactor dù hành vi không đổi; chi tiết ở bài Mockito & test double.
- **Phân loại theo kích thước của Google**: small (một process, không I/O, không `sleep`), medium (một máy, được dùng `localhost`), large (nhiều máy). Phân theo tài nguyên thì kiểm được, còn "unit hay integration" thì mỗi team hiểu một kiểu. Khi tranh luận, hỏi test chạy bao lâu và phụ thuộc vào gì.
- **Vì sao e2e chập chờn theo cấp số nhân**: một lần chạy qua 10 thành phần, mỗi thành phần ổn định 99,5%, chỉ xanh khoảng 0,995¹⁰ ≈ 95% số lần dù code đúng. Thêm thành phần là thêm lý do đỏ, và lúc đỏ test không nói lỗi nằm ở đâu.
- **E2E nên giữ cho**: vài hành trình sống còn (đăng nhập, đặt hàng, thanh toán), chạy làm [[smoke-test|smoke test]] sau mỗi lần deploy, và chạy định kỳ ở production dưới dạng [[synthetic-monitoring|synthetic monitoring]].
- **Giữa các service**: thay vì dựng cả chục service để chạy e2e, kiểm hợp đồng bằng [[consumer-driven-contract|consumer-driven contract test]] (bài Contract testing) và giả lập service bên kia bằng stub HTTP (bài Test HTTP client với WireMock).
- **Tầng đáy của trophy là phân tích tĩnh**: compiler, kiểm null (NullAway, JSpecify), Error Prone, SpotBugs. Lỗi bắt được ở đây rẻ nhất vì không cần viết test.
- **Không test framework, nhưng test cấu hình của mình trên framework**: `SecurityFilterChain`, `@Transactional` có đi qua proxy không, mapping JPA, tên topic Kafka. Bug thật hay nằm ở đây, và mock không bắt được; đó là việc của integration test (bài Spring Boot Test).
- **Chạy ở đâu**: mỗi commit chạy unit và integration nhanh; trước merge chạy đầy đủ; sau deploy chạy smoke; production có synthetic monitoring. Tách nhóm bằng tag hoặc Surefire/Failsafe (bài JUnit 5 chuyên sâu).
- **Coverage**: cho biết dòng nào chưa từng chạy, không chứng minh test kiểm đúng. Đo chất lượng test bằng [[mutation-testing|mutation testing]] ở bài Thiết kế test tốt.
- **Bug lọt production**: trước khi sửa, viết một [[regression-test|regression test]] tái hiện bug ở mức thấp nhất có thể bắt được nó. Nếu chỉ e2e bắt được thì đó là tín hiệu thiếu một tầng.
- **Test ở production không thay test trước deploy**: [[canary-release|canary]], [[feature-flag|feature flag]] và quan sát metric bù cho những gì không tái hiện được trước deploy (dữ liệu thật, tải thật), không phải lý do để bỏ integration test.
- **Test tay vẫn có chỗ**: thử khám phá (exploratory) cho luồng mới và trải nghiệm người dùng. Lặp lại cùng một kịch bản tay mỗi lần release mới là thứ cần tự động hoá.
