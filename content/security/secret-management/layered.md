## Quick

[[secret|Secret]] là thứ cầm được thì vào được hệ thống: mật khẩu database, API key, khoá ký token, private key TLS. Quy tắc: **không nằm trong code, git, image hay log; lấy lúc chạy từ một kho có phân quyền và ghi log truy cập; xoay được mà không sập**. Tốt nhất là **không cần secret**: [[workload-identity|danh tính của workload]] đổi lấy credential ngắn hạn.

## Interview

**Thứ tự ưu tiên**: không có secret (IAM role cho pod, đăng nhập database bằng token IAM) hơn [[dynamic-secret|dynamic secret]] (Vault cấp user database riêng cho từng instance, hết hạn sau vài giờ) hơn secret tĩnh được [[secret-rotation|xoay vòng]] tự động hơn secret tĩnh không ai đụng tới.

**Kho**: [[secrets-manager|AWS Secrets Manager]], [[vault|HashiCorp Vault]], GCP Secret Manager, Azure Key Vault. Kho cho [[least-privilege|phân quyền tối thiểu]] theo từng secret, ghi log mỗi lần đọc, giữ phiên bản và hỗ trợ xoay. Khác với [[kms|KMS]]: KMS giữ khoá và không trả khoá ra, chỉ mã hoá hộ; secret manager trả giá trị về cho ứng dụng dùng.

**Lấy secret cũng cần danh tính**: đó là bài toán [[secret-zero|secret zero]]. Giải bằng danh tính nền tảng cấp sẵn: IAM role của pod, service account token của Kubernetes khi đăng nhập Vault.

**Bẫy hay gặp**:
- [[kubernetes-secret|Kubernetes Secret]] chỉ là Base64, ai có quyền đọc Secret hoặc tạo pod trong namespace đều đọc được.
- Biến môi trường chỉ đọc lúc khởi động và lọt vào crash report, tiến trình con.
- `toString` của object cấu hình in mật khẩu ra log.
- Xoay mật khẩu database trong khi ứng dụng vẫn giữ mật khẩu cũ: connection cũ còn chạy, tới lúc pool mở connection mới thì sập.

**Secret lọt vào git**: coi như đã lộ. Xoay ngay trước, xem log xem đã bị dùng chưa, rồi mới dọn lịch sử. `git rm` không xoá được gì vì commit cũ vẫn còn. Phòng bằng [[secret-scanning|secret scanning]] ở server (GitHub push protection) và trong CI, không chỉ dựa vào hook ở máy dev.

## Deep

- **Đã chạy: xoay mật khẩu khi pool vẫn giữ mật khẩu cũ** (PostgreSQL 17.6, HikariCP 7.1.0, pgjdbc 42.7.7, scratchpad `code/RotateLab.java`):
  - `ALTER ROLE orders_app PASSWORD 'pw-v2'` không cắt connection đang mở: pool 4 connection chạy bình thường thêm 20 giây.
  - Tới `maxLifetime` (lab 30 giây, mặc định 30 phút) Hikari đóng connection cũ, mở connection mới bằng mật khẩu cũ: `FATAL: password authentication failed for user "orders_app"`. Request nhận `Connection is not available, request timed out after 3012ms (total=0, active=0, idle=0, waiting=0)`, lỗi xác thực chỉ có ở `cause`; log của Hikari ở mức `DEBUG` mới in lý do.
  - Lỗi tới muộn và tăng dần theo tốc độ connection hết hạn, nên dễ bị đổ cho sự cố khác. Với `maxLifetime` 30 phút, sự cố lộ hết sau khoảng 30 phút kể từ lúc xoay.
  - Gọi `ds.getHikariConfigMXBean().setPassword("pw-v2")` ngay sau khi xoay thì connection mới dùng mật khẩu mới, không lỗi (`setCredentials` đổi cả user lẫn mật khẩu một lần). HikariCP 7 còn có `setCredentialsProvider`: Hikari hỏi provider mỗi lần mở connection mới, nên provider đọc secret từ kho (có cache) là đủ. Spring Boot 3.5 đi kèm HikariCP 6, kiểm API có trong bản bạn dùng.
- **Chiến lược xoay mật khẩu database** (AWS Secrets Manager dùng Lambda xoay, bốn bước `createSecret`, `setSecret`, `testSecret`, `finishSecret`, nhãn `AWSPENDING`/`AWSCURRENT`/`AWSPREVIOUS`):
  - Single user: đổi mật khẩu của chính user ứng dụng. Có khoảng ngắn giữa `setSecret` và `finishSecret` mà database đã đổi còn secret vẫn trả bản cũ, và ứng dụng giữ bản cũ trong bộ nhớ sẽ lỗi khi mở connection mới.
  - Alternating users: hai user `app` và `app_clone`, mỗi lần xoay đổi mật khẩu của user đang không dùng rồi chuyển `AWSCURRENT` sang nó. Credential cũ còn đúng tới lần xoay sau, nên ứng dụng cache vài giờ vẫn chạy. Cần một user admin để Lambda đổi mật khẩu.
  - Ứng dụng phải lấy lại secret khi xác thực lỗi: AWS có driver JDBC bọc (`aws-secretsmanager-jdbc`, plugin Secrets Manager của AWS Advanced JDBC Wrapper) tự đọc lại secret và thử lại. Thư viện cache của Secrets Manager cho Java mặc định giữ giá trị 1 giờ.
  - RDS hỗ trợ đăng nhập bằng token IAM sống 15 phút, không còn mật khẩu để xoay; đổi lại giới hạn số connection mới mỗi giây và phải dùng TLS.
- **Kubernetes Secret**:
  - `data.password: UHIwZC1TM2NyZXQtMjAyNg==` chỉ là Base64 của `Pr0d-S3cret-2026`. Mặc định lưu rõ trong etcd; cần bật encryption at rest (`EncryptionConfiguration` với KMS provider). EKS mã hoá envelope mọi dữ liệu API bằng KMS từ phiên bản 1.28.
  - Quyền `get`/`list` trên `secrets` của một namespace là đọc được mọi secret trong đó. Ai tạo được pod trong namespace cũng mount được mọi secret của namespace, kể cả không có quyền đọc Secret. Tách namespace theo ranh giới tin cậy.
  - Mount thành file thì kubelet cập nhật file khi Secret đổi (trễ tới khoảng một phút); mount bằng `subPath` thì không bao giờ cập nhật; biến môi trường thì chỉ đổi khi pod khởi động lại. Spring Boot đọc thư mục file bằng `spring.config.import=configtree:/etc/secrets/` (bài Auto-configuration & cấu hình), nhưng giá trị đã bind vào `DataSource` không tự đổi theo.
  - Đồng bộ từ kho ngoài: [[external-secrets-operator|External Secrets Operator]] chép secret vào Kubernetes Secret theo `refreshInterval` (thường 1 giờ, tức pod mới khởi động có thể vẫn nhận bản cũ tới một giờ); Secrets Store CSI Driver mount thẳng từ kho vào pod. Muốn pod tự khởi động lại khi Secret đổi cần thêm công cụ như Reloader.
  - Giữ secret trong git dạng mã hoá cho GitOps: [[sealed-secrets|Sealed Secrets]] (mã hoá bằng khoá của controller trong cluster) hoặc SOPS (mã hoá từng giá trị bằng KMS hoặc age). Mất khoá controller là mất mọi secret đã seal; sao lưu nó.
- **Vault**:
  - Dữ liệu mã hoá bằng khoá nằm trong bộ nhớ; khởi động lên ở trạng thái sealed. Unseal mặc định bằng Shamir 5 phần, cần 3 (`-key-shares=5 -key-threshold=3`); production thường dùng auto-unseal bằng KMS hoặc HSM.
  - Auth method: Kubernetes (pod gửi service account token, Vault hỏi API server), AWS IAM, AppRole cho máy ngoài cloud. Policy theo đường dẫn, ví dụ chỉ `read` trên `secret/data/orders/*`.
  - Database secrets engine: mỗi lần đọc tạo user mới với lease (`default_ttl`, `max_ttl`). Ứng dụng gia hạn lease; tới `max_ttl` thì phải lấy credential mới và đổi cho pool, Spring Cloud Vault không tự đổi credential của `DataSource` đang chạy. Database phải chịu được số user tạo và xoá liên tục.
  - Transit engine mã hoá hộ, khoá không rời Vault, giống KMS. PKI engine cấp chứng chỉ ngắn hạn cho mTLS.
  - Audit device: khi không ghi được vào audit device nào, Vault từ chối request. Đĩa log đầy là Vault dừng phục vụ.
  - Từ 8/2023 Vault đổi sang license BSL (trước đó MPL 2.0); bản fork OpenBao thuộc Linux Foundation giữ license mở (bài Build hay buy & chọn vendor).
- **Secret lọt ở đâu ngoài git**:
  - Image: `ENV`, `ARG` hay file `COPY` vào layer đều đọc được bằng `docker history` hoặc giải nén layer, xoá ở layer sau vẫn còn ở layer trước. Dùng `RUN --mount=type=secret` của BuildKit.
  - Log CI: masking chỉ che đúng chuỗi đã khai; in dạng Base64 hay từng ký tự là lọt.
  - Biến môi trường: tiến trình con kế thừa (`ProcessBuilder` mặc định chép môi trường), `docker inspect` và `/proc/<pid>/environ` đọc được với cùng user, công cụ báo lỗi hay gửi kèm môi trường.
  - Log ứng dụng: record cấu hình có trường mật khẩu, `toString` tự sinh in hết (đã chạy: `DbProps[url=..., username=orders_app, password=Pr0d-S3cret-2026]`); Lombok `@Data` cũng vậy. Ghi đè `toString` hoặc dùng kiểu bọc che giá trị.
  - [[heap-dump|Heap dump]] và `/actuator/heapdump` chứa mọi secret trong bộ nhớ dạng rõ (bài OWASP Top 10 với Java/Spring); file dump phải được bảo vệ như secret. `char[]` thay `String` cho mật khẩu ít tác dụng vì JDBC, Spring và HTTP client đều giữ `String`.
  - Terraform state lưu rõ giá trị của resource có secret; state phải nằm trong backend mã hoá có phân quyền, không commit.
- **Secret lọt vào git, các bước**:
  - Đã chạy: commit file có mật khẩu rồi `git rm` và commit tiếp, `git log -S 'Pr0d-S3cret'` vẫn ra cả hai commit và `git show HEAD~1:application-prod.properties` in nguyên mật khẩu.
  - Xoay hoặc thu hồi trước tiên. Repo public bị bot quét trong vài phút; AWS tự gắn policy cách ly cho access key bị phát hiện trên GitHub công khai nhưng đó là lưới an toàn, không phải xử lý.
  - Xem log truy cập của credential đó (CloudTrail, log database) từ lúc commit.
  - Dọn lịch sử bằng `git filter-repo` hoặc BFG rồi force push là để giảm lộ thêm, không phải để "chưa từng lộ": clone, fork, cache CI, pull request cũ vẫn còn bản cũ.
  - Phát hiện: gitleaks, TruffleHog (kiểm cả secret còn hiệu lực không) trong CI; GitHub secret scanning và push protection (bật mặc định cho repo public) chặn ngay lúc push. Hook pre-commit ở máy dev bỏ qua được bằng `--no-verify`, chỉ là lớp tiện.
- **Quản lý vòng đời**: mỗi secret có chủ, mục đích, nơi dùng, ngày xoay gần nhất. Xoay ngay khi người có quyền nghỉ việc hoặc nghi lộ; có khả năng xoay quan trọng hơn chu kỳ xoay. API key bên thứ ba nên hỗ trợ hai key cùng lúc để xoay không gián đoạn; khoá ký JWT xoay qua JWKS (bài JWT chuyên sâu). Cảnh báo khi một secret được đọc từ danh tính lạ hoặc tần suất bất thường.
- **Chi phí và lựa chọn trên AWS** (giá tham khảo, kiểm lại trước khi dùng): Secrets Manager 0,40 USD mỗi secret mỗi tháng cộng 0,05 USD mỗi 10.000 lần gọi API, có xoay tự động; Parameter Store `SecureString` bậc standard miễn phí nhưng không có xoay sẵn. Ứng dụng nên cache secret thay vì gọi kho mỗi request: vừa tốn tiền vừa biến kho thành dependency trên đường nóng.
- **Liên quan**: envelope encryption và KMS: bài Mật mã cho kỹ sư; workload identity, IRSA, SSRF lấy credential từ metadata: bài Kiến trúc bảo mật; Config Server và `{cipher}`: bài Spring Cloud.
