## Quick

[[jpa|JPA]] là chuẩn ánh xạ object sang bảng; Hibernate là bản cài đặt phổ biến nhất. Mỗi entity có [[entity-state|trạng thái]]: **transient** (mới `new`), **managed** (nằm trong [[persistence-context|persistence context]]), **detached** (context đã đóng), **removed**. **Chỉ entity managed được theo dõi**: sửa field là đủ, Hibernate tự sinh `UPDATE` lúc flush; sửa entity detached thì không có gì xảy ra.

## Interview

**Persistence context** là bộ nhớ của một `EntityManager`, trong Spring thường sống bằng một transaction:
- Mỗi id chỉ có một object: `find(Order.class, 42)` hai lần trả cùng một instance và chỉ chạy một query.
- Hibernate giữ bản chụp lúc tải. Lúc flush (trước commit, trước query có thể bị ảnh hưởng), nó so từng entity với bản chụp và sinh `UPDATE` cho chỗ khác. Đó là [[dirty-checking|dirty checking]].

**Các thao tác**:
- `persist()`: transient thành managed, `INSERT` lúc flush.
- `merge(detached)`: tải bản managed rồi chép state từ object truyền vào; trả về **bản managed khác**, object cũ vẫn detached.
- `remove()`: thành removed, `DELETE` lúc flush.
- `save()` của Spring Data gọi `persist` nếu entity mới, ngược lại gọi `merge`.

**Quan hệ**:
- Hai chiều thì chỉ **[[owning-side|owning side]]** (bên giữ khoá ngoại, thường là `@ManyToOne`) quyết định cột FK; bên `mappedBy` bị bỏ qua khi ghi. Viết method `addItem()` cập nhật cả hai phía.
- `cascade = PERSIST/MERGE/REMOVE` lan thao tác sang entity con. `orphanRemoval = true` xoá con bị gỡ khỏi collection.
- Mặc định `@ManyToOne` và `@OneToOne` là EAGER, collection là LAZY. Nên đặt mọi thứ LAZY và tải có chủ đích (bài N+1 Query).

**Entity hay DTO**: entity để ghi và chạy nghiệp vụ trong transaction; màn hình đọc nên dùng DTO hoặc projection. Trả entity ra API thì lộ cấu trúc, kích hoạt lazy loading ngoài transaction (`LazyInitializationException`) và lặp vô hạn ở quan hệ hai chiều.

**Bẫy hay gặp**: sửa entity managed trong method `@Transactional` mà không gọi `save()` vẫn được lưu. Đây là tính năng, nhưng cũng là nguồn của `UPDATE` ngoài ý muốn: code chỉ định "tính thử" trên entity cũng bị ghi xuống database.

## Deep

- **Sinh id**:
  - `GenerationType.IDENTITY` (auto increment) buộc Hibernate `INSERT` ngay khi `persist` để lấy id, nên tắt JDBC batch insert.
  - `SEQUENCE` với `allocationSize = 50` (mặc định của JPA) lấy 50 id mỗi lần gọi sequence và batch được. Sequence trong database phải có `INCREMENT BY` khớp `allocationSize`. Từ Hibernate 5.4, mặc định Hibernate đọc metadata của sequence lúc khởi động và báo lỗi nếu hai số khác nhau. Nếu chiến lược bị đổi sang `NONE` hay `LOG`, hoặc không đọc được metadata, optimizer hiểu sai giá trị và hai node có thể cấp trùng id.
  - UUID sinh ở ứng dụng nên dùng [[uuid-v7|UUID v7]] để không làm vỡ index.
- **`save()` thừa một `SELECT`**: entity có id gán sẵn (UUID tự sinh trong constructor) bị Spring Data coi là "không mới", nên `save` gọi `merge`, và `merge` chạy `SELECT` trước. Sửa bằng `@Version Long` (kiểu wrapper: `null` nghĩa là mới; kiểu `long` nguyên thuỷ thì Spring Data quay lại xét id) hoặc implement `Persistable.isNew()`.
- **Hibernate 6.6+ (Boot 3.4+)**: entity có `@GeneratedValue` mà code tự gán id, và không có dòng nào khớp, thì `save()` đi đường `merge` và ném `ObjectOptimisticLockingFailureException` thay vì insert như trước. Hay gặp sau khi nâng cấp ở code import dữ liệu.
- **Thứ tự SQL khi flush**: Hibernate không chạy theo thứ tự bạn gọi mà theo nhóm: orphan removal, insert, update, thao tác trên collection, cuối cùng là delete. Vì vậy `remove(a)` rồi `persist(b)` cùng unique key sinh `INSERT` trước `DELETE` và vi phạm ràng buộc unique; cần `flush()` giữa hai bước.
- **Query tự flush**: với flush mode `AUTO`, trước khi chạy JPQL đụng tới bảng có thay đổi chưa flush, Hibernate flush trước để query thấy dữ liệu mới. Native SQL thì Hibernate không biết đụng bảng nào nên flush toàn bộ context (Hibernate 6+, cả qua `Session`), trừ khi khai báo query space bằng `addSynchronizedEntityClass`. Đây là lý do một `SELECT` đơn giản lại sinh ra `UPDATE` trong log.
- **`getReference()`** (`getReferenceById` trong Spring Data) trả proxy chưa tải, hợp để gán khoá ngoại (`item.setOrder(orders.getReferenceById(id))`) mà không `SELECT`. Đọc field của proxy ngoài transaction thì lỗi `LazyInitializationException`. Id không tồn tại thì vẫn nhận được proxy; lỗi chỉ lộ ra sau, là vi phạm khoá ngoại lúc flush hoặc `EntityNotFoundException` khi chạm vào proxy.
- **Cascade REMOVE trên `@ManyToMany`** gần như luôn sai: xoá một bài viết sẽ xoá luôn tag dùng chung. Với `@ManyToMany`, dùng `Set` thay vì `List` để tránh Hibernate xoá rồi chèn lại toàn bộ bảng nối khi sửa một phần tử.
- **`equals`/`hashCode` của entity**: không dùng id tự sinh ngây thơ, vì id thay đổi sau `persist` làm entity "biến mất" khỏi `HashSet` (bài Spring Data JPA & Hibernate chuyên sâu).
- **Cache cấp 1 không thay database**: persistence context chỉ sống một transaction và chỉ trả object theo id. Query JPQL vẫn chạy SQL, rồi trả lại object đã có trong context nếu trùng id, nên dữ liệu vừa bị transaction khác sửa có thể không hiện ra.
- **Phiên bản**: Boot 2 dùng Hibernate 5 với `javax.persistence`; Boot 3 dùng Hibernate 6 với `jakarta.persistence` (đổi cách sinh SQL, bỏ `@Type` kiểu cũ, ánh xạ kiểu thời gian khác; `GenerationType.AUTO` chuyển từ một `hibernate_sequence` chung sang sequence `<entity>_seq` riêng với bước 50, nên schema cũ bước 1 sẽ lỗi lúc khởi động); Boot 4 dùng Hibernate 7 và JPA 3.2. Nâng major Hibernate cần chạy lại test với log SQL bật.
