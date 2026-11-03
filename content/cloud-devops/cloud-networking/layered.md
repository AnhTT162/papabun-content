## Quick

Mạng trên cloud là [[route-table|route table]], [[security-group|security group]] và vài loại "cửa" giữa các mạng: [[nat-gateway|NAT gateway]] ra Internet, [[vpc-endpoint|VPC endpoint]] tới dịch vụ AWS, [[privatelink|PrivateLink]] tới service của tài khoản khác, [[vpc-peering|peering]] hay [[transit-gateway|Transit Gateway]] giữa các VPC, VPN hay Direct Connect về data center. **Kết nối chỉ chạy khi route đúng ở cả hai chiều và luật cho phép ở mọi lớp trên đường đi**; quy hoạch [[cidr|CIDR]] từ đầu quyết định sau này nối được những gì.

## Interview

Tôi chia mạng theo tài khoản và môi trường: mỗi môi trường một VPC, CIDR lấy từ bảng phân bổ chung của cả tổ chức để không trùng với VPC khác và với mạng văn phòng, vì trùng là không bao giờ nối được. Mỗi VPC có subnet public, private, database ở mỗi AZ (bài AWS cho kỹ sư backend).

Đường ra: app ra Internet qua NAT gateway mỗi AZ; tới S3 và DynamoDB qua gateway endpoint miễn phí; tới các dịch vụ AWS khác (Secrets Manager, ECR, CloudWatch) qua interface endpoint, vừa không ra Internet vừa không trả phí xử lý của NAT. Muốn kiểm soát app được gọi tới tên miền nào thì thêm egress proxy hay Network Firewall có allowlist.

Giữa các VPC: peering là nối một-một, không bắc cầu, rẻ, hợp khi chỉ vài VPC. Khi có hàng chục VPC và kết nối về on-premises, tôi dùng Transit Gateway làm hub: mỗi VPC gắn một lần, route table của Transit Gateway quyết định ai đi được tới ai, nên tách được prod khỏi dev. Muốn cho service khác gọi một API mà không mở cả mạng, dùng PrivateLink: phía cung cấp đặt service sau NLB, phía dùng tạo interface endpoint; chỉ một cổng đi qua, CIDR trùng nhau cũng không sao.

Về on-premises: Site-to-Site VPN dựng nhanh, đi qua Internet, mỗi tunnel chuẩn tới 1,25 Gbps; Direct Connect là đường riêng, băng thông và latency ổn định, nhưng mất nhiều tuần để có và không tự mã hoá. Production thường dùng Direct Connect và giữ VPN làm dự phòng.

DNS nội bộ: Route 53 private hosted zone cho tên trong VPC; VPC Resolver với inbound và outbound endpoint để on-premises phân giải tên trên AWS và ngược lại.

Bẫy hay gặp: thêm route một chiều nên kết nối timeout; luật security group tham chiếu SG của VPC khác mà chưa bật tính năng đó trên Transit Gateway; mọi traffic tới S3 đi qua NAT tốn tiền; và hết IP trong subnet khi EKS cấp IP thật cho mỗi pod.

## Deep

- **Quy hoạch IP**:
  - Mỗi VPC tối đa `/16` cho CIDR chính, thêm được CIDR phụ. Lập bảng phân bổ cho mọi tài khoản, region, mạng văn phòng và đối tác trước khi tạo VPC đầu tiên; AWS IPAM quản lý và kiểm trùng.
  - EKS với VPC CNI cấp mỗi pod một IP của subnet: node `m7i.large` chạy tới 29 pod là 29 IP. Thiếu IP thì dùng prefix delegation (mỗi ô IP của ENI được thay bằng một khối `/28`) hoặc thêm CIDR phụ trong dải `100.64.0.0/10` chỉ dành cho pod.
- **Route và các lớp lọc**: một kết nối đi qua route table của subnet nguồn, NACL của subnet nguồn và đích (stateless, phải mở cả chiều về), security group của đích và của nguồn (stateful), route của Transit Gateway nếu có, rồi route table chiều về. Timeout thường là thiếu route hay luật ở một trong các chặng đó; connection refused là gói đã tới nơi (bài Mạng máy tính cơ bản). Reachability Analyzer của VPC tính đường đi một chiều theo cấu hình mà không gửi gói (lỗi chiều về thì chạy thêm chiều ngược lại); VPC Flow Logs ghi `ACCEPT`/`REJECT` thật.
- **NAT gateway**: zonal, mỗi AZ một cái, tính tiền theo giờ và theo GB; khoảng 55.000 kết nối đồng thời tới mỗi đích (bài Mạng máy tính cơ bản). AWS có thêm chế độ NAT gateway regional tự mở rộng qua các AZ; kiểm hỗ trợ và giá trước khi chọn.
- **VPC endpoint**:
  - Gateway endpoint (S3, DynamoDB): một mục trong route table, miễn phí, chỉ dùng trong cùng region và chỉ cho traffic xuất phát trong VPC đó: on-premises, VPC peering hay Transit Gateway không đi qua nó được (dùng interface endpoint cho S3 khi cần).
  - Interface endpoint: ENI có IP private trong subnet của bạn, tính theo giờ mỗi AZ và theo GB; với private DNS bật, tên dịch vụ chuẩn (`secretsmanager.ap-southeast-1.amazonaws.com`) tự phân giải ra IP private.
  - Endpoint policy và điều kiện `aws:SourceVpce` trong bucket policy giới hạn ai và bucket nào đi qua (bài Kiến trúc bảo mật).
- **PrivateLink**: phía cung cấp tạo endpoint service trước một NLB, cho phép từng tài khoản; phía dùng tạo interface endpoint. Một chiều (bên dùng gọi bên cung cấp), không lộ CIDR, chịu được CIDR trùng nhau; hỗ trợ truy cập khác region. Đây cũng là cách nhiều SaaS (database managed, observability) nhận traffic từ VPC của khách hàng.
- **Peering**: một-một, không bắc cầu (A nối B, B nối C thì A vẫn không tới C), không trùng CIDR, cùng region thì tham chiếu được security group của VPC bên kia. Không phí theo giờ; truyền qua AZ hay region vẫn tính theo GB.
- **Transit Gateway**:
  - Hub cấp region: gắn VPC, VPN, Direct Connect gateway, peering với Transit Gateway region khác. Mỗi attachment gắn với một route table (association) và đẩy CIDR của nó vào các route table (propagation); tách prod/dev/shared bằng nhiều route table.
  - Route table của từng VPC vẫn phải có route tới Transit Gateway cho CIDR đích; quên phía bên kia là timeout.
  - Attachment chỉ tới được các AZ có subnet đã chọn cho attachment; thiếu AZ là traffic tới AZ đó bị bỏ. VPC chứa thiết bị kiểm tra (firewall tập trung) cần bật appliance mode để hai chiều của một luồng đi cùng một AZ.
  - MTU qua Transit Gateway là 8.500 byte, thấp hơn 9.001 trong VPC.
  - Tính theo giờ mỗi attachment và theo GB xử lý: với lưu lượng lớn giữa hai VPC cố định, peering rẻ hơn.
  - Luật inbound của security group tham chiếu được SG của VPC khác gắn cùng Transit Gateway, nhưng chỉ khi bật security group referencing ở cả Transit Gateway lẫn VPC attachment, và không dùng cho luật outbound; nếu không thì dùng CIDR hoặc prefix list.
- **Hybrid**:
  - Site-to-Site VPN: hai tunnel IPsec qua hai endpoint khác nhau phía AWS, cấu hình cả hai và dùng BGP để chuyển khi một tunnel rớt. Tunnel chuẩn tới 1,25 Gbps (có loại băng thông lớn hơn); cần hơn thì nhiều tunnel với ECMP trên Transit Gateway.
  - Direct Connect: cổng vật lý 1/10/100/400 Gbps tại điểm kết nối (nối với Transit Gateway qua Direct Connect gateway và transit VIF), latency ổn định, phí truyền ra rẻ hơn Internet. Không mã hoá mặc định: dùng MACsec (một số cổng) hoặc VPN trên Direct Connect, hay TLS ở tầng ứng dụng. Muốn bền thì hai kết nối ở hai điểm kết nối khác nhau.
  - Kiểm MTU: VPN và một số đường hybrid nhỏ hơn 9.001 của VPC; gói lớn bị bỏ khi chặn ICMP (bài Mạng máy tính cơ bản).
- **[[dns|DNS]] nội bộ**:
  - VPC Resolver ở địa chỉ VPC+2 (ví dụ `10.0.0.2`) trả lời tên trong private hosted zone gắn với VPC đó, tên nội bộ của EC2 và tên công khai.
  - Inbound endpoint cho DNS on-premises chuyển truy vấn vào AWS; outbound endpoint kèm forwarding rule để VPC hỏi DNS on-premises cho tên miền nội bộ. Chia sẻ rule qua nhiều tài khoản bằng AWS RAM.
  - Private hosted zone gắn sai VPC hoặc trùng tên với zone công khai làm cùng một tên phân giải khác nhau trong và ngoài VPC (split-horizon), dễ gây khó hiểu khi gỡ lỗi.
- **Cân bằng tải L4 và L7**: ALB cho HTTP (định tuyến theo host/path, WAF), NLB cho TCP/UDP, IP tĩnh, PrivateLink; Gateway Load Balancer chèn thiết bị kiểm tra (firewall) vào đường đi. Mặc định và bẫy của ALB/NLB ở bài AWS cho kỹ sư backend.
- **Kiểm soát chiều ra**: phần lớn service chỉ cần gọi dịch vụ AWS (qua endpoint) và vài đối tác. AWS Network Firewall hay proxy egress với allowlist tên miền chặn dữ liệu bị đẩy ra ngoài sau khi bị xâm nhập; Route 53 DNS Firewall chặn truy vấn tới tên miền không được phép.
