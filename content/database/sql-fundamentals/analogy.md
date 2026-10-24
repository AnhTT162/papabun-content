Bếp trưởng nhận một phiếu: "các món chay, nhóm theo loại, chỉ lấy loại có từ 3 món trở lên, ghi tên và giá, xếp theo giá". Phiếu viết theo thứ tự đó, nhưng bếp **làm** theo thứ tự khác:
1. Lấy cả kho nguyên liệu ra.
2. Bỏ những món không chay.
3. Chia vào từng khay theo loại.
4. Bỏ các khay có ít hơn 3 món.
5. Ghi tên và giá lên đĩa.
6. Xếp đĩa theo giá.

Hiểu thứ tự làm của bếp thì hiểu được vì sao bước 2 không thể dùng "giá sau giảm" (lúc đó chưa ai tính), còn bước 6 thì dùng được.

Có một chi tiết nữa: món ghi giá "chưa biết" không đắt hơn, không rẻ hơn, cũng không bằng món nào. Hỏi "món này có đúng 50 nghìn không?" thì câu trả lời là "chưa biết", không phải "không".

SQL cũng vậy. Câu `SELECT` có [[logical-query-order|thứ tự xử lý logic]] khác với thứ tự viết, và `NULL` tuân theo [[three-valued-logic|logic ba giá trị]]: so sánh với `NULL` ra `UNKNOWN`, không ra `TRUE` hay `FALSE`.
