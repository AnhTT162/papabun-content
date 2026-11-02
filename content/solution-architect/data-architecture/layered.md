## Quick

Database nghiệp vụ ([[oltp|OLTP]]) được tối ưu cho nhiều transaction nhỏ; báo cáo và phân tích ([[olap|OLAP]]) quét hàng triệu dòng, join nhiều nguồn và giữ lịch sử. Kiến trúc dữ liệu là đường đi từ hệ thống nguồn qua nạp, lưu, mô hình hoá tới người dùng báo cáo. **Báo cáo không chạy trên primary; mỗi đường nạp phải bắt được cả dòng commit muộn lẫn dòng bị xoá, có người sở hữu, có độ tươi đã cam kết và có đối soát với nguồn.**

## Interview

Tôi bắt đầu từ câu hỏi người dùng dữ liệu: báo cáo nào, trễ bao lâu thì chấp nhận được, cần lịch sử bao xa, cần join những nguồn nào. Câu trả lời quyết định nên dừng ở bậc nào.

Bậc đầu là [[read-replica|read replica]] dành riêng cho báo cáo. Rẻ, nhưng chỉ có một nguồn và không giữ lịch sử. Trên PostgreSQL, query dài trên replica hoặc bị huỷ, hoặc giữ dòng chết trên primary nếu bật [[hot-standby-feedback|hot standby feedback]]. Nên không bao giờ dùng chung replica của ứng dụng cho BI.

Khi cần nhiều nguồn, lịch sử và quét lớn, tôi đưa dữ liệu sang [[data-warehouse|data warehouse]] hoặc [[lakehouse|lakehouse]]. Lakehouse là file [[parquet|Parquet]] trên object storage cộng một [[open-table-format|open table format]] như Iceberg, để có transaction và nhiều engine cùng đọc. Đội nhỏ thì warehouse managed thường đủ.

Về nạp dữ liệu, tôi ưu tiên [[cdc|CDC]] đọc log giao dịch. Trích xuất theo `updated_at > watermark` bỏ sót dòng của transaction commit muộn và không thấy dòng bị xoá. Tôi theo [[elt|ELT]]: nạp bản thô trước, biến đổi bằng SQL trong warehouse (thường là [[dbt|dbt]]), để sửa logic xong thì chạy lại từ bản thô được.

Mô hình cho báo cáo là [[star-schema|star schema]]: bảng fact ở một grain rõ ràng, bảng dimension mang ngữ cảnh. Thuộc tính thay đổi theo thời gian như vùng của khách thì dùng [[slowly-changing-dimension|SCD type 2]] để số năm ngoái không tự đổi.

Bẫy hay gặp: CDC thô làm lộ schema nội bộ nên team ứng dụng đổi tên cột là pipeline vỡ, cần [[data-contract|data contract]]. Dựng streaming cho mọi bảng trong khi báo cáo chỉ cần số mỗi giờ. Không đo độ tươi và không đối soát tổng với nguồn. Và chép PII thô vào kho mà ai cũng đọc được.

## Deep

- **Bậc thang tách tải báo cáo**, đi lên khi bậc dưới không đủ:
  - Query trên primary: chỉ cho truy vấn nhỏ có index, có `statement_timeout`.
  - Replica riêng cho BI: không chung với replica phục vụ ứng dụng.
  - Bảng tổng hợp hoặc [[materialized-view|materialized view]] làm mới định kỳ.
  - Warehouse hoặc OLAP engine, nạp bằng CDC hoặc theo lô.
  - Chọn theo độ tươi cần, hình dạng truy vấn, số nguồn phải join, lịch sử cần giữ.
- **Replica dùng cho báo cáo trên PostgreSQL**: cơ chế xung đột ở bài Replication & high availability và bài MVCC, VACUUM & undo log; đây là hệ quả kiến trúc. Đã chạy PostgreSQL 17.6 trên máy local, báo cáo giữ snapshot 45 giây trong khi primary xoá 100.000 dòng rồi `VACUUM`:
  - `hot_standby_feedback = off`: standby ngừng áp WAL, `replay_lag` lên 10 → 20 → 30,4 giây, rồi huỷ báo cáo sau 33 giây với `canceling statement due to conflict with recovery`. Trong 30 giây đó mọi lượt đọc khác trên replica thấy dữ liệu cũ.
  - `hot_standby_feedback = on`: báo cáo chạy xong, lag gần 0, nhưng `VACUUM` trên primary để lại đủ 100.000 dòng chết (`n_dead_tup = 100000`), vì replica giữ lùi [[xmin-horizon|xmin horizon]] của primary. Báo cáo chạy hàng giờ thì bảng cập nhật nhiều của primary phình.
  - Bật feedback cũng không hết huỷ hẳn: xung đột khoá (`DROP`, `TRUNCATE`, VACUUM cắt page rỗng cuối bảng) vẫn huỷ query trên replica.
  - Với replica chỉ cho BI: tắt feedback, tăng `max_standby_streaming_delay` (mặc định 30 giây) theo độ trễ BI chấp nhận được, đặt `statement_timeout` cho user BI. Xuất dữ liệu nhiều giờ thì chuyển sang warehouse.
  - MySQL không huỷ query trên replica theo kiểu này, nhưng SELECT dài giữ metadata lock: một DDL được nhân bản tới phải chờ, replica trễ theo.
- **Warehouse, lake, lakehouse**:
  - Warehouse (BigQuery, Redshift, Snowflake): schema khi ghi, SQL, lưu theo cột, managed. Tính tiền theo dữ liệu quét hoặc theo compute.
  - [[data-lake|Data lake]]: file trên object storage, schema khi đọc, rẻ và nhận mọi định dạng. Không có transaction: job ghi dở để lại file lẻ, hai job ghi cùng lúc giẫm nhau, không ai biết file nào còn dùng. Thiếu catalog và quy ước thì thành bãi rác dữ liệu.
  - Lakehouse: open table format (Apache Iceberg, Delta Lake, Apache Hudi) giữ metadata và snapshot trên chính object storage. Mỗi lần ghi là một commit nguyên tử (với Iceberg là đổi con trỏ tới file metadata mới trong catalog), có time travel, đổi schema không viết lại dữ liệu. Iceberg còn đổi được cách partition mà không ghi lại dữ liệu cũ; Delta Lake phải ghi lại bảng hoặc chuyển sang liquid clustering. Spark, Flink, Trino, Doris và nhiều warehouse cùng đọc một bảng.
  - Giá của lakehouse: phải vận hành compaction (gộp file nhỏ), xoá snapshot và file mồ côi, catalog. Ghi streaming mỗi phút sinh rất nhiều file nhỏ.
- **Parquet**: định dạng file lưu theo cột, chia row group, mỗi cột có thống kê min/max nên engine bỏ qua được row group không khớp điều kiện (cùng ý tưởng zone map ở bài OLAP & Apache Doris), nén tốt vì giá trị cùng cột giống nhau. Chọn ít cột thì đọc ít byte; `SELECT *` trên warehouse tính tiền theo dữ liệu quét là đắt.
- **[[etl|ETL]] và ELT**: ETL biến đổi trước khi nạp, hợp khi đích đắt hoặc phải che dữ liệu nhạy cảm trước khi rời nguồn. ELT nạp thô rồi biến đổi trong warehouse bằng SQL, giữ được bản thô để chạy lại khi sửa logic ([[backfill|backfill]]). Bẫy của ELT: PII thô nằm trong kho mà nhiều người có quyền đọc.
- **Trích xuất theo watermark và bẫy của nó** ([[incremental-extraction|trích xuất tăng dần]]): đã chạy PostgreSQL 17.6, job lấy `updated_at > watermark` rồi đặt watermark bằng giá trị lớn nhất đã thấy.
  - Transaction A chèn đơn 1 (`updated_at = now()` là lúc transaction bắt đầu) và chưa commit. Transaction B chèn đơn 2 và xoá đơn 100, commit. Job chạy: chỉ thấy đơn 2, watermark nhảy tới giờ của đơn 2.
  - A commit. Lần chạy sau: `updated_at` của đơn 1 nhỏ hơn watermark nên không bao giờ được lấy. Kho có [2, 100], nguồn có [1, 2]: thiếu đơn 1, thừa đơn 100 đã xoá.
  - Đổi `now()` sang `clock_timestamp()` không sửa được: mọi mốc thời gian gán trước lúc commit đều có lỗ này.
  - Lùi watermark một khoảng chồng lấn rồi khử trùng theo khoá chỉ giảm rủi ro, không loại được transaction dài hơn khoảng đó. Xoá cứng thì phải đổi sang xoá mềm hoặc so toàn bộ khoá định kỳ.
  - CDC đọc log theo thứ tự commit và thấy cả lệnh xoá, nên tránh được cả hai lỗi.
- **CDC cho phân tích**: Debezium chụp snapshot ban đầu rồi đọc log; lệnh xoá thành event riêng. Change log giữ nguyên ở bronze; bảng trạng thái hiện tại áp bằng `MERGE` theo khoá chính, sau khi giữ thay đổi có LSN lớn nhất của mỗi khoá trong lô (nhiều warehouse báo lỗi khi một dòng đích khớp nhiều dòng nguồn), để nạp lại không nhân đôi. [[replication-slot|Slot logical]] giữ WAL trên primary khi connector dừng: đặt `max_slot_wal_keep_size` và cảnh báo (bài Transactional outbox & CDC). Từ PostgreSQL 17, slot logical tạo với `failover = true` và standby bật `sync_replication_slots` thì đi theo failover; bản cũ hơn mất slot khi chuyển primary, connector phải snapshot lại. CDC từ hệ thống cũ đi qua anti-corruption layer (bài Integration patterns).
- **Data contract**: CDC thô biến bảng nội bộ của team ứng dụng thành giao diện cho team dữ liệu mà không ai đồng ý. Ghi rõ bảng và cột nào thuộc hợp đồng, kiểu và nghĩa, người sở hữu; đổi theo expand-contract; CI của repo ứng dụng kiểm migration không phá hợp đồng. Hoặc phát event nghiệp vụ qua outbox dành cho phân tích thay vì để lộ bảng.
- **[[medallion-architecture|Medallion]]**: bronze giữ change log thô như nhận (append, có LSN và thời điểm nạp, không `MERGE` đè, vì SCD type 2 và việc chạy lại đều dựng từ đây); silver làm sạch, khử trùng, chuẩn hoá mã, che PII; gold là bảng phục vụ báo cáo theo nghiệp vụ. Ba tầng là quy ước, không phải bắt buộc; điều quan trọng là giữ bản thô để chạy lại.
- **Mô hình dimension (Kimball)**:
  - Chốt grain trước: một dòng fact là một dòng đơn hàng, hay một đơn, hay tổng theo ngày. Trộn grain trong một bảng fact làm cộng sai.
  - [[fact-table|Fact]] giữ số đo cộng được (số lượng, tiền) và khoá tới dimension. [[dimension-table|Dimension]] giữ ngữ cảnh để lọc và nhóm (khách, sản phẩm, cửa hàng, ngày).
  - SCD type 1 ghi đè: đơn giản, nhưng báo cáo quá khứ đổi theo giá trị hiện tại. Type 2 thêm dòng mới với `valid_from`, `valid_to` và [[surrogate-key|surrogate key]] riêng mỗi phiên bản; fact trỏ tới phiên bản đúng lúc phát sinh. Type 3 giữ thêm cột giá trị trước, hiếm dùng.
  - Ví dụ: khách mua 10 triệu đồng năm 2025 khi ở Hà Nội, tháng 3/2026 chuyển vào TP.HCM. Type 1: doanh thu 2025 của Hà Nội tự giảm 10 triệu khi báo cáo chạy lại. Type 2: giữ ở Hà Nội. Thường cần cả hai câu hỏi, nên giữ thêm cột vùng hiện tại trên mọi phiên bản (Kimball gọi là type 6).
- **Thời gian trong dữ liệu**: event time (lúc xảy ra) khác processing time (lúc nạp). Dữ liệu tới muộn (POS mất mạng đồng bộ sau hai ngày) làm thay đổi partition cũ: nạp idempotent bằng `MERGE` hoặc ghi đè cả partition, và chạy lại vài ngày gần nhất. Ngày kinh doanh theo múi giờ nào phải ghi trong định nghĩa chỉ số (bài Thời gian, múi giờ & encoding).
- **[[lambda-architecture|Lambda]] và [[kappa-architecture|Kappa]]**: Lambda chạy song song lớp batch (đúng, chậm) và lớp speed (nhanh, gần đúng), hai bộ code cho một chỉ số nên hay lệch nhau. Kappa chỉ có luồng stream, tính lại bằng cách đọc lại log từ đầu, cần log giữ đủ lâu. Thực tế phần lớn báo cáo chỉ cần mỗi giờ hoặc mỗi ngày; micro-batch 5–15 phút từ CDC đủ cho đa số yêu cầu "gần real-time" với chi phí vận hành thấp hơn nhiều so với streaming đầy đủ.
- **Phục vụ dữ liệu**: BI nội bộ trên warehouse. Dashboard cho khách hàng bên ngoài (hàng nghìn truy vấn mỗi phút, cần dưới một giây) thường cần OLAP engine real-time như Doris (bài OLAP & Apache Doris). [[reverse-etl|Reverse ETL]] đẩy kết quả tính trong kho (phân khúc khách, điểm rủi ro) ngược về CRM hay ứng dụng; khi đó kho thành phụ thuộc của luồng nghiệp vụ và cần SLA như hệ thống sản xuất.
- **Chất lượng và vận hành**: mỗi bảng gold có người sở hữu và cam kết độ tươi ("doanh thu hôm qua có trước 6 giờ sáng"). Đo độ tươi, số dòng so với ngày trước, null bất thường, khoá trùng. [[reconciliation|Đối soát]] tổng với nguồn theo ngày kinh doanh: số đơn, tổng tiền (cách làm ở bài Integration patterns).
- **Quản trị**: [[data-catalog|data catalog]] ghi bảng nào nghĩa gì, ai sở hữu; [[data-lineage|lineage]] cho biết một chỉ số đi từ bảng nguồn nào, đổi cột thì ảnh hưởng tới báo cáo nào. Phân quyền theo cột và dòng, che PII ngay ở tầng silver. Yêu cầu xoá dữ liệu cá nhân phải chạy được tới cả kho và các snapshot cũ (bài Dữ liệu cá nhân & tuân thủ).
- **[[data-mesh|Data mesh]]** (Zhamak Dehghani): bốn nguyên tắc: domain sở hữu dữ liệu của mình, dữ liệu là sản phẩm có người dùng và chất lượng, nền tảng tự phục vụ, quản trị liên kết bằng chính sách tự động. Hợp khi nhiều domain và team dữ liệu trung tâm thành nút thắt. Thiếu nền tảng và quản trị thì thành nhiều kho rời nhau, mỗi nơi định nghĩa "doanh thu" một kiểu. Công ty vài team không cần.
- **Chi phí**: warehouse tính theo dữ liệu quét thì partition theo ngày và cluster theo cột hay lọc; dashboard tự làm mới mỗi phút trên bảng lớn là nguồn hoá đơn bất ngờ. Đặt giới hạn quét hoặc ngân sách cho mỗi user và mỗi dashboard.
