## Quick

DDD chiến thuật là bộ khối xây dựng mô hình bên trong một [[bounded-context|bounded context]]: [[ddd-entity|entity]] (có danh tính), [[value-object|value object]] (bất biến, so sánh bằng giá trị), [[aggregate-root|aggregate]] (cụm object giữ một nhóm [[invariant|bất biến]] và thay đổi trong một transaction), [[domain-event|domain event]] và repository cho mỗi aggregate. **Quy tắc quan trọng nhất: aggregate nhỏ, tham chiếu aggregate khác bằng id, một transaction chỉ sửa một aggregate.**

## Interview

**Entity và value object**: `Order` có danh tính (`OrderId`), trạng thái đổi theo thời gian, hai đơn cùng nội dung vẫn là hai đơn. `Money`, `Address`, `DateRange` không có danh tính: bất biến, bằng nhau khi giá trị bằng nhau, tự kiểm tra hợp lệ trong constructor. Trong Java hiện đại, value object thường là `record` có compact constructor.

**Aggregate**: ranh giới nhất quán. `Order` (root) chứa các `OrderLine`; bất biến "tổng tiền không vượt hạn mức, tối đa 50 dòng, đơn đã giao thì không sửa" do root giữ. Bên ngoài chỉ gọi method của root (`order.addLine(...)`), không sửa `OrderLine` trực tiếp, và không có setter.

**Bốn quy tắc thiết kế aggregate**:
- Chỉ đưa vào aggregate những thứ phải nhất quán **ngay lập tức** với nhau.
- Giữ aggregate nhỏ: aggregate lớn bị tranh chấp khoá và phải tải nhiều dữ liệu.
- Tham chiếu aggregate khác bằng id (`CustomerId customerId`), không bằng object.
- Ngoài ranh giới thì dùng [[eventual-consistency|eventual consistency]]: phát domain event, bên kia xử lý trong transaction riêng.

**Domain event**: điều đã xảy ra mà nghiệp vụ quan tâm (`OrderPlaced`, `PaymentFailed`), đặt tên ở thì quá khứ, mang id và dữ liệu cần thiết. Đây là cách phối hợp nhiều aggregate thay vì sửa cùng lúc.

**Domain service và application service**: domain service chứa quy tắc nghiệp vụ không thuộc riêng aggregate nào (tính phí vận chuyển từ nhiều nguồn). Application service điều phối use case: tải aggregate, gọi method, lưu, mở transaction; nó không chứa quy tắc.

**Bẫy hay gặp**: aggregate khổng lồ `Customer` chứa mọi đơn hàng; entity đầy setter ([[anemic-domain-model|domain anemic]]); một transaction sửa cả `Order` lẫn `Inventory` để "cho chắc".

## Deep

- **Map aggregate bằng JPA**: con của root dùng `@OneToMany(mappedBy = ..., cascade = ALL, orphanRemoval = true)` để vòng đời gắn với root; repository chỉ có cho root. Value object là `@Embeddable`; Hibernate 6.2+ (Spring Boot 3.1 trở đi) hỗ trợ `record` làm embeddable; Boot 3.0 đi với Hibernate 6.1 thì chưa. Quan hệ tới aggregate khác lưu bằng cột id, không dùng `@ManyToOne` (tránh vô tình tải và sửa aggregate khác).
- **[[optimistic-locking|Optimistic locking]] trên root**: `@Version` trên root chỉ bảo vệ cả aggregate khi version của root thật sự tăng. Với cách map khuyên ở trên (`@OneToMany(mappedBy = ...)`), thêm, xoá hay sửa `OrderLine` **không** làm tăng version của root, nên hai request song song có thể cùng phá bất biến "tối đa 50 dòng" mà không có `OptimisticLockException`. Cách sửa: tải root với `LockModeType.OPTIMISTIC_FORCE_INCREMENT`, hoặc đổi một trường của root trong mọi method thay đổi (ví dụ `updatedAt`); `@OptimisticLock(excluded = false)` trên collection chỉ có tác dụng khi thêm hoặc xoá phần tử. Collection một chiều (join column hay join table) thì mặc định có tăng version.
- **`equals` của entity**: so theo id, nhưng id do database sinh thì là `null` trước khi lưu, nên entity mới bỏ vào `HashSet` rồi lưu sẽ đổi `hashCode`. Gán id phía ứng dụng (UUID, hoặc id lấy từ sequence trước khi tạo) trong constructor tránh được vấn đề này. Đổi lại, Spring Data coi entity có id là không mới, nên `save` gọi `merge` (thừa một câu SELECT trước INSERT); thêm `@Version` hoặc implement `Persistable` để `save` gọi `persist`.
- **Value object và `BigDecimal`**: `record Money(BigDecimal amount, Currency currency)` dùng `BigDecimal.equals`, vốn so cả scale: `10.0` khác `10`. Chuẩn hoá scale trong compact constructor theo tiền tệ: `amount.setScale(currency.getDefaultFractionDigits(), RoundingMode.UNNECESSARY)` (VND có 0 chữ số thập phân, USD có 2). `UNNECESSARY` ném `ArithmeticException` khi dữ liệu thừa chữ số thay vì âm thầm làm tròn; làm tròn là quy tắc nghiệp vụ, đặt ở nơi tính toán và do nghiệp vụ quyết định.
- **Phát domain event với Spring Data**: kế thừa `AbstractAggregateRoot` và gọi `registerEvent(...)` trong method của entity. Event chỉ được phát khi gọi `save`, `saveAll`, `delete`, `deleteAll`, `deleteInBatch`, `deleteAllInBatch` của repository, rồi danh sách được xoá (`@AfterDomainEventPublication`). Không phát khi chỉ dựa vào [[dirty-checking|dirty checking]], và **không phát với `deleteById`**, vì repository có thể xoá bằng query mà không có object aggregate. Listener nên là `@TransactionalEventListener` (`AFTER_COMMIT`); nhưng process chết ngay sau commit là event mất, nên event không được phép mất hoặc phải ra ngoài process thì đi qua [[outbox]].
- **Đọc không cần đi qua aggregate**: màn hình danh sách đơn hay báo cáo không cần dựng aggregate đầy đủ. Query thẳng ra DTO projection, hoặc một read model riêng (tách mô hình đọc khỏi mô hình ghi). Repository của aggregate trả aggregate; query cho màn hình trả DTO. Aggregate dành cho việc **thay đổi** có bất biến.
- **Kích thước aggregate theo số liệu**: một `Product` chứa toàn bộ `Review` (hàng chục nghìn) thì mỗi lần thêm review phải tải tất cả và mọi người viết review tranh khoá trên cùng root. Review nên là aggregate riêng tham chiếu `productId`; nếu cần "điểm trung bình" thì cập nhật bằng event.
- **Factory và tạo hợp lệ**: aggregate phức tạp được tạo qua static factory (`Order.place(customerId, lines, policy)`) kiểm tra mọi bất biến, để không bao giờ tồn tại object ở trạng thái sai. Constructor không tham số cho JPA để `protected`.
- **Khi nào không cần**: CRUD đơn giản không có bất biến đáng kể thì entity JPA thường cùng service là đủ. DDD chiến thuật đáng công ở core domain có quy tắc phức tạp.
