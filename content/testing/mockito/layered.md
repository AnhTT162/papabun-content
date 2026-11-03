## Quick

[[test-double|Test double]] là object đứng thay một phụ thuộc thật trong test: dummy, [[test-stub|stub]] (trả câu trả lời dựng sẵn), [[test-spy|spy]] (ghi lại lời gọi), [[mock-object|mock]] (kiểm lời gọi), [[fake-object|fake]] (cài đặt chạy được nhưng đơn giản, như repository trong bộ nhớ). Mockito tạo stub, mock và spy lúc chạy. **Mock thứ chậm hoặc không kiểm soát được (mạng, email, cổng thanh toán), không mock value object hay logic của chính mình; kiểm kết quả trước, chỉ verify lời gọi khi chính lời gọi là hành vi cần kiểm.**

## Interview

**Năm loại test double** (Gerard Meszaros): dummy chỉ để lấp tham số; stub trả câu trả lời dựng sẵn; spy ghi lại lời gọi để kiểm sau; mock được đặt kỳ vọng về lời gọi; fake là cài đặt thật nhưng đơn giản (`HashMap` thay database). Trong Mockito, `mock()` vừa làm stub (`when(...).thenReturn(...)`) vừa làm mock (`verify`); còn `spy()` bọc một object thật, khác nghĩa "spy" của Meszaros.

**Mockito chạy thế nào**: từ Mockito 5, inline mock maker sửa bytecode của chính class qua Java agent, nên mock được class `final` và method `static` (`mockStatic`). Method chưa stub trả giá trị mặc định: `null`, `0`, collection rỗng, `Optional.empty()`.

**[[strict-stubbing|Strict stubbing]]**: `MockitoExtension` mặc định ở mức `STRICT_STUBS`. Stub không được dùng tới làm test fail (`UnnecessaryStubbingException`); code gọi method đã stub với tham số khác thì fail ngay (`PotentialStubbingProblem`). Mock tạo bằng `Mockito.mock()` ngoài extension không có kiểm tra này, nên test có thể xanh sai lý do.

**Khi nào không nên mock**: value object và class nghiệp vụ đơn giản của mình (dùng bản thật); database (mock repository không chạy câu SQL nào, dùng Testcontainers); HTTP client của bên thứ ba (nguyên tắc "don't mock types you don't own": bọc bằng adapter của mình, test adapter bằng WireMock); thời gian (tiêm `Clock`).

**Bẫy hay gặp**: verify mọi lời gọi (`verifyNoMoreInteractions`) làm test vỡ mỗi lần refactor; `when(spy.method())` gọi method thật ngay lúc stub; mock trả về mock (deep stubs) là dấu hiệu code đi xuyên qua nhiều tầng object.

## Deep

- **Mockito 5** (1/2023): inline mock maker thành mặc định, baseline Java 11, artifact `mockito-inline` không còn cần. Từ JDK 21 (JEP 451), JVM cảnh báo khi agent tự attach lúc chạy. Đo với JDK 27 và Mockito 5.24.0: log in "Mockito is currently self-attaching to enable the inline-mock-maker. This will no longer work in future releases of the JDK" kèm cảnh báo dynamic agent. Sửa bằng cách thêm `-javaagent:<đường dẫn mockito-core.jar>` vào `argLine` của Surefire (lấy đường dẫn bằng goal `dependency:properties`); chạy với agent thì hết cảnh báo.
- **Nới strictness có chủ đích**: `lenient().when(...)` cho đúng một stub, hoặc `@MockitoSettings(strictness = Strictness.LENIENT)` cho cả class. Lỗi `UnnecessaryStubbingException` hay gặp nhất là stub dùng chung đặt trong `@BeforeEach` mà vài test không dùng; tách setup theo test hoặc dùng `lenient()` cho stub đó, đừng hạ strictness cả class.
- **`PotentialStubbingProblem` chỉ bắt lời gọi từ code đang test**: đã thử, cùng stub `find(42L)` nhưng gọi `find(43L)` ngay trong method test thì Mockito báo `UnnecessaryStubbingException`; gọi qua class service thì báo "Strict stubbing argument mismatch".
- **Argument matcher**: một tham số dùng matcher thì mọi tham số phải dùng matcher (`eq(...)` cho giá trị cụ thể), nếu không sẽ có `InvalidUseOfMatchersException`. `any(String.class)` không khớp `null`, còn `any()` thì khớp (đã thử: `verify(s).note(any(String.class))` sau `note(null)` báo `ArgumentsAreDifferent`).
- **[[argument-captor|ArgumentCaptor]] giữ tham chiếu**: object bị sửa sau lời gọi thì captor thấy trạng thái cuối. Đo: gửi list `[a]`, `clear()`, thêm `b`, gửi lại; captor trả `[[b], [b]]`. Code tái dùng buffer cần `doAnswer` để chép dữ liệu ngay lúc gọi.
- **Spy**: `when(spy.send(x))` chạy `send` thật một lần lúc stub (đo: biến đếm số lần gửi tăng lên 1). Dùng `doReturn(...).when(spy).send(x)`. Phải spy một class của mình thường là dấu hiệu class đó làm quá nhiều việc.
- **`mockStatic`**: chỉ có hiệu lực trên thread hiện tại và phải đóng (try-with-resources), nếu không sẽ rò sang test sau. Với thời gian, tiêm `Clock` và dùng `Clock.fixed(...)` thay vì mock `Instant.now()`; chi tiết ở bài Test chập chờn.
- **Fake hay mock**: fake (`InMemoryOrderRepository`) cho test đọc như code thật và ít vỡ khi refactor, nhưng có thể lệch hành vi thật (unique constraint, transaction, phân biệt hoa thường). Chạy chung một bộ [[contract-test|contract test]] cho fake và cho cài đặt thật trên Testcontainers để giữ hai bên khớp nhau.
- **`@InjectMocks` im lặng**: dùng constructor nhiều tham số nhất nếu được (tham số không có mock phù hợp thì truyền `null`); chỉ khi không dùng được constructor mới tiêm qua setter hoặc field. Tiêm hỏng không báo lỗi. Tự tạo `new OrderService(repo, clock)` trong test rõ ràng hơn và bắt được khi constructor đổi.
- **Mock trong Spring**: `@Mock` không dựng Spring context, nên chạy mili giây. `@MockitoBean` (Spring Framework 6.2) thay `@MockBean` (deprecated từ Spring Boot 3.4, gỡ hẳn ở 4.0); mỗi tổ hợp bean bị thay là một cấu hình context mới, làm mất cache context (bài Spring Boot Test).
- **Mockist và classical**: mock mọi class cộng tác cho test cô lập và chỉ ra lỗi chính xác, nhưng gắn test vào cấu trúc bên trong; [[sociable-test|dùng class thật]] và chỉ thay phụ thuộc chậm thì test sống qua refactor. Hai trường phái ở bài Test pyramid & chiến lược test.
- **BDDMockito**: `given(...).willReturn(...)` và `then(mock).should()` chỉ là tên khác cho `when` và `verify`, đọc hợp với test viết theo given/when/then.
