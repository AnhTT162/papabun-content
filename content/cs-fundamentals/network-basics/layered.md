## Quick

Mỗi gói tin mang [[ip-address|IP]] nguồn và đích để tới đúng máy, [[network-port|port]] để tới đúng process trên máy đó. [[cidr|CIDR]] (`10.0.16.0/20`) mô tả một dải IP liên tục, router chọn đường theo [[route-table|route table]], còn [[nat|NAT]] đổi địa chỉ khi gói đi qua ranh giới mạng. **Khi service không gọi được nhau, hỏi lần lượt: tên có ra đúng IP không, có đường tới IP đó không, firewall có cho qua port đó không, và process có đang lắng nghe đúng địa chỉ và port không.**

## Interview

Tôi hay giải thích theo mô hình TCP/IP bốn tầng, và gọi tên theo số tầng của [[osi-model|mô hình OSI]] vì ai cũng dùng: tầng 2 là Ethernet với MAC, tầng 3 là IP, tầng 4 là TCP/UDP với port, tầng 7 là HTTP. [[load-balancer|Load balancer]] "L4" chỉ nhìn IP và port, "L7" đọc được HTTP.

**IP và subnet**: IPv4 là số 32 bit. `/20` nghĩa là 20 bit đầu là phần mạng, 12 bit còn lại cho host: 4.096 địa chỉ, từ `10.0.16.0` tới `10.0.31.255`. Hai máy cùng [[subnet]] nói chuyện trực tiếp; khác subnet thì gửi tới gateway. Router so IP đích với route table và chọn route có prefix dài nhất khớp; `0.0.0.0/0` là route mặc định.

**Port**: số 16 bit chỉ process đích. Một kết nối TCP được xác định bằng bộ năm (giao thức, IP nguồn, port nguồn, IP đích, port đích). Client dùng [[ephemeral-port|ephemeral port]] do kernel cấp.

**NAT**: máy trong dải [[private-ip|IP private]] (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) ra Internet qua NAT. NAT thay IP nguồn bằng IP public của nó và ghi lại để chuyển response về đúng máy. Đối tác cần whitelist IP thì phải whitelist IP của NAT, không phải IP của pod.

**Khi service không gọi được nhau**, lỗi của Java nói ngay tầng nào hỏng:
- `UnknownHostException`: [[dns|DNS]] không phân giải được tên.
- `ConnectException: Connection refused`: đã tới máy đích nhưng không process nào nghe port đó (hoặc firewall chủ động từ chối).
- `SocketTimeoutException: Connect timed out`: gói SYN bị bỏ lặng lẽ, thường do [[security-group|security group]], route sai hoặc IP sai.

Bẫy hay gặp nhất: app trong container chỉ nghe `127.0.0.1` nên từ ngoài bị refused, và dải IP trùng nhau (bridge Docker trên Linux `172.17.0.0/16` trùng dải của VPN công ty) làm route đi nhầm đường.

## Deep

- **Đếm IP theo prefix**: `/n` có 2^(32−n) địa chỉ. Mạng truyền thống trừ 2 địa chỉ (địa chỉ mạng và broadcast), nên `/24` còn 254 host. AWS giữ lại 5 địa chỉ mỗi subnet (4 đầu và 1 cuối), nên `/24` trên VPC chỉ còn 251; subnet nhỏ nhất là `/28` (16 địa chỉ, dùng được 11).
- **Kiểm IP có nằm trong dải không** chỉ là phép AND với mask: `/20` là mask `255.255.240.0`. `10.0.31.200` AND mask ra `10.0.16.0` nên thuộc `10.0.16.0/20`; `10.0.32.9` ra `10.0.32.0` nên không thuộc.
- **Subnet cạn IP trên Kubernetes**: với CNI cấp IP thật của VPC cho mỗi pod (như Amazon VPC CNI), một node có thể giữ hàng chục IP. Chọn subnet `/24` cho cluster lớn thì đến lúc scale pod nằm `Pending` vì hết IP chứ không phải hết CPU. Chọn CIDR rộng và không trùng nhau ngay từ đầu, vì đổi CIDR sau này rất đau.
- **Dải trùng nhau là lỗi im lặng**: VPC A và VPC B cùng dùng `10.0.0.0/16` thì không peering hay nối VPN được. Máy Linux có bridge Docker `172.17.0.0/16` thì gọi một server `172.17.x.x` sau VPN sẽ đi vào bridge local. Kiểm bằng `ip route get <IP>` (Linux) hoặc `route get <IP>` (macOS) để thấy gói đi qua interface nào.
- **Refused và timeout khác nhau ở gói trả về**: refused là host đích trả RST (port đóng) hoặc firewall REJECT; timeout là không có gì trả về. Firewall kiểu DROP và security group của AWS cho kết quả timeout. Không đặt connect timeout thì Java chờ theo kernel: Linux mặc định thử SYN 6 lần lại (`net.ipv4.tcp_syn_retries`), mất khoảng 127 giây. Luôn đặt connect timeout ngắn (vài trăm ms tới vài giây) cho gọi nội bộ.
- **Bind `127.0.0.1` và `0.0.0.0`**: nghe ở `127.0.0.1` chỉ nhận kết nối từ chính máy (hoặc chính container). Spring Boot mặc định nghe mọi interface (`server.address` để trống), nhưng nhiều tool dev, database chạy local hay app tự cấu hình lại nghe localhost. Trong container, `localhost` là chính container đó, không phải máy host.
- **Lỗi kết nối khác**: `NoRouteToHostException: No route to host` thường là router hay firewall trả ICMP host unreachable, hoặc cùng subnet mà không tìm được MAC của IP đích (ARP thất bại, máy đích tắt); `Network is unreachable` là máy mình không có route nào tới dải đó. `Connection reset` khác refused: kết nối đã mở rồi bị bên kia (hoặc thiết bị ở giữa, như NAT hay LB hết idle timeout) gửi RST. Mỗi client báo timeout một kiểu: `java.net.Socket` ném `SocketTimeoutException: Connect timed out`, `java.net.http.HttpClient` ném `HttpConnectTimeoutException`, driver JDBC và Netty bọc lại bằng thông điệp riêng, nên đọc cả `cause`.
- **Cùng subnet thì nói chuyện thế nào**: máy hỏi bằng ARP "ai giữ IP 10.0.1.40?" để lấy địa chỉ MAC rồi gửi frame Ethernet thẳng tới đó. Khác subnet thì gửi frame tới MAC của default gateway, gateway đọc IP đích và chuyển tiếp. `ping` dùng ICMP, nên ping không được chưa chắc là port đóng (nhiều nơi chặn ICMP), và ping được chưa chắc là port mở; `traceroute` cho thấy gói dừng ở chặng nào. TCP và UDP khác nhau ở tầng 4: TCP có kết nối, đảm bảo thứ tự và gửi lại gói mất; UDP gửi từng gói rời (DNS, QUIC dùng nó). Chi tiết ở bài TCP chuyên sâu.
- **Stateful và stateless firewall**: security group của AWS là stateful, cho chiều vào thì response tự được đi ra. Network ACL là stateless, phải mở cả chiều về cho dải ephemeral port. Linux mặc định cấp ephemeral port trong `32768–60999` (`net.ipv4.ip_local_port_range`), Windows và IANA dùng `49152–65535`.
- **NAT có giới hạn kết nối**: NAT phải dùng port nguồn của chính nó cho mỗi kết nối. AWS NAT gateway giữ tối đa 55.000 kết nối đồng thời tới mỗi đích duy nhất (IP, port, giao thức); vượt thì có lỗi `ErrorPortAllocation`. Service gọi một API ngoài với rất nhiều kết nối ngắn sẽ chạm trần này; dùng connection pool và [[keep-alive]], hoặc thêm IP cho NAT. Trên node Kubernetes, kube-proxy cũng NAT qua [[conntrack]], xem bài Điều tra API chậm.
- **[[mtu|MTU]]**: Ethernet mặc định 1.500 byte mỗi frame, AWS trong VPC cho 9.001 (jumbo frame). Qua VPN hay tunnel, header thêm vào làm gói vượt MTU; nếu ICMP "fragmentation needed" bị chặn, handshake nhỏ chạy được nhưng response lớn bị treo. Triệu chứng kinh điển: `curl` trang nhỏ được, tải file lớn thì treo.
- **IPv6** dùng 128 bit, không cần NAT để tiết kiệm địa chỉ, subnet thường là `/64`. Java xử lý IPv6 trong suốt, nhưng `java.net.preferIPv6Addresses` và thứ tự bản ghi AAAA/A ảnh hưởng tới việc kết nối thử địa chỉ nào trước.
- Bài liên quan: đường đi đầy đủ của một request qua DNS, TCP, TLS và load balancer ở bài HTTP request đi qua những gì; handshake, `TIME_WAIT` và backlog ở bài TCP chuyên sâu; subnet public/private, PrivateLink và Transit Gateway ở bài Network trên cloud.
