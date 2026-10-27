## Quick

Thời gian người dùng chờ phần lớn nằm ngoài server: **số [[rtt|round-trip]], số byte phải tải, và thứ gì được cache**. Giảm theo thứ tự đó: bớt request nối tiếp, [[http-compression|nén]] và cắt payload thừa, cache file tĩnh bằng tên có hash và [[cdn|CDN]]. Đo bằng [[core-web-vitals|Core Web Vitals]] ở **p75 của người dùng thật**, không chỉ bằng Lighthouse.

## Interview

**Core Web Vitals** là ba chỉ số Google dùng để đánh giá trải nghiệm, xét ở p75 lượt tải trang, tách mobile và desktop:
- [[lcp|LCP]]: thời điểm phần nội dung lớn nhất hiện ra, tốt khi ≤ 2,5 giây.
- [[inp|INP]]: độ trễ từ lúc người dùng bấm tới khi màn hình phản hồi, tốt khi ≤ 200ms. INP thay FID từ tháng 3/2024.
- [[cls|CLS]]: mức nội dung bị xô lệch khi tải, tốt khi ≤ 0,1.

**LCP chia thành bốn phần**: [[ttfb|TTFB]] (chờ byte đầu của HTML), độ trễ trước khi bắt đầu tải tài nguyên LCP, thời gian tải nó, và thời gian render. Biết phần nào lớn nhất thì mới biết sửa ở server, ở mạng hay ở frontend.

**Round-trip đắt nhất**: mạng di động có RTT 100ms trở lên. Trang gọi 10 API nối tiếp là ít nhất 1 giây chỉ để chờ mạng, dù server trả trong 20ms. Gộp lời gọi (endpoint tổng hợp, [[bff|BFF]]), gọi song song, và dùng lại kết nối (keep-alive, HTTP/2).

**Byte**: nén text bằng gzip hoặc Brotli (giảm JSON 70–90%), không nén ảnh và video vì chúng đã nén sẵn. Trả đúng trường màn hình cần thay vì cả entity, phân trang, ảnh đúng kích thước và định dạng AVIF hoặc WebP.

**[[http-caching|Cache]]**: file tĩnh có hash nội dung trong tên thì `Cache-Control: public, max-age=31536000, immutable`; HTML thì `no-cache` kèm [[etag|`ETag`]]. Đổi nội dung là đổi tên file ([[cache-busting|cache busting]]), nên cache được lâu mà vẫn cập nhật ngay. Đặt CDN trước để file tĩnh được trả từ máy chủ gần người dùng. Cơ chế `Cache-Control`, `Vary` và CDN xem bài Cache là gì & cache ở đâu.

**Bẫy hay gặp**: lazy-load chính ảnh LCP, filter của server gắn `no-store` cho mọi response kể cả file tĩnh, cache dài file tên cố định, và tối ưu theo điểm Lighthouse trong khi dữ liệu thật vẫn xấu.

## Deep

- **Lab và field**: Lighthouse, WebPageTest là dữ liệu lab, lặp lại được, dùng để tìm nguyên nhân. Dữ liệu field đến từ người dùng thật: CrUX (Chrome gom lại theo 28 ngày) hoặc RUM tự gắn bằng thư viện `web-vitals`. Bản sửa chỉ được tính là xong khi p75 field cải thiện, và CrUX cần vài tuần mới phản ánh hết.
- **Bốn phần của LCP**: chỉ áp đủ khi phần tử LCP là ảnh hay tài nguyên phải tải; LCP là khối chữ thì chỉ còn TTFB và render (cộng thời gian tải font). TTFB chậm là việc của server và CDN. Độ trễ trước khi tải lớn nghĩa là trình duyệt phát hiện ảnh LCP muộn: ảnh nằm trong CSS, được JS chèn vào, hoặc gắn `loading="lazy"`. Sửa bằng thẻ `<img>` trong HTML có `fetchpriority="high"` hoặc `<link rel="preload">`. Thời gian tải lớn là do ảnh nặng. Render chậm là do CSS hoặc JS chặn render.
- **Gzip, Brotli, zstd**: client gửi `Accept-Encoding`, server chọn và trả `Content-Encoding`, kèm `Vary: Accept-Encoding` để cache không trả bản nén sai loại. Brotli thường nhỏ hơn gzip 15–25% với text. Mức nén cao của Brotli rất chậm, nên nén trước file tĩnh ở mức cao lúc build, còn response động dùng mức thấp (4–5). zstd được Chrome 123 và Firefox 126 trở lên hỗ trợ, nén nhanh hơn Brotli ở tỉ lệ tương đương; không phải trình duyệt nào cũng có, nên server luôn chọn theo `Accept-Encoding` và giữ gzip làm dự phòng. Bật nén ở Spring Boot xem bài Tuning server & HTTP client.
- **BREACH**: nén response HTTPS chứa cả secret ([[csrf|CSRF]] token) lẫn dữ liệu do người dùng gửi lên phản chiếu lại cho phép kẻ tấn công đoán secret bằng cách quan sát kích thước response. Giảm rủi ro bằng cách không phản chiếu input vào cùng response với secret, hoặc che token ngẫu nhiên mỗi lần trả (Spring Security 6 làm vậy với CSRF token).
- **INP**: main thread của trình duyệt chỉ có một. Task dài hơn 50ms (parse JSON lớn, render danh sách dài, script bên thứ ba) làm mọi cú bấm phải chờ. Chia nhỏ việc, ảo hoá danh sách dài, trì hoãn script quảng cáo và analytics. Payload JSON 2 MB tốn cả thời gian tải lẫn thời gian parse trên điện thoại yếu.
- **CLS**: ảnh và iframe không khai báo `width`/`height`, banner chèn vào trên nội dung sau khi tải, font thay thế đổi kích thước chữ. Giữ chỗ trước bằng kích thước cố định hoặc `aspect-ratio`.
- **HTTP/2 và HTTP/3**: HTTP/2 chạy nhiều request trên một kết nối nên mẹo cũ như chia domain (domain sharding) hay gộp mọi ảnh thành sprite không còn cần, và chia domain còn làm hại vì tốn thêm kết nối. HTTP/3 trên QUIC tránh head-of-line blocking ở TCP, có lợi rõ nhất trên mạng di động mất gói. `103 Early Hints` cho server gợi ý trình duyệt tải trước CSS, font trong lúc HTML còn đang được tạo.
- **CDN cho API**: response public (danh mục, giá niêm yết) cache ở CDN bằng `s-maxage` ngắn và `stale-while-revalidate`, giảm cả TTFB lẫn tải cho origin. Response của riêng người dùng phải `private` hoặc `no-store`. Cache key, `Vary` và việc cache nhầm dữ liệu cá nhân xem bài Cache là gì & cache ở đâu.
- **App di động cũng vậy**: `URLSession` trên iOS và OkHttp trên Android tôn trọng `Cache-Control` và `ETag` nếu server gửi đúng. API trả `no-store` cho mọi thứ là tự bỏ cache sẵn có của client. Payload và số lời gọi nối tiếp ảnh hưởng tới app y như web.
