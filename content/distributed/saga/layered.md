## Quick

[[saga|Saga]] thực hiện một nghiệp vụ trải qua nhiều service bằng **chuỗi transaction cục bộ**; bước sau thất bại thì chạy **[[compensating-transaction|bù trừ]]** cho các bước đã xong, theo thứ tự ngược lại. Bù trừ là **hành động nghiệp vụ mới** (hoàn tiền, nhả hàng), không phải rollback. Saga có tính nguyên tử và bền vững nhưng **không có isolation**: người khác thấy được trạng thái dở dang, nên thiết kế phải chủ động che nó.

## Interview

**Hai cách phối hợp**:
- **[[choreography|Choreography]]**: không ai điều khiển. Order phát `OrderPlaced`, Inventory nghe và phát `StockReserved`, Payment nghe và thu tiền. Ít thành phần, hợp với 2–3 bước. Luồng nằm rải trong nhiều service, khó trả lời "đơn đang ở bước nào", và dễ thành vòng phụ thuộc giữa các service.
- **[[orchestration|Orchestration]]**: một orchestrator (thường nằm trong service khởi xướng) giữ trạng thái của từng saga, gửi lệnh (`ReserveStock`, `ChargePayment`) và nhận kết quả. Luồng đọc được ở một chỗ, dễ thêm timeout và bù trừ. Bẫy: orchestrator ôm luôn logic nghiệp vụ của các bên; nó chỉ nên quyết định bước tiếp theo.

**Ba loại bước** (theo Chris Richardson):
- **Compensatable**: có bù trừ (giữ hàng ↔ nhả hàng).
- **[[pivot-transaction|Pivot]]**: điểm không quay lại; xong bước này saga chỉ đi tiếp. Là bước không hoàn lại được hoặc hoàn lại rất tốn kém: xuất vé, giao hàng; thu tiền chỉ là pivot khi hoàn tiền mất phí hay mất nhiều ngày.
- **Retriable**: sau pivot, phải thành công nên retry tới khi được (gửi hàng, cộng điểm).

Sắp bước khó bù trừ về cuối, sát pivot.

**Bù trừ phải đúng**: idempotent (lệnh bù trừ cũng bị gửi lại), không được thất bại vĩnh viễn (retry tới khi xong, quá ngưỡng thì báo người xử lý), và chạy được kể cả khi bước gốc chưa từng chạy (nhả hàng cho đơn chưa giữ là no-op).

**Thiếu isolation**: đơn đã giữ hàng nhưng chưa trả tiền, nơi khác đã thấy. Che bằng **[[semantic-lock|semantic lock]]** (trạng thái `PENDING` mà mọi bên hiểu là chưa xong), cập nhật giao hoán (cộng trừ thay vì ghi đè số), hoặc đọc lại giá trị trước khi ghi.

**Timeout không phải thất bại**: gọi Payment hết giờ thì tiền có thể đã trừ. Không bù trừ mù: tra cứu trạng thái theo idempotency key rồi mới quyết.

## Deep

- **Orchestrator phải bền**: lưu trạng thái saga (bước hiện tại, dữ liệu cần cho bù trừ) trong database của nó, và gửi lệnh qua [[outbox|outbox]] trong cùng transaction với việc chuyển trạng thái. Pod chết ở đâu thì khởi động lại đọc trạng thái và gửi lại lệnh của bước dở; bên nhận khử trùng theo id saga và bước (bài Transactional outbox & CDC, bài Idempotency).
- **Workflow engine**: Temporal, Camunda, AWS Step Functions lưu lịch sử từng bước và tự retry, timeout, nên code orchestrator gọn như code tuần tự. Đổi lại thêm một hệ thống phải vận hành, và với Temporal, code workflow phải deterministic (không đọc giờ hệ thống, không sinh số ngẫu nhiên trực tiếp) vì engine phát lại lịch sử để dựng lại trạng thái; dùng API thời gian và random của SDK, và đổi logic workflow đang chạy thì phải versioning.
- **Deadline của cả saga**: đơn ở `PENDING_PAYMENT` quá 15 phút thì tự huỷ và bù trừ. Không có deadline thì saga kẹt giữ hàng mãi; cần cảnh báo cho số saga ở một trạng thái quá lâu.
- **Kết quả đến muộn sau khi đã bù trừ**: đã kết luận "chưa trừ tiền" và huỷ đơn, rồi webhook báo đã trừ. Phải có nhánh xử lý: hoàn tiền cho đơn đã huỷ, và [[reconciliation|đối soát]] với cổng thanh toán hằng ngày. Thiết kế từng trạng thái để chịu được mọi event đến muộn hoặc trùng.
- **Bất thường do thiếu isolation**: *lost update* (saga A ghi đè thay đổi của saga B trên cùng đơn), *dirty read* (Loyalty cộng điểm theo đơn mà sau đó bị huỷ). Các countermeasure khác: *pessimistic view* (đổi thứ tự bước để việc rủi ro đọc dữ liệu dở dang xảy ra sau pivot), *by value* (rủi ro cao như số tiền lớn thì dùng 2PC hoặc xử lý tay).
- **Bù trừ không phải lúc nào cũng hoàn lại được**: email đã gửi chỉ có thể gửi thư đính chính; hoàn tiền có thể mất phí và mất vài ngày; hàng đã giao thì bù trừ là quy trình trả hàng. Đó là lý do bước không bù trừ được phải sau pivot.
- **Choreography lớn dần**: thêm bước thứ năm, thứ sáu thì mỗi service phải nghe event của nhiều service khác, và đổi thứ tự bước phải sửa nhiều nơi. Dấu hiệu nên chuyển sang orchestration: không ai vẽ được luồng mà không đọc code của mọi service.
- **Song song**: giữ hàng và kiểm tra gian lận có thể chạy cùng lúc; orchestrator chờ cả hai. Một bên lỗi thì bù trừ bên kia, kể cả khi bên kia trả kết quả sau.
- **Saga và người dùng**: API trả `202 Accepted` kèm id đơn, giao diện hiển thị "đang xử lý" và hỏi lại hoặc nhận thông báo. Giấu bất đồng bộ sau một lời gọi đồng bộ chờ cả saga xong thì quay về đúng vấn đề latency mà saga tránh.
- **TCC (Try-Confirm-Cancel)**: biến thể mà mỗi bên có bước "giữ chỗ" (Try) rồi Confirm hoặc Cancel, như pre-authorization của thẻ. Bên tham gia phải hỗ trợ trạng thái giữ chỗ có hạn, đổi lại bù trừ chỉ là huỷ phần đang giữ.
- **Saga trong một service**: một database thì dùng transaction cục bộ, đừng dựng saga. Saga có giá, chỉ dùng khi bước nằm ở các service hay hệ thống thật sự tách rời (bài Nhất quán dữ liệu giữa các service, bài 2PC & giao dịch phân tán).
