## Quick

Câu "kể về dự án của bạn" và các [[behavioral-interview|câu hỏi hành vi]] ("kể một lần bạn bất đồng...") kiểm tra bạn **thật sự đã làm gì và nghĩ thế nào**, không kiểm tra dự án to cỡ nào. Kể dự án theo bối cảnh → vai trò → quyết định → kết quả → bài học; kể câu chuyện hành vi theo [[star-method|STAR]]. **Mỗi câu chuyện cần một chữ "tôi" rõ ràng, một quyết định có phương án bị loại và cái giá, và một kết quả có số.**

## Interview

Khi được hỏi "kể về dự án gần nhất", tôi trả lời trong khoảng hai phút theo năm phần.

**Bối cảnh** (20 giây): hệ thống giải quyết bài toán gì cho ai, quy mô bằng bậc độ lớn: số người dùng, số request mỗi giây, số team. Không mở đầu bằng danh sách công nghệ.

**Vai trò** (10 giây): tôi chịu trách nhiệm phần nào, dẫn bao nhiêu người, ai quyết định cái gì. Tách rõ "team làm" với "tôi làm".

**Kiến trúc** (20 giây): một câu và một sơ đồ trong đầu: các khối chính, dữ liệu nằm đâu, phần nào đồng bộ, phần nào bất đồng bộ.

**Quyết định khó** (một phút): một hai quyết định tôi trực tiếp tham gia. Mỗi quyết định có vấn đề, các phương án, lý do chọn, cái giá chấp nhận. Đây là phần người phỏng vấn sẽ đào sâu, nên tôi chọn chỗ tôi hiểu tới cơ chế.

**Kết quả và bài học** (20 giây): con số trước và sau, và một điều tôi sẽ làm khác nếu làm lại.

Câu hỏi hành vi như xung đột, thất bại, thời hạn gấp thì tôi kể theo STAR: tình huống, nhiệm vụ của tôi, hành động của tôi, kết quả. Phần hành động chiếm khoảng một nửa thời gian.

Bẫy hay gặp: nói "chúng tôi" từ đầu tới cuối nên người nghe không biết bạn làm gì; kể công nghệ thay vì vấn đề; không có số; câu chuyện thất bại giả kiểu "tôi quá cầu toàn"; đổ lỗi cho người khác; nói quá vai trò rồi bị lộ khi bị hỏi sâu ba tầng. Cách làm đúng là chuẩn bị sẵn sáu tới tám câu chuyện thật, mỗi câu dùng được cho vài loại câu hỏi, luyện nói thành tiếng, và giữ bí mật của công ty bằng bậc độ lớn thay cho số thật.

## Deep

- **Người phỏng vấn chấm gì**: phỏng vấn hành vi dựa trên giả định hành vi trong quá khứ là cách dự đoán tốt cho hành vi tương lai. Họ chấm theo bảng tiêu chí: bạn hiểu vấn đề sâu tới đâu, tự chịu trách nhiệm phần nào ([[ownership|ownership]]), đánh giá phương án ra sao, làm việc với người khác thế nào, rút ra gì. Một dự án nhỏ kể rõ quyết định thắng một dự án lớn kể mơ hồ.
- **"Tôi" và "chúng tôi"**: dùng "chúng tôi" cho bối cảnh và kết quả của team, "tôi" cho việc bạn làm. Nếu người phỏng vấn hỏi "cụ thể anh làm gì?" mà bạn phải nghĩ lâu, câu chuyện đó chưa sẵn sàng. Ngược lại, nhận công của người khác dễ bị lộ ở câu hỏi đào sâu, và đôi khi người phỏng vấn kiểm tra lại qua người tham chiếu.
- **Đào sâu ba tầng**: người phỏng vấn kỹ thuật thường hỏi theo chuỗi: "vì sao chọn Redis?" → "Redis failover thì lock có còn không?" → "vậy anh đã kiểm tra thế nào?". Với mỗi quyết định trong câu chuyện, tự hỏi trước ba tầng như vậy. Chỗ nào chỉ trả lời được tầng một thì đừng đưa vào phần quyết định khó.
- **Con số**: dùng số đo được trước và sau (latency p99, số sự cố mỗi tháng, chi phí mỗi tháng, thời gian deploy). Không nhớ chính xác thì nói bậc độ lớn và nói rõ là ước chừng. Bịa số chi tiết rất dễ vỡ khi bị hỏi "đo bằng gì?". Kiểm tra số có hợp lý với nhau: "100 request mỗi giây" mà "p99 giảm từ 10 giây xuống 50 ms nhờ thêm index" sẽ bị hỏi lại ngay.
- **Giữ bí mật**: không nêu tên khách hàng, số doanh thu thật, chi tiết bảo mật hay mã nguồn. Mô tả domain chung ("một ví điện tử cỡ vài triệu người dùng"), dùng bậc độ lớn. Nói thẳng "phần này tôi không chia sẻ được chi tiết" là chuyên nghiệp, không bị trừ điểm.
- **STAR và biến thể**: Situation (bối cảnh, ngắn), Task (trách nhiệm của bạn), Action (bạn làm gì, vì sao, theo thứ tự), Result (kết quả có số). Nhiều người thêm L (Learning): điều bạn rút ra và đã áp dụng ở lần sau. Lỗi phổ biến là Situation dài một phút còn Action chỉ một câu.
- **Kho câu chuyện**: chọn sáu tới tám câu chuyện từ dự án thật, lập bảng câu chuyện × loại câu hỏi: xung đột với đồng nghiệp, bất đồng với cấp trên, thất bại hay sai lầm, thời hạn gấp, dẫn dắt không có quyền chính thức, quyết định khi thiếu dữ liệu, sự cố production, thuyết phục stakeholder. Một sự cố production tốt thường dùng được cho ba bốn ô. Tránh dùng một câu chuyện cho hai câu hỏi trong cùng buổi.
- **Câu hỏi về xung đột**: người phỏng vấn muốn thấy bạn tách người khỏi vấn đề, tìm hiểu lý do của bên kia, đưa bất đồng về dữ liệu ([[proof-of-concept|PoC]], phép đo, bảng so), và chấp nhận kết quả. Kết thúc tốt không nhất thiết là bạn thắng: "tôi không đồng ý nhưng cam kết làm theo, và đây là điều tôi học được" ([[disagree-and-commit|disagree and commit]]) cũng là câu trả lời mạnh. Tránh câu chuyện trong đó đồng nghiệp là người xấu.
- **Câu hỏi về thất bại**: chọn một sai lầm thật có hậu quả thật, do chính bạn gây ra hoặc góp phần. Kể rõ bạn phát hiện thế nào, khắc phục ra sao, và thay đổi gì để không lặp lại (test, cảnh báo, quy trình). Thất bại quá nhỏ hay "lỗi của team khác" cho thấy bạn né tránh. Thất bại gây thiệt hại lớn mà không có bài học thì nguy hiểm hơn.
- **Ở cấp SA**: câu chuyện nên có nhiều stakeholder, đánh đổi giữa business và kỹ thuật (phạm vi, thời hạn, chi phí), quyết định khó đảo ngược, và việc bạn giúp người khác ra quyết định. Câu chuyện chỉ có code thì hợp với vòng senior developer hơn. Xem bài Vai trò Solution Architect.
- **Câu hỏi "nếu làm lại"**: luôn chuẩn bị. Câu trả lời tốt chỉ ra một quyết định cụ thể và vì sao bây giờ bạn quyết khác (thông tin mới, quy mô đổi), không phải "tôi sẽ dùng microservices cho mọi thứ". Câu trả lời "không có gì khác" bị coi là thiếu tự nhìn lại.
- **Thời lượng**: trả lời đầu tiên hai tới ba phút, rồi dừng và để người phỏng vấn chọn chỗ đào sâu. Nói năm phút liền thì người nghe mất dấu và bạn mất thời gian của các câu hỏi khác. Phiên bản 60 giây của dự án cũng nên có sẵn cho vòng sàng lọc qua điện thoại.
- **Luyện tập**: nói thành tiếng và ghi âm; viết ra giấy nghe rất khác lúc nói. Nhờ một người hỏi đào sâu ba tầng. Luyện với hồ sơ dự án thật trong tính năng "Dự án của tôi" của app, nơi giữ số liệu thật ngoài nội dung công khai.
