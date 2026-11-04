## Quick

Migration là chuyển hệ thống sang nơi khác hay nền khác; modernization là thay đổi cách nó được xây. **Quyết định theo từng ứng dụng bằng [[seven-rs|7 R]] (retire, retain, [[rehost|rehost]], relocate, [[repurchase|repurchase]], [[replatform|replatform]], refactor), đừng gộp hạn chót rời datacenter với việc viết lại kiến trúc, và thay hệ thống cũ từng phần theo [[strangler-fig|strangler fig]] thay vì viết lại một lần.** Phần khó nhất là dữ liệu: ở mỗi thời điểm phải biết bên nào là nguồn sự thật, [[reconciliation|đối soát]] được, và biết khi nào qua [[point-of-no-return|điểm không quay lại]].

## Interview

Tôi bắt đầu bằng đánh giá danh mục, không bằng công nghệ. Mỗi ứng dụng được gắn một trong 7 R: tắt hẳn (retire), giữ nguyên (retain), chuyển nguyên trạng (rehost), chuyển cả nền ảo hoá (relocate), đổi một phần nền như database sang dịch vụ managed (replatform), thay bằng SaaS (repurchase), hay thiết kế lại (refactor). Thường 10–20% ứng dụng có thể tắt, và phần lớn còn lại nên rehost hay replatform. Chỉ vài hệ thống lõi, nơi kiến trúc cũ thật sự chặn nghiệp vụ, mới đáng refactor.

Nếu có hạn chót như hết hợp đồng datacenter, tôi tách làm hai bước: chuyển trước, hiện đại hoá sau. Gộp cả hai thì rủi ro của dự án viết lại thành rủi ro của hạn chót. Khi chuyển, ứng dụng và database đi cùng một [[move-group|nhóm]]: app nói nhiều với database mà cách nó 10 ms thì một màn hình 900 câu SQL mất 9 giây.

Hiện đại hoá theo strangler fig: đặt một lớp định tuyến trước hệ thống cũ, xây từng phần mới, chuyển dần lưu lượng, cuối cùng tắt phần cũ. Chọn lát cắt có giá trị và ít phụ thuộc trước. Để hệ thống cũ còn chạy trong lúc chuyển, dùng [[event-interception|chặn event]] và [[legacy-mimic|giả lập giao diện cũ]], kể cả code chỉ sống trong giai đoạn chuyển tiếp ([[transitional-architecture|transitional architecture]]).

Với dữ liệu: một nguồn sự thật cho mỗi phần dữ liệu ở mỗi thời điểm, đồng bộ qua [[cdc|CDC]] chứ không [[dual-write|ghi hai nơi]] từ ứng dụng. Trước khi chuyển, [[parallel-run|chạy song song]] và so kết quả, đối soát bằng số dòng, tổng và hash theo khoảng khoá. Giữ [[reverse-replication|đồng bộ ngược]] về hệ thống cũ để còn đường rollback.

Bẫy hay gặp: đòi [[feature-parity|tính năng ngang bằng]] với hệ thống cũ trước khi chuyển bất kỳ ai; viết lại một lần với ngày "big bang"; quên rằng chạy hai hệ thống cùng lúc tốn tiền gấp đôi trong nhiều tháng.

## Deep

- **7 R của AWS** (từ 5 R của Gartner năm 2011, AWS mở rộng thành 6 rồi 7):
  - Retire: tắt. Ứng dụng không ai đăng nhập 90 ngày, báo cáo không ai mở. Đây là phần tiết kiệm rẻ nhất.
  - Retain: giữ lại chỗ cũ, vì chưa đáng chuyển, vướng pháp lý, hay sắp thay.
  - Rehost (lift and shift): chuyển máy ảo nguyên trạng. Nhanh, không sửa code; bỏ được chi phí datacenter và chọn lại cỡ máy, nhưng công vận hành chính ứng dụng không đổi.
  - Relocate: chuyển cả nền ảo hoá (ví dụ VMware sang VMware Cloud on AWS) mà không đổi từng máy.
  - Replatform (lift, tinker and shift): đổi một phần nền mà không đổi kiến trúc: database sang RDS, app server sang container, cron sang dịch vụ lập lịch.
  - Repurchase: chuyển sang SaaS (HR, CRM, ticketing). Phần khó là migrate dữ liệu và các tích hợp vào sản phẩm mới.
  - Refactor/re-architect: thiết kế lại cho cloud. Đắt và lâu nhất; chỉ cho hệ thống có lý do nghiệp vụ.
- **Đánh giá danh mục**: danh sách ứng dụng, chủ sở hữu, số người dùng, phụ thuộc mạng và dữ liệu giữa chúng (đo từ luồng mạng thật, không chỉ hỏi người), giấy phép phần mềm, yêu cầu pháp lý về nơi lưu dữ liệu. Ứng dụng gọi nhau nhiều được gom thành move group và chuyển trong cùng một đợt.
- **Bẫy hybrid khi chuyển dở**: app chuyển lên cloud trước, database còn ở datacenter. Màn hình hồ sơ bồi thường chạy 900 câu SQL tuần tự: ở datacenter mỗi vòng 0,3 ms là 0,27 giây; qua Direct Connect hay VPN với RTT 10 ms là 9 giây. Phát hiện trước bằng cách đếm số câu SQL mỗi request (trace hoặc log của driver) và đo RTT thật giữa hai nơi, rồi xếp app và database vào cùng move group.
- **Chuyển trước, hiện đại hoá sau**: hạn rời datacenter không dời được, còn dự án refactor thì hay trễ. Rehost hoặc replatform hệ thống lõi trước (ví dụ giữ Oracle nhưng chuyển sang RDS for Oracle), rồi hiện đại hoá trên cloud theo strangler. Cái giá: trả giấy phép Oracle thêm một thời gian, và một số việc làm hai lần.
- **Strangler fig** (Martin Fowler, 2004, theo cây đa bóp nghẹt cây chủ): lớp định tuyến là API gateway, load balancer theo path, hoặc một facade trong chính monolith. Lát cắt đầu tiên nên có giá trị thấy được, ít dữ liệu dùng chung, và có cách chuyển lưu lượng dần (theo tenant, theo loại sản phẩm, theo ngày tạo). Cách chia khéo: hồ sơ mới vào hệ thống mới, hồ sơ đang xử lý chạy hết vòng đời ở hệ thống cũ. Không cần migrate dữ liệu đang dở dang, chỉ cần dữ liệu lịch sử cho tra cứu. Tách module bên trong ứng dụng thì dùng [[branch-by-abstraction|branch by abstraction]] (bài Refactoring & nợ kỹ thuật); quy trình tách module thành service ở bài Modular monolith.
- **Các pattern thay thế hệ thống cũ** (loạt Patterns of Legacy Displacement trên martinfowler.com):
  - Divert the flow: chuyển trước các hoạt động dùng chung toàn công ty ra khỏi hệ thống cũ (ví dụ báo cáo tổng hợp đọc từ nhiều hệ thống, chuyển sang warehouse), để các phần còn lại dễ di dời hơn. Đưa một nhóm người dùng sang sớm để lấy phản hồi là việc khác: pilot hay canary.
  - Event interception: chặn các thay đổi trạng thái (từ message, từ CDC, từ lớp định tuyến) và phát thành event cho hệ thống mới, khi hệ thống cũ không phát event.
  - Legacy mimic: hệ thống mới giả làm giao diện mà hệ thống cũ mong đợi (ghi lại bảng cũ, gửi file cũ), để phần còn lại của hệ thống cũ không biết gì thay đổi.
  - Transitional architecture: code chỉ để sống trong giai đoạn chuyển (adapter, đồng bộ ngược, facade). Lên kế hoạch tắt nó từ đầu, có người phụ trách và ngày.
  - Feature parity là bẫy: hệ thống cũ có nhiều tính năng không ai còn dùng. Đo log sử dụng, hỏi người dùng thật, và chỉ làm lại những gì còn cần.
- **Viết lại một lần (big bang) hiếm khi đúng**: hệ thống cũ vẫn thay đổi mỗi tuần trong lúc bản mới đuổi theo, quy tắc nghiệp vụ ngầm nằm trong code không ai nhớ, và giá trị chỉ tới vào ngày cuối. Big bang chỉ hợp lý khi hệ thống nhỏ, dữ liệu ít và có thể dừng dịch vụ.
- **Nguồn sự thật trong giai đoạn chuyển**: viết rõ cho từng loại dữ liệu bên nào được ghi. Hệ thống cũ là nguồn thì hệ thống mới đọc bản sao qua CDC, mọi lệnh ghi đi qua API hoặc giao diện của hệ thống cũ. Sau khi chuyển quyền ghi, đảo chiều: hệ thống mới là nguồn, đồng bộ ngược về hệ thống cũ cho các báo cáo và tích hợp chưa chuyển. Không bao giờ để hai nơi cùng nhận ghi một bản ghi rồi "merge sau". Ghi hai nơi từ ứng dụng thì một bên lỗi là lệch vĩnh viễn; dùng [[outbox]] hoặc CDC (bài Outbox & CDC).
- **Parallel run và shadow traffic**: chạy cùng đầu vào qua cả hai hệ thống, trả kết quả của hệ thống cũ, so và ghi khác biệt (thư viện Scientist của GitHub làm đúng việc này cho code Ruby: control, candidate, so kết quả, luôn trả kết quả control). Chỉ áp cho thao tác đọc hoặc tính toán; với thao tác ghi, bản shadow phải ghi vào chỗ riêng và không gọi ra ngoài (gửi email, trừ tiền hai lần). Đặt ngưỡng khác biệt chấp nhận được và phân loại từng nhóm khác biệt trước khi chuyển.
- **Migrate dữ liệu bằng full load + CDC** (AWS DMS, Debezium, GoldenGate):
  - Nạp toàn bộ khi hệ thống cũ vẫn chạy, rồi CDC đuổi theo thay đổi. Downtime chỉ là lúc chặn ghi, chờ CDC hết lag, đối soát và đổi kết nối.
  - AWS DMS chỉ tạo bảng, primary key và đôi khi unique index ở đích; index phụ, khoá ngoại, giá trị mặc định phải tạo bằng công cụ chuyển schema (AWS SCT, DMS Schema Conversion) hay script riêng. Với task full load + CDC, tạo index phụ sau full load nhưng trước khi áp các thay đổi đã cache (setting `StopTaskCachedChangesNotApplied` dừng task đúng lúc đó): nạp nhanh mà lúc áp CDC không phải quét bảng thiếu index.
  - DMS ở limited LOB mode cắt LOB dài hơn giới hạn đã đặt. Đo độ dài LOB lớn nhất trước khi chọn mode.
  - Sequence không đi theo dữ liệu. Đo trên PostgreSQL 17.6: nạp 1.000 dòng có id sẵn vào cột identity, insert tiếp theo lỗi `duplicate key value violates unique constraint`; phải `SELECT setval(pg_get_serial_sequence('policy','id'), (SELECT max(id) FROM policy));` cho mọi sequence ngay trước khi mở ghi.
  - Trigger và khoá ngoại ở đích có thể chạy lại logic hay chặn thứ tự nạp: tắt trong lúc nạp, bật trước khi chuyển.
- **Đối soát**: so theo khoảng khoá, mỗi khoảng có số dòng, tổng các cột tiền và hash của các dòng đã chuẩn hoá. Đo trên 1.000 dòng chia 4 khoảng: sửa một dòng lệch 0,01 thì chỉ khoảng chứa nó đổi tổng và hash, nên biết ngay phải soi khoảng nào. Tổng không bắt được hai dòng đổi giá trị cho nhau; hash thì bắt được. Hash giữa hai loại database khác nhau chỉ khớp khi chuẩn hoá giống nhau: định dạng số, múi giờ, NULL, khoảng trắng cuối của `CHAR`. Đối soát cả trước và sau khi chuyển, và tiếp tục trong lúc đồng bộ ngược còn chạy.
- **Oracle sang PostgreSQL, các khác biệt làm hỏng dữ liệu hoặc code**:
  - Oracle coi chuỗi rỗng là NULL; PostgreSQL thì không (`'' is null` ra `false`). Dữ liệu cũ toàn NULL, code mới ghi `''`, và `WHERE middle_name IS NULL` bỏ sót các dòng mới. Chuẩn hoá một cách và kiểm bằng ràng buộc.
  - `DATE` của Oracle có giờ phút giây; chuyển sang `date` của PostgreSQL là mất giờ. Dùng `timestamp(0)`.
  - Tên không đặt trong nháy: Oracle đổi thành chữ hoa, PostgreSQL thành chữ thường. Code có `"CLAIM_ID"` trong nháy sẽ không tìm thấy cột.
  - Lỗi trong transaction: Oracle chỉ huỷ câu lỗi, transaction vẫn dùng tiếp được. PostgreSQL huỷ cả transaction: đo với pgjdbc 42.7.7, câu sau lỗi duplicate key nhận `25P02 current transaction is aborted`. Code bắt exception rồi chạy tiếp phải dùng [[savepoint]] (hoặc tham số `autosave` của pgjdbc, có chi phí mỗi câu).
  - `VARCHAR2(10)` mặc định tính theo byte, `varchar(10)` của PostgreSQL tính theo ký tự. Thứ tự sắp xếp chuỗi theo collation của database đích có thể khác `NLS_SORT` của Oracle.
  - PL/SQL package không có tương đương trực tiếp; extension orafce mô phỏng một số hàm và package của Oracle (`DBMS_OUTPUT`, `UTL_FILE`, `DBMS_PIPE`). Logic nằm trong procedure là phần tốn công nhất của chuyển database.
- **[[cutover|Cutover]]**: runbook có thời gian từng bước, người làm và điều kiện dừng; diễn tập ít nhất hai lần trên bản sao dữ liệu thật để đo thời gian. Ghi rõ điểm không quay lại: sau khi hệ thống mới nhận ghi mà không có đồng bộ ngược, rollback nghĩa là mất dữ liệu hoặc phải nhập tay. Có đồng bộ ngược thì đẩy điểm đó ra xa, đổi lại phải vận hành thêm một luồng và đối soát nó.
- **Chi phí và thời gian**: trong lúc chuyển, trả tiền cho cả hai nơi (datacenter, giấy phép cũ, cloud mới); giảm bằng các đợt nhỏ đều đặn và tắt ngay cái đã chuyển xong. Tắt hệ thống cũ là một mốc có ngày và người phụ trách, không phải "khi nào xong". Strangler không bao giờ tắt được phần cũ thì thành hai hệ thống phải bảo trì mãi.
