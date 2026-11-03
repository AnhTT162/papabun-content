## Quick

Chi phí cloud là một thuộc tính kiến trúc như latency hay availability: nó sinh ra từ quyết định thiết kế (bao nhiêu AZ, dữ liệu đi đường nào, log giữ bao lâu) và đổi theo tải. [[finops|FinOps]] là cách vận hành để kỹ sư, tài chính và business cùng nhìn một con số và cùng chịu trách nhiệm về nó. **Ước tính từ driver nghiệp vụ ra đơn vị tài nguyên rồi ra tiền, đo bằng chi phí trên một đơn vị nghiệp vụ ([[unit-economics|unit cost]]), và tối ưu theo thứ tự: bỏ thứ không dùng, [[rightsizing|rightsize]], rồi mới mua cam kết; không cắt vào phần dự phòng mà SLO cần.**

## Interview

Khi ước tính, tôi đi từ driver nghiệp vụ: số đơn mỗi ngày, dung lượng dữ liệu và tốc độ tăng, thời gian lưu, lưu lượng ra Internet. Từ đó ra tài nguyên: số node theo throughput đo được, database theo dữ liệu và IOPS, băng thông. Rồi nhân đơn giá, cộng các môi trường dev và staging, log, support, và đưa ra một khoảng chứ không một con số. Những khoản hay bị quên là truyền dữ liệu (giữa AZ, qua [[nat-gateway|NAT gateway]], ra Internet), log và dữ liệu không bao giờ xoá.

Sau khi chạy, việc đầu tiên là biết tiền đi đâu: tách tài khoản theo môi trường và team, gắn [[cost-allocation-tag|tag]] bắt buộc, chia chi phí dùng chung như cluster Kubernetes theo request của pod, rồi [[showback|showback]] hằng tháng cho từng team. Chỉ số tôi theo dõi là unit cost, ví dụ chi phí hạ tầng trên một đơn hàng: tổng tiền tăng 40% khi số đơn tăng 50% là tốt, còn số đơn tăng 10% thì có vấn đề.

Tối ưu theo thứ tự. Tắt và xoá thứ không dùng: môi trường dev chạy cả đêm, volume không gắn vào đâu, log giữ vĩnh viễn. Rightsize theo mức dùng thật. Sửa đường đi của dữ liệu: [[vpc-endpoint|gateway endpoint]] cho S3, đọc từ replica cùng AZ. Cuối cùng mới mua [[savings-plan|Savings Plans]] hay [[reserved-instance|reserved instance]] cho phần tải nền ổn định, và dùng [[spot-instance|spot]] cho phần chịu được bị thu hồi.

Bẫy hay gặp là cắt chi phí bằng cách cắt độ tin cậy mà không ai quyết rõ: chuyển database production về một AZ, đưa toàn bộ capacity lên spot, giảm replication. Mỗi khoản đó tôi quy ra tiền tiết kiệm và rủi ro tăng thêm theo RTO, SLO, rồi để người chịu rủi ro quyết. Bẫy thứ hai là mua cam kết ba năm trước khi rightsize hay trước một đợt đổi kiến trúc.

## Deep

- **Hoá đơn gồm những gì** (giá us-east-1 theo AWS Price List API, 10/2026):
  - Compute tính theo giây hoặc giờ chạy, không theo mức dùng: m7i.large 0,1008 USD/giờ dù CPU 5% hay 95%.
  - Storage tính theo dung lượng *cấp*, không theo dung lượng dùng: EBS gp3 0,08 USD/GB-tháng, gp2 0,10. RDS gp3 0,115 cho Single-AZ và 0,23 cho Multi-AZ.
  - Request: S3 0,005 USD cho 1.000 PUT, 0,0004 cho 1.000 GET; tỉ lệ này đáng kể khi object nhỏ và nhiều.
  - Truyền dữ liệu: vào AWS miễn phí; giữa hai AZ 0,01 USD/GB **mỗi chiều**, tức 0,02 cho mỗi GB đi qua; ra Internet 0,09 USD/GB cho 10 TB đầu mỗi tháng rồi giảm dần.
  - Dịch vụ quản lý thu phí thêm theo giờ hay theo GB: NAT gateway 0,045 USD/giờ cộng 0,045 USD cho mỗi GB đi qua; control plane EKS 0,10 USD/giờ mỗi cluster; IPv4 public 0,005 USD/giờ mỗi địa chỉ (từ 2/2024).
  - Log: CloudWatch Logs 0,50 USD mỗi GB đưa vào (lớp Standard), 0,03 USD/GB-tháng lưu trữ; log group mặc định **không bao giờ hết hạn**.
  - Ngoài hoá đơn hạ tầng: gói support (tính theo phần trăm hoá đơn), license (Oracle, Windows, công cụ observability tính theo host hay theo GB; bẫy đếm core của Oracle khi ảo hoá ở bài Build hay buy & chọn vendor), và công người vận hành. So sánh phương án phải tính cả các khoản này; tổng chi phí sở hữu và build hay buy ở bài Build hay buy & chọn vendor.
- **Truyền dữ liệu là khoản hay bất ngờ nhất**:
  - NAT gateway tính phí xử lý cho mọi GB đi qua, kể cả khi đích là S3 cùng region. Gateway endpoint cho S3 và DynamoDB miễn phí và đi thẳng; layer image của ECR cũng tải từ S3 nên được gateway endpoint gánh phần lớn. Interface endpoint cho các dịch vụ khác tốn 0,01 USD/giờ mỗi AZ cộng 0,01 USD/GB, vẫn rẻ hơn NAT khi lưu lượng lớn.
  - Kafka tự chạy trên 3 AZ với replication factor 3: mỗi GB ghi vào bị chép sang 2 AZ khác, producer gửi tới leader ở AZ khác khoảng 2/3 số lần, consumer cũng vậy. 5 MB/s ghi trung bình là khoảng 13 TB mỗi tháng, ra khoảng 60 TB đi qua ranh giới AZ nếu có 3 consumer group, tức khoảng 1.200 USD. Fetch from follower (KIP-392, Kafka 2.4+: `broker.rack`, `replica.selector.class=org.apache.kafka.common.replica.RackAwareReplicaSelector`, `client.rack` ở consumer) cho consumer đọc replica cùng AZ. Đổi lại, follower chỉ trả dữ liệu tới high watermark nó đã biết, nên latency từ lúc ghi tới lúc consumer nhận tăng thêm khoảng một vòng fetch replication; consumer ở mỗi AZ phải đặt đúng `client.rack`. Replication thì không bỏ được: đó là giá của độ bền. Amazon MSK không tính phí truyền dữ liệu giữa các broker trong cluster.
  - Service gọi nhau qua AZ: Kubernetes có Topology Aware Routing và trường `trafficDistribution` của Service để ưu tiên endpoint cùng zone; đổi lại phải đủ pod ở mỗi zone, nếu không zone ít pod sẽ quá tải.
  - Mô hình multi-region và DR: chép dữ liệu giữa region tính phí theo GB (us-east-1 sang region khác 0,02 USD/GB). Bài High availability & disaster recovery sở hữu các mức DR và giá của chúng.
- **Ước tính khi chưa có hệ thống** (pre-sales, đề xuất kiến trúc):
  - Bảng driver: người dùng hoạt động, request/giây trung bình và đỉnh, kích thước bản ghi, dữ liệu mới mỗi tháng, thời gian lưu, tỉ lệ đọc/ghi, lưu lượng ra Internet, số môi trường. Mỗi driver có nguồn ghi rõ (số liệu hệ thống cũ, kế hoạch kinh doanh) và mức tin cậy. Cách ước lượng nhanh ở bài Ước lượng nhanh.
  - Ra tài nguyên bằng số đo, không bằng cảm giác: throughput một pod từ load test, rồi số pod theo bài Capacity planning & autoscaling (có headroom và N+1 khi mất AZ). Database theo dữ liệu nóng, IOPS và số kết nối.
  - Nhân đơn giá từ AWS Pricing Calculator hoặc Price List API; ghi ngày lấy giá và region (giá khác nhau giữa region, ví dụ Singapore thường cao hơn N. Virginia).
  - Cộng các môi trường không phải production (thường 20–40% production nếu không quản), log và monitoring, backup, support. Đưa khoảng thấp/kỳ vọng/cao theo kịch bản tải, kèm các giả định. Giả định sai thì báo lại, như change request ở bài Khai thác yêu cầu & ước lượng (ở đó có fixed price và T&M).
  - Chi phí theo tải thay đổi hình dạng của lựa chọn kiến trúc: điểm hoà vốn giữa Lambda và container ở bài Chọn kiểu kiến trúc; chi phí chạy song song hai nơi trong thời gian chuyển đổi ở bài Migration & hiện đại hoá.
- **[[finops|FinOps]]** theo FinOps Foundation:
  - Sáu nguyên tắc: các team phải phối hợp; giá trị kinh doanh dẫn dắt quyết định công nghệ; mọi người chịu trách nhiệm về mức dùng của mình; dữ liệu FinOps phải dễ truy cập, kịp thời và chính xác; FinOps được hỗ trợ tập trung; tận dụng mô hình chi phí biến đổi của cloud.
  - Ba giai đoạn lặp lại: Inform (thấy và phân bổ được chi phí, dự báo), Optimize (giảm lãng phí, mua cam kết), Operate (đưa vào quy trình: ngân sách, review, tự động hoá). Mức trưởng thành crawl, walk, run.
  - FOCUS (FinOps Open Cost and Usage Specification) là định dạng dữ liệu hoá đơn chung; AWS, Azure và Google Cloud đều xuất được, giúp gộp nhiều cloud và SaaS vào một báo cáo.
  - Một đội FinOps trung tâm nhỏ lo dữ liệu, mua cam kết và chính sách; team sản phẩm chịu trách nhiệm phần mình dùng. Đội trung tâm tự đi tối ưu thay các team thì không bền.
- **Phân bổ chi phí**:
  - Tài khoản riêng theo môi trường và theo team (AWS Organizations) là cách phân bổ chắc nhất, vì không phụ thuộc người nhớ gắn tag.
  - Tag (`team`, `service`, `env`, `cost-center`) chỉ hiện trong báo cáo chi phí sau khi được kích hoạt làm cost allocation tag trong Billing; có thể yêu cầu áp ngược tối đa 12 tháng. Bắt buộc tag bằng tag policy, SCP hoặc kiểm tra trong pipeline IaC; tài nguyên không có tag là một chỉ số cần theo dõi.
  - Chi phí dùng chung: cluster Kubernetes chia theo request CPU/bộ nhớ của pod (AWS có split cost allocation data cho EKS; OpenCost, Kubecost làm việc tương tự), NAT và hạ tầng mạng chia theo tỉ lệ, phần còn lại để ở dòng "nền tảng". Đừng tranh cãi phân bổ tới từng đô.
  - [[showback|Showback]] là cho mỗi team thấy họ tiêu bao nhiêu; [[cost-chargeback|chargeback]] là trừ thẳng vào ngân sách của họ. Bắt đầu bằng showback; chargeback khi số liệu phân bổ đã được tin.
- **Unit economics**: chọn đơn vị gắn với doanh thu (đơn hàng, giao dịch, tenant hoạt động, GB xử lý). Theo dõi xu hướng unit cost, không chỉ tổng. Tổng tăng khi kinh doanh tăng là bình thường; unit cost tăng là tín hiệu thiết kế hay vận hành đang lãng phí. Với SaaS, chi phí trên mỗi tenant cho biết gói giá nào đang lỗ (bài Kiến trúc multi-tenant).
- **[[rightsizing|Rightsizing]] và lãng phí hay gặp**:
  - Pod xin 2 CPU nhưng dùng 0,3: node đầy theo request trong khi CPU thật 15%. Chỉnh request theo p95 mức dùng thật, xem bài Capacity planning & autoscaling.
  - Môi trường dev và staging chạy 24/7: tắt ngoài 12 giờ × 5 ngày làm việc thì chỉ chạy 60/168 giờ, giảm khoảng 64%. Staging không cần Multi-AZ trừ khi đang thử chính failover.
  - gp2 sang gp3 giảm 20% giá dung lượng, kèm sẵn 3.000 IOPS và 125 MiB/s; đổi tại chỗ không dừng máy. Volume không gắn vào máy nào, snapshot cũ, IP public không dùng.
  - Log: hạ log DEBUG trên production, đặt retention cho mọi log group, chuyển log cần lưu lâu (audit) sang S3. Đổi log lặp lại thành metric (bài Log cho production).
  - S3: lifecycle chuyển dữ liệu ít đọc sang Standard-IA (0,0125 USD/GB) hoặc Glacier Instant Retrieval (0,004). Các lớp này có thời gian tính tối thiểu (30 ngày với IA, 90 ngày với Glacier IR) và tính mỗi object ít nhất 128 KB, kèm phí đọc theo GB; object nhỏ, hay bị xoá sớm hoặc hay đọc lại thì chuyển là lỗ. Intelligent-Tiering tự chuyển theo mức truy cập, thu phí theo dõi 0,0025 USD mỗi 1.000 object; object dưới 128 KB không bị thu phí này nhưng cũng không bao giờ được chuyển lớp.
  - Đổi kiến trúc CPU: m7g.large (Graviton) rẻ hơn m7i.large 19% mỗi giờ. Cần image multi-arch, kiểm thư viện native, và đo lại throughput chứ không chỉ so giá.
- **Cam kết sử dụng**:
  - [[savings-plan|Savings Plans]] cam kết một mức chi tính bằng USD/giờ trong 1 hoặc 3 năm. Compute Savings Plans áp cho EC2 mọi family, region, hệ điều hành, cùng Fargate và Lambda; EC2 Instance Savings Plans khoá một family trong một region nhưng giảm sâu hơn. Với m7g.large: on-demand 0,0816, Compute SP 1 năm không trả trước 0,0599 (giảm 26,6%), EC2 Instance SP 1 năm 0,054 (33,8%), Compute SP 3 năm 0,0414 (49,3%).
  - Cam kết tính theo từng giờ: giờ nào dùng ít hơn mức cam kết thì phần thiếu mất luôn, không dồn sang giờ sau. Compute SP 1 năm ở mức giá trên chỉ có lợi khi phần được phủ chạy hơn 73,4% số giờ. Vì vậy chỉ cam kết cho tải nền (đáy của nhiều tuần), không cho đỉnh.
  - Hai chỉ số: coverage (bao nhiêu phần chi tiêu đủ điều kiện được cam kết phủ) và utilization (bao nhiêu phần cam kết được dùng). Mua theo từng đợt nhỏ lệch tháng nhau thay vì một lần lớn, để các hợp đồng hết hạn rải rác và điều chỉnh được.
  - Database không nằm trong Compute Savings Plans. Có hai cách: [[reserved-instance|reserved instance]] (RDS, ElastiCache, OpenSearch, Redshift), gắn với engine và family, có kỳ hạn 3 năm; và Database Savings Plans (từ 12/2025), cam kết USD/giờ chỉ 1 năm, linh hoạt giữa engine và family nhưng giảm ít hơn. Với db.r7g.xlarge PostgreSQL Multi-AZ (0,956 on-demand): RI 1 năm không trả trước 0,7363 (giảm 23%), Database SP 1 năm 0,7648 (giảm 20%). RI standard của EC2 giảm sâu hơn convertible nhưng không đổi family được.
  - Cam kết là một quyết định khó đảo ngược (bài Ra quyết định & trade-off): đừng mua 3 năm cho workload sắp chuyển sang serverless, sắp đổi sang Graviton theo EC2 Instance SP của family cũ, hay sắp bị tắt.
- **[[spot-instance|Spot]]**: dùng capacity thừa của AWS, giảm tới khoảng 90% nhưng có thể bị thu hồi với thông báo trước 2 phút (kèm tín hiệu rebalance recommendation sớm hơn). Hợp với batch, CI, worker đọc hàng đợi, pod stateless có dư. Đa dạng nhiều instance type và AZ, chọn chiến lược price-capacity-optimized, xử lý tín hiệu thu hồi để drain pod (Karpenter, AWS Node Termination Handler). Không đặt phần capacity mà SLO cần khi mất một AZ lên spot.
- **Giám sát chi phí**:
  - AWS Budgets gửi cảnh báo theo ngưỡng thực tế hoặc dự báo, nhưng **không tự chặn chi tiêu**; budget action có thể áp IAM policy, SCP hoặc dừng EC2/RDS khi chạm ngưỡng, phải cấu hình riêng.
  - Cost Anomaly Detection tìm mức chi bất thường theo service, tài khoản hoặc tag. Dữ liệu chi phí trễ nhiều giờ (Cost Explorer cập nhật ít nhất mỗi 24 giờ), nên với rủi ro chạy mất kiểm soát (vòng lặp Lambda và S3, job tạo log vô hạn), cần thêm metric và alert kỹ thuật như số lần gọi, byte log đưa vào.
  - Đưa chi phí vào review thiết kế: mỗi đề xuất có dòng ước tính chi phí tháng và unit cost; trụ cột cost optimization ở bài AWS Well-Architected; chi phí là một NFR ở bài NFR & quality attribute. Có thể tự động hoá thành fitness function: pipeline IaC báo chênh lệch chi phí (Infracost) trên mỗi pull request.
- **Chi phí và độ tin cậy**:
  - Multi-AZ cho RDS gần gấp đôi: db.r7g.xlarge PostgreSQL 0,478 USD/giờ Single-AZ, 0,956 Multi-AZ; storage cũng gấp đôi. Đổi lại, failover tự động trong khoảng một tới hai phút thay vì restore từ backup.
  - Capacity dự phòng cho static stability (mỗi AZ gánh được một nửa tải đỉnh khi chạy 3 AZ) là máy chạy không có chủ đích, không phải lãng phí; bài Độ tin cậy & SRE.
  - Cắt log và metric quá tay làm chậm điều tra sự cố. Giữ log lỗi và trace có lấy mẫu, cắt log thành công lặp lại.
  - Mỗi đề xuất cắt giảm chạm vào độ tin cậy nên được viết thành: tiết kiệm bao nhiêu mỗi tháng, RTO/RPO hay SLO đổi thế nào, ai chấp nhận rủi ro. Tiết kiệm 579 USD/tháng bằng cách bỏ Multi-AZ cho database chính hiếm khi đáng nếu một giờ ngừng mất nhiều hơn số đó.
