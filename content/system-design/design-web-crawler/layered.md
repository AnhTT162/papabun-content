## Quick

Web crawler tải trang, rút link mới, rồi lặp lại, trên hàng trăm triệu URL. Trái tim của nó là [[url-frontier|URL frontier]]: hàng đợi quyết định tải URL nào tiếp theo, vừa theo độ ưu tiên vừa theo [[crawl-politeness|politeness]] (không dồn request vào một host). **Tốc độ crawl bị chặn bởi số host chứ không bởi số máy: mỗi host chỉ nhận vài request mỗi giây, nên khi URL dồn vào vài site lớn thì thêm fetcher cũng không nhanh hơn.** Phần còn lại là chống trùng (URL đã [[url-normalization|chuẩn hoá]], nội dung gần giống nhau), tôn trọng [[robots-txt|robots.txt]], và tránh [[crawler-trap|bẫy crawl]].

## Interview

Tôi hỏi trước: crawl cả web hay một tập site, bao nhiêu URL, làm mới thường xuyên tới đâu, có cần chạy JavaScript không. Giả định cho dịch vụ so sánh giá: 20.000 shop, 200 triệu URL sản phẩm, làm mới cả tập mỗi tuần và 20 triệu trang phổ biến mỗi ngày. Tức khoảng 560 trang mỗi giây.

**Luồng**: frontier → fetcher ([[dns|DNS]] có cache, kiểm robots.txt, tải với timeout và giới hạn kích thước) → lưu bản thô lên S3 → parser rút dữ liệu và link → link mới qua chuẩn hoá và kiểm trùng rồi quay lại frontier.

**Frontier** có hai tầng. Tầng trước xếp URL theo ưu tiên (trang bán chạy, trang hay đổi giá). Tầng sau có một hàng đợi cho mỗi host, cùng một heap giữ "lúc sớm nhất được gọi host này". Frontier chia shard theo hash của host, nên mỗi host chỉ do một node lo và politeness không cần phối hợp giữa các node.

**Politeness là ràng buộc chính**: tôi mô phỏng 10 triệu URL trên 100.000 host phân bố Zipf, 1 request mỗi giây cho mỗi host, 1.000 fetcher. Nửa đầu xong trong 36 phút, nhưng 90% mất 50 giờ và 100% mất 9,6 ngày, vì host lớn nhất có 827.000 URL. Cách gỡ: thoả thuận tốc độ cao hơn với site lớn và tự giảm khi site chậm hay trả 429, dùng sitemap và conditional GET để không tải lại trang không đổi, và crawl theo ưu tiên thay vì cố crawl hết.

**Chống trùng**: chuẩn hoá URL rồi kiểm bằng [[bloom-filter|Bloom filter]] (9,6 bit mỗi URL ở 1% dương tính giả). Nội dung trùng thì so hash của phần nội dung chính, và dùng [[simhash|SimHash]] cho trang gần giống.

**Bẫy**: bộ lọc tổ hợp `?color=&size=&sort=` sinh vô hạn URL, lịch có link "tháng sau" không bao giờ hết, session id trong URL. Đặt giới hạn số URL và độ sâu cho mỗi host, và chạy JavaScript chỉ khi thật cần vì nó đắt gấp nhiều lần.

## Deep

- **Ước lượng** cho dịch vụ so sánh giá: 560 trang mỗi giây, HTML trung bình 150 KB, nén gzip khi truyền còn khoảng 30 KB, tức khoảng 17 MB/s (135 Mbps) vào. Lưu bản thô đã nén để parse lại khi đổi parser: khoảng 1,4 TB mỗi ngày, giữ 7 ngày là khoảng 10 TB trên S3 theo định dạng WARC (định dạng lưu trữ web: request, response và header trong một file). Dữ liệu đã rút (giá, tồn kho) nhỏ hơn nhiều và vào database.
- **Frontier kiểu Mercator**:
  - Front queue theo mức ưu tiên. Back queue: mỗi hàng đợi chỉ chứa URL của một host. Heap giữ `(next_allowed_time, back_queue)`.
  - Fetcher lấy đỉnh heap, chờ tới giờ cho phép, tải một URL, rồi đặt lại giờ cho phép là bây giờ cộng độ trễ của host. Back queue rỗng thì nạp thêm URL từ front queue.
  - Frontier lớn hơn RAM: phần đuôi của mỗi hàng đợi nằm trên đĩa (RocksDB, hoặc file theo host), chỉ phần đầu nằm trong bộ nhớ.
- **Shard theo host**: hash của host (dùng [[consistent-hashing|consistent hashing]] để thêm bớt node ít xáo trộn) quyết định node nào lo host đó. Link mới rút ra ở node A mà thuộc host của node B thì gửi sang B theo lô. Politeness nên tính theo cả IP: nhiều site nhỏ cùng nằm trên một shared hosting, và 50 host cùng IP mỗi host 1 request/giây là 50 request/giây vào một máy.
- **Politeness, mô phỏng**: 10 triệu URL trên 100.000 host theo Zipf, mỗi host tối đa 1 request mỗi giây, 1.000 fetcher mỗi lần tải 300 ms (trần 3.333 trang/giây).
  - Nếu URL rải đều thì chỉ mất 50 phút. Thực tế 50% xong sau 0,6 giờ.
  - Sau 1 giờ chỉ còn 300 host có URL, tốc độ còn 300 trang/giây. Sau 1 ngày còn 9 host, 9 trang/giây.
  - 90% xong sau 50 giờ, 99% sau 202 giờ, 100% sau 9,6 ngày, vì host lớn nhất có 827.120 URL.
  - Thêm fetcher không giúp được gì. Phải giảm số URL cần tải ở site lớn, hoặc tăng tốc độ được phép cho riêng site đó.
- **Tốc độ theo từng site**: bắt đầu thấp (ví dụ 1 request/giây), tăng dần khi thời gian phản hồi ổn định, giảm ngay khi chậm đi. Gặp 429 hay 503 thì lùi theo `Retry-After`. Site lớn thường chịu được hàng chục request mỗi giây, và có thể thoả thuận trực tiếp (feed hay API cho đối tác). `Crawl-delay` không có trong RFC 9309, nhiều crawler bỏ qua nó, nhưng crawler lịch sự vẫn nên tôn trọng.
- **robots.txt theo RFC 9309**:
  - Chọn nhóm `User-agent` khớp với tên crawler, không phân biệt hoa thường; nhiều nhóm cùng khớp thì gộp quy tắc lại; không có nhóm nào khớp thì dùng nhóm `*`.
  - Trong nhóm, quy tắc khớp **dài nhất** thắng; `Allow` và `Disallow` dài bằng nhau thì `Allow` thắng. `*` khớp mọi chuỗi, `$` đánh dấu cuối đường dẫn.
  - Lab tự viết theo quy tắc đó: với `Disallow: /shop/`, `Allow: /shop/product/`, `Disallow: /*?sort=`, thì `/shop/product/123?sort=price` vẫn được phép, vì `/shop/product/` (14 ký tự) dài hơn `/*?sort=` (8 ký tự). Riêng quy tắc `Disallow: /*.pdf$` chặn `/catalog.pdf` nhưng không chặn `/catalog.pdf?v=2` (trong lab URL đó vẫn bị `Disallow: /` chặn). `Allow: /folder` và `Disallow: /folder` dài bằng nhau thì ra allow.
  - Tải được robots.txt (2xx) thì theo quy tắc. Lỗi 4xx thì được crawl mọi thứ. Lỗi 5xx hay lỗi mạng thì phải coi như cấm toàn bộ. Theo ít nhất 5 lần redirect.
  - Không dùng bản cache quá 24 giờ, trừ khi robots.txt không truy cập được: khi đó được dùng bản cache cũ; chưa có bản cache thì coi như cấm toàn bộ. Phải đọc được ít nhất 500 KiB của file.
  - robots.txt là lời đề nghị, không phải kiểm soát truy cập. Crawler tử tế vẫn theo, và gửi `User-Agent` có link mô tả crawler kèm cách liên hệ.
- **Chuẩn hoá URL, lab JDK 27**:
  - `java.net.URI.normalize()` chỉ bỏ các đoạn `.` và `..`. `HTTP://Shop.Example.COM:80/a/./b/../c?utm_source=fb&id=7#reviews` thành `HTTP://Shop.Example.COM:80/a/c?utm_source=fb&id=7#reviews`: scheme và host vẫn hoa, cổng mặc định, tham số theo dõi và fragment vẫn còn.
  - Chuẩn hoá tự viết: scheme và host chữ thường, bỏ cổng mặc định, bỏ fragment, bỏ `utm_*` và các tham số session đã biết, sắp xếp tham số, viết hoa mã percent-encoding (`%e1` thành `%E1`). Kết quả là `http://shop.example.com/a/c?id=7`.
  - Bẫy: với host có dấu như `https://điệnmáy.vn/tivi`, `URI.getHost()` trả `null` vì `java.net.URI` không nhận ký tự ngoài ASCII trong tên host. Phải lấy authority rồi `IDN.toASCII` (ra `xn--...`).
  - Bỏ tham số nào là quyết định theo từng site: `?page=2` là trang khác, `?ref=home` thì không. Dùng `<link rel="canonical">` của trang nếu có.
- **URL đã thấy**: 10 tỷ URL ở 1% dương tính giả cần khoảng 12 GB Bloom filter, ở 0,1% khoảng 18 GB. Lab với 10 triệu URL, m = 95,9 triệu bit, k = 7, đo được tỉ lệ dương tính giả 1,007%. Dương tính giả nghĩa là bỏ qua một URL chưa từng tải, chấp nhận được với crawler. Cần chính xác (ví dụ URL đã biết để lập lịch tải lại) thì giữ bảng key-value theo hash của URL đã chuẩn hoá trên đĩa (RocksDB), Bloom filter đứng trước để tránh đọc đĩa với URL mới.
- **Nội dung trùng**:
  - Trùng y hệt: SHA-256 của phần nội dung chính. Hash cả trang thì không bao giờ trùng, vì trang có giờ cập nhật, số người đang xem, quảng cáo thay đổi.
  - Gần giống: SimHash 64 bit, mỗi đặc trưng (ví dụ cụm 3 từ) được hash rồi cộng trừ theo từng bit. Hai trang giống nhau có ít bit khác nhau ([[hamming-distance|Hamming distance]] nhỏ). Bài báo của Google năm 2007 dùng 64 bit, ngưỡng 3 bit cho 8 tỷ trang.
  - Lab trên một trang sản phẩm ngắn khoảng 100 từ: thêm dòng giờ cập nhật làm khác 9 bit, đổi khối quảng cáo cũng 9 bit, sản phẩm cùng dòng khác 6 thông số lại chỉ 11 bit, sản phẩm khác hẳn 30 bit. Với trang ngắn, ngưỡng 3 bit không bắt được bản gần trùng, và ngưỡng đủ rộng để bắt thì lại nhập nhầm hai sản phẩm khác nhau.
  - Bài học: rút phần nội dung chính (bỏ menu, quảng cáo, dòng giờ) trước khi hash, và với trang sản phẩm thì so theo dữ liệu đã rút (mã sản phẩm, giá) thay vì theo văn bản.
- **Tải lại thông minh**:
  - [[conditional-get|Conditional GET]]: gửi `If-None-Match` với [[etag|ETag]] hoặc `If-Modified-Since` với giờ lần trước. Trang không đổi thì server trả 304, không có body.
  - [[sitemap|Sitemap]] có `<lastmod>`, đáng tin ở site làm cẩn thận.
  - Chu kỳ theo lịch sử thay đổi: trang đổi kể từ lần trước thì giảm chu kỳ một nửa, không đổi thì tăng gấp đôi, ví dụ trong khoảng 1 giờ tới 30 ngày. Trang bán chạy được ưu tiên hơn trang không ai xem.
- **Bẫy crawl**:
  - Bộ lọc tổ hợp: 10 màu × 8 cỡ × 5 cách sắp xếp × 20 trang là 8.000 URL cho cùng một danh mục.
  - Lịch có "tháng sau" chạy vô hạn, session id trong đường dẫn, đường dẫn tương đối lỗi sinh `/a/a/a/a/...`.
  - Cách chặn: giới hạn số URL mỗi host mỗi chu kỳ (crawl budget) và độ sâu từ trang gốc; phát hiện mẫu URL có quá nhiều biến thể của một tham số; giới hạn độ dài URL; ưu tiên sitemap hơn link tự tìm.
- **Fetcher bằng Java**:
  - `HttpClient` với [[virtual-thread|virtual thread]] phù hợp, vì việc chủ yếu là chờ mạng. Đặt `connectTimeout` và `timeout` cho từng request.
  - Đọc body dạng stream và dừng khi vượt giới hạn (ví dụ 5 MB).
  - `Redirect.NORMAL` theo redirect trừ khi đi từ HTTPS sang HTTP. Tự theo redirect thì nên giới hạn số lần, và cho mỗi URL đích đi qua chuẩn hoá và kiểm trùng.
  - `java.net.http.HttpClient` không tự giải nén: gửi `Accept-Encoding: gzip` thì nhận về đúng các byte gzip (lab: hai byte đầu là `1f 8b`) và phải tự bọc `GZIPInputStream`.
  - DNS: cache lâu hơn mặc định, hoặc chạy resolver riêng, vì crawl hàng chục nghìn host là hàng chục nghìn lần tra DNS (bài DNS & CDN).
- **JavaScript**: trình duyệt headless tốn CPU và RAM gấp hàng chục lần một lần tải HTML. Trước khi bật, kiểm xem trang có dữ liệu sẵn trong HTML không: nhiều trang sản phẩm nhúng JSON-LD (`<script type="application/ld+json">` theo schema.org `Product` có giá trong `offers`), hoặc gọi một API JSON mà đọc thẳng được. Chỉ dùng headless cho các site thật sự cần, và cho chúng một nhóm máy riêng.
- **Quan sát**: số trang mỗi giây theo host lớn, tỉ lệ lỗi theo mã (429, 5xx, timeout), tỉ lệ 304 khi tải lại, độ dài frontier theo mức ưu tiên, tuổi của dữ liệu ở trang bán chạy (lần tải thành công gần nhất), và số URL mới mỗi host (tăng vọt thường là bẫy crawl).
