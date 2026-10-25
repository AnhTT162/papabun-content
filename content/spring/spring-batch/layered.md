## Quick

Spring Batch chạy việc xử lý lô (đối soát, tính lãi, xuất file, import dữ liệu) theo mô hình **[[chunk-processing|chunk]]**: đọc từng item, xử lý, rồi ghi theo nhóm, mỗi nhóm một transaction. Trạng thái của mọi lần chạy và vị trí đã xử lý được lưu trong **[[job-repository|JobRepository]]** (các bảng `BATCH_*`), nhờ đó job lỗi giữa chừng có thể **chạy lại từ chunk đã commit cuối cùng** thay vì từ đầu. Phần khó không nằm ở API, mà ở chỗ làm cho job chạy lại an toàn, chạy song song đúng, và chỉ chạy một bản trên cả cụm.

## Interview

**Các khái niệm**:
- `Job` gồm nhiều `Step`. Mỗi lần chạy với một bộ tham số định danh là một [[job-instance|`JobInstance`]]; mỗi lần thử của instance đó là một `JobExecution`.
- Instance đã `COMPLETED` không chạy lại được với cùng tham số (`JobInstanceAlreadyCompleteException`); job hằng ngày thường dùng ngày nghiệp vụ làm tham số định danh.
- Step dạng chunk: `ItemReader` → `ItemProcessor` → `ItemWriter`. Với chunk 500, transaction bao 500 lần đọc và xử lý cùng một lần ghi, rồi commit kèm `ExecutionContext` (vị trí đọc).

**Chạy lại (restart)**: execution lỗi thì chạy lại cùng tham số, reader đọc vị trí từ `ExecutionContext` và đi tiếp. Điều kiện:
- Reader phải có thứ tự ổn định (`ORDER BY` theo khoá duy nhất). `JdbcPagingItemReader` phân trang theo `sortKey` kiểu [[keyset-pagination|keyset]].
- Writer phải [[idempotency-key|idempotent]]: chunk lỗi sau khi đã gửi ra ngoài (gọi API, gửi Kafka) sẽ được ghi lại lần nữa.

**Skip và retry** (`faultTolerant()`):
- `retry(TransientDataAccessException.class).retryLimit(3)` cho lỗi tạm thời.
- `skip(ValidationException.class).skipLimit(100)` để bỏ qua dòng hỏng mà không dừng cả job; ghi dòng bị bỏ qua ra đâu đó bằng `SkipListener`.
- Khi **ghi** lỗi, Spring Batch rollback chunk rồi xử lý lại từng item để tìm item hỏng: processor bị gọi lại, nên không được có tác dụng phụ.

**Tăng tốc**:
- Multi-threaded step: ở Batch 5 các thread dùng chung một reader, nên reader phải thread-safe và mất vị trí khi restart; Batch 6 (`chunk(int)` mới) đọc trên một thread, xử lý song song.
- **[[step-partitioning|Partitioning]]**: chia dữ liệu thành dải id, mỗi dải là một step riêng có `ExecutionContext` riêng, chạy song song trên thread pool hoặc trên nhiều worker. Restart được theo từng partition.

**Chạy trong cụm**: Boot mặc định chạy job lúc ứng dụng khởi động. Deploy 3 pod là 3 lần khởi chạy; `JobRepository` chặn hai execution cùng instance chạy cùng lúc, nhưng job có tham số khác nhau (như `run.id` tự tăng) vẫn chạy trùng. Nên chạy job như một tiến trình riêng (Kubernetes `CronJob` với `concurrencyPolicy: Forbid`) thay vì trong service web.

## Deep

- **Spring Batch 5 (Boot 3)**:
  - `JobBuilderFactory` và `StepBuilderFactory` bị deprecated ở 5.0 và xoá ở 5.2; dùng `new JobBuilder("name", jobRepository)` và `new StepBuilder("name", jobRepository).chunk(500, transactionManager)`, transaction manager phải truyền rõ.
  - Thêm `@EnableBatchProcessing` vào ứng dụng Boot 3 sẽ **tắt** auto-configuration của Boot cho Batch (kể cả chạy job lúc khởi động và tạo bảng).
  - Ứng dụng có nhiều job thì phải đặt `spring.batch.job.name` để Boot biết chạy job nào lúc khởi động.
- **Spring Batch 6 (Boot 4)**: `JobOperator` thay `JobLauncher` làm điểm vào chính, `JobExplorer` gộp vào `JobRepository`, chunk step được viết lại. Boot 4 tách starter: `spring-boot-starter-batch` dùng repository không cần database, `spring-boot-starter-batch-jdbc` lưu metadata vào database; cần restart sau khi pod chết thì phải dùng bản JDBC. API `chunk(500, transactionManager)` của bản 5 bị deprecated; dùng `chunk(500).transactionManager(tm)`. Không dùng Boot thì `@EnableBatchProcessing` ở bản 6 không lưu metadata; cần `@EnableJdbcJobRepository` để restart được.
- **Execution kẹt ở `STARTED`**: pod bị `kill -9` hay OOMKilled thì không ai cập nhật trạng thái. Lần chạy sau báo `JobExecutionAlreadyRunningException`.
  - Batch 6: gọi `jobOperator.recover(execution)` để đánh dấu `FAILED`, rồi restart.
  - Batch 5: phải cập nhật `BATCH_JOB_EXECUTION` và `BATCH_STEP_EXECUTION` sang `FAILED` (kèm `END_TIME`) bằng script có kiểm soát. Đừng dùng `abandon`: execution `ABANDONED` không restart được.
- **Chặn chạy trùng**: `createJobExecution` chạy ở isolation `SERIALIZABLE` (`isolationLevelForCreate`), nên khi nhiều tiến trình cùng tạo execution cho một instance, chỉ một bên thành công. Hạ isolation này (một số database buộc phải hạ) là mở cửa cho chạy trùng.
- **Reader**:
  - `JdbcCursorItemReader` giữ một cursor mở suốt step, nhanh nhưng giữ connection lâu và không thread-safe; restart bằng cách đọc bỏ qua số dòng đã xử lý.
  - `JdbcPagingItemReader` thread-safe, mỗi trang một query theo `sortKey`; muốn dùng trong multi-threaded step thì `saveState(false)` và chấp nhận không restart được.
  - Với PostgreSQL, cursor reader cần `fetchSize` và `connectionAutoCommit(false)`; với MySQL cần `useCursorFetch=true` hoặc fetch size `Integer.MIN_VALUE`. Thiếu thì driver tải hết bảng vào heap (bài JDBC & cách ứng dụng nói chuyện với DB).
  - `JpaPagingItemReader` phân trang bằng `OFFSET`: chậm dần ở trang sau và dễ sót dòng nếu dữ liệu thay đổi trong lúc chạy.
- **Writer**:
  - `JdbcBatchItemWriter` dùng JDBC batch cho cả chunk.
  - `JpaItemWriter` gọi `merge` từng entity; mỗi chunk là một transaction nên persistence context không phình, nhưng vẫn chậm hơn JDBC batch nhiều lần (bài Spring Data JPA & Hibernate chuyên sâu).
  - Ghi ra file thì `FlatFileItemWriter` hỗ trợ restart bằng cách cắt file về vị trí đã commit.
- **Chọn kích thước chunk**: lớn thì ít commit hơn, nhưng mỗi lần lỗi phải làm lại nhiều hơn và lock giữ lâu hơn. Vài trăm tới vài nghìn là điểm bắt đầu; đo thời gian mỗi chunk thay vì đoán.
- **Partitioning chi tiết**:
  - `Partitioner` trả về các `ExecutionContext`, ví dụ `minId`/`maxId` cho từng dải; số partition nên lớn hơn số thread để dải chậm không kéo dài cả job.
  - Mỗi partition dùng connection riêng: pool phải đủ cho số thread cộng các thành phần khác.
  - Remote partitioning gửi partition qua message broker tới worker khác (Spring Batch Integration).
- **Kết thúc và mã thoát**: chạy như tiến trình riêng thì `System.exit(SpringApplication.exit(context))` để mã thoát phản ánh kết quả job; scheduler (CronJob, Airflow) dựa vào đó để báo lỗi và chạy lại.
- **Dọn metadata**: các bảng `BATCH_*` lớn dần theo mỗi lần chạy; cần job dọn bản ghi cũ theo thời gian lưu giữ.
- **Khi nào không cần Spring Batch**: việc nhỏ chạy vài giây và chạy lại từ đầu cũng được thì một method `@Scheduled` với ShedLock (bài @Async, @Scheduled & event) là đủ. Xử lý luồng liên tục thì dùng Kafka consumer. Biến đổi dữ liệu lớn trong cùng database thì một câu SQL `INSERT ... SELECT` theo lô thường nhanh hơn hẳn.
