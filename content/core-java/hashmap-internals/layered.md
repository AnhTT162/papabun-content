## Quick

`HashMap` là một mảng [[bucket]]: key được trộn bit bằng `h ^ (h >>> 16)`, chọn ô bằng `(n - 1) & hash`, trùng ô thì nối vào chuỗi. **Khi `size` vượt `capacity × 0.75` thì bảng gấp đôi; một bucket dài quá 8 node chỉ thành cây khi capacity đã ≥ 64, nếu chưa thì bảng resize.**

## Interview

`HashMap` (Java 8+) giữ một mảng `Node[] table`, độ dài luôn là lũy thừa của 2, mặc định 16 và chỉ được tạo ở lần `put` đầu tiên.

**Put một key**:
1. Tính `hash = h ^ (h >>> 16)` với `h = key.hashCode()`. Bước [[hash-spreading|hash spreading]] này kéo 16 bit cao xuống trộn với 16 bit thấp, vì bước sau chỉ dùng vài bit thấp.
2. Chọn bucket: `index = (n - 1) & hash`. Với `n` là lũy thừa của 2, phép `&` cho cùng kết quả như lấy dư không âm `hash mod n` nhưng rẻ hơn.
3. Bucket trống thì đặt node mới. Có node rồi thì duyệt chuỗi: so `hash` trước, rồi `==` hoặc `equals`. Trùng key thì thay value, không thì nối node mới vào cuối ([[separate-chaining|separate chaining]]).
4. Sau khi thêm, `++size > threshold` thì [[rehash|resize]]. `threshold = capacity × loadFactor`, [[load-factor|load factor]] mặc định 0.75.

**Resize** gấp đôi bảng. Java 8 không băm lại từng key: mỗi node chỉ cần xem bit `hash & oldCap`. Bằng 0 thì ở nguyên index `j` (danh sách lo), khác 0 thì sang `j + oldCap` (danh sách hi), giữ nguyên thứ tự trong chuỗi.

**[[treeify|Treeify]]**: khi một bucket có hơn 8 node (`TREEIFY_THRESHOLD = 8`) và capacity ≥ 64 (`MIN_TREEIFY_CAPACITY`), chuỗi được đổi thành [[red-black-tree|cây đỏ-đen]], lookup từ O(n) xuống O(log n). Capacity còn nhỏ thì resize thay vì treeify. Khi resize tách cây, nửa nào còn ≤ 6 node (`UNTREEIFY_THRESHOLD`) thì trở lại danh sách.

**Key `null`** có hash 0 nên luôn nằm ở bucket 0; chỉ có một key `null`.

Bẫy hay gặp: dùng key mutable rồi sửa sau khi `put`, và dùng `HashMap` chung giữa nhiều thread. `HashMap` **không thread-safe**: hai `put` đồng thời có thể ghi đè lên nhau, `size` sai, resize song song làm hỏng cấu trúc. Cần map dùng chung thì dùng `ConcurrentHashMap`.

## Deep

- **Capacity luôn là lũy thừa của 2**: `new HashMap<>(10)` làm tròn lên 16 (`tableSizeFor`), resize lần đầu khi có entry thứ 13. Nhờ đó `(n - 1) & hash` thay được `%`, và lúc resize chỉ cần đúng một bit `hash & oldCap` để tách lo/hi. Đổi lại, index chỉ dùng bit thấp, nên mới cần hash spreading.
- **Biết trước số phần tử thì đặt sẵn kích thước**: `new HashMap<>(1000)` vẫn resize khi vượt 768 phần tử. Java 19+ có `HashMap.newHashMap(1000)` tự tính capacity theo load factor 0.75.
- **Node lưu sẵn `hash`** của key lúc `put`. Lookup so `hash` trước rồi mới gọi `equals`. Sửa field tham gia `hashCode` sau khi `put` thì entry nằm sai bucket và có `hash` cũ: `get` bằng key cũ hay key mới đều trả về `null`.
- **Thứ tự treeify thật**: bắt đầu từ `HashMap(8)`, put 16 key cùng hashCode (`AaAaAaAa`, `AaAaAaBB`...): key thứ 7 resize vì vượt threshold 6, key thứ 9 và 10 làm chuỗi dài quá 8 nhưng capacity mới 16 rồi 32 nên lại resize, tới key thứ 11 (capacity 64) bucket mới thành `TreeNode`.
- **Cây sắp xếp theo gì**: theo `hash`, cùng hash thì dùng `compareTo` nếu key là `Comparable` cùng class (String được), không thì phân định bằng `System.identityHashCode`. Key không `Comparable` mà trùng hash nhiều vẫn có thể chậm. Tree bin có từ JEP 180 (Java 8) để chống tấn công dồn key trùng hash.
- **Untreeify**: lúc resize, nửa nào ≤ 6 node thì trở lại danh sách. Lúc `remove`, cây chỉ trở lại danh sách khi đã rất nhỏ (gốc hoặc nhánh con rỗng), không đếm đúng 6.
- **Key `null` và value `null`**: `hash(null) = 0` nên vào bucket 0. Value `null` hợp lệ, nên `get` trả về `null` không phân biệt được "không có key" và "value là null"; dùng `containsKey`. `ConcurrentHashMap` từ chối cả key và value `null`.
- **Thứ tự duyệt** theo index bucket rồi thứ tự trong chuỗi, và đổi sau mỗi lần resize. Cần thứ tự chèn thì dùng `LinkedHashMap`.
- **Iterator [[fail-fast]]**: sửa cấu trúc map trong lúc duyệt (không qua `iterator.remove()`) làm tăng `modCount`, lần `next()` sau ném `ConcurrentModificationException`. Đây chỉ là cơ chế "cố gắng phát hiện", không phải đảm bảo an toàn đa luồng.
- **Không thread-safe**: hai thread cùng `put` vào một bucket trống có thể cùng thấy `null` và một entry bị mất; `++size` không atomic. Java 7 chèn đầu chuỗi khi resize nên resize song song có thể tạo vòng lặp vô hạn; Java 8 chèn cuối và giữ thứ tự nên tránh được lỗi đó, nhưng vẫn mất dữ liệu. `ConcurrentHashMap` dùng CAS cho bucket trống và `synchronized` trên node đầu bucket; `Collections.synchronizedMap` khoá cả map.
