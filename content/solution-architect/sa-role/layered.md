## Quick

[[solution-architect|Solution architect]] (SA) chịu trách nhiệm về giải pháp kỹ thuật cho một bài toán nghiệp vụ cụ thể, thường trải qua nhiều team và nhiều hệ thống: biến yêu cầu (cả [[non-functional-requirement|yêu cầu phi chức năng]], chi phí, pháp lý, thời hạn) thành kiến trúc làm được, rồi theo tới khi nó chạy. [[enterprise-architect|Enterprise architect]] nhìn cả tổ chức trong nhiều năm; [[tech-lead|tech lead]] dẫn một team xây một phần. **Việc chính của SA là các quyết định khó đảo ngược: chọn đúng, ghi lại lý do và cái giá, và làm cho mọi [[stakeholder]] hiểu vì sao.**

## Interview

Tôi phân biệt ba vai theo phạm vi và tầm thời gian.

**Enterprise architect** làm ở mức tổ chức, tầm vài năm: danh mục hệ thống, chuẩn công nghệ, lộ trình, review board. Họ trả lời "công ty nên có những năng lực gì và hệ thống nào làm việc đó".

**Solution architect** làm ở mức một giải pháp, tầm vài tháng tới một năm: một sản phẩm mới, một lần tích hợp, một đợt chuyển lên cloud. Đầu vào là bài toán nghiệp vụ và ràng buộc; đầu ra là kiến trúc, các quyết định có ghi lý do (ví dụ [[adr|ADR]]), ước lượng chi phí và rủi ro. SA phải đi qua mọi tầng: nói chuyện giá trị với business, nói chuyện chi phí với tài chính, nói chuyện khả thi với các team, nói chuyện vận hành với người trực sự cố.

**Tech lead** làm trong một team, theo nhịp sprint tới vài quý: thiết kế chi tiết, chia việc, review code, gỡ vướng, chịu trách nhiệm chất lượng phần team giao.

Ở công ty nhỏ, một người làm cả ba; chức danh cũng khác nhau giữa các nơi, nên khi phỏng vấn tôi hỏi rõ phạm vi.

Trọng tâm của SA là quyết định khó đổi: ranh giới service, database chính, mô hình dữ liệu, cách cô lập tenant, vendor. Quyết định dễ đổi thì để team tự quyết.

Bẫy hay gặp là kiến trúc sư "tháp ngà": vẽ xong giao cho team rồi đi, không biết bản vẽ có thi công được không. Bẫy ngược lại là ôm phần code khó nhất nên thành nút cổ chai của sprint. Tôi giữ cân bằng bằng cách vẫn viết [[proof-of-concept|PoC]] cho phần rủi ro, đọc code ở các PR quan trọng, và đo thành công bằng kết quả: yêu cầu phi chức năng đạt, chi phí trong dự toán, các team không chặn nhau, và ít quyết định phải đảo ngược tốn kém.

## Deep

- **Kiến trúc là gì để biết SA lo gì**: Martin Fowler gọi kiến trúc là những thứ quan trọng và khó thay đổi về sau. Đổi tên biến là thiết kế; đổi database chính sau hai năm chạy production là kiến trúc. SA dành thời gian cho nhóm thứ hai, vì sai ở đó tốn hàng tháng để sửa. Cách phân loại quyết định dễ và khó đảo ngược ở bài Ra quyết định & trade-off.
- **Ba vai, hỏi thêm hai câu: nói với ai nhiều nhất, và sai thì tốn gì**:
  - Enterprise architect: lãnh đạo và các SA; sai thì cả tổ chức trả bằng nhiều năm hệ thống trùng lặp hoặc chuẩn không ai theo.
  - Solution architect: business và các team; sai thì vài team phải làm lại một phần lớn trong nhiều tháng.
  - Tech lead: team và product owner; sai thì thường sửa được trong vài sprint.
- **Các biến thể của vai SA**: SA trong công ty sản phẩm lo giải pháp từ khi lên ý tưởng tới khi chạy. SA pre-sales ở công ty outsource hoặc nhà cung cấp cloud đọc hồ sơ mời thầu ([[rfp|RFP]]), viết đề xuất, ước lượng công sức và chi phí, làm PoC để thắng hợp đồng, rồi bàn giao cho team giao hàng: sai ước lượng ở đây thành lỗ của cả dự án. Ở các công ty dùng thang staff engineer, vai "architect" là một kiểu staff engineer chịu trách nhiệm một mảng kỹ thuật lớn. Hỏi rõ vai nào trước khi nhận việc hay vào phỏng vấn.
- **Một tuần làm việc điển hình**: workshop khai thác yêu cầu với business; viết yêu cầu phi chức năng có số; so hai ba phương án và viết ADR; vẽ sơ đồ cho từng loại người nghe; review thiết kế của các team; PoC cho phần chưa chắc; ước lượng chi phí cloud; trả lời câu hỏi của bộ phận bảo mật và pháp lý; theo dõi khi các team xây để điều chỉnh. Phần lớn thời gian là nói và viết, không phải code.
- **Bản đồ stakeholder**: business owner và product owner hỏi giá trị và thời hạn; người dùng hỏi trải nghiệm; các team dev hỏi có làm được không; vận hành và người trực hỏi chạy, giám sát, khôi phục thế nào; bảo mật và pháp lý hỏi dữ liệu ở đâu, ai truy cập; tài chính hỏi tốn bao nhiêu mỗi tháng; enterprise architect hỏi có theo chuẩn không. Cùng một kiến trúc, mỗi nhóm cần một bản trình bày khác. Liệt kê họ ngay tuần đầu; stakeholder bị quên thường xuất hiện lúc sắp go-live với một yêu cầu chặn tất cả (ví dụ bảo mật đòi dữ liệu không được rời khỏi một vùng).
- **Architect elevator**: Gregor Hohpe ví SA như người đi thang máy giữa tầng lãnh đạo và phòng máy. Ở tầng trên, nói bằng rủi ro, chi phí, thời gian; ở tầng dưới, nói bằng timeout, index, số kết nối. Giá trị của SA là dịch hai chiều: biết "giảm 30% chi phí" nghĩa là đổi gì trong hệ thống, và biết "đổi sang event-driven" nghĩa là gì với thời hạn của business.
- **Ai quyết định**: thoả thuận từ đầu quyền quyết của từng vai, ví dụ bằng bảng [[raci|RACI]]. SA thường quyết các điểm kiến trúc xuyên team; tech lead quyết thiết kế bên trong team; business quyết đánh đổi phạm vi và thời hạn. Không rõ quyền thì mọi bất đồng đều leo thang.
- **Kiến trúc sư tháp ngà**: vẽ sơ đồ đẹp, chọn công nghệ mới nhất, giao xuống rồi biến mất. Triệu chứng: team âm thầm làm khác bản vẽ, sơ đồ lỗi thời sau hai tháng, sự cố lặp lại ở cùng một ranh giới. Cách tránh: ngồi cùng team ở giai đoạn đầu, nhận phản hồi từ code thật, sửa kiến trúc khi bằng chứng đổi.
- **SA còn code không**: nên còn đọc code và viết PoC, vì quyết định không có cảm giác về code thật thường đánh giá thấp độ khó (migrate dữ liệu, bài toán nhất quán, giới hạn thư viện). Không nên nhận task trên đường găng của sprint: SA bị kéo vào họp thì task đó trễ và kéo cả team.
- **Chọn công nghệ để làm đẹp CV**: thêm Kafka, service mesh, Kubernetes cho hệ thống 50 request mỗi giây vì muốn học. Team gánh chi phí vận hành nhiều năm. Mỗi công nghệ mới cần một lý do truy về yêu cầu, và một người chịu vận hành nó.
- **Phỏng vấn vị trí SA khác senior developer**: vòng System Design có thêm chi phí, bảo mật, cách chuyển từ hệ cũ, cách chia cho team; vòng hành vi hỏi về stakeholder, xung đột, quyết định sai; có nơi yêu cầu trình bày một case kiến trúc trước hội đồng. Xem bài Kể về dự án & câu hỏi hành vi và bài Trình bày kiến trúc cho stakeholder.
- **Từ senior developer lên SA**: bắt đầu bằng việc viết ADR cho quyết định của team, dẫn một thiết kế chạm tới hai ba team, đọc hoá đơn cloud của hệ thống mình, và ngồi các buổi làm việc với business. Kỹ năng thiếu thường không phải công nghệ mà là viết, trình bày và thuyết phục người không cùng chuyên môn.
