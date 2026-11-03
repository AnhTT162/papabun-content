## Quick

Trình bày kiến trúc là giúp một nhóm người cụ thể **ra một quyết định cụ thể**, không phải kể lại mọi thứ mình đã thiết kế. **Bắt đầu bằng kết luận và quyết định cần có, nói bằng thứ người nghe quan tâm (tiền, rủi ro, thời gian, công sức), đưa vài phương án kèm khuyến nghị và cái giá của nó, mỗi sơ đồ một thông điệp cho đúng người nghe, và gặp riêng người quyết định trước buổi họp.** Phản biện là thông tin: tìm mối lo phía sau trước khi trả lời.

## Interview

Trước khi chuẩn bị gì, tôi trả lời ba câu: cần quyết định gì, ai quyết, và mỗi người trong phòng lo điều gì. Giám đốc tài chính hỏi tốn bao nhiêu và bao lâu hoàn vốn; vận hành hỏi nhân viên phải làm gì khác; CTO hỏi rủi ro kỹ thuật và ai vận hành; bảo mật hỏi dữ liệu đi đâu.

Cấu trúc tôi dùng là [[pyramid-principle|pyramid principle]]: câu đầu là đề nghị và quyết định cần ([[bluf|BLUF]]), sau đó ba lý do, rồi tới số liệu. Không kể theo trình tự "chúng tôi đã khảo sát, rồi thử, rồi...". Tôi luôn đưa hai ba phương án, gồm giữ nguyên và một phương án rẻ, so khuyến nghị với phương án rẻ nhất chứ không với việc không làm gì, và nói rõ cái giá của khuyến nghị.

Sơ đồ theo người nghe: lãnh đạo xem một hình trước và sau với năm hộp và một con số; team dev xem [[c4-model|C4]] container và sequence; vận hành xem deployment và chỗ có thể hỏng; bảo mật xem luồng dữ liệu. Mỗi sơ đồ đi kèm một câu nói thông điệp của nó.

Với quyết định lớn, tôi viết đề xuất vài trang gửi trước, vì văn bản buộc lập luận phải liền mạch, còn slide thì không. Trước buổi họp tôi gặp riêng từng người quyết định ([[pre-wiring|pre-wiring]]) để biết phản đối và sửa đề xuất, để trong phòng không ai bất ngờ.

Khi bị phản biện, tôi nghe hết, nhắc lại mối lo bằng lời mình, hỏi điều gì phía sau. Hiểu lầm thì giải thích; thiếu dữ liệu thì hẹn ngày trả lời; khác ưu tiên thì nói rõ trade-off và để người có thẩm quyền quyết. Không biết thì nói không biết.

Bẫy hay gặp: mở đầu bằng công nghệ, sơ đồ bốn mươi hộp, giấu chi phí ở cuối, chỉ một phương án, và hứa hoàn vốn bằng cách so với không làm gì.

## Deep

- **Biết người nghe trước khi soạn**: liệt kê ai quyết, ai có quyền phủ quyết, ai bị ảnh hưởng (bản đồ [[stakeholder|stakeholder]] ở bài Vai trò Solution Architect). Với từng người: họ đo thành công bằng gì, họ sợ gì, lần trước họ bị hứa gì mà không thành. Một CFO từng duyệt dự án hạ tầng không hoàn vốn sẽ nghe mọi con số với nghi ngờ; chuẩn bị bằng chứng cho đúng nỗi nghi ngờ đó.
- **[[pyramid-principle|Pyramid principle]]** (Barbara Minto, McKinsey): ý chính ở đỉnh, các ý đỡ nó ở dưới, mỗi nhóm không chồng nhau và đủ bao phủ. Phần mở đầu theo SCQ: Situation (bối cảnh người nghe đã đồng ý), Complication (điều thay đổi hay đang hỏng), Question (câu hỏi sinh ra), rồi Answer. [[bluf|BLUF]] (bottom line up front) là cùng ý, quen trong văn bản quân đội: câu đầu tiên là kết luận và việc người đọc cần làm.
- **Nói bằng đơn vị của người nghe**: "Kafka và [[cdc|CDC]]" không có nghĩa với CFO; "mỗi tháng 9.880 đơn bị huỷ vì hết hàng, tốn khoảng 1,19 tỷ đồng tiền bồi thường và chăm sóc khách hàng" thì có. Đổi lợi ích kỹ thuật thành tiền, rủi ro, thời gian ra thị trường, hoặc trải nghiệm khách hàng. Làm tròn số, nói khoảng tin cậy khi có, và tách *sự thật đã đo*, *giả định*, *ước lượng*.
- **Phương án và khuyến nghị**:
  - Hai ba phương án, trong đó có giữ nguyên (cái giá của việc không làm) và một phương án rẻ, nhanh. Thiếu phương án rẻ, người nghe sẽ tự nghĩ ra nó giữa buổi họp và đề xuất của bạn trông như đã bỏ sót.
  - So khuyến nghị với phương án tốt nhất còn lại, không với không làm gì. Một dự án "hoàn vốn trong 2 tháng" so với không làm gì có thể chỉ hoàn vốn trong 7 tháng so với một thay đổi cấu hình hai tuần (scenario của bài này).
  - Nói cái giá: tiền, người, thời gian, thứ phải hoãn, rủi ro mới. Đề xuất không có nhược điểm là đề xuất chưa được nghĩ kỹ.
  - Quyết định lớn chia giai đoạn có điểm dừng và [[kill-criteria|tiêu chí dừng]] đặt trước: "nếu sau giai đoạn 1 tỉ lệ huỷ ở cửa hàng thử không dưới 1% thì dừng". Người quyết dễ đồng ý hơn khi biết mình không bị khoá vào toàn bộ khoản tiền ([[one-way-door|quyết định một chiều]] và hai chiều ở bài Ra quyết định & trade-off).
- **Sơ đồ theo người nghe** (ký hiệu và các mức C4 ở bài ADR, C4 model & tài liệu kiến trúc):


| Người nghe | Họ hỏi | Sơ đồ |
|---|---|---|
| Lãnh đạo business | Đổi gì, được gì | Trước và sau, 4–6 hộp, một con số |
| Product | Người dùng thấy gì | Hành trình người dùng, màn hình nào đổi |
| Team dev | Xây thế nào | C4 container, [[sequence-diagram|sequence]] cho luồng khó |
| Vận hành | Chạy và hỏng thế nào | Deployment, dependency, chỗ có thể hỏng |
| Bảo mật, pháp chế | Dữ liệu đi đâu | Luồng dữ liệu, ranh giới tin cậy, nơi lưu |
| Tài chính | Tốn bao nhiêu | Bảng chi phí theo tháng và theo giai đoạn |

- **Quy tắc vẽ cho người khác đọc**:
  - C4 khuyên mỗi sơ đồ có tiêu đề nêu loại và phạm vi; khi trình bày, thêm một câu thông điệp ("Tồn kho cửa hàng tới web trong 5 giây thay vì 15 phút"). "Kiến trúc tổng thể" không nói gì với người nghe.
  - Tô màu phần thay đổi, phần giữ nguyên để xám. Có chú thích ký hiệu. Quá khoảng mười hộp thì tách sơ đồ.
  - Trình bày bằng cách dựng dần từng lớp, không đưa hình đầy đủ ngay rồi đọc từng hộp.
- **Văn bản cho quyết định, slide cho trình bày**: slide khuyến khích gạch đầu dòng rời rạc, che đi các bước lập luận còn hở. Bezos cấm PowerPoint trong cuộc họp của nhóm lãnh đạo Amazon từ email năm 2004; thư gửi cổ đông năm 2017 mô tả [[narrative-memo|bản ghi nhớ sáu trang]] viết dạng văn xuôi, mọi người đọc im lặng ở đầu cuộc họp rồi mới bàn. Không cần theo đúng hình thức đó, nhưng gửi bản đọc trước một hai ngày và để vài phút đầu đọc là cách rẻ để mọi người bàn trên cùng thông tin.
- **Khung một đề xuất kiến trúc**:
  1. Tóm tắt một đoạn: đề nghị, chi phí, lợi ích, quyết định cần hôm nay.
  2. Vấn đề có số, và vì sao phải làm bây giờ.
  3. Mục tiêu và những gì *không* làm.
  4. Phương án và bảng so sánh; khuyến nghị và lý do.
  5. Rủi ro lớn nhất và cách giảm; giả định cần kiểm.
  6. Kế hoạch theo giai đoạn, điểm dừng, người phụ trách.
  7. Phụ lục: sơ đồ kỹ thuật, tính toán chi phí, link [[design-doc|design doc]].
  - Design doc viết cho người xây; đề xuất viết cho người quyết. Quyết định đã chốt ghi vào [[adr|ADR]].
- **[[pre-wiring|Pre-wiring]]** (người Nhật gọi là nemawashi): gặp riêng từng người quyết định và người có thể phản đối trước buổi họp chính. Mục đích là nghe, không phải vận động: phản đối nói riêng thường thật hơn nói trước đám đông, và sửa đề xuất lúc này rẻ hơn sửa trong phòng họp. Buổi họp chính khi đó là để quyết, không phải để lần đầu nghe.
- **Xử lý phản biện**:
  - Nghe hết, không ngắt. Nhắc lại: "Anh lo nhân viên cửa hàng phải thêm thao tác ở quầy, đúng không?" Hỏi tiếp điều phía sau: phản đối về công nghệ thường là lo về người, tiền hay rủi ro.
  - Phân loại rồi trả lời theo loại: hiểu lầm thì giải thích bằng ví dụ; thiếu dữ liệu thì ghi lại, hẹn ngày trả lời và giữ hẹn; khác giá trị hay ưu tiên thì nói rõ trade-off, đề xuất cách giảm, và để người có thẩm quyền quyết.
  - Hỏi "điều gì phải đúng để anh thấy phương án này hợp lý?" để biến bất đồng thành điều kiện kiểm được.
  - Trình bày lại quan điểm đối lập ở dạng mạnh nhất của nó ([[steelman|steelman]]) trước khi phản bác. Người phản đối thấy mình được hiểu thì nghe tiếp.
  - Không biết thì nói không biết. Đoán bừa một con số trước CFO rồi bị phát hiện làm mất uy tín của cả đề xuất.
  - Sau khi đã quyết khác ý mình: [[disagree-and-commit|disagree and commit]] (bài Ra quyết định & trade-off), ghi rủi ro đã nêu và người chấp nhận vào ADR.
- **Khi người có chức vụ cao nhất đã chọn sẵn**: đừng tranh luận về sở thích; nói hậu quả bằng con số và điều kiện ("phương án này cần thêm 4 tháng và 2 người trực đêm"), đề xuất cách thử nhỏ để kiểm. Quyết định vẫn là của họ; việc của SA là để họ quyết khi đã thấy đủ.
- **Báo tin xấu và tiến độ**: báo sớm, kèm phương án; trạng thái xanh, vàng, đỏ phải gắn với tiêu chí cụ thể. Dự án báo xanh nhiều tháng rồi đỏ đột ngột trước hạn ("dưa hấu": xanh bên ngoài, đỏ bên trong) làm người quyết mất niềm tin vào mọi báo cáo sau.
- **Trình bày case kiến trúc trong phỏng vấn**: một số nơi yêu cầu trình bày 30–45 phút trước hội đồng. Khung hay dùng: bối cảnh và yêu cầu có số (5 phút), các phương án và vì sao chọn (10 phút), đi sâu một phần khó (10 phút), rủi ro và điều sẽ làm khác (5 phút), còn lại để hỏi. Vẽ sơ đồ trước, dừng sau mỗi phần để hội đồng chọn chỗ đào. Giữ bí mật công ty cũ bằng bậc độ lớn thay số thật (bài Kể về dự án & câu hỏi hành vi).
