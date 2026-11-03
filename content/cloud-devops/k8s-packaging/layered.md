## Quick

[[helm|Helm]] sinh manifest từ template cộng values và quản lý [[helm-release|release]] có lịch sử để rollback; [[kustomize|Kustomize]] giữ YAML thuần làm base rồi vá theo từng môi trường bằng [[kustomize-overlay|overlay]]. Cả hai phục vụ một nguyên tắc: **một artifact, một bộ manifest gốc, khác biệt giữa môi trường nằm ở vài file nhỏ được review**. Bẫy lớn nhất của Helm: values kiểu map được gộp, kiểu **list bị thay cả list**.

## Interview

Khi số môi trường và số service tăng, chép YAML cho từng môi trường sẽ lệch nhau rất nhanh. Có hai cách tiếp cận.

Helm là trình đóng gói: một [[helm-chart|chart]] gồm template Go và file `values.yaml` mặc định. Lúc cài, Helm gộp values theo thứ tự ưu tiên: `values.yaml` của chart, values của chart cha, các file `-f` (file sau thắng file trước), cuối cùng là `--set`. Map được gộp đệ quy, còn list thì giá trị ưu tiên hơn thay toàn bộ. Helm lưu mỗi lần cài hay nâng cấp thành một revision của release (mặc định là Secret trong namespace), nên `helm rollback` áp lại manifest cũ. Helm hợp khi phát hành phần mềm cho người khác cài, hoặc nhiều service dùng chung một chart nền.

Kustomize không có template. Base là YAML hợp lệ, overlay của mỗi môi trường khai báo patch, đổi image, số replica, sinh ConfigMap. `configMapGenerator` gắn hash nội dung vào tên [[configmap|ConfigMap]] và sửa mọi chỗ tham chiếu, nên đổi cấu hình là Deployment tự rolling update. Kustomize có sẵn trong `kubectl apply -k`.

Cách tôi tổ chức: một chart hoặc một base cho mỗi service, mỗi môi trường một file values hay một overlay chỉ chứa phần khác biệt; image tag do pipeline ghi vào, không sửa tay. CI chạy `helm template` hoặc `kustomize build` cho mọi môi trường, kiểm schema, và hiện diff trong pull request, để người review thấy chính xác manifest sẽ đổi gì.

[[kubernetes-secret|Secret]] không nằm trong values hay overlay dạng rõ: dùng [[external-secrets-operator|External Secrets Operator]] kéo từ secret manager, hoặc mã hoá bằng [[sealed-secrets|Sealed Secrets]]/SOPS trước khi commit.

Bẫy hay gặp: đổi ConfigMap qua Helm mà pod không restart vì pod template không đổi; và list `env` trong values của prod thay mất các biến chart đã khai báo.

## Deep

- **Thứ tự gộp values của Helm** (helm.sh, mã nguồn `coalesce.go` của Helm 4.3.1):
  - Ưu tiên tăng dần: `values.yaml` của chart, của chart cha (với subchart), `-f` theo thứ tự (file phải nhất thắng), `--set`/`--set-string`/`--set-json`.
  - Chỉ khi cả hai phía là map thì mới gộp đệ quy. List, chuỗi, số: giá trị ưu tiên hơn thay hẳn. Đặt một key thành `null` để xoá giá trị mặc định của chart.
  - Hệ quả thiết kế chart: thứ người dùng sẽ thêm từng phần (biến môi trường, annotation, volume) nên khai báo dạng map, hoặc tách `env` của chart khỏi `extraEnv` của người dùng.
  - `values.schema.json` trong chart kiểm kiểu và trường bắt buộc lúc render; hàm `required` báo lỗi khi thiếu value quan trọng thay vì render ra rỗng.
- **`--reuse-values` nguy hiểm khi nâng chart**: lấy toàn bộ values đã dùng ở lần trước (gồm cả default của chart cũ) làm nền, nên default mới và key mới của chart không có hiệu lực, tính năng mới có thể nhận giá trị rỗng. Tốt hơn: luôn truyền đủ file values từ git; `--reset-then-reuse-values` là lựa chọn giữa hai bên.
- **Release và rollback**:
  - Mỗi revision lưu trong Secret `sh.helm.release.v1.<tên>.v<số>` ở namespace của release (đổi bằng `HELM_DRIVER`); `--history-max` mặc định 10. Secret này chứa manifest đã render, gồm cả Secret của app, nên ai đọc được Secret của namespace là đọc được.
  - `helm rollback` áp lại manifest của revision cũ và tạo revision mới. Nó không quay lại schema database hay dữ liệu đã migrate (bài Rolling, blue-green, canary).
  - Helm 4: `--atomic` đổi tên thành `--rollback-on-failure`, `--force` thành `--force-replace` (tên cũ vẫn chạy kèm cảnh báo); cài mới mặc định dùng [[server-side-apply|server-side apply]], release cũ giữ cách apply trước đó; `--wait` dùng kstatus để chờ tài nguyên sẵn sàng.
  - Không có `--wait` thì `helm upgrade` báo thành công ngay khi API server nhận manifest, kể cả khi pod mới CrashLoopBackOff.
- **CRD**: file trong thư mục `crds/` của chart chỉ được cài lần đầu; Helm không nâng cấp và không xoá CRD. Nâng CRD (của cert-manager, Prometheus Operator...) là bước riêng, làm trước khi nâng chart.
- **Xem trước thay đổi**: `helm diff upgrade` (plugin) hoặc `helm template ... | kubectl diff -f -` cho thấy chính xác cluster sẽ đổi gì; chạy trong pull request.
- **Chart dùng chung**: dependency khai báo trong `Chart.yaml`, chart lưu và kéo từ registry OCI (`helm push oci://...`), ghim theo phiên bản hoặc digest.
- **Hook**: `pre-upgrade` hay chạy Job migration database. Tài nguyên hook không thuộc release (không bị xoá khi uninstall, không rollback); đặt `helm.sh/hook-delete-policy`. Hook thất bại làm upgrade thất bại, nhưng migration đã chạy một phần thì không tự hoàn tác.
- **Đổi ConfigMap mà pod không restart**: Deployment chỉ rolling update khi pod template đổi. Helm: thêm annotation `checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}` vào pod template (mẹo trong tài liệu Helm). Kustomize: `configMapGenerator` đổi tên ConfigMap theo hash nên pod template đổi theo; đừng tắt hash bằng `disableNameSuffixHash` trừ khi có lý do.
- **Kustomize**:
  - [[strategic-merge-patch|Strategic merge patch]] biết khoá gộp của list Kubernetes: patch `containers` theo `name`, `env` theo `name`, nên overlay thêm một biến môi trường không xoá các biến của base. JSON patch (RFC 6902) cho chỗ cần sửa theo vị trí.
  - `images:` đổi tag hay digest mà không sửa base (`kustomize edit set image` trong pipeline); `replicas:`, `namePrefix`, `labels`, `components` cho tính năng bật theo môi trường.
  - `kubectl apply -k` dùng bản Kustomize nhúng trong kubectl, thường cũ hơn bản `kustomize` độc lập; dùng cùng một bản ở máy dev và CI.
  - Không có cơ chế release: xoá một tài nguyên khỏi overlay thì `kubectl apply` không xoá nó trên cluster (`--prune` vẫn ở mức alpha và cần `-l` hoặc `--all`), nên thường đi cùng công cụ GitOps.
- **Helm hay Kustomize**:
  - Helm: đóng gói để phân phối (chart của bên thứ ba như ingress controller, Prometheus), logic tham số hoá nhiều, cần rollback theo release. Giá: template YAML bằng Go template khó đọc, lỗi thụt lề; logic điều kiện phình ra.
  - Kustomize: app nội bộ, base đơn giản, khác biệt giữa môi trường nhỏ. Giá: không có biến hay vòng lặp, khác biệt lớn thì nhiều patch.
  - Dùng chung: Helm render chart bên thứ ba rồi Kustomize vá thêm (`helmCharts` trong kustomization, cần `kustomize build --enable-helm`, hoặc post-renderer của Helm).
- **Cấu hình nhiều môi trường**:
  - Không dùng mỗi môi trường một nhánh git: nhánh lệch nhau và merge cấu hình rất khó. Dùng thư mục `overlays/dev`, `overlays/staging`, `overlays/prod` hoặc `values-<env>.yaml` trên cùng nhánh.
  - Khác biệt giữa môi trường nên ít và có chủ đích: số replica, resource, URL backing service, cờ tính năng. Khác cả cấu trúc (prod có sidecar, staging không) là dấu hiệu dev/prod parity kém (bài Twelve-Factor App).
  - Image tag là thứ thay đổi nhiều nhất: CI ghi digest vào file của môi trường, promote sang môi trường sau bằng một pull request đổi đúng dòng đó. Argo CD đọc git và đồng bộ cluster ở bài Infrastructure as Code & GitOps.
- **Secret** (bài Quản lý secret): External Secrets Operator tạo Kubernetes Secret từ AWS Secrets Manager hay Vault; Sealed Secrets mã hoá bằng khoá công khai của controller để commit được; SOPS mã hoá giá trị trong file YAML bằng KMS. Không truyền secret bằng `--set` trong pipeline: nó vào log CI và nằm trong release Secret.
- **Drift**: ai đó `kubectl edit` hay `kubectl scale` trực tiếp thì cluster lệch git. Với server-side apply, lần apply sau báo conflict về field manager hoặc ghi đè (`--force-conflicts`); HPA quản lý `replicas` thì đừng khai báo `replicas` trong manifest kẻo mỗi lần deploy reset số pod.
