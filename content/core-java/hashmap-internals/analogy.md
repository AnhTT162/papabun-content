Chung cư mới có một dãy **8 hộp thư**. Ban quản lý không xếp thư theo tên: họ lấy mã căn hộ, **trộn mấy chữ số đầu vào mấy chữ số cuối** rồi chỉ nhìn phần đuôi để biết thư vào hộp số mấy. Trộn trước là để các căn có mã giống nhau ở phần đuôi không dồn hết vào một hộp.

Hai căn khác nhau vẫn có thể rơi vào cùng một hộp. Khi đó thư được **xếp nối đuôi nhau**, và người lấy thư phải lật từng lá, so đúng tên căn hộ mới lấy.

Khi số thư vượt **3/4 số hộp**, ban quản lý lắp dãy mới gấp đôi. Thư trong mỗi hộp cũ chỉ đi tới một trong hai chỗ: **giữ nguyên số hộp**, hoặc sang hộp **số cũ + 8**. Hộp nào dày quá 8 lá mà dãy đã đủ lớn thì được thay bằng ngăn có chia mục theo thứ tự để tìm nhanh hơn.

Trong `HashMap`, bước trộn mã là [[hash-spreading|hash spreading]], hộp thư là [[bucket]], thư nối đuôi là [[separate-chaining|separate chaining]], ngưỡng 3/4 là [[load-factor|load factor]], lắp dãy gấp đôi là [[rehash|resize]], còn ngăn chia mục là [[treeify]] thành [[red-black-tree|cây đỏ-đen]].
