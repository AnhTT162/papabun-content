## Quick

[[coupling|Coupling]] là mức một module phải biết về chi tiết của module khác; [[cohesion|cohesion]] là mức các phần trong một module cùng phục vụ một mục đích. **Mục tiêu là low coupling, high cohesion**: đổi một yêu cầu thì chỉ đổi một chỗ. [[dry|DRY]], [[kiss|KISS]], [[yagni|YAGNI]], [[law-of-demeter|Law of Demeter]] và [[composition-over-inheritance|composition over inheritance]] đều là cách đạt mục tiêu đó, không phải luật tự thân.

## Interview

**Đo coupling bằng câu hỏi "đổi X thì phải đổi bao nhiêu chỗ khác"**. Coupling có nhiều mức, từ tệ tới chấp nhận được:
- Một class sửa trực tiếp field của class khác, hoặc nhiều module đọc ghi chung một biến static hay một bảng database.
- Truyền cờ điều khiển (`process(order, true)`): bên gọi phải biết logic bên trong.
- Truyền cả object lớn trong khi chỉ cần hai field.
- Chỉ truyền đúng dữ liệu cần qua interface hẹp: mức nên nhắm tới.

**Cohesion**: class `OrderPricing` chỉ tính giá là cohesion cao. Class `CommonUtils` chứa format ngày, gửi mail và tính thuế là cohesion thấp: mỗi thay đổi chạm vào một class mà ai cũng import.

**Composition over inheritance**: kế thừa buộc lớp con phụ thuộc vào **chi tiết cài đặt** của lớp cha, không chỉ hợp đồng của nó ([[fragile-base-class|fragile base class]]). Dùng kế thừa khi quan hệ "là một" thật và lớp cha được thiết kế để kế thừa; còn lại thì giữ object kia làm field và gọi nó.

**DRY là về tri thức, không phải về code giống nhau**. Hai đoạn validate trông giống hệt nhau nhưng thay đổi vì hai lý do khác nhau (quy định của kế toán và của kho) thì không nên gộp: gộp tạo ra coupling giữa hai nhóm yêu cầu. Quy tắc thực tế: đợi tới lần lặp thứ ba và chắc chúng đổi cùng nhau rồi mới tách.

**KISS**: đơn giản là ít thành phần, ít trạng thái và ít đường đi cần nghĩ tới, không phải ít dòng code hay "dễ viết". **YAGNI**: không thêm interface, cấu hình hay tầng trừu tượng cho nhu cầu "có thể sẽ có". Thêm khi nhu cầu xuất hiện thường rẻ hơn mang theo nó từ bây giờ.

**Law of Demeter**: một method chỉ gọi method của chính nó, tham số, field và object nó tạo ra. `order.getCustomer().getAddress().getCity()` khiến bên gọi phụ thuộc vào cấu trúc của ba class. Sửa bằng cách hỏi thẳng thứ mình cần (`order.shippingCity()`), hoặc chuyển hành vi về nơi có dữ liệu.

## Deep

- **Fragile base class trong JDK**: `HashSet` kế thừa `addAll` từ `AbstractCollection`, và `addAll` gọi `add` cho từng phần tử. Lớp con đếm ở cả `add` và `addAll` sẽ đếm hai lần. Lớp con của `ArrayList` thì ngược lại: `ArrayList.addAll` chép mảng trực tiếp, không gọi `add`. Cùng một ý định, kết quả phụ thuộc vào chi tiết lớp cha có thể đổi giữa các phiên bản JDK.
- **Đóng kế thừa có chủ đích**: class không thiết kế để kế thừa thì khai báo `final`. Java 17 có `sealed` để chỉ định đúng những lớp con được phép, hợp với mô hình domain có số biến thể cố định. Kế thừa từ class của thư viện (`HashMap`, `ArrayList`, entity của framework) là nguồn bug hay gặp khi nâng cấp phiên bản.
- **Composition vẫn có giá**: lớp bọc phải tự chuyển tiếp từng method sang object bên trong. Interface lớn thì nhiều code chuyển tiếp; Java không có delegation tự động như Kotlin `by`. Object bên trong đăng ký callback bằng `this` thì callback đi thẳng vào nó, bỏ qua lớp bọc; và `equals` giữa lớp bọc với object bên trong không còn đối xứng.
- **Đo coupling trên package** (theo Robert C. Martin): [[afferent-coupling|afferent coupling]] (Ca) là số class bên ngoài phụ thuộc vào class trong package này, efferent coupling (Ce) là số class bên ngoài mà package này phụ thuộc; nhiều công cụ đếm theo package thay vì class. Instability `I = Ce / (Ca + Ce)`. Package nhiều nơi dùng (I gần 0) nên ổn định và trừu tượng. `jdeps` của JDK in đồ thị phụ thuộc; [[archunit|ArchUnit]] viết được test chặn phụ thuộc sai chiều.
- **Coupling ẩn**: hai service cùng đọc ghi một bảng, cùng parse một chuỗi định dạng tự chế, cùng giả định thứ tự gọi (phải gọi `init()` trước `process()`, cũng hay được gọi là temporal coupling). Không có dòng `import` nào lộ ra nhưng đổi một bên là hỏng bên kia. Phụ thuộc tĩnh vào `LocalDateTime.now()` hay `UUID.randomUUID()` cũng là coupling vào thời gian thật: inject `Clock` để test được.
- **Coupling trong hệ phân tán**: service A gọi đồng bộ service B nghĩa là B chết thì A chết theo: hai bên phải cùng sống một lúc, nghĩa thứ hai của [[temporal-coupling|temporal coupling]]. Chia sẻ DTO dạng thư viện chung giữa các service khiến mọi service phải deploy cùng nhau. Xem các bài track Distributed Systems.
- **DRY sai chỗ nguy hiểm hơn lặp code**: một abstraction phục vụ hai nhu cầu dần mọc thêm tham số `boolean`, rồi `if (type == ...)` bên trong. Lúc đó nên inline lại về hai bản rồi tách theo đúng ranh giới thay đổi.
- **Demeter không áp dụng máy móc**: API dạng chuỗi (fluent API, `builder.name(..).age(..)`), Stream (`list.stream().filter(..).map(..)`) hay đọc DTO lồng nhau để render JSON không vi phạm, vì không có hành vi bị phụ thuộc. Nguyên tắc nhắm tới việc **ra quyết định** dựa trên cấu trúc bên trong của object khác.
- **Interface cho mọi class là over-engineering**: `OrderService` + `OrderServiceImpl` duy nhất thêm một file mà không giảm coupling. Spring tạo proxy [[cglib|CGLIB]] được cho class (bài Spring AOP & proxy), mock framework mock được class. Thêm interface khi có hai cài đặt thật, hoặc khi cần đảo chiều phụ thuộc giữa hai module (bài SOLID).
- **Common closure** (đóng gói theo thay đổi): thứ đổi cùng nhau thì đặt cùng nhau. Tổ chức package theo tính năng (`order/`, `payment/`) thường cho cohesion cao hơn theo tầng (`controller/`, `service/`), xem bài Kiến trúc phân lớp.
