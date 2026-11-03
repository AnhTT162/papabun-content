## Quick

Kubernetes là hệ thống **khai báo**: bạn ghi trạng thái mong muốn vào API server, các controller liên tục so với thực tế và sửa cho khớp. [[kubernetes-pod|Pod]] là đơn vị chạy và có thể chết bất cứ lúc nào; [[kubernetes-deployment|Deployment]] giữ đủ số pod, [[kubernetes-service|Service]] cho chúng một tên và IP ổn định, [[configmap|ConfigMap]] và Secret đưa cấu hình vào từ ngoài image.

## Interview

Kubernetes chia làm [[kubernetes-control-plane|control plane]] và node. Control plane gồm API server (cửa duy nhất, lưu mọi object vào etcd), scheduler (chọn node cho pod mới theo resource request và ràng buộc), controller manager (các vòng lặp đối soát). Mỗi node có [[kubelet|kubelet]] nhận pod được giao và chạy container qua containerd, và [[kube-proxy|kube-proxy]] lập trình quy tắc chuyển tiếp cho Service. `kubectl apply` chỉ ghi trạng thái mong muốn; mọi việc còn lại là các controller phản ứng với thay đổi đó.

Pod là một hay vài container dùng chung network namespace và volume, có IP riêng. Pod không tự sống lại; khi node chết, pod mất và controller tạo pod mới với IP mới. Vì vậy tôi không bao giờ tạo pod trần mà dùng Deployment: Deployment tạo [[replicaset|ReplicaSet]] theo từng phiên bản pod template, ReplicaSet giữ đúng số pod. Đổi image là tạo ReplicaSet mới và rolling update: mặc định thêm tối đa 25% pod mới và cho phép 25% pod không sẵn sàng tại mỗi thời điểm; `kubectl rollout undo` quay lại ReplicaSet cũ.

Service chọn pod theo label, có tên DNS và một ClusterIP ảo ổn định. Pod chưa qua [[readiness-probe|readiness probe]] bị đánh dấu chưa sẵn sàng trong danh sách endpoint nên không nhận traffic; không khai báo readiness probe thì pod được coi là sẵn sàng ngay khi container chạy. Service là cân bằng tải L4 theo kết nối: kết nối giữ lâu như HTTP/2, gRPC sẽ dính vào một pod. Traffic từ ngoài vào đi qua [[ingress|Ingress]] hoặc Gateway API để định tuyến theo host và path.

Cấu hình đưa vào bằng ConfigMap, dữ liệu nhạy cảm bằng [[kubernetes-secret|Secret]], mount thành biến môi trường hoặc file. Bẫy hay gặp: đổi ConfigMap mà pod dùng biến môi trường thì không có gì thay đổi cho tới khi pod khởi động lại; Secret chỉ là Base64, không phải mã hoá.

Probe, resource request/limit, [[hpa|HPA]] và các lỗi như CrashLoopBackOff ở bài Vận hành ứng dụng trên Kubernetes.

## Deep

- **Khai báo và đối soát**: mỗi controller watch object qua API server và chạy vòng lặp "đọc mong muốn, đọc thực tế, sửa phần lệch". Không có bước nào "chạy lệnh deploy" theo kiểu tuần tự; vì vậy xoá tay một pod của Deployment chỉ làm ReplicaSet tạo pod khác. Chỉ API server nói chuyện với etcd; mất etcd là mất trạng thái cluster, nên control plane tự vận hành phải backup etcd.
- **Thành phần trên node**: kubelet nhận PodSpec, gọi container runtime qua CRI (containerd, CRI-O), chạy probe, báo trạng thái. Mạng pod do plugin CNI dựng (VPC CNI trên EKS cấp IP thật của VPC cho pod, Calico, Cilium). kube-proxy chạy ở chế độ iptables (mặc định) hoặc nftables; chế độ IPVS bị deprecated từ 1.35, tắt mặc định từ 1.40 và bị xoá ở 1.43. Một số CNI như Cilium thay kube-proxy bằng eBPF.
- **Pod**:
  - Các container trong pod gọi nhau qua `localhost`, chung volume, cùng được lên lịch vào một node.
  - Init container chạy tuần tự trước container app, ví dụ chờ database hay tải cấu hình. Sidecar gốc (init container có `restartPolicy: Always`, stable từ Kubernetes 1.33) khởi động trước app, chạy suốt đời pod và dừng sau app, sửa được lỗi cũ là sidecar log hay proxy tắt trước app.
  - Thay đổi CPU và bộ nhớ của container đang chạy mà không tạo lại pod (in-place resize) stable từ 1.35.
- **Deployment và rolling update** (mặc định trong mã nguồn `apps/v1`, Kubernetes 1.37):
  - `replicas` 1, `maxSurge` 25% (làm tròn lên), `maxUnavailable` 25% (làm tròn xuống), `revisionHistoryLimit` 10, `progressDeadlineSeconds` 600.
  - Với 4 replica: tối đa 5 pod cùng lúc và luôn ít nhất 3 pod sẵn sàng. Với 1 replica: `maxUnavailable` làm tròn xuống thành 0, nên pod mới phải sẵn sàng trước khi pod cũ bị xoá.
  - Quá `progressDeadlineSeconds` thì Deployment chỉ đánh dấu `ProgressDeadlineExceeded`, **không tự rollback**; pipeline phải kiểm `kubectl rollout status` và tự quay lại.
  - `selector` không đổi được sau khi tạo. Label `pod-template-hash` phân biệt pod của mỗi ReplicaSet.
  - Trong lúc [[rolling-deployment|rollout]], hai phiên bản cùng phục vụ; schema database và API phải tương thích cả hai (bài Rolling, blue-green, canary).
- **Service**:
  - Loại: `ClusterIP` (mặc định, chỉ trong cluster), `NodePort` (mở port 30000–32767 trên mọi node), `LoadBalancer` (cloud tạo load balancer trỏ vào), `ExternalName` (bản ghi CNAME). [[headless-service|Headless]] (`clusterIP: None`) trả IP từng pod, dùng cho StatefulSet và client tự cân bằng tải.
  - Endpoint được lưu trong [[endpointslice|EndpointSlice]]; pod không Ready vẫn có trong slice nhưng bị đánh dấu không sẵn sàng và không nhận traffic.
  - DNS: `orders.shop.svc.cluster.local`; trong cùng namespace gọi `orders` là đủ. Bẫy `ndots:5` với tên ngoài cluster ở bài DNS & CDN.
  - L4 theo kết nối: pool HTTP keep-alive hay kênh gRPC giữ kết nối lâu thì tải lệch về vài pod, và pod mới sau scale-out không nhận kết nối cũ. Cách xử lý (headless + cân bằng phía client, mesh) ở bài Giao tiếp giữa service.
- **Ingress và Gateway API**: Ingress định tuyến HTTP theo host/path và kết thúc TLS, cần một Ingress controller cài riêng. API Ingress đã đóng băng tính năng, controller ingress-nginx ngừng bảo trì từ 3/2026; hệ thống mới nên dùng [[gateway-api|Gateway API]] (bài API gateway, BFF & service mesh). Trên AWS, AWS Load Balancer Controller tạo ALB từ Ingress hay Gateway.
- **ConfigMap và Secret**:
  - Dạng biến môi trường: không cập nhật khi ConfigMap đổi, cần restart pod. Dạng volume: kubelet cập nhật file sau khoảng chu kỳ đồng bộ cộng độ trễ cache, có thể tới cả phút; mount bằng `subPath` thì không bao giờ cập nhật. App phải tự đọc lại file mới có tác dụng.
  - Cách hay dùng: coi cấu hình là bất biến và đổi tên ConfigMap mỗi lần đổi nội dung (hash ở hậu tố), để Deployment rolling update theo (bài Helm, Kustomize & cấu hình nhiều môi trường). `immutable: true` còn giảm tải cho API server vì kubelet không cần watch.
  - Giới hạn 1 MiB mỗi object. Secret mount dạng volume cũng được cập nhật như ConfigMap.
  - Secret chỉ là Base64. Trong etcd nó cũng chỉ là Base64 trừ khi API server bật encryption at rest (`EncryptionConfiguration`, nên dùng provider KMS; EKS có tuỳ chọn mã hoá Secret bằng KMS). Quyền [[rbac|RBAC]] `get`/`list` trên `secrets` là đọc được mọi Secret của namespace, và ai tạo được pod trong namespace là mount được chúng (bài Quản lý secret).
- **[[kubernetes-namespace|Namespace]]**: phạm vi tên, quyền RBAC, quota tài nguyên. Namespace **không** cô lập mạng: mặc định pod ở namespace nào cũng gọi được pod ở namespace khác, phải thêm NetworkPolicy (và CNI hỗ trợ nó).
- **Workload khác**: [[statefulset|StatefulSet]] cho pod cần danh tính và volume riêng ổn định (database, Kafka); DaemonSet chạy một pod mỗi node (agent log, CNI); Job và CronJob cho tác vụ chạy xong rồi thoát (migration, báo cáo đêm).
- **Mặc định hay gây bất ngờ** (Kubernetes 1.37): image không có tag hoặc tag `latest` thì `imagePullPolicy: Always`, tag khác hoặc tham chiếu bằng digest thì `IfNotPresent` (node có sẵn image cũ cùng tag thì không kéo bản mới; digest bất biến nên `IfNotPresent` là đủ); `terminationGracePeriodSeconds` 30 giây trước khi SIGKILL (bài Graceful shutdown & vòng đời process).
- **Khi nào không cần Kubernetes**: vài service, team nhỏ, không có người vận hành nền tảng thì ECS/Fargate, App Runner, Cloud Run hay PaaS rẻ hơn về công sức. Managed Kubernetes (EKS, GKE, AKS) lo control plane nhưng nâng cấp phiên bản mỗi năm vài lần, add-on, node, mạng vẫn là việc của bạn.
