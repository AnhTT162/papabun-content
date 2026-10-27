## Quick

Maven và Gradle tải dependency, kéo theo cả [[transitive-dependency|dependency trung gian]], rồi chọn **một** phiên bản cho mỗi thư viện. **Maven chọn bản gần gốc nhất trong cây (cùng độ sâu thì bản khai báo trước), Gradle chọn bản cao nhất**; không cái nào kiểm tra hai bản có tương thích không. Muốn kiểm soát thì khai báo phiên bản ở một chỗ ([[bom|BOM]], `dependencyManagement`, `constraints`) và đọc cây dependency.

## Interview

**Maven lifecycle**: `validate → compile → test → package → verify → install → deploy`. Gọi một phase là chạy mọi phase trước nó; plugin gắn goal vào phase (surefire vào `test`, jar vào `package`). `install` chép artifact vào `~/.m2` của máy, `deploy` đẩy lên repository dùng chung.

**[[dependency-scope|Scope]]**: `compile` (mặc định, có ở mọi classpath), `provided` (biên dịch được nhưng runtime đã có sẵn, như Servlet API trong Tomcat ngoài, Lombok), `runtime` (chỉ lúc chạy, như JDBC driver), `test`, và `import` (chỉ dùng trong `dependencyManagement` để nhập BOM). Gradle tách rõ hơn: `implementation` không lộ dependency sang module dùng mình, `api` (plugin `java-library`) thì lộ, `compileOnly`, `runtimeOnly`, `testImplementation`.

**[[dependency-mediation|Chọn phiên bản]]**: `invoice-lib` cần `money-util:1.0`, `payment-sdk` cần `money-util:2.0`, cả hai cùng độ sâu. Maven lấy bản của dependency khai báo trước, nên đổi thứ tự hai dòng trong `pom.xml` là đổi phiên bản; Gradle lấy 2.0. Code của thư viện cần bản bị loại sẽ ném `NoSuchMethodError` hay `ClassNotFoundException` lúc chạy, không lúc biên dịch.

**BOM** (Bill of Materials) là một pom chỉ chứa danh sách phiên bản đã được kiểm tra chạy cùng nhau, như `spring-boot-dependencies` hay `jackson-bom`. Nhập BOM rồi khai báo dependency không cần version.

**[[semantic-versioning|Semantic versioning]]** `MAJOR.MINOR.PATCH`: tăng MAJOR khi phá tương thích, MINOR khi thêm tính năng tương thích ngược, PATCH khi sửa lỗi. Nó chỉ là lời hứa của tác giả; nhiều thư viện Java phá tương thích ở bản minor.

Bẫy hay gặp: không đọc cây dependency khi nâng cấp, version range (`[1.4,2.0)`) hay [[snapshot-version|SNAPSHOT]] làm build hôm nay khác hôm qua, ghi đè phiên bản mà Spring Boot BOM quản lý rồi quên.

Cách làm đúng: một BOM hoặc version catalog cho cả repo, chạy `mvn dependency:tree -Dverbose` hay `gradle dependencies` khi đổi dependency, bật kiểm tra hội tụ phiên bản trên CI.

## Deep

- **Đã chạy với Maven 3.10.0 và Gradle 9.8.0** (lab): cùng cây dependency, Maven chọn `money-util:1.0` và báo `omitted for conflict with 1.0` trong `dependency:tree -Dverbose`, chạy ra `NoSuchMethodError`; Gradle in `demo:money-util:1.0 -> 2.0` và chạy đúng. Bản cao nhất không phải lúc nào cũng đúng: nếu 2.0 xoá một method mà thư viện kia cần thì Gradle cũng hỏng.
- **Phát hiện sớm**: Maven Enforcer với `dependencyConvergence` (mọi đường phải cùng phiên bản) hoặc `requireUpperBoundDeps` (bản được chọn không thấp hơn bản nào được yêu cầu). Gradle có `failOnVersionConflict()` và `dependencyInsight --dependency money-util` để xem vì sao một phiên bản thắng.
- **`dependencyManagement` không thêm dependency**, chỉ định phiên bản cho nơi nào có dùng; muốn ép bản của dependency trung gian thì khai báo ở đây. Thứ tự import nhiều BOM cũng theo "khai báo trước thắng". Gradle tương đương là `platform(...)` và `constraints { }`; `enforcedPlatform` thì ép kể cả khi có bản cao hơn.
- **Spring Boot parent**: `spring-boot-starter-parent` kế thừa BOM `spring-boot-dependencies` làm parent và cấu hình sẵn plugin, cho phép đổi phiên bản bằng property (`<jackson-bom.version>`). Ghi đè một thư viện lẻ trong bộ (chỉ `jackson-databind` mà không đổi `jackson-core`) là nguồn lỗi kinh điển; đổi cả BOM của bộ đó.
- **`exclusions`** cắt một dependency trung gian khỏi cây, dùng khi nó thừa hoặc bị thay (bỏ `commons-logging` để dùng `jcl-over-slf4j`, bỏ Logback để dùng Log4j2). Cắt nhầm thứ thư viện cần thì lỗi chỉ lộ ra lúc chạy đúng đường code đó.
- **SNAPSHOT và version range**: `1.4-SNAPSHOT` được tải lại theo `updatePolicy` (mặc định mỗi ngày một lần), range được resolve thành bản cao nhất có trong repository lúc build. Cả hai làm cùng một commit cho ra hai artifact khác nhau. Bản release nên cấm chúng: Enforcer `banDynamicVersions` cấm cả range, `LATEST`/`RELEASE` và SNAPSHOT (`requireReleaseDeps` chỉ cấm SNAPSHOT); Gradle có dependency locking (`gradle.lockfile`).
- **[[reproducible-build|Build tái lập]]**: cố định phiên bản mọi plugin (Maven 3 cảnh báo khi plugin thiếu version), dùng Maven Wrapper/Gradle Wrapper để cố định cả công cụ, đặt `project.build.outputTimestamp` để jar không chứa thời điểm build. Hai lần build cùng commit cho cùng checksum thì kiểm chứng được artifact không bị chèn gì.
- **Scope có truyền không**: dependency `compile` của thư viện thành `compile` ở bên dùng, `runtime` thành `runtime`, còn `provided` và `test` không truyền. `<parent>` kế thừa cả cấu hình lẫn `dependencyManagement` nhưng chỉ có một parent; `import` BOM thì nhập được nhiều cái và chỉ lấy `dependencyManagement`.
- **Optional dependency**: `<optional>true</optional>` nghĩa là dependency không truyền sang bên dùng thư viện; thường gặp ở thư viện hỗ trợ nhiều backend. Thiếu nó lúc chạy thì `NoClassDefFoundError` khi chạm tính năng đó.
- **[[fat-jar|Fat jar]]** của Spring Boot giữ các jar nguyên vẹn trong `BOOT-INF/lib`, nên xung đột phiên bản vẫn là xung đột của cây dependency; shading (Maven Shade) mới đổi tên package. Cũng vì vậy hai jar chứa cùng một class (`javax.annotation` ở hai artifact khác tên) không bị Maven phát hiện, vì Maven chỉ so `groupId:artifactId`.
- **Bảo mật chuỗi cung ứng**: quét lỗ hổng dependency (OWASP Dependency-Check, Dependabot, `mvn versions:display-dependency-updates`), xác minh checksum/chữ ký (Gradle `verification-metadata.xml`), và repository proxy nội bộ để build không phụ thuộc Maven Central trực tiếp.
