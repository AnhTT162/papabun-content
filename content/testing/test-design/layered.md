## Quick

Test tốt **đỏ khi hành vi sai, xanh khi hành vi đúng dù cài đặt đổi, và đọc được như tài liệu**. Mỗi test kiểm một hành vi theo cấu trúc [[arrange-act-assert|Arrange-Act-Assert]], tên nói điều kiện và kết quả mong đợi, dữ liệu nằm ngay trong test. [[code-coverage|Coverage]] chỉ cho biết dòng nào đã chạy, **không cho biết test có kiểm gì**; [[mutation-testing|mutation testing]] mới đo được điều đó.

## Interview

**Cấu trúc**: Arrange dựng dữ liệu và phụ thuộc, Act gọi đúng một hành vi, Assert kiểm kết quả (Given-When-Then là cùng ý). Một test một hành vi, không nhất thiết một assert: kiểm tổng tiền, trạng thái và event của cùng một lần đặt hàng vẫn là một hành vi.

**Tên test**: nói điều kiện và kết quả, như `vipOrderBelowThreshold_shipsFree`. Đọc danh sách tên test phải thấy được quy tắc nghiệp vụ.

**[[test-smell|Test smell]] hay gặp** (danh mục của Gerard Meszaros và van Deursen): *assertion roulette*, nhiều assert không message nên fail không biết cái nào; *mystery guest*, dữ liệu nằm ở file hay bảng ngoài test; *eager test*, một test kiểm cả chục hành vi; *conditional logic*, `if` và vòng lặp trong test; *fragile test*, vỡ khi refactor vì kiểm chi tiết cài đặt; *sleepy test*, chờ bằng `Thread.sleep`.

**DAMP hơn DRY**: trong test, lặp lại một chút để mỗi test tự đọc hiểu được tốt hơn helper chung che mất dữ liệu quan trọng. Dùng [[test-data-builder|test data builder]] với giá trị mặc định hợp lệ, test chỉ ghi phần khác biệt: `anOrder().withTotal(500_000).build()`.

**Coverage**: line coverage và branch coverage (JaCoCo) chỉ ra vùng chưa có test. 100% không chứng minh gì: test chạy qua dòng code mà assert lỏng vẫn được tính. Google gợi ý 60% là chấp nhận được, 75% là tốt, 90% là mẫu mực, và khuyên không áp con số từ trên xuống.

**Mutation testing**: PIT tự sửa code (đổi `>` thành `>=`, đảo điều kiện, trả 0), chạy lại test; test vẫn xanh thì mutant "sống sót", chỉ ra chỗ test không bảo vệ. Chạy cho phần code quan trọng hoặc code vừa đổi, vì tốn thời gian.

## Deep

- **Đo trên ví dụ thật** (PIT 1.30.1, JaCoCo 0.8.16, JUnit 6.1.3): `fee(total, vip)` có ba test (đơn lớn, đơn nhỏ, khách VIP). JaCoCo: 4/4 dòng, 4/4 nhánh. PIT sinh 4 mutant, giết 3; mutant "changed conditional boundary" ở dòng `orderTotal > FREE_FROM` sống sót, vì không test nào chạm đúng ngưỡng 500.000. Thêm test ở 499.999, 500.000, 500.001 thì lộ bug (`expected: <0> but was: <30000>`), sửa thành `>=` thì PIT giết 4/4.
- **Phân vùng tương đương và giá trị biên**: chia đầu vào thành các vùng cùng hành vi (đơn dưới ngưỡng, từ ngưỡng trở lên, VIP), lấy một giá trị đại diện mỗi vùng và **ngay tại biên cùng hai bên biên**. Bug thật hay nằm ở biên: `>` với `>=`, ngày cuối tháng, số lượng 0, chuỗi rỗng. [[parameterized-test|Parameterized test]] với `@CsvSource` hợp để viết bảng này.
- **Cấu hình PIT với JUnit 5/6**: plugin `org.pitest:pitest-maven` (1.30.1) cần thêm dependency `org.pitest:pitest-junit5-plugin` (1.2.3) trong khối `<plugin>`; thiếu nó, PIT không tìm thấy test Jupiter nào. Chạy bằng `mvn org.pitest:pitest-maven:mutationCoverage`, báo cáo ở `target/pit-reports`.
- **Đọc kết quả PIT**: *killed* (test đỏ, tốt), *survived* (thiếu test hoặc assert lỏng), *no coverage* (không test nào chạy tới), *timed out* (thường là vòng lặp vô hạn, tính là killed). "Test strength" chỉ tính trên mutant có coverage. Nhóm mutator `DEFAULTS` gồm conditionals boundary, negate conditionals, math, increments, invert negatives, void method calls và các mutator đổi giá trị trả về.
- **[[equivalent-mutant|Equivalent mutant]]**: mutant không đổi hành vi quan sát được, như đổi `value >= 0 ? value : -value` thành `value > 0 ? value : -value`: tại 0 cả hai đều trả 0. Không test nào giết được; đừng cố đạt 100% mutation score.
- **Chi phí của mutation testing**: mỗi mutant chạy lại các test phủ dòng đó. PIT chỉ chạy test liên quan, có phân tích tăng dần (`withHistory`) và goal `scmMutationCoverage` chỉ phân tích file đã đổi trong Git. Chạy theo pull request cho module lõi (tính tiền, quyền), không chạy cho cả monolith mỗi commit.
- **Các bộ đếm của JaCoCo**: instruction (bytecode), branch, line, complexity, method, class. Branch coverage chỉ đòi mỗi nhánh của `if` chạy một lần, không đòi mọi tổ hợp điều kiện con. Code sinh tự động (Lombok, record) làm sai lệch con số nếu không loại ra.
- **Coverage của code vừa đổi** (diff coverage) hữu ích hơn tổng coverage: chặn pull request thêm logic không test, mà không ép viết test cho code cũ ít rủi ro. Đặt chỉ tiêu tổng coverage thường sinh test không assert gì (định luật Goodhart).
- **Kiểm qua API public**: muốn test method private là dấu hiệu nó nên là một class riêng có API riêng. Nới `private` thành package-private chỉ để test thì gắn test vào cài đặt.
- **Assert rõ ràng**: AssertJ (`assertThat(order.lines()).extracting(OrderLine::sku).containsExactly(...)`) cho message chỉ đúng phần khác. `assertAll` hoặc `SoftAssertions` báo mọi điểm sai trong một lần chạy. So sánh object bằng `usingRecursiveComparison()` thay vì `equals` khi class không định nghĩa `equals` theo giá trị.
- **Test data builder hay [[object-mother|Object Mother]]**: Object Mother (`TestOrders.shippedVipOrder()`) tiện nhưng sinh hàng chục biến thể và giấu dữ liệu quan trọng; builder để mỗi test nêu đúng trường nó quan tâm. Tránh dùng chung một bộ dữ liệu SQL cho mọi test (mystery guest, test này sửa dữ liệu làm hỏng test khác).
- **Xác định**: không dùng `Random` không seed, `Instant.now()`, múi giờ máy, thứ tự `HashMap`; tiêm `Clock` và seed. Nguyên nhân và cách sửa test chập chờn ở bài Test chập chờn.
- **[[property-based-testing|Property-based testing]]** (jqwik): thay vì vài ví dụ, mô tả tính chất phải đúng với mọi đầu vào (tổng sau giảm giá không âm, `decode(encode(x)) == x`); thư viện sinh hàng trăm đầu vào và thu nhỏ ví dụ hỏng về dạng nhỏ nhất. Hợp với parser, serialize, tính toán.
- **Approval/snapshot test**: lưu output lớn (JSON response, báo cáo) làm "bản chuẩn" và so lần sau. Bắt được thay đổi ngoài ý muốn nhưng dễ bị cập nhật mù; review diff của bản chuẩn như review code. [[characterization-test|Characterization test]] cho code cũ là một dạng của kỹ thuật này.
- **Test code là code**: refactor test cùng lúc với code, xoá test trùng lặp hoặc không còn kiểm gì. Một test không ai hiểu vì sao đỏ thường bị tắt, và test bị tắt còn tệ hơn không có test vì tạo cảm giác an toàn.
