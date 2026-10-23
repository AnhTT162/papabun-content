Hãy tưởng tượng tủ gửi đồ ở siêu thị có 16 ngăn. Nhân viên không lục từng ngăn để tìm túi của bạn: họ nhìn **số trên thẻ** để biết túi nằm ở ngăn nào, rồi mới mở đúng ngăn đó và **so từng túi** xem túi nào là của bạn.

Nếu hai chiếc túi giống hệt nhau nhưng lại được phát hai số thẻ khác nhau, nhân viên sẽ tìm ở sai ngăn và báo "không có túi nào như vậy".

Trong Java, số trên thẻ là [[hash-code|hashCode]]: nó quyết định phần tử nằm ở [[bucket]] nào. Việc so từng túi là `equals`: nó quyết định phần tử nào trong bucket đó đúng là thứ bạn tìm.
