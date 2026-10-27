## Quick

Phần lớn bài coding khi phỏng vấn rơi vào vài mẫu: [[two-pointers|hai con trỏ]], [[sliding-window-technique|sliding window]], [[binary-search|binary search]], [[bfs|BFS]]/[[dfs|DFS]] trên đồ thị hay lưới, và [[dynamic-programming|quy hoạch động]]. Mỗi mẫu biến lời giải vét cạn [[big-o|O(n²)]] hay O(2ⁿ) thành O(n), O(n log n) nhờ khai thác một tính chất của đề (đã sắp xếp, đơn điệu, bài toán con lặp lại). **Nhận ra tính chất đó là phần chính; rồi nói rõ độ phức tạp và thử các ca biên (rỗng, một phần tử, trùng, số âm, tràn số) trước khi nói "xong".**

## Interview

**Cách làm một bài**: hỏi lại ràng buộc (n tối đa, số âm, trùng, đã sắp xếp chưa), nói lời giải vét cạn, tìm tính chất để tối ưu, viết code, chạy tay với ca biên. Ràng buộc gợi ý độ phức tạp: n tới 10⁵ thì O(n²) là 10¹⁰ phép tính, quá chậm; cần O(n log n) hoặc O(n).

**Năm mẫu chính**:
- **Hai con trỏ**: mảng đã sắp xếp, tìm cặp có tổng bằng k: một con trỏ đầu, một con trỏ cuối, tổng nhỏ thì dịch trái lên, lớn thì dịch phải xuống. O(n) thay vì O(n²).
- **Sliding window**: mảng con hay chuỗi con liên tiếp thoả điều kiện (chuỗi con dài nhất không lặp ký tự). Mở rộng bên phải, co bên trái khi vi phạm; mỗi phần tử vào ra một lần, O(n).
- **Binary search**: không chỉ tìm trong mảng mà trên **mọi điều kiện đơn điệu**: "tải trọng nhỏ nhất để giao hết hàng trong 5 ngày". Nếu x làm được thì mọi giá trị lớn hơn cũng làm được, nên tìm ranh giới trong O(log khoảng giá trị).
- **BFS và DFS**: BFS đi theo từng lớp nên tìm đường ít bước nhất trên đồ thị không trọng số; DFS đi sâu, hợp cho tìm vùng liên thông, phát hiện vòng, duyệt mọi tổ hợp ([[backtracking]]). Có trọng số thì Dijkstra.
- **Quy hoạch động**: bài toán con trùng nhau (Fibonacci, đổi tiền, chuỗi con chung dài nhất). Định nghĩa trạng thái, công thức chuyển, ca cơ sở; cài bằng [[memoization]] (đệ quy có cache) hoặc bảng từ dưới lên.

**Bẫy hay gặp**: `(lo + hi) / 2` tràn `int`; sliding window áp cho mảng có số âm; BFS đánh dấu đã thăm khi lấy ra thay vì khi đưa vào; DFS đệ quy sâu gây `StackOverflowError`; quên tràn số khi cộng dồn (dùng `long`).

**Cách làm đúng**: nói ra mẫu mình chọn và tính chất nào của đề cho phép dùng nó; người phỏng vấn chấm cách suy nghĩ nhiều hơn code.

## Deep

- **Tràn số trong binary search**: `int mid = (lo + hi) / 2` với `lo = 1050000001`, `hi = 2100000000` ra `-572483647` (đã chạy trên JDK 27); dùng `lo + (hi - lo) / 2` hoặc `(lo + hi) >>> 1`, cả hai ra `1575000000`. Chính `Arrays.binarySearch` của JDK có lỗi này tới Java 5, sửa từ Java 6 (JDK-5045582), nay dùng `>>> 1`. `Arrays.binarySearch` không tìm thấy thì trả `-(điểm chèn) - 1`, ví dụ tìm 4 trong `{1, 3, 5, 7}` ra `-3`, không phải `-1`.
- **Ba dạng binary search**: tìm đúng giá trị, tìm vị trí đầu tiên thoả (lower bound), tìm vị trí cuối cùng thoả. Lỗi hay gặp là vòng lặp không thu hẹp (`lo = mid` khi `mid` làm tròn xuống thì kẹt khi `hi = lo + 1`). Giữ một quy ước: khoảng `[lo, hi)` hoặc `[lo, hi]`, và kiểm tra bằng mảng 1 và 2 phần tử.
- **Sliding window cần tính đơn điệu**: co cửa sổ chỉ đúng khi bỏ phần tử bên trái làm tổng giảm, tức mọi số không âm. "Mảng con ngắn nhất có tổng ≥ k" với `{1, -1, 5}`, `k = 5`: cửa sổ trả 3, đáp án đúng là 1 (chỉ `{5}`). Có số âm thì dùng [[prefix-sum|prefix sum]] với hash map (đếm mảng con có tổng bằng k) hoặc deque đơn điệu.
- **Hai con trỏ cần mảng đã sắp xếp**: sắp xếp trước tốn O(n log n) và làm mất chỉ số gốc. Đề yêu cầu trả chỉ số (two sum) thì hash map một lượt O(n) tốt hơn.
- **BFS đánh dấu khi đưa vào hàng đợi**: đánh dấu khi lấy ra thì một ô bị đưa vào nhiều lần từ các ô kề; trên lưới 12×12 (144 ô), số lần đưa vào queue là 265 so với 144 (đã chạy). Lưới lớn hay đồ thị dày, khác biệt thành hết bộ nhớ. Dùng `ArrayDeque` cho queue và stack, không dùng `Stack` (đồng bộ, kế thừa `Vector`) hay `LinkedList`.
- **Độ sâu đệ quy**: DFS đệ quy trên chuỗi 100.000 node (cây danh mục bị nhập sai thành chuỗi, comment trả lời lồng nhau) ném `StackOverflowError` ở khoảng 20.000 tầng trên JDK 27 macOS ARM với stack mặc định 2 MB (Linux x64 mặc định 1 MB); với `-Xss8m` vẫn chỉ tới khoảng 85.000 (đã chạy). Độ sâu đổi theo kích thước frame và JIT, đừng dựa vào nó. Dữ liệu sâu không kiểm soát được thì viết DFS bằng `ArrayDeque` làm stack.
- **Memoization so với bảng**: Fibonacci đệ quy thuần với n = 40 gọi hàm 331.160.281 lần (đã đếm); có cache thì chỉ tính 39 giá trị (từ 2 tới 40), mỗi giá trị một lần. Memoization dễ viết từ công thức đệ quy nhưng tốn stack và hash map; bảng từ dưới lên không đệ quy, và thường chỉ cần giữ một hai hàng trước nên bộ nhớ từ O(n²) xuống O(n). Khoá của memo bằng `HashMap<List<Integer>, ...>` rất chậm; mã hoá trạng thái thành một `long` hay chỉ số mảng.
- **Tràn số và chia lấy dư**: đếm số cách thường vượt `long`, đề yêu cầu mod `1_000_000_007`; lấy mod sau mỗi phép cộng. Trong Java `-7 % 3` là `-1`, dùng `Math.floorMod(-7, 3)` ra `2` khi cần chỉ số không âm (vòng tròn, bucket). `Math.abs(Integer.MIN_VALUE)` vẫn là `-2147483648`.
- **Heap, top-k, sắp xếp topo**: đã ở bài Cấu trúc dữ liệu cơ bản & Big-O; đề "k phần tử lớn nhất" là min-heap cỡ k, đề "thứ tự build theo phụ thuộc" là [[topological-sort|sắp xếp topo]] (Kahn: BFS từ các node bậc vào 0, còn node chưa xử lý là có vòng).
- **Greedy**: chọn tốt nhất tại mỗi bước (xếp lịch họp theo giờ kết thúc sớm nhất). Nhanh và gọn, nhưng chỉ đúng khi chứng minh được; đổi tiền với mệnh giá {1, 3, 4} và số 6, greedy chọn 4+1+1 (3 đồng), đúng là 3+3 (2 đồng), nên phải dùng DP.
- **Khi người phỏng vấn hỏi tiếp**: "dữ liệu không vừa bộ nhớ thì sao" (sắp xếp ngoài, chia theo hash ra nhiều file rồi xử lý từng phần), "chạy trên nhiều máy" (map-reduce), "luồng dữ liệu vô hạn" (cửa sổ theo thời gian, cấu trúc xác suất ở bài Cấu trúc dữ liệu trong hệ thống lớn). Đây là chỗ bài thuật toán nối sang system design.
