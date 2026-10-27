## Quick

[[big-o|Big-O]] mô tả thời gian (hoặc bộ nhớ) tăng thế nào khi dữ liệu tăng, bỏ qua hằng số. Mỗi cấu trúc dữ liệu làm nhanh một số thao tác và trả giá ở thao tác khác: mảng đọc theo vị trí O(1), [[hash-table|hash table]] tra theo key O(1) trung bình, cây cân bằng giữ thứ tự với O(log n), [[binary-heap|heap]] lấy phần tử nhỏ nhất O(log n). **Chọn cấu trúc theo thao tác chạy nhiều nhất, rồi mới tính tới hằng số và bộ nhớ.**

## Interview

**Đọc Big-O**: O(1) không phụ thuộc n, O(log n) mỗi bước bỏ một nửa (1 triệu phần tử chỉ khoảng 20 bước), O(n) duyệt hết, O(n log n) là sắp xếp tốt, O(n²) là hai vòng lặp lồng nhau (1 triệu phần tử thành 10^12 bước). Cần nói rõ đang nói trường hợp xấu nhất, trung bình hay [[amortized-complexity|khấu hao]].

**Các cấu trúc chính**:
- **Mảng**: các phần tử nằm liền nhau, đọc theo chỉ số O(1), chèn giữa O(n). Mảng động (`ArrayList`) tăng 1,5 lần khi đầy nên thêm vào cuối là O(1) khấu hao.
- **Linked list**: chèn hay xoá khi đã cầm node là O(1), nhưng tìm phần tử thứ i là O(n), và nhảy theo con trỏ không tận dụng được cache.
- **Hash table**: hàm hash biến key thành vị trí trong mảng bucket. Trung bình O(1); [[hash-collision|va chạm]] nhiều thì xấu dần tới O(n), nên bảng resize khi số phần tử vượt [[load-factor|load factor]] (0,75 ở `HashMap`).
- **Cây tìm kiếm cân bằng** ([[red-black-tree|cây đỏ-đen]]): mọi thao tác O(log n) và duyệt được theo thứ tự, tìm theo khoảng.
- **[[b-tree|B-tree]]**: cây rất thấp, mỗi node là một page chứa hàng trăm key, nên database chỉ đọc 3–4 page để tìm trong hàng chục triệu dòng.
- **Heap**: luôn biết phần tử nhỏ nhất, thêm và lấy ra O(log n); dùng cho hàng đợi ưu tiên, lịch hẹn giờ, top-k.
- **[[graph|Graph]]**: node và cạnh; BFS tìm đường ít bước nhất, DFS phát hiện vòng, [[topological-sort|sắp xếp topo]] tìm thứ tự khởi động theo phụ thuộc.

**Bẫy hay gặp**: O(1) không có nghĩa là nhanh hơn O(log n) ở mọi kích thước, và O(n²) ẩn trong `contains` của list trong vòng lặp là lỗi hiệu năng phổ biến nhất trong code nghiệp vụ.

**Cách làm đúng**: xác định thao tác nóng (tra key, duyệt theo thứ tự, lấy min, đi theo quan hệ), chọn cấu trúc tương ứng, đo bằng dữ liệu cỡ production.

## Deep

- **Big-O bỏ hằng số, máy thật thì không**: mảng phẳng duyệt tuần tự được prefetch ([[cache-locality]]), linked list mỗi bước có thể trượt cache, nên `ArrayList` thường thắng `LinkedList` kể cả khi chèn giữa (số đo ở bài CPU, bộ nhớ & các con số latency). Với n nhỏ (vài chục), tìm tuyến tính trong mảng thường nhanh hơn hash table vì không phải tính hash.
- **Khấu hao không phải trung bình**: `ArrayList.add` O(1) khấu hao nghĩa là tổng n lần thêm là O(n), dù đúng lần resize tốn O(n). Hệ thống nhạy latency vẫn thấy cú resize đó; biết trước kích thước thì đặt sẵn capacity. Hash table resize cũng vậy: một lần `put` có thể chép lại toàn bộ bảng.
- **Hash table có hai cách xử lý va chạm**: chaining (mỗi bucket là danh sách, Java `HashMap` đổi sang cây đỏ-đen khi bucket dài, xem bài HashMap Internals) và open addressing (dò sang ô kế tiếp trong cùng mảng, thân thiện với cache, dùng trong `IdentityHashMap`, Python `dict`). Kẻ tấn công gửi nhiều key cùng hash làm bảng thoái hoá thành O(n) mỗi lần tra (hash flooding); cách chống là hash có khoá bí mật như SipHash, hoặc chuyển bucket dài thành cây như Java làm (chỉ giữ được O(log n) khi key là `Comparable`).
- **Hash table mất thứ tự và không tìm theo khoảng**: "đơn hàng từ 10h tới 11h" hay "giá gần 500.000 nhất" cần cây (`TreeMap.subMap`, `floorKey`) hoặc B-tree index. Đó là lý do index mặc định của database là B-tree chứ không phải hash.
- **[[binary-search-tree|Cây nhị phân tìm kiếm]] không cân bằng thoái hoá**: chèn key đã sắp xếp (id tăng dần) tạo ra một đường thẳng, mọi thao tác thành O(n). Cây đỏ-đen và AVL tự xoay để chiều cao luôn O(log n); AVL cân bằng chặt hơn nên tra nhanh hơn chút, đổi lại ghi tốn hơn.
- **Vì sao B-tree thấp**: với page 8 KB và key 8 byte cộng con trỏ, một node chứa vài trăm key (fan-out cao). Ba tầng × fan-out 400 là 64 triệu key. Cây nhị phân cho cùng số key cao khoảng 26 tầng, mỗi tầng một lần đọc đĩa. Database tối ưu theo số page phải đọc, không theo số phép so sánh. Chi tiết ở bài Index & Execution Plan.
- **Heap là mảng**: node ở vị trí i có con ở 2i+1 và 2i+2, nên không cần con trỏ. Duyệt hay `toString()` một heap không ra thứ tự đã sắp; chỉ lấy ra lần lượt mới đúng thứ tự. Xây heap từ n phần tử có sẵn là O(n), không phải O(n log n). Top-k dùng min-heap cỡ k: O(n log k) thời gian, O(k) bộ nhớ.
- **Stack và queue**: stack (LIFO) cho undo, duyệt DFS, gọi hàm lồng nhau; queue (FIFO) cho BFS, xử lý theo thứ tự đến. Trong Java dùng `ArrayDeque` cho cả hai. DFS viết đệ quy trên cây hay graph sâu hàng chục nghìn tầng gây `StackOverflowError`; chuyển sang vòng lặp với stack tường minh.
- **Graph trong production**: biểu diễn bằng danh sách kề (mỗi node giữ danh sách hàng xóm, O(V + E) bộ nhớ) cho graph thưa như quan hệ gọi giữa service; ma trận kề (O(V²)) chỉ hợp graph dày, nhỏ. Sắp xếp topo cho thứ tự build module Maven, thứ tự migration, thứ tự tạo bean; không sắp được nghĩa là có vòng, như lỗi circular dependency của Spring hay Maven.
- **Bộ nhớ cũng là chi phí**: trong Java, mỗi entry của `HashMap` là một object riêng, key và value còn là hai object `Long` đã boxing, cộng mảng bucket. Đo trên JDK 27: `HashMap<Long, Long>` một triệu phần tử chiếm khoảng 68 MB heap, hai mảng `long[]` cùng dữ liệu chỉ 16 MB. Dữ liệu lớn và chỉ đọc thì mảng đã sắp xếp cộng tìm nhị phân (`Arrays.binarySearch`) vừa gọn vừa nhanh.
- **Chọn theo thao tác**: tra theo key → hash table; tra theo key và cần thứ tự hay khoảng → cây cân bằng hoặc B-tree; lấy min/max liên tục → heap; thêm/lấy hai đầu → deque; kiểm tra "có thể đã thấy" với bộ nhớ rất ít → [[bloom-filter|Bloom filter]]. Cấu trúc dành cho hệ thống lớn (skip list, LSM tree, HyperLogLog, trie) ở bài Cấu trúc dữ liệu trong hệ thống lớn; cài đặt cụ thể trong Java ở bài Collections Overview.
