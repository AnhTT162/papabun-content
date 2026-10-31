## Quick

Hệ lưu trữ file và video có ba đường riêng: **upload** đi thẳng từ client lên [[object-storage|object storage]] theo từng phần ([[multipart-upload|multipart upload]] qua [[presigned-url|presigned URL]]), **xử lý** chạy bất đồng bộ sau khi file đã đủ (kiểm tra, [[transcoding|transcoding]] ra nhiều mức chất lượng), và **phát** qua [[cdn|CDN]]. Database chỉ giữ metadata và trạng thái. **File không bao giờ đi qua app server, và file chỉ được coi là sẵn sàng khi bước xử lý cuối cùng đã xong, không phải khi upload xong.**

## Interview

Tôi hỏi trước: loại file gì, lớn nhất bao nhiêu, bao nhiêu file mỗi ngày, ai được xem, file gốc có được mất không, upload xong bao lâu thì phải xem được. Giả định cho nền tảng khoá học: 500 video mỗi ngày, trung bình 15 phút và 1,5 GB, tối đa 20 GB; đỉnh 200.000 người xem cùng lúc; chỉ học viên đã mua được xem.

**Upload**: client gọi API tạo upload. Server tạo dòng metadata trạng thái `PENDING`, tự sinh key (không dùng tên file của người dùng), gọi `CreateMultipartUpload` và trả URL đã ký cho từng part. Client gửi các part song song, part nào lỗi thì gửi lại riêng part đó. Mô phỏng upload 2 GiB trên mạng trung bình rớt mỗi 500 MiB: gửi một lần phải gửi tổng cộng khoảng 29 GiB (gấp 14 lần), part 16 MiB chỉ gấp 1,02.

**Hoàn tất**: client báo API, API gọi `CompleteMultipartUpload`, kiểm kích thước thật, chuyển trạng thái `UPLOADED` và ghi job vào [[outbox|outbox]] trong cùng transaction.

**Xử lý**: worker kiểm định dạng bằng nội dung file chứ không tin `Content-Type`, rồi transcode ra [[adaptive-bitrate|ABR]]: 5 mức từ 240p tới 1080p, chia [[hls|HLS]] thành đoạn 6 giây, keyframe thẳng hàng giữa các mức để player đổi mức giữa chừng. Video dài thì cắt thành đoạn một phút, transcode song song trên nhiều worker. Kết quả ghi vào prefix có phiên bản; chỉ khi đủ mọi mức thì metadata mới chuyển `READY`.

**Phát**: 200.000 người × 3 Mbps là 600 Gbps, phải qua CDN. Bucket để private, CDN đọc bucket bằng quyền riêng, người xem nhận [[signed-cookie|signed cookie]] vì một video có hàng nghìn file đoạn.

**Bẫy**: đánh dấu sẵn sàng ngay khi upload xong; tin ETag là MD5 của file; quên dọn upload dở (S3 vẫn tính tiền các part); presigned URL cho từng part không giới hạn được tổng dung lượng.

## Deep

- **Ước lượng** cho nền tảng khoá học:
  - File gốc: 500 × 1,5 GB = 750 GB mỗi ngày, khoảng 270 TB mỗi năm.
  - Bản đã transcode, ladder 5/3/1,5/0,8/0,4 Mbps (tổng 10,7 Mbps): 4,82 GB cho mỗi giờ video. 125 giờ video mỗi ngày là khoảng 600 GB mỗi ngày.
  - Upload: 750 GB rải trong giờ làm việc là vài trăm Mbps vào S3, không qua server nào của mình.
  - Xem: đỉnh 600 Gbps ra từ CDN; origin chỉ nhận phần miss.
- **Multipart upload của S3**:
  - Part từ 5 MiB tới 5 GiB (part cuối được nhỏ hơn), tối đa 10.000 part. 5 MiB × 10.000 chỉ là 48,8 GiB, nên client phải chọn cỡ part theo cỡ file: 100 GiB cần part ít nhất 10,2 MiB, 1 TiB cần 105 MiB.
  - Part gửi song song, theo thứ tự bất kỳ. Gửi lại cùng số part thì ghi đè. Lưu `uploadId` trong metadata; app khởi động lại thì `ListParts` để biết part nào đã có và gửi tiếp.
  - `CompleteMultipartUpload` nhận danh sách số part và ETag theo thứ tự tăng dần. Request này có thể trả HTTP 200 mà body là lỗi; SDK của AWS tự xử lý, client HTTP tự viết thì phải đọc body.
  - Upload dở không hiện trong danh sách object nhưng các part vẫn bị tính tiền tới khi `Abort` hoặc `Complete`. Luôn có lifecycle rule `AbortIncompleteMultipartUpload`, ví dụ sau 7 ngày.
- **Lab cỡ part**: mô phỏng 2 GiB, điểm rớt mạng theo phân phối mũ trung bình 500 MiB, mỗi lần rớt chỉ mất part đang gửi:
  - Một lần PUT cả file: gửi trung bình 28,9 GiB (gấp 14,4, khớp công thức m·(e^(L/m) − 1)). Part 256 MiB: gấp 1,31. Part 64 MiB: 1,07. Part 16 MiB: 1,02. Part 8 MiB: 1,01.
  - Part nhỏ hơn thì nhiều request hơn (mỗi part một request ký và một lần bắt tay), nên mạng di động thường chọn 8–16 MiB, mạng ổn định chọn 64–100 MiB.
- **Giới hạn dung lượng khi dùng presigned**: presigned POST có policy `content-length-range` nhưng chỉ cho một request (tối đa 5 GB). Với multipart, server quyết định số part từ kích thước khai báo và chỉ ký đúng chừng đó số part; trước khi `Complete`, gọi `ListParts` cộng kích thước thật, vượt thì `Abort`; gửi kèm header `x-amz-mp-object-size` khi `Complete` thì S3 tự từ chối (400) nếu kích thước thật lệch con số đó. Policy của presigned POST đã nói ở bài Các khối xây dựng. Hạn URL ngắn (vài chục phút, ký thêm khi cần). Chữ ký SigV4 dài nhất 7 ngày, và nếu ký bằng credential tạm (role của pod, của task) thì URL hết hạn khi credential đó hết hạn, sớm hơn con số `expires` đã đặt.
- **[[etag|ETag]] không phải MD5**: lab với file 12 MiB, part 5 MiB: MD5 cả file là `78875d13...`, ETag là `704ec3a5...-3`, tức MD5 của chuỗi ghép các MD5 từng part, thêm số part. Cùng một file upload với cỡ part khác ra ETag khác. Kiểm toàn vẹn bằng checksum riêng. Với multipart có hai kiểu: full-object (chỉ CRC64NVME, CRC32, CRC32C) so được với checksum cả file mà client tính; composite (SHA-1, SHA-256) là checksum của các checksum từng part kèm `-N`, không so được với SHA-256 cả file. SDK AWS bản mới (từ cuối 2024) tự tính CRC khi upload. Lưu checksum full-object của file gốc trong metadata.
- **Giao thức resume khác**: [[resumable-upload|resumable upload]] của Google Cloud Storage (một session, gửi tiếp từ byte cuối server đã nhận), giao thức tus, và bản nháp IETF Resumable Uploads for HTTP (header `Upload-Offset`). Ứng dụng di động nên dùng upload nền của hệ điều hành (iOS `URLSession` background) để upload tiếp khi app bị tắt.
- **Ai gọi Complete**: client gọi thẳng S3 rồi dựa vào S3 event notification là đường dễ mất. Event của S3 là at-least-once, có thể trùng, có thể trễ cả phút, và không bảo đảm thứ tự, và không gửi thẳng vào SQS FIFO được (muốn vậy thì đi qua EventBridge). Cho API gọi `Complete` thì server biết chắc kết quả và ghi job cùng transaction. Vẫn cần job đối soát tìm upload `PENDING` quá vài giờ (client bỏ ngang) để `Abort` và dọn.
- **Kiểm tra file**:
  - Không tin `Content-Type` và đuôi file: đọc byte đầu (magic bytes) hoặc chạy `ffprobe` để biết là video thật, lấy thời lượng, codec, độ phân giải. Giới hạn thời lượng và độ phân giải trước khi transcode.
  - File tài liệu: quét mã độc trong vùng cách ly (bucket hoặc prefix riêng), chỉ chuyển sang vùng chính khi sạch.
  - Phục vụ file người dùng tải lên từ một tên miền riêng, không cùng tên miền với app: một file HTML hay SVG chứa script mà chạy dưới tên miền chính là stored XSS. Thêm `X-Content-Type-Options: nosniff`, và `Content-Disposition: attachment` cho loại không phải media.
- **Ladder và HLS**:
  - Mỗi mức là một độ phân giải và bitrate; player đo băng thông và đổi mức giữa các đoạn. 1 giờ video theo ladder ở trên tốn 2,25 + 1,35 + 0,68 + 0,36 + 0,18 = 4,82 GB.
  - Đặc tả HLS của Apple khuyên đoạn 6 giây. Keyframe cố định mỗi 2 giây ở mọi mức (ffmpeg `-g` cố định và `-sc_threshold 0` để không chèn keyframe khi đổi cảnh), để ranh giới đoạn trùng nhau giữa các mức.
  - CMAF (đoạn fMP4) dùng chung được cho cả HLS và DASH, khỏi lưu hai bộ đoạn.
  - HEVC hay AV1 giảm đáng kể bitrate cùng chất lượng nhưng encode tốn hơn nhiều và không phải thiết bị nào cũng giải được: chỉ encode thêm cho video được xem nhiều, H.264 vẫn là mức nền.
- **Transcode song song**: cắt video gốc tại keyframe thành đoạn khoảng một phút, mỗi đoạn một job, ghép các đoạn kết quả rồi sinh playlist. Video 15 phút xong trong vài phút thay vì bằng thời lượng. Worker chạy trên máy spot, job có lease và retry (bài Thiết kế job scheduler). Job idempotent theo `(video_id, profile_version)`: chạy lại ghi đè cùng prefix `videos/{id}/p{version}/`, không sinh bản thừa.
- **Đổi bản không làm gián đoạn người đang xem**: metadata trỏ tới prefix hiện hành. Transcode lại (ladder mới, sửa lỗi) ghi vào prefix mới, đổi con trỏ khi xong, xoá prefix cũ sau vài ngày. File đoạn không bao giờ bị ghi đè, nên CDN cache được rất lâu (`Cache-Control: max-age=31536000, immutable`).
- **Kiểm soát quyền xem**:
  - Bucket private, CDN đọc bucket bằng quyền riêng (CloudFront Origin Access Control), không ai đọc thẳng S3 được.
  - Signed URL hợp cho một file. HLS có playlist và hàng nghìn đoạn, nên dùng signed cookie (CloudFront) hoặc token trong đường dẫn mà edge kiểm được. Thời hạn ngắn, gia hạn khi player còn xem.
  - Signed cookie chỉ chặn người không có quyền, không chặn người có quyền tải về rồi chia sẻ. Nội dung cần bảo vệ thật thì dùng DRM (Widevine, FairPlay, PlayReady), đoạn mã hoá theo CENC (scheme `cbcs` để một bộ đoạn CMAF dùng được cho cả ba).
- **CDN và đuôi dài**: phân phối lượt xem theo Zipf trên 1 triệu video, nếu cache giữ đúng 10.000 video phổ biến nhất thì chỉ được 36% lượt xem khi phân phối thoải (s = 0,8), 68% khi dốc (s = 1,0). Khoá học cũ ít người xem nên miss nhiều; bật [[origin-shield|origin shield]] (bài DNS & CDN) để nhiều edge miss cùng đoạn chỉ tạo một request tới S3.
- **Tải MP4 trực tiếp**: player dùng [[range-request|range request]] (`Range: bytes=...`, server trả 206). Phần `moov` (chỉ mục của MP4) phải nằm đầu file (ffmpeg `-movflags +faststart`), nếu không player phải tải cuối file trước rồi mới phát được.
- **Chi phí lưu trữ**: bản gốc chỉ cần khi transcode lại, nên chuyển sang [[storage-class|storage class]] lạnh bằng lifecycle rule sau 30 ngày. Mỗi lớp có thời gian lưu tối thiểu: Standard-IA 30 ngày (và tính tối thiểu 128 KB mỗi object), Glacier Flexible Retrieval 90 ngày, Deep Archive 180 ngày; lấy lại từ Glacier Flexible Retrieval mất 3–5 giờ ở mức Standard, 1–5 phút ở mức Expedited (đắt hơn). Bản đã transcode được xem thì để Standard hoặc Intelligent-Tiering.
- **Metadata**: `files(id, owner_id, status, size_bytes, checksum, storage_key, upload_id, created_at)` và `renditions(file_id, profile_version, playlist_key, ready_at)`. Key do server sinh (UUID); tên file gốc chỉ là một cột để hiện ra và đặt `Content-Disposition`. Dùng tên file người dùng làm key gây trùng, lộ thông tin và lỗi đường dẫn.
- **Xoá**: đánh dấu xoá ở metadata để chặn quyền xem ngay, xoá object bất đồng bộ, purge CDN cho nội dung nhạy cảm. Bucket bật versioning thì xoá chỉ tạo delete marker, bản cũ vẫn bị tính tiền tới khi lifecycle dọn noncurrent version.
- **Đồng bộ file kiểu Dropbox: chia block**:
  - Chia file thành block, mỗi block định danh bằng SHA-256; chỉ gửi block mà server chưa có.
  - Lab với file 64 MiB, chèn 1 byte (hay 100 byte) ở vị trí 10 MiB: chia cố định 4 MiB thì 15/17 block đổi, phải gửi 56 MiB, vì mọi ranh giới sau chỗ chèn đều lệch. [[content-defined-chunking|Chia theo nội dung]] (gear hash, min 256 KiB, trung bình khoảng 1,2 MiB, max 4 MiB) chỉ đổi 1 block, gửi 0,83 MiB. Sửa tại chỗ không đổi độ dài thì cả hai cách đều chỉ đổi 1 block.
  - Khử trùng giữa nhiều người dùng tiết kiệm dung lượng nhưng lộ thông tin: upload xong tức thì nghĩa là ai đó đã có file này. Chỉ khử trùng trong phạm vi một người dùng, hoặc khử trùng phía server mà không báo cho client.
- **Quota**: giữ chỗ theo kích thước khai báo khi tạo upload, chốt theo kích thước thật khi `Complete`, nhả khi `Abort`. Cộng dồn bằng câu `UPDATE` có điều kiện để hai upload đồng thời không cùng vượt hạn mức.
