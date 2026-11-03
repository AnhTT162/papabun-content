## Quick

Ba probe làm ba việc khác nhau: [[liveness-probe|liveness]] thất bại thì **restart** container, [[readiness-probe|readiness]] thất bại thì **rút khỏi traffic**, [[startup-probe|startup]] che hai probe kia trong lúc khởi động chậm. **Requests** quyết định pod được xếp lên node nào và được đảm bảo bao nhiêu; **limits** là trần: vượt bộ nhớ thì OOMKilled, chạm CPU thì bị throttle. [[pod-disruption-budget|PodDisruptionBudget]] giữ đủ pod khi node bị rút. Rất nhiều sự cố vận hành bắt nguồn từ cấu hình sai một trong ba thứ này.

## Interview

Probe là chỗ tôi thấy sai nhiều nhất. Liveness chỉ nên trả lời "process này còn làm việc được không", không kiểm database hay service khác: database chậm mà liveness phụ thuộc nó thì mọi pod cùng bị restart, biến sự cố của dependency thành sự cố của mình. Readiness trả lời "có nên nhận traffic lúc này không", được phép phản ánh dependency thiết yếu. Với Spring Boot, tôi dùng `/actuator/health/liveness` và `/actuator/health/readiness`. App Java khởi động 40–60 giây thì dùng startup probe với ngân sách đủ rộng, thay vì đặt `initialDelaySeconds` lớn cho liveness.

Requests là cam kết: scheduler chỉ đặt pod lên node còn đủ requests, HPA tính phần trăm CPU theo requests, và khi node thiếu bộ nhớ thì pod dùng vượt requests bị trục xuất trước. Với JVM, tôi đặt memory request bằng limit, và tính heap theo limit: pod không bao giờ dùng bộ nhớ vượt requests nên thuộc nhóm bị trục xuất sau cùng (hạng là Guaranteed nếu CPU cũng request = limit, Burstable nếu bỏ CPU limit). CPU limit gây throttle làm latency xấu đi; nhiều đội chỉ đặt CPU request cho service nhạy latency (bài JVM trong container).

Khi có sự cố, tôi đọc trạng thái của pod rồi đi đúng nhánh: `CrashLoopBackOff` thì xem `kubectl logs --previous` và exit code; exit 137 kèm `OOMKilled` thì so bộ nhớ với limit; `Pending` thì xem event của scheduler (thiếu CPU, affinity, taint); `ImagePullBackOff` thì tên image, quyền registry, kiến trúc; `CreateContainerConfigError` thường là thiếu key trong ConfigMap hay Secret.

Về tính sẵn sàng: ít nhất 2–3 replica trải qua các AZ bằng topology spread, PDB để việc rút node không lấy đi quá nhiều pod cùng lúc, và [[hpa|HPA]] theo metric hợp lý (thuật toán và mặc định ở bài Capacity planning & autoscaling).

Bẫy hay gặp: liveness timeout 1 giây mặc định trên endpoint chậm; PDB `minAvailable` bằng số replica làm việc rút node treo mãi; và không đặt requests nên pod là BestEffort, bị trục xuất đầu tiên.

## Deep

- **Mặc định của probe**: `periodSeconds` 10, `timeoutSeconds` 1, `failureThreshold` 3, `successThreshold` 1. Liveness với GC pause hay CPU bị throttle dễ vượt 1 giây; đặt timeout 2–5 giây và endpoint thật nhẹ.
- **Liveness**:
  - Thất bại đủ ngưỡng thì kubelet giết container bằng SIGTERM rồi SIGKILL sau grace period, rồi chạy lại; exit code thường 143 hoặc 137.
  - Không kiểm dependency; không làm việc nặng (truy vấn database, gọi HTTP ra ngoài). Một pod bị deadlock thật mới là thứ liveness cần bắt.
  - Thiếu liveness thì pod treo vẫn ở đó mãi; liveness quá nhạy thì restart dưới tải đúng lúc cần pod nhất.
- **Readiness**: thất bại thì pod bị đánh dấu không sẵn sàng trong EndpointSlice, không restart. Phản ánh được trạng thái thiết yếu (pool database đã mở), nhưng nếu mọi pod cùng phụ thuộc một dependency đang sập thì mọi pod rời traffic và người dùng nhận lỗi ở gateway thay vì lỗi có ý nghĩa từ app; cân nhắc trả lỗi nhanh có kiểm soát thay vì rút hết.
- **Startup probe**: liveness và readiness chưa chạy cho tới khi startup probe thành công; ngân sách là `failureThreshold × periodSeconds` (30 × 5 giây = 150 giây). Thay cho `initialDelaySeconds` cố định, vốn hoặc quá ngắn (giết app đang khởi động) hoặc quá dài (pod treo lúc khởi động không bị phát hiện). Giảm thời gian khởi động ở bài Khởi động nhanh: CDS, CRaC, GraalVM native.
- **Requests, limits và QoS** ([[pod-qos-class|QoS class]]):
  - Guaranteed: mọi container (kể cả sidecar) có requests bằng limits cho cả CPU và bộ nhớ. Burstable: không đạt Guaranteed nhưng có ít nhất một requests hoặc limits (gồm trường hợp hay gặp: có requests mà không có CPU limit). BestEffort: không container nào đặt gì.
  - Node thiếu tài nguyên thì kubelet trục xuất theo thứ tự: BestEffort hoặc Burstable đang dùng vượt requests trước (xét Priority rồi mức vượt), Guaranteed và pod dùng dưới requests sau cùng. Ngưỡng cứng mặc định trên Linux gồm `memory.available<100Mi`, `nodefs.available<10%`; với ngưỡng cứng, kubelet giết ngay, không theo PDB hay grace period.
  - Bộ nhớ không nén được: vượt limit là [[oomkilled|OOMKilled]] (exit 137), dù node còn trống. CPU nén được: chạm limit là [[cpu-throttling|throttle]] theo chu kỳ 100 ms.
  - Requests quá thấp so với thực tế thì node bị xếp quá dày, các pod tranh nhau và bị trục xuất; quá cao thì lãng phí và Pending. Đặt theo số đo thật (VPA ở chế độ gợi ý, metric p95 của container). Thay đổi requests của pod đang chạy không cần tạo lại pod từ Kubernetes 1.35 (in-place resize).
  - `LimitRange` đặt mặc định cho namespace, `ResourceQuota` đặt trần tổng.
- **HPA**: tính phần trăm theo requests, nên thiếu requests là HPA không chạy được với CPU. Mặc định scale xuống có cửa sổ ổn định 300 giây. Thuật toán, metric tuỳ chỉnh, KEDA ở bài Capacity planning & autoscaling; đừng khai báo `replicas` trong manifest khi HPA quản lý nó (bài Helm, Kustomize & cấu hình nhiều môi trường).
- **PodDisruptionBudget**:
  - Chỉ chặn gián đoạn tự nguyện đi qua Eviction API: `kubectl drain`, nâng node, [[cluster-autoscaler|cluster autoscaler]] rút node. Không chặn node chết, OOMKilled, trục xuất do thiếu tài nguyên, hay rolling update (Deployment tự dùng `maxUnavailable`).
  - `minAvailable` bằng số replica (hoặc `maxUnavailable: 0`) thì không pod nào được trục xuất: drain treo, nâng cấp node bị chặn. Dùng `maxUnavailable: 1` hoặc phần trăm.
  - Mặc định (`IfHealthyBudget`), pod Running nhưng không Ready chỉ được trục xuất khi ngân sách còn khoẻ, nên vài pod CrashLoop có thể làm drain kẹt. Đặt `unhealthyPodEvictionPolicy: AlwaysAllow` (tài liệu khuyên, ổn định từ 1.31) để pod hỏng luôn trục xuất được.
  - Pod đang bị thay trong rolling update vẫn làm giảm số pod sẵn sàng, nên drain chạy cùng lúc với deploy dễ bị chặn.
- **Phân bố pod**: `topologySpreadConstraints` theo `topology.kubernetes.io/zone` để mất một AZ không mất hết pod; `podAntiAffinity` để hai replica không cùng một node. Priority class cho phép workload quan trọng chiếm chỗ (preemption) của workload ít quan trọng khi cluster đầy.
- **Đọc trạng thái pod**:
  - `CrashLoopBackOff`: container thoát lặp lại; kubelet chờ 10 giây, 20, 40… tối đa 300 giây giữa các lần chạy lại, và đặt lại bộ đếm khi container chạy ổn 10 phút. Xem `kubectl logs --previous`, `Last State` và exit code trong `kubectl describe pod`.
  - `OOMKilled`: thường do vượt memory limit của container: so working set với limit, heap với phần ngoài heap (bài JVM trong container). Nếu container chưa chạm limit mà vẫn bị giết, đó là OOM của kernel ở mức node (kubelet không kịp trục xuất), nạn nhân chọn theo `oom_score_adj`.
  - `Pending`: event `FailedScheduling` (`Insufficient cpu`, `didn't match pod affinity`, `untolerated taint`, `volume node affinity conflict` khi volume EBS nằm ở AZ khác); PVC chưa bind; requests lớn hơn mọi loại node thì cluster autoscaler cũng không giúp được. Vượt `ResourceQuota` thì pod không được tạo: xem event của ReplicaSet.
  - `ImagePullBackOff`/`ErrImagePull`: sai tên/tag, thiếu quyền kéo image, hoặc image không có kiến trúc của node (bài Docker & container).
  - `CreateContainerConfigError`: ConfigMap hay Secret được tham chiếu không tồn tại hoặc thiếu key.
  - `Evicted`: node thiếu bộ nhớ hay đĩa, hoặc pod vượt `ephemeral-storage` của nó (heap dump, log ghi vào container); xem `kubectl describe node` phần Conditions. Pod Evicted còn lại ở trạng thái Failed, cần dọn.
  - Công cụ: `kubectl describe`, `kubectl get events --sort-by=.lastTimestamp`, `kubectl top`, `kubectl debug` gắn ephemeral container (bài Lệnh Linux để điều tra sự cố).
