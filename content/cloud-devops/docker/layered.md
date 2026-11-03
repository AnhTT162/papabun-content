## Quick

Container là **một process Linux bình thường** được cô lập bằng [[linux-namespace|namespace]] và giới hạn tài nguyên bằng [[cgroup|cgroup]], chạy trên kernel của máy host; nó không phải máy ảo. [[container-image|Image]] là chồng [[image-layer|layer]] chỉ đọc: **xoá file ở layer sau không xoá nó khỏi image**, nên secret không bao giờ được nằm trong một layer (qua `COPY`, `ARG`, `ENV` hay file do `RUN` tạo ra).

## Interview

Container không có kernel riêng. Docker nhờ kernel tạo process với các namespace riêng: PID (process thấy mình là [[pid-1|PID 1]]), network (interface, IP, port riêng), mount (cây thư mục riêng), UTS (hostname), IPC; user namespace chỉ khi chạy rootless hoặc bật riêng. Cgroup giới hạn CPU, bộ nhớ, số process; vượt memory limit thì kernel giết process, exit code 137. Vì dùng chung kernel, container khởi động trong mili giây và nhẹ hơn máy ảo, nhưng cô lập yếu hơn: lỗ hổng kernel có thể cho thoát ra host.

Image theo chuẩn [[oci-image|OCI]] gồm manifest, config (entrypoint, user, biến môi trường) và các layer là file tar, mỗi thứ đặt tên bằng digest SHA-256. Mỗi lệnh `RUN`, `COPY` trong Dockerfile tạo một layer. Khi chạy, overlayfs xếp các layer thành một cây thư mục và thêm một lớp ghi được ở trên; container bị xoá là lớp đó mất.

Với service Java, tôi viết Dockerfile theo bốn ý. Một, [[multi-stage-build|multi-stage build]]: stage build có JDK và Maven, stage chạy chỉ có JRE và jar, nên image chạy nhỏ và không chứa source, cache Maven hay công cụ build. Hai, sắp layer theo tần suất thay đổi: copy `pom.xml` và tải dependency trước, source sau; Spring Boot có `-Djarmode=tools extract --layers` để tách dependency (vài chục MB, ít đổi) khỏi code của app (vài KB, đổi mỗi lần build). Ba, chạy đúng process: `ENTRYPOINT` dạng exec (`["java", "-jar", "app.jar"]`) để JVM là PID 1 và nhận được SIGTERM. Bốn, bảo mật: user không phải root, base image tối giản và vá thường xuyên, quét lỗ hổng, không để secret trong layer mà dùng `RUN --mount=type=secret` của BuildKit.

Bẫy hay gặp: image build trên Mac Apple Silicon ra arm64, đẩy lên node amd64 thì báo `exec format error`; tag `latest` bị ghi đè nên không biết đang chạy bản nào; và tưởng `RUN rm` đã xoá được file nhạy cảm. Cách JVM đọc memory limit để tính heap ở bài JVM trong container.

## Deep

- **Namespace**: Linux có tám loại: mount, UTS, IPC, PID, network, user, cgroup, time. Docker mặc định tạo riêng mount, UTS, IPC, PID, network; user namespace chỉ bật khi cấu hình (`userns-remap`) hoặc chạy rootless. Không có user namespace thì root trong container là root thật trên host, chỉ bị bớt capability và chặn syscall bằng seccomp. Kubernetes cho các container trong một pod dùng chung network namespace, nên chúng gọi nhau qua `localhost`.
- **Cgroup**: vượt `memory.max` thì [[oom-killer|OOM killer]] của kernel giết process, Docker báo `OOMKilled: true`, exit code 137 (128 + 9). CPU limit là quota theo chu kỳ 100 ms: dùng hết quota thì bị [[cpu-throttling|throttle]] tới chu kỳ sau, latency tăng mà CPU trung bình vẫn thấp. Ảnh hưởng tới JVM ở bài JVM trong container.
- **Container so với máy ảo**: máy ảo có kernel riêng trên hypervisor, cô lập mạnh hơn nhưng khởi động chậm và tốn bộ nhớ hơn. Khi chạy code không tin được của nhiều khách hàng chung máy, dùng sandbox mạnh hơn như gVisor, Kata Containers hay Firecracker (nền của AWS Lambda và Fargate).
- **Layer và overlayfs**:
  - Sửa một file thuộc layer dưới thì overlayfs chép cả file lên lớp ghi được (copy-up, một dạng [[copy-on-write|copy-on-write]]) rồi mới sửa: sửa file lớn trong container tốn kém.
  - Xoá file thì layer mới chỉ chứa một file đánh dấu `.wh.<tên>` (whiteout, theo OCI image spec); nội dung vẫn nằm ở layer cũ, ai tải image cũng giải nén ra được. Xoá cả thư mục rồi tạo lại thì dùng opaque whiteout `.wh..wh..opq`.
  - `ARG` và `ENV` cũng lộ: giá trị `ENV` nằm trong config của image, giá trị `ARG` dùng trong `RUN` hiện ra ở `docker history`. Không truyền password qua `--build-arg`. `RUN apt-get install ... && rm -rf /var/lib/apt/lists/*` phải nằm trong **cùng một** `RUN` mới giảm được kích thước.
  - Image cùng base dùng chung layer trên node và trên registry, nên đẩy bản mới chỉ đẩy layer đổi.
- **Build cache**: mỗi lệnh có khoá cache từ lệnh trước và nội dung của nó; `COPY` so checksum các file được copy. Một lệnh miss thì mọi lệnh sau build lại. `COPY . .` trước `mvn package` làm mỗi lần sửa một dòng code là tải lại toàn bộ dependency. BuildKit (builder mặc định từ Docker Engine 23) có `RUN --mount=type=cache,target=/root/.m2` để giữ repository Maven giữa các lần build mà không đưa vào image.
- **Build context và `.dockerignore`**: `docker build .` gửi cả thư mục cho builder. Thiếu `.dockerignore` thì `.git`, `target/`, file `.env` có thể vào image qua `COPY . .`, và context lớn làm build chậm.
- **Chọn base image cho JVM** (kích thước nén, amd64, đo trên registry 11/2026):
  - `eclipse-temurin:21-jdk` 224,6 MB; `21-jre` 115,5 MB; `21-jre-alpine` 74,2 MB; `gcr.io/distroless/java21-debian12:nonroot` 63,2 MB (đã có bản `debian13` 63,6 MB); `maven:3.9-eclipse-temurin-21` 245,2 MB (chỉ dùng cho stage build).
  - Image chạy không cần JDK: không cần `javac`, `jshell`. Đổi lại JRE không có `jcmd`, `jstack`; vẫn lấy được thread dump bằng `kill -3`, hoặc gắn ephemeral container có JDK (bài Bộ công cụ chẩn đoán JVM). Muốn nhỏ nữa thì `jlink` tạo runtime chỉ gồm các module app dùng.
  - Alpine dùng musl thay glibc: khác ở DNS resolver, cấp phát bộ nhớ và công cụ chẩn đoán; tiết kiệm vài chục MB ít khi đáng rủi ro.
  - [[distroless|Distroless]] không có shell và package manager: bề mặt tấn công nhỏ, nhưng không `exec` vào để gỡ lỗi được; dùng [[ephemeral-container|ephemeral container]] (`kubectl debug`, bài Lệnh Linux để điều tra sự cố).
- **Spring Boot [[layered-jar|layered jar]]**: từ Boot 3.3, `java -Djarmode=tools -jar app.jar extract --layers --destination extracted` tạo bốn thư mục `dependencies`, `spring-boot-loader`, `snapshot-dependencies`, `application`. Thử với app Spring Boot 4.1.2 một controller: `dependencies` 19 MB (34 jar), `application` chỉ còn jar 2,8 KB có `Class-Path` trỏ vào `lib/`. Copy bốn thư mục theo thứ tự đó vào cùng một chỗ rồi `java -jar app.jar` chạy được. Sửa code chỉ làm đổi layer cuối. Boot 2.3–3.2 dùng cú pháp cũ `-Djarmode=layertools -jar app.jar extract`, chạy bằng `JarLauncher` thay vì `java -jar`.
- **PID 1 và tín hiệu**:
  - Kernel không áp hành động mặc định của tín hiệu cho PID 1 trong namespace: PID 1 không tự cài handler SIGTERM thì SIGTERM bị bỏ qua. JVM có cài handler nên chạy JVM làm PID 1 là đúng.
  - `CMD java -jar app.jar` (dạng shell) chạy qua `/bin/sh -c`. Nhiều shell tự `exec` khi chỉ có một lệnh đơn nên có lúc vẫn chạy đúng "tình cờ", rồi hỏng khi thêm `&&`, pipe hay lệnh thứ hai. Script entrypoint gọi `java` mà không có `exec` thì shell là PID 1, JVM là con: `docker stop` gửi SIGTERM tới shell, JVM không nhận, chờ hết 10 giây (Kubernetes mặc định 30 giây) rồi SIGKILL, exit code 137. Chú ý cả khi JVM nhận được tín hiệu: Spring Boot chờ request dở tối đa 30 giây mỗi pha, lâu hơn 10 giây của `docker stop`. Shutdown hook và graceful shutdown không chạy. Sửa: dạng exec, hoặc `exec java ...` ở cuối script (entrypoint của image Temurin kết thúc bằng `exec "$@"`).
  - PID 1 còn phải dọn process zombie. Ứng dụng có tạo process con thì dùng `docker run --init` hoặc `tini`.
  - Phần còn lại của tắt êm (`preStop`, rút connection, consumer) ở bài Graceful shutdown & vòng đời process.
- **`ENTRYPOINT` và `CMD`**: `ENTRYPOINT` là chương trình, `CMD` là tham số mặc định; `docker run image args` thay `CMD`. Đặt `ENTRYPOINT` riêng trong image con thì bỏ entrypoint của base image (ví dụ script nạp chứng chỉ CA của Temurin).
- **Tag, digest, đa kiến trúc**:
  - Tag là con trỏ đổi được; [[image-digest|digest]] (`@sha256:...`) là bất biến. Deploy bằng tag theo commit SHA hoặc digest, không dùng `latest`.
  - Một tag có thể là image index chứa nhiều bản theo kiến trúc. `docker buildx build --platform linux/amd64,linux/arm64` build cả hai; node Graviton chạy arm64 rẻ hơn.
- **Bảo mật image**:
  - Image Temurin mặc định chạy root (config không có `User`); thêm `USER 10001` hoặc dùng distroless `:nonroot` (UID 65532). Kết hợp root filesystem chỉ đọc, bỏ hết capability.
  - Không mount `/var/run/docker.sock` vào container: ai điều khiển được socket là root trên host.
  - Quét lỗ hổng (Trivy, Grype) trong CI, build lại định kỳ để nhận bản vá của base image, ký image và tạo [[sbom|SBOM]] (bài Bảo mật trong quy trình phát triển).
- **Docker và Kubernetes**: Kubernetes bỏ dockershim từ bản 1.24 và chạy container qua containerd hoặc CRI-O. Image build bằng Docker vẫn chạy bình thường vì đều theo chuẩn OCI. `HEALTHCHECK` trong Dockerfile bị Kubernetes bỏ qua; dùng probe. Jib và Cloud Native Buildpacks (`spring-boot:build-image`) tạo image cho app Java không cần viết Dockerfile; Jib không cần Docker daemon.
