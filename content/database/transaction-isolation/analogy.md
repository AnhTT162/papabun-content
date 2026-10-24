Hai kế toán cùng cập nhật số tồn kho của một mặt hàng trên một cuốn sổ chung. Mỗi người chép số hiện tại (100) ra giấy nháp, trừ số hàng mình vừa bán, rồi ghi đè kết quả vào sổ. Người thứ nhất ghi 70, người thứ hai ghi 80. Sổ còn 80, trong khi thực tế chỉ còn 50: một lần bán đã biến mất.

Muốn tránh, phải có luật dùng sổ. Có thể "ai cầm sổ thì người kia phải chờ" (khoá trước khi đọc). Có thể "ghi đè thì phải kiểm tra số trong sổ chưa đổi so với lúc chép, đổi rồi thì làm lại" (kiểm tra phiên bản). Hoặc đơn giản là ghi "trừ 30" thay vì ghi một con số cụ thể. Luật càng chặt thì càng an toàn, nhưng càng nhiều người phải chờ.

Trong database, mỗi kế toán là một [[transaction]], lỗi trên là [[lost-update|lost update]], còn bộ luật về việc một transaction được thấy công việc dở dang của transaction khác tới đâu chính là [[isolation-level|isolation level]].
