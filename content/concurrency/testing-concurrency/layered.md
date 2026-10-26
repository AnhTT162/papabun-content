## Quick

Lỗi đồng thời phụ thuộc vào cách các thread xen nhau, nên một test xanh chưa chứng minh được code đúng; nó chỉ cho biết lần chạy đó không trúng lịch xấu. **Một [[flaky-test|test flaky]] thường là bug thật, không phải hạ tầng chập chờn. Muốn bắt lỗi thì làm lịch xấu dễ xảy ra (nhiều thread, xuất phát cùng lúc, lặp nhiều), hoặc ép đúng lịch xấu bằng điểm chặn trong code; lỗi về visibility và reordering thì dùng [[jcstress|JCStress]].**

## Interview

Có bốn kiểu test, mỗi kiểu bắt một loại lỗi:

1. **Stress test**: N thread cùng xuất phát nhờ một `CountDownLatch` hay `CyclicBarrier`, mỗi thread lặp nhiều lần, rồi kiểm tra bất biến (tổng, không trùng id, không mất phần tử). Bắt được [[race-condition]] kiểu mất cập nhật, nhưng chỉ theo xác suất.
2. **Test xen kẽ có kiểm soát**: chèn điểm chặn (latch, callback) vào giữa bước "kiểm tra" và bước "làm" để test ép thread B chạy đúng lúc thread A dừng. Lỗi tái hiện 100% số lần, nên dùng làm regression test sau khi sửa.
3. **JCStress**: cho lỗi ở tầng [[jmm|Java Memory Model]] (thiếu `volatile`, công bố không an toàn). Mỗi `@Actor` chạy trên một thread, JCStress chạy hàng triệu lần với nhiều cách xếp lịch và đếm từng kết quả theo `@Outcome` (`ACCEPTABLE`, `FORBIDDEN`, `ACCEPTABLE_INTERESTING`).
4. **Test code bất đồng bộ**: chờ kết quả bằng `future.get(timeout)`, latch, hoặc Awaitility (`await().atMost(5, SECONDS).untilAsserted(...)`), không bằng `Thread.sleep`. Code có thời gian (`timeout`, retry, lịch chạy) thì tiêm `Clock` hoặc dùng virtual time (`StepVerifier.withVirtualTime`) để test chạy trong mili giây.

Bẫy hay gặp:
- Gặp test flaky thì bật retry cho tới khi xanh: bug vẫn ở đó và lên production.
- `Thread.sleep(500)` để "chờ thread kia xong": chậm, và vẫn fail khi CI tải nặng.
- Test chỉ chạy trên laptop 10 core: CI 2 vCPU xếp lịch khác hẳn.
- Assert bên trong thread phụ: `AssertionError` chết cùng thread đó, test vẫn xanh. Gom kết quả bằng `Future` và `get()` ở thread test.

Cách làm đúng: đo tỉ lệ flaky (chạy lặp vài trăm lần), tìm bug trong code chính trước khi nghi test, sửa rồi giữ lại một test xen kẽ có kiểm soát để chống lỗi quay lại.

## Deep

- **Vì sao test trong lab chỉ fail khoảng 3%**: tạo và start một thread tốn hàng chục micro giây, còn 1.000 lần `hits++` xong trong vài micro giây, nên phần lớn lần chạy hai thread không hề chạy chồng nhau. Chạy thử trên JDK 27 lặp 1.000 lần ra 26 đến 35 lần fail; thêm `CountDownLatch` cũng không giúp, vì thread được latch thả ra vẫn mất hàng chục micro giây mới chạy, lâu hơn cả vòng lặp. Tăng lên 100.000 vòng cũng chỉ khoảng 2%: một lý do là JIT được phép giữ `hits` trong thanh ghi suốt vòng lặp rồi mới ghi ra, nên hai thread ít khi đụng nhau, nhưng mỗi lần đụng là mất cả mảng lớn (lần fail mất gần trọn 100.000 lần cộng của một thread, còn chạy với `-Xint` thì gần như lần nào cũng fail). Số vòng to không thay được việc kiểm tra đúng bất biến.
- **Làm lịch xấu dễ xảy ra**: nhiều thread hơn số core; `CyclicBarrier` mỗi vòng để các thread đồng loạt chạm vùng nguy hiểm; chạy với `-XX:ActiveProcessorCount=2` để các pool mặc định có kích thước như CI, và giới hạn CPU thật bằng `docker run --cpus=2` (hoặc `taskset -c 0,1` trên Linux), vì cờ JVM không làm thread bớt chạy song song; chạy cả trên ARM, nơi reordering lộ ra mà x86 che.
- **Điểm chặn trong code chính**: ví dụ một `BiConsumer<Stage, Key>` hay interface `Hooks` chỉ có cài đặt rỗng ở production; test truyền vào cài đặt chặn bằng latch đúng sau bước kiểm tra. Đổi lại code chính có thêm một điểm mở; giữ nó package-private và tài liệu rõ.
- **JCStress cụ thể**: tạo project từ archetype `jcstress-java-test-archetype`, viết class có `@JCStressTest`, `@State`, các method `@Actor` và kết quả trong `II_Result` (hai `int`), rồi khai báo `@Outcome(id = "0, 0", expect = ACCEPTABLE_INTERESTING)`. JCStress tự chọn cách ghép thread, bật tắt JIT, và in bảng số lần mỗi kết quả xuất hiện. Nó chậm (từ vài chục giây mỗi test, cả bộ có thể hàng giờ) nên chạy trong job riêng, không trong unit test thường.
- **Lincheck** (JetBrains, chạy được với Java): kiểm tra một cấu trúc dữ liệu đồng thời có tuyến tính hoá được không (linearizability). Bạn khai báo các thao tác; nó sinh kịch bản song song, so kết quả với một bản tuần tự, và với chế độ model checking thì in ra đúng lịch xen kẽ gây lỗi.
- **Deadlock trong test**: đặt `@Timeout` (JUnit 5) hoặc `assertTimeoutPreemptively` để test treo thì fail thay vì làm treo cả pipeline CI; khi fail, in `ThreadMXBean.findDeadlockedThreads()` hoặc thread dump để có bằng chứng.
- **`@RepeatedTest(500)`** hợp để đo tỉ lệ flaky và chứng minh bản sửa có tác dụng (0/500), không hợp để để lại trong bộ test thường: chậm và vẫn chỉ là xác suất.
- **Nguồn flaky không phải race**: trạng thái `static` dùng chung giữa test (lộ ra khi bật `junit.jupiter.execution.parallel.enabled`), dữ liệu database còn từ test trước, thứ tự duyệt `HashMap`/`Set`, `Instant.now()` và múi giờ, port cố định, chờ bằng `sleep`. Mỗi loại có cách sửa riêng: dọn trạng thái, tiêm `Clock`, port ngẫu nhiên, Awaitility.
- **Retry ở tầng build**: Surefire `rerunFailingTestsCount` hay plugin retry của Gradle che lỗi; nếu buộc phải dùng tạm, đánh dấu test là flaky, ghi ticket và đo tỉ lệ, để nó không bị quên.
- **Kiểm tra cấu hình đồng thời bằng test**: virtual thread mà quên giới hạn, pool quá nhỏ gây deadlock khi task chờ task con. Viết test tích hợp bắn N request đồng thời vào service (cùng Testcontainers) và kiểm tra cả kết quả lẫn số connection tối đa tới database.
- **Giới hạn của test**: test chỉ cho thấy có lỗi, không chứng minh không có lỗi. Với phần lõi đồng thời, review kỹ theo happens-before, dùng lớp có sẵn của `java.util.concurrent` thay vì tự viết, và giữ trạng thái chia sẻ ít nhất có thể.
