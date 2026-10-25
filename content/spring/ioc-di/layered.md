## Quick

[[ioc|IoC]] nghĩa là object không tự `new` dependency của nó; container tạo và đưa vào. [[dependency-injection|Dependency Injection]] là cách Spring làm IoC: bạn khai báo bean và dependency, container dựng cả đồ thị lúc khởi động. **Dùng [[constructor-injection|constructor injection]]**: dependency là `final`, thiếu là lỗi ngay lúc khởi động, test chỉ cần `new`.

## Interview

**Container làm gì**: lúc khởi động, Spring đọc cấu hình thành [[bean-definition|BeanDefinition]] (class, scope, dependency, lazy hay không), rồi tạo mọi singleton theo thứ tự dependency: muốn tạo `OrderService` thì tạo `OrderRepository` trước. Lỗi cấu hình lộ ra ngay lúc khởi động, không đợi tới request đầu.

**Khai báo bean**:
- `@Component`, `@Service`, `@Repository`, `@Controller` cho class của bạn, được tìm qua [[component-scan|component scan]].
- Method `@Bean` trong class `@Configuration` cho class bạn không sửa được, như client của thư viện.

**Ba kiểu inject**:
- **Constructor**: kiểu nên dùng. Class chỉ có một constructor thì không cần `@Autowired` (từ Spring 4.3). Constructor 8 tham số là tín hiệu class đang làm quá nhiều việc.
- **Setter**: cho dependency không bắt buộc.
- **Field** (`@Autowired` trên field): gọn nhưng không `final` được, dependency bị ẩn, và test không có Spring phải dùng reflection.

**Chọn bean theo kiểu**:
- Không có bean nào khớp: `NoSuchBeanDefinitionException`, trừ khi tham số là `Optional` hoặc `ObjectProvider`.
- Có nhiều bean khớp: `NoUniqueBeanDefinitionException`. Sửa bằng `@Primary` cho bean mặc định, hoặc `@Qualifier` chỉ đích danh.
- Cần tất cả thì inject `List<PaymentGateway>` hoặc `Map<String, PaymentGateway>` (key là tên bean). Đây là cách làm strategy pattern gọn nhất.

**[[circular-dependency|Circular dependency]]**: A cần B và B cần A.
- Qua constructor: không giải được, khởi động lỗi `BeanCurrentlyInCreationException`.
- Từ Boot 2.6, mọi vòng tròn đều bị chặn mặc định, kể cả qua field. Log hiện `UnsatisfiedDependencyException`, và Boot in "The dependencies of some of the beans in the application context form a cycle" kèm sơ đồ vòng.

Cách sửa đúng là tách phần dùng chung ra bean thứ ba, hoặc dùng event. `@Lazy` ở chỗ inject vẫn chạy được (nó inject proxy nên phá vòng lúc tạo), còn bật lại `spring.main.allow-circular-references` thì cũng vậy: cả hai chỉ che vấn đề thiết kế.

## Deep

- **`BeanFactory` và `ApplicationContext`**: `BeanFactory` là container tối thiểu, tạo bean khi được hỏi. `ApplicationContext` tạo sẵn mọi singleton lúc khởi động, tự đăng ký `BeanPostProcessor`, có event, `Environment` và i18n. Ứng dụng thực tế luôn dùng `ApplicationContext`.
- **`@Configuration` và chế độ lite**:
  - Class `@Configuration` được CGLIB tạo lớp con: gọi `dataSource()` từ một method `@Bean` khác vẫn trả đúng singleton trong container.
  - Với `@Configuration(proxyBeanMethods = false)`, hoặc method `@Bean` nằm trong class `@Component`, đó là chế độ lite: mỗi lần gọi method là một object mới, ngoài container.
  - Auto-configuration của Boot dùng `proxyBeanMethods = false` để khởi động nhanh, nên trong đó dependency được truyền qua tham số method.
- **Vòng tròn qua field được giải thế nào (khi được bật)**:
  - Spring có ba tầng cache singleton. Bean A tạo xong object nhưng chưa inject thì để một factory "tham chiếu sớm" vào tầng ba; B cần A thì lấy tham chiếu sớm đó.
  - Nếu A cần proxy, AOP tạo proxy sớm cho tham chiếu này. Nhưng một số proxy như của `@Async` không hỗ trợ tạo sớm, nên khởi động lỗi `Bean with name 'a' has been injected into other beans ... in its raw version`.
- **Tên tham số**: Spring 6.1 bỏ việc đọc tên tham số từ debug info. Muốn fallback theo tên tham số (một `PaymentGateway momo` chọn đúng bean `momo`) thì phải biên dịch với `-parameters`. Parent pom và Gradle plugin của Boot bật sẵn; build không dùng chúng thì có thể gặp `NoUniqueBeanDefinitionException` sau khi nâng cấp. `@PathVariable` và `@RequestParam` không ghi tên cũng hỏng theo.
- **Generic là qualifier**: `Repository<Order>` và `Repository<Customer>` được phân biệt theo tham số kiểu, không cần `@Qualifier`.
- **Thứ tự trong `List`**: theo `@Order` hoặc `Ordered`, không có thì theo thứ tự đăng ký, không nên dựa vào. `@Primary` không ảnh hưởng thứ tự. Spring 6.2 có thêm `@Fallback`: bean chỉ được chọn khi không còn ứng viên nào khác.
- **Trùng tên bean**: hai class `OrderMapper` ở hai package cùng có tên bean mặc định `orderMapper`, nên component scan báo `ConflictingBeanDefinitionException`. Với `@Bean` trùng tên, Boot từ 2.1 tắt việc ghi đè bean definition mặc định và báo `BeanDefinitionOverrideException`, thay vì âm thầm thay bean.
- **Ngoài phạm vi scan**: component scan bắt đầu từ package của class `@SpringBootApplication`. Class nằm ở package anh em (`com.shop.common` khi main ở `com.shop.order`) không được tìm thấy, và Boot báo "Consider defining a bean of type ...".
- **Tự `new` một bean**: `new OrderService(...)` tạo object ngoài container, nên không có proxy: `@Transactional`, `@Async` trên object đó không chạy, và field `@Autowired` là `null`.
- **Lấy bean muộn**: `ObjectProvider<T>` cho phép lấy bean lúc cần (`getIfAvailable`, `stream`), hữu ích khi bean không bắt buộc hoặc scope ngắn hơn (bài Bean lifecycle & scope). `@Lazy` trên tham số inject một proxy, tạo bean thật ở lần gọi đầu.
- **`@Autowired`, `@Inject`, `@Resource`**: `@Inject` (Jakarta) gần như giống `@Autowired` nhưng không có `required = false`. `@Resource` tìm theo **tên** trước rồi mới theo kiểu, nên đổi tên field có thể đổi bean được inject.
- **Đăng ký bằng code**: Spring Framework 7 thêm `BeanRegistrar`, đăng ký bean bằng code Java (vòng lặp, điều kiện) thay vì annotation, và vẫn tương thích AOT.
- **Service locator**: gọi `context.getBean(...)` khắp nơi là quay lại tự đi lấy dependency, mất lợi ích của DI và khó test. Chỉ hợp ở code hạ tầng.
- **DI không cần Spring**: constructor injection là Java thuần. Unit test gọi `new OrderService(fakeRepository)`, không cần context, nên nhanh hơn nhiều so với test khởi động Spring.
