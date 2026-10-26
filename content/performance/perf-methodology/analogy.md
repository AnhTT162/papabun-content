Quán phở buổi sáng. Một tô ra mất bao lâu là [[latency]]; một giờ bán được bao nhiêu tô là [[throughput]]. Hai con số này khác nhau: thuê thêm người bưng thì một giờ bán được nhiều tô hơn, nhưng mỗi tô vẫn phải chờ chần bánh và chan nước như cũ.

Chủ quán nói "khách chờ trung bình 4 phút". Nghe ổn, nhưng cứ trăm khách lại có một người chờ 25 phút vì bếp làm nhầm đơn, và người đó không quay lại. Con số trung bình giấu mất họ; [[percentile|p99]] thì không.

Quán chỉ có một nồi nước dùng, mỗi lần chan được một tô. Thuê thêm năm người thái thịt thì khâu thái nhanh hơn, nhưng mọi tô vẫn xếp hàng ở nồi nước. Khâu tuần tự đó quyết định quán nhanh được tới đâu. Và khi nồi nước đã bận 90% thời gian, chỉ cần khách đông thêm một chút là hàng chờ dài ra rất nhanh.

Muốn biết quán chậm ở đâu, chủ quán đi từng khâu: bếp, nồi nước, bàn, quầy thu tiền. Khâu nào cũng xem ba thứ: đang bận bao nhiêu, có ai đang phải chờ, có làm hỏng đơn nào không. Đó là [[use-method|USE method]]. Nhìn từ phía khách (bao nhiêu đơn, bao nhiêu đơn sai, chờ bao lâu) là [[red-method|RED method]]. Chuyện nồi nước là [[amdahls-law|Amdahl's law]], còn quan hệ giữa số khách đang chờ, tốc độ khách tới và thời gian chờ là [[littles-law|Little's law]].
