## Quick

Review kiến trúc là tìm **rủi ro** trong một thiết kế khi còn sửa rẻ, đối chiếu với các [[quality-attribute|quality attribute]] mà business cần, không phải chấm điểm hay bắt lỗi người thiết kế. **Đầu ra tốt là vài rủi ro có thứ tự, viết dạng "nếu ... thì ...", mỗi cái có người xử lý và hạn, kèm kết luận rõ: đi tiếp, đi tiếp có điều kiện, hay làm lại phần nào.** [[atam|ATAM]] rút gọn và [[risk-storming|risk storming]] là hai cách làm hay dùng.

## Interview

Mục tiêu của review là trả lời một câu: thiết kế này có đạt được những gì business cần không, và chỗ nào có thể làm nó thất bại. Tôi review sớm, lúc thiết kế còn trên giấy, vì sau khi xây xong chỉ còn hai lựa chọn là cho qua hoặc làm lại.

Chuẩn bị: tôi đọc trước [[design-doc|design doc]], hỏi rõ mục tiêu business và [[non-functional-requirement|NFR]] có số. Không có NFR thì việc đầu tiên là chốt chúng, vì không có thước đo thì review chỉ là ý kiến cá nhân.

Buổi review tôi làm theo [[atam|ATAM]] rút gọn trong khoảng một ngày: business driver, người thiết kế trình bày kiến trúc, dựng [[utility-tree|utility tree]] và chọn vài scenario quan trọng nhất, rồi đi từng scenario qua kiến trúc: luồng nào đáp ứng nó, quyết định nào nó phụ thuộc. Sau đó tôi chạy [[risk-storming|risk storming]]: mọi người tự viết rủi ro lên sơ đồ trong mười phút, rồi gom lại. Cách này bắt được rủi ro mà người thiết kế không nghĩ tới, nhất là từ vận hành và bảo mật.

Câu hỏi tôi luôn hỏi: dependency nào nằm trên đường đồng bộ và nó chết thì sao; đỉnh tải là bao nhiêu, đã đo chưa; dữ liệu nào là nguồn sự thật; retry có an toàn không; khôi phục thế nào, [[rpo-rto|RPO/RTO]] bao nhiêu; ai trực; chi phí mỗi tháng.

Đầu ra là danh sách rủi ro dạng "nếu ... thì ...", phân loại [[sensitivity-point|sensitivity point]], [[tradeoff-point|tradeoff point]], [[non-risk|non-risk]], gom thành [[risk-theme|risk theme]], và kết luận đi tiếp có điều kiện hay không. Mỗi rủi ro chặn có chủ và hạn.

Bẫy hay gặp: review quá muộn; danh sách sáu mươi góp ý không thứ tự; người review áp công nghệ ưa thích; hỏi "có hay không" thay vì đòi bằng chứng.

## Deep

- **Các loại review, đừng lẫn**: design review trước khi xây (bài này); [[architecture-board|review board]] duyệt quyết định có tác động rộng (governance, bài Enterprise architecture & governance); [[well-architected-framework|Well-Architected review]] đi theo bộ câu hỏi sáu trụ cột (bài AWS Well-Architected); [[production-readiness-review|production readiness review]] trước khi lên production hay giao trực (bài Độ tin cậy & SRE); postmortem sau sự cố. Cùng một hệ thống có thể qua cả năm, mỗi loại hỏi một câu khác nhau.
- **[[atam|ATAM]] đầy đủ** (Architecture Tradeoff Analysis Method, SEI, báo cáo kỹ thuật CMU/SEI-2000-TR-004 của Kazman, Klein và Clements): đội đánh giá vài người tách khỏi dự án, chia pha:
  - Phase 0: thoả thuận phạm vi, ai tham gia, tài liệu cần có.
  - Phase 1 (đội đánh giá với người ra quyết định của dự án): 1 giới thiệu ATAM, 2 trình bày business driver, 3 trình bày kiến trúc, 4 xác định các cách tiếp cận kiến trúc đã dùng, 5 dựng [[utility-tree|utility tree]], 6 phân tích các cách tiếp cận theo scenario ưu tiên cao.
  - Phase 2 (thêm [[stakeholder|stakeholder]] rộng hơn, thường vài tuần sau): 7 brainstorm và bỏ phiếu chọn scenario, so với utility tree; 8 phân tích lại theo scenario mới; 9 trình bày kết quả.
  - Phase 3: báo cáo và theo dõi.
  - Bước 7 đáng giá vì stakeholder hay đưa ra scenario mà người thiết kế không nghĩ tới; nếu scenario được bỏ phiếu cao không có trong utility tree, đó là dấu hiệu kiến trúc đang tối ưu cho thứ khác với điều người dùng cần.
- **ATAM rút gọn**: sách *Software Architecture in Practice* (Bass, Clements, Kazman, bản 3) mô tả bản nhẹ (Lightweight Architecture Evaluation) cho team nội bộ, tổng khoảng 4–6 giờ: bỏ phần giới thiệu phương pháp, làm nhanh business driver và trình bày kiến trúc, dành phần lớn thời gian cho phân tích scenario, bỏ bước 7–8 (stakeholder nội bộ góp scenario ngay khi dựng utility tree), vẫn giữ bước trình bày kết quả. Cách chia thời gian tôi hay dùng, có thêm risk storming không thuộc ATAM: business driver 15 phút, kiến trúc 30 phút, utility tree 45 phút, phân tích 4–6 scenario hàng đầu 2–3 giờ, risk storming 45 phút, tổng kết 30 phút.
- **Phân tích một scenario thế nào**: lấy một [[quality-attribute-scenario|quality attribute scenario]] (nguồn, kích thích, môi trường, thành phần, phản hồi, thước đo; bài NFR & quality attribute), đi theo luồng trên sơ đồ, hỏi quyết định nào làm nó đạt hay trượt. Ví dụ "7 giờ thứ Hai, 60.000 người mở app đặt lịch trong 10 phút, p95 dưới 800 ms": đi qua gateway, service, cache, DB, hệ thống đối tác; tìm chặng có trần thấp nhất và chặng không có trần đo.
- **Năm loại phát hiện của ATAM**:
  - Rủi ro: quyết định có thể dẫn tới hậu quả xấu cho một quality attribute. Viết "nếu ... thì ...": "Nếu hệ thống của đối tác bảo trì 23h–1h thì không ai đặt lịch được trong khung giờ đó".
  - [[non-risk|Non-risk]]: quyết định tốt, kèm lý do. Ghi lại để không ai đổi nó vì quên lý do, và để buổi review không chỉ toàn tin xấu.
  - [[sensitivity-point|Sensitivity point]]: tham số mà một thuộc tính phụ thuộc mạnh (chu kỳ làm mới cache quyết định độ chính xác của số slot trống).
  - [[tradeoff-point|Tradeoff point]]: quyết định là sensitivity point của nhiều thuộc tính theo hướng ngược nhau (bài Ra quyết định & trade-off).
  - [[risk-theme|Risk theme]]: nhóm rủi ro cùng gốc. Báo cáo cho lãnh đạo nên mở đầu bằng theme ("mọi luồng đặt lịch phụ thuộc đồng bộ vào hệ thống của đối tác"), không bằng danh sách hai mươi dòng; theme cũng chỉ ra rủi ro tới mục tiêu business nào.
- **[[risk-storming|Risk storming]]** (Simon Brown, tác giả [[c4-model|C4]]): hợp với team tự review, không cần chuyên gia phương pháp.
  1. Vẽ sơ đồ ở vài mức (context, container, có thể deployment) lên bảng.
  2. Mỗi người tự viết rủi ro lên giấy dán, mỗi tờ một rủi ro, trong khoảng 10 phút, im lặng. Làm riêng để tránh người nói to nhất kéo cả nhóm, giống cách của [[pre-mortem|pre-mortem]]. Mỗi rủi ro chấm xác suất và tác động, ví dụ mỗi trục 1–3; tích của hai trục là mức ưu tiên (1–2 thấp, 3–4 trung bình, 6–9 cao), dùng màu giấy dán khác nhau cho từng mức.
  3. Dán rủi ro lên gần chỗ trên sơ đồ mà nó liên quan. Chỗ nhiều giấy dán là điểm nóng.
  4. Xem lại và tóm tắt, chú ý rủi ro mà chỉ một người thấy: đó thường là kiến thức chỉ người đó có. Rồi chọn cách xử lý cho các rủi ro cao. Giữ cả những rủi ro sau khi bàn được chấm là không đáng kể, để biết đã xem xét.
  - Mời đủ góc nhìn: dev, vận hành, bảo mật, DBA, người tích hợp với đối tác. Rủi ro về con người cũng là rủi ro: một người duy nhất biết hệ thống ([[bus-factor|bus factor]]), vendor không có người trực đêm.
- **Câu hỏi nên hỏi**, theo nhóm:
  - Mục tiêu: thành công đo bằng gì; NFR nào là cứng; quyết định nào là [[one-way-door|một chiều]].
  - Tải: đỉnh bao nhiêu, đến từ đâu; trần của từng chặng đã đo hay đoán (bài Load & performance testing).
  - Lỗi: dependency nào trên đường đồng bộ; nó chậm (không phải chết) thì sao; có timeout, giới hạn retry, [[circuit-breaker|circuit breaker]] không; [[single-point-of-failure|điểm chết đơn]]. Availability của chuỗi đồng bộ là tích các thành phần (bài NFR & quality attribute).
  - Dữ liệu: nguồn sự thật ở đâu; hai nơi giữ cùng dữ liệu thì lệch nhau thế nào; retry có tạo bản ghi trùng không ([[idempotency-key|idempotency key]]); migrate dữ liệu cũ; thời gian lưu và xoá.
  - Bảo mật: dữ liệu nhạy cảm đi qua đâu, kể cả log và SMS; ai được truy cập; bí mật lưu ở đâu (bài Kiến trúc bảo mật).
  - Vận hành: đo bằng gì, ai được báo động; deploy và rollback; [[rpo-rto|RPO/RTO]] và lần khôi phục thử gần nhất.
  - Chi phí và con người: tiền mỗi tháng ở tải đỉnh và tải thường; team nào sở hữu từng phần; ai biết hệ thống của đối tác.
  - Tiến hoá: phần nào sẽ đổi nhiều nhất; thoát khỏi vendor thế nào.
- **Đòi bằng chứng thay vì hỏi có hay không**: "có load test chưa" luôn được trả lời "có". Hỏi "kết quả load test gần nhất ở bao nhiêu request/s, chặng nào bão hoà trước", "lần restore thử gần nhất là khi nào, mất bao lâu". Thiếu bằng chứng thì ghi là giả định chưa kiểm, không ghi là rủi ro đã đóng.
- **Review một hệ thống đang chạy** (tiếp quản, đánh giá trước khi mua lại, trước khi hiện đại hoá): có dữ liệu thật thay cho giả định. Đọc lịch sử sự cố và [[postmortem|postmortem]], [[slo|SLO]] và mức tiêu [[error-budget|error budget]], tần suất deploy và tỉ lệ deploy lỗi, hoá đơn cloud, đồ thị dependency, file vừa sửa nhiều vừa phức tạp ([[hotspot|hotspot]]), ai commit vào phần nào. Ba sự cố cùng một gốc là risk theme rõ hơn mọi phân tích trên giấy.
- **Viết kết luận**:
  - Một trang đầu: kết luận, 3–5 rủi ro hàng đầu và theme, quyết định cần lãnh đạo đưa ra. Chi tiết ở phụ lục.
  - Mỗi phát hiện có mức: *chặn* (phải xử lý trước khi đi tiếp), *nên sửa* (có hạn), *cân nhắc* (team tự quyết). Không phân mức thì sáu mươi góp ý ngang nhau và team sửa cái dễ trước.
  - Kết luận là một trong ba: đi tiếp; đi tiếp có điều kiện (liệt kê điều kiện, người, hạn); làm lại phần nào rồi review lại riêng phần đó.
  - Rủi ro được chấp nhận cũng là kết quả hợp lệ, miễn có người có thẩm quyền ký nhận; ghi vào [[risk-register|risk register]] và [[adr|ADR]].
- **Cách cư xử của người review**: review thiết kế, không review người; hỏi để hiểu trước khi đề xuất; nêu rủi ro kèm hậu quả, để team chọn cách sửa; tách "phải" và "tôi thích". Người review không chịu hậu quả của quyết định thì đừng ép nó. Người có chức vụ cao nhất nói sau cùng, nếu không cả phòng sẽ chỉ đồng ý theo.
- **Các phương pháp khác của SEI**: SAAM (tiền thân của ATAM, tập trung vào khả năng sửa đổi); ARID (Active Reviews for Intermediate Designs): người review dùng thử bản thiết kế dở dang để giải bài tập cụ thể, hợp để review interface của một module; CBAM thêm phân tích chi phí và lợi ích sau ATAM, để chọn sửa rủi ro nào trước.
- **Khi nào không cần review đầy đủ**: quyết định [[two-way-door|hai chiều]] trong một team, [[proof-of-concept|PoC]] ngắn, công cụ nội bộ ít người dùng. Một buổi 30 phút với người vận hành và bảo mật là đủ. Review cả ngày cho mọi thay đổi biến review thành hàng đợi.
