## Quick

`hash(key) % N` chuyển **gần hết key** sang node khác mỗi khi N đổi. [[consistent-hashing|Consistent hashing]] đặt node và key lên cùng một **vòng hash**; key thuộc node gặp đầu tiên theo chiều kim đồng hồ, nên thêm hay bớt một node chỉ chuyển **khoảng 1/N** số key. Mỗi node cần **nhiều [[virtual-node|virtual node]]** để tải đều, và hệ lưu trữ ghi mỗi key lên **N bản sao** liền nhau trên vòng, đọc ghi theo [[quorum|quorum]] (R, W).

## Interview

**Vì sao không dùng modulo**: 4 node lên 5 node, key chỉ đứng yên khi `h % 4 == h % 5`. Đo thật với 100.000 key: **80%** key phải chuyển. Với cache, đó là cache miss hàng loạt dồn xuống database; với kho dữ liệu, là chuyển gần hết dữ liệu qua mạng.

**Vòng hash**: không gian hash (ví dụ 0 tới 2^64) uốn thành vòng. Mỗi node được hash ra một điểm. Key thuộc điểm node đầu tiên ≥ hash của key, quá cuối vòng thì quay về đầu. Thêm node E chỉ lấy đoạn vòng ngay trước điểm của E; các key khác không đổi chủ. Đo thật: 4 lên 5 node, **khoảng 20%** key chuyển, đúng bằng phần của node mới.

**Virtual node**: một điểm cho mỗi node thì các đoạn dài ngắn ngẫu nhiên. Đo thật với 4 node: một node nhận 55% key, node khác 1,3%. Cho mỗi node 100 điểm (`A#0` tới `A#99`): mỗi node 24–26%. Thêm node mới thì nó lấy một ít từ **mọi** node, không dồn lên một node láng giềng. Node mạnh hơn được nhiều điểm hơn.

**Bản sao và quorum**: hệ kiểu Dynamo (Cassandra, Riak) ghi key lên N node phân biệt kế tiếp trên vòng (bỏ qua virtual node của cùng một máy, và rải qua rack). Ghi chờ W xác nhận, đọc hỏi R bản; `R + W > N` thì tập đọc luôn giao tập ghi. N = 3, W = 2, R = 2 chịu được một node chết mà vẫn đọc thấy lần ghi đã thành công.

**Bẫy hay gặp**:
- [[hot-key|Key nóng]]: phân phối đều theo **số key**, không đều theo **lưu lượng**. Một key nóng vẫn dồn vào một node.
- Hàm hash khác nhau giữa các client (mỗi thư viện một kiểu) làm cùng key đi về hai node.
- Thêm node lúc đang quá tải: chuyển dữ liệu tốn thêm I/O đúng lúc hệ thống yếu nhất.

## Deep

- **Code tối giản** (Java 21, đã chạy thử với hash là 8 byte đầu của MD5):
  ```java
  private final TreeMap<Long, String> ring = new TreeMap<>();

  void add(String node) {
      for (int i = 0; i < vnodes; i++) ring.put(hash(node + "#" + i), node);
  }

  String nodeFor(String key) {
      var e = ring.ceilingEntry(hash(key));                  // điểm đầu tiên theo chiều kim đồng hồ
      return (e != null ? e : ring.firstEntry()).getValue(); // quá điểm cuối thì vòng về đầu
  }
  ```
  Thêm node chỉ `put` thêm điểm, không đụng điểm cũ. Tra cứu O(log(số node × số virtual node)). Với 100.000 key, 4 lên 5 node: 17,3% key chuyển khi mỗi node một điểm, 19,6% khi mỗi node 100 điểm, so với 80,0% của modulo.
- **Chọn số virtual node**: nhiều điểm thì tải đều hơn nhưng bảng định tuyến lớn hơn và việc chuyển dữ liệu chia thành nhiều đoạn nhỏ. Cassandra 4.0 hạ `num_tokens` mặc định từ 256 xuống 16, kèm thuật toán cấp token theo replication factor (`allocate_tokens_for_local_replication_factor`) thay cho cấp ngẫu nhiên, để vẫn đều mà ít đoạn hơn.
- **Slot cố định là phương án khác**: Redis Cluster chia key vào 16.384 [[hash-slot|hash slot]] (`CRC16(key) % 16384`) rồi gán slot cho node; thêm node là chuyển một số slot. Không phải vòng, nhưng cùng ý: số phần cố định, chỉ đổi chủ của phần. Kafka thì ngược lại: `murmur2(key) % số partition`, tăng partition làm đổi partition của key và phá thứ tự theo key.
- **[[rendezvous-hashing|Rendezvous hashing]]** (highest random weight): tính `hash(key, node)` cho mọi node, chọn node điểm cao nhất. Không cần virtual node, tải đều, bỏ một node chỉ chuyển key của node đó; đổi lại tra cứu O(N), hợp khi số node nhỏ.
- **Jump consistent hash** (Google, 2014): không cần bộ nhớ, rất nhanh, phân phối đều; nhưng node được đánh số 0..N-1 và chỉ thêm, bớt ở cuối. Hợp cho shard của kho dữ liệu, không hợp cho cache server có thể chết bất kỳ.
- **Maglev và ring hash trong load balancer**: Envoy có `RING_HASH` và `MAGLEV` để giữ cùng một key (header, cookie) về cùng backend khi pool thay đổi (bài Load balancing).
- **Bounded load**: consistent hashing with bounded loads đặt trần cho mỗi node (ví dụ 1,25 lần trung bình); node đã đầy thì key đi tiếp sang node kế. HAProxy có `hash-balance-factor` cho việc này. Giảm hot spot, đổi lại một key có thể đổi node khi tải thay đổi.
- **Key nóng**: tách key (`counter:42#0..7` rồi cộng khi đọc), cache cục bộ ngắn hạn ở client, hoặc nhân bản key đọc nhiều lên nhiều node. Đo bằng phân phối request theo key, không chỉ theo node.
- **Rebalance an toàn**: node mới nhận dữ liệu (streaming) trước, chỉ nhận lưu lượng khi đã đủ; trong lúc chuyển, ghi vào cả chủ cũ và chủ mới hoặc chuyển tiếp yêu cầu. Giới hạn băng thông streaming (Cassandra `nodetool setstreamthroughput`; trong `cassandra.yaml` là `stream_throughput_outbound` từ 4.1, `stream_throughput_outbound_megabits_per_sec` ở 4.0) để không bóp nghẹt lưu lượng thật.
- **Node chết tạm thời**: bài báo Dynamo và Riak dùng [[sloppy-quorum|sloppy quorum]]: ghi tạm lên node kế tiếp ngoài N node chuẩn và **tính nó vào W**, kèm gợi ý "trả lại cho C" ([[hinted-handoff|hinted handoff]]); C quay lại thì nhận dữ liệu bù. Ghi vẫn thành công nhưng `R + W > N` không còn bảo đảm đọc thấy nó. Cassandra có hinted handoff nhưng quorum chặt: hint không được tính vào mức nhất quán (trừ mức `ANY`), thiếu bản sao thật thì lần ghi `QUORUM` báo lỗi.
- **Vì sao token ngẫu nhiên lùi dần**: cấp điểm ngẫu nhiên cần rất nhiều virtual node mới đều, làm repair và streaming chia vụn. Các hệ mới chia không gian hash thành phần đều cố định (Riak chia vòng thành số partition cố định, Redis Cluster 16.384 slot, Cassandra 4.0 cấp token có tính toán) rồi chỉ đổi chủ của phần.
- **Sửa bản sao lệch**: [[read-repair|read repair]] (lần đọc thấy bản sao cũ thì ghi bản mới đè lên) và [[anti-entropy|anti-entropy]] định kỳ so cây [[merkle-tree|Merkle]] giữa các bản sao để chỉ chuyển phần khác (Cassandra `nodetool repair`). Không chạy repair trong khoảng `gc_grace_seconds` thì dữ liệu đã xoá có thể sống lại.
- **Quorum không phải linearizable**: ghi lỗi vì thiếu W nhưng đã nằm trên một bản sao vẫn có thể bị đọc thấy, và hai lần đọc liên tiếp có thể thấy mới rồi cũ (bài Consistency, CAP & PACELC).
- **Client hay server định tuyến**: client biết vòng (driver Cassandra token-aware, Jedis Cluster) thì gọi thẳng node chủ, đỡ một bước nhảy; nhưng mọi client phải cập nhật bản đồ khi vòng đổi. Proxy định tuyến (Twemproxy, Envoy) giấu việc đó, đổi lại thêm một bước mạng.
