## Quick

Trình duyệt tự đính kèm cookie vào mọi request tới tên miền của cookie, kể cả request do trang khác khởi tạo. [[same-origin-policy|Same-origin policy]] chỉ **chặn đọc response, không chặn gửi request**, nên [[cors|CORS]] không chống được [[csrf|CSRF]]. Chống CSRF bằng **CSRF token hoặc kiểm `Origin`/`Sec-Fetch-Site`**, dùng cookie [[samesite|SameSite]] làm lớp thêm; chống [[xss|XSS]] gây hại bằng escape đầu ra và [[csp|CSP]].

## Interview

**Origin và site**: [[web-origin|origin]] là bộ ba scheme + host + port; `https://app.shop.example.com` và `https://help.shop.example.com` là hai origin khác nhau. [[site|Site]] là scheme + tên miền đăng ký được (eTLD+1), nên hai origin trên **cùng site**. SOP làm việc theo origin, SameSite làm việc theo site.

**SOP và CORS**: trang ở origin A gửi được form, `<img>`, `fetch` tới origin B; trình duyệt chỉ không cho JavaScript của A đọc response. CORS là cách B nới lỏng: trả `Access-Control-Allow-Origin` để cho A đọc. Request không phải [[simple-request|simple request]] (JSON, header tự đặt, `PUT`/`DELETE`) phải qua [[cors-preflight|preflight]] `OPTIONS` trước. Cấu hình CORS sai làm lộ dữ liệu; cấu hình đúng cũng không chặn được request ghi.

**Cookie**: `HttpOnly` để JavaScript không đọc được, `Secure` để chỉ đi qua HTTPS, `SameSite`:
- `Strict`: không gửi khi request đến từ site khác, kể cả bấm link.
- `Lax`: chỉ gửi khi người dùng điều hướng `GET` từ site khác. Chrome mặc định `Lax` khi không khai báo.
- `None` (bắt buộc kèm `Secure`): luôn gửi.

**CSRF**: trang độc tự submit form tới ứng dụng, cookie [[http-session|session]] đi kèm, server làm theo. Spring Security bật chống CSRF mặc định: token lưu trong session, form phải gửi lại. API dùng bearer token trong header thì không bị CSRF vì trình duyệt không tự gắn header đó.

**Bẫy hay gặp**: tắt CSRF vì "đã có SameSite" trong khi một tên miền con cùng site chứa nội dung người dùng; `GET` làm thay đổi dữ liệu; CORS phản chiếu mọi `Origin` kèm `allowCredentials`; nghĩ `HttpOnly` chống được XSS (script vẫn gửi request thay người dùng, chỉ không lấy được cookie); không có CSP nên một lỗi escape thành chạy script.

## Deep

- **Site tính theo Public Suffix List**: `github.io` là public suffix, nên `a.github.io` và `b.github.io` khác site; `a.shop.example.com` và `b.shop.example.com` cùng site `example.com`. Chrome tính cả scheme: `http://` và `https://` của cùng tên miền là khác site.
- **Đã chạy với Chrome 156** (server Java, hai host trỏ về máy, HTTP), trang tấn công tự gửi form `POST` và `fetch` có `credentials: 'include'`:

  | Trang tấn công | Cookie `Lax`/`Strict` | Cookie không khai `SameSite` (vừa đặt) | `fetch` JSON |
  |---|---|---|---|
  | `help.shop.test` (cùng site) | đi, server làm theo | đi | chỉ có `OPTIONS`, không cookie |
  | `evil.test` (khác site) | không đi | **vẫn đi** với form `POST` | chỉ có `OPTIONS` |

  `fetch` dạng form từ cả hai trang đều tới server và được xử lý, còn JavaScript chỉ nhận `TypeError: Failed to fetch`. Cookie `SameSite=None; Secure` bị loại vì trang chạy HTTP. Header `Sec-Fetch-Site` không có, vì nó chỉ gửi tới URL đáng tin (HTTPS hoặc `localhost`).
- **Ngoại lệ "Lax + POST" của Chrome**: cookie **không khai** `SameSite` được coi là `Lax`, nhưng trong 2 phút đầu sau khi đặt vẫn đi theo `POST` điều hướng từ site khác (để luồng đăng nhập kiểu SSO cũ không gãy). Khai `SameSite=Lax` tường minh thì không có ngoại lệ này. Firefox và Safari không mặc định `Lax` (tính đến cuối 2026, Chrome 156), nên đừng dựa vào mặc định của trình duyệt.
- **Simple request** (không preflight): `GET`/`HEAD`/`POST`, chỉ header an toàn, `Content-Type` là `application/x-www-form-urlencoded`, `multipart/form-data` hoặc `text/plain`. Endpoint nhận JSON mà vẫn đọc được body `text/plain` là mở cửa cho CSRF bằng `fetch`. Preflight không bao giờ mang cookie: filter xác thực phải để `OPTIONS` qua, Spring Security xử lý bằng `.cors(withDefaults())` (bài Kiến trúc Spring Security).
- **Đọc response có credentials** cần đủ: `Access-Control-Allow-Origin` là đúng origin (không phải `*`), `Access-Control-Allow-Credentials: true`, và cookie phải được gửi (tức `SameSite` cho phép). Phản chiếu `Origin` thì thêm `Vary: Origin`, nếu không CDN cache response của origin này trả cho origin khác.
- **`*` không phải lúc nào cũng sai**: API công khai không dùng cookie (tỷ giá, danh mục sản phẩm) trả `Access-Control-Allow-Origin: *` là đúng. Rủi ro của `*` là API nội bộ không xác thực (chỉ dựa vào "ở trong mạng công ty"): trang ngoài đọc được qua trình duyệt của nhân viên.
- **Header trong CORS**: request đặt header tự chọn cần server liệt kê trong `Access-Control-Allow-Headers`. Chiều về, JavaScript chỉ đọc được vài header an toàn; header như `X-Request-Id` đọc ra `null` nếu thiếu `Access-Control-Expose-Headers`.
- **SPA và API khác site** (`shop.example.com` gọi `api.shop-api.example.net` bằng cookie): cookie phải `SameSite=None; Secure`, CORS có credentials với origin cụ thể, và vẫn cần CSRF token vì `None` tắt hẳn lớp SameSite. Đơn giản hơn là đưa API về cùng origin qua reverse proxy (`shop.example.com/api`).
- **Bẫy CORS trong Spring** (spring-web 7.0.10, đã chạy):
  - `allowedOrigins("*")` cùng `allowCredentials(true)` ném `IllegalArgumentException: When allowCredentials is true, allowedOrigins cannot contain the special value "*"`.
  - Đổi sang `allowedOriginPatterns("*")` để "hết lỗi" thì `checkOrigin("https://evil.example.net")` trả về chính origin đó: mọi trang đều đọc được dữ liệu của người đang đăng nhập.
  - Pattern `https://*.shop.example.com` khớp `https://help.shop.example.com`, không khớp `https://shop.example.com`, `http://help...` hay `https://evil.shop.example.com.attacker.net`. Tự viết `origin.endsWith("example.com")` thì khớp cả `https://evilexample.com`.
  - Đừng cho phép origin `null`: trang trong iframe `sandbox` hay file local đều gửi `Origin: null`.
  - `maxAge` mặc định của `applyPermitDefaultValues()` và `@CrossOrigin` là 1800 giây; Chromium giới hạn cache preflight 2 giờ, Firefox 24 giờ, không có header thì 5 giây.
- **Cookie `Domain` và prefix**: không đặt `Domain` thì cookie chỉ thuộc đúng host. `Domain=shop.example.com` gửi cho mọi tên miền con, và một tên miền con bị chiếm cũng đặt được cookie cho tên miền cha ([[cookie-tossing|cookie tossing]], ghi đè session hay CSRF cookie). [[cookie-prefix|Prefix]] `__Host-` bắt buộc `Secure`, `Path=/`, không có `Domain`, nên không bị tên miền con ghi đè. Spring Boot: `server.servlet.session.cookie.name=__Host-SESSION`, cùng `same-site`, `secure`, `http-only` (mặc định `true`).
- **Các cách chống CSRF**:
  - Synchronizer token: mặc định của Spring Security, `HttpSessionCsrfTokenRepository`; `XorCsrfTokenRequestAttributeHandler` che token khác nhau mỗi lần trả để chống BREACH (bài Hiệu năng phía client). Token nạp trễ, chỉ khi cần. Thiếu token thì `403`. Thymeleaf tự chèn `_csrf` vào form có `th:action`.
  - SPA: Spring Security 7 có `csrf.spa()`, cấu hình `CookieCsrfTokenRepository.withHttpOnlyFalse()` (cookie `XSRF-TOKEN`, JavaScript đọc rồi gửi header `X-XSRF-TOKEN`) và handler riêng cho SPA. Bản 6.x phải tự cấu hình hai thứ đó.
  - Double-submit cookie không ký thì yếu trước tên miền con ghi được cookie; dùng `__Host-` hoặc ký token gắn với session.
  - Kiểm [[fetch-metadata|Fetch Metadata]]: từ chối request ghi có `Sec-Fetch-Site: cross-site` (và `same-site` nếu không tin tên miền con), hoặc so `Origin` với danh sách cho phép. Là lớp tốt bổ sung, nhưng trình duyệt cũ và HTTP thường không gửi: thiếu header thì quay về kiểm token hoặc `Origin`, không coi là hợp lệ. Giá trị `none` (người dùng tự gõ URL, bookmark) là điều hướng hợp lệ, đừng chặn nhầm.
  - `GET`, `HEAD`, `OPTIONS`, `TRACE` không được kiểm CSRF, nên không bao giờ đổi trạng thái bằng `GET`: `Lax` vẫn gửi cookie khi bấm link `GET`.
  - Login CSRF: kẻ tấn công đăng nhập nạn nhân vào tài khoản của mình (để nạn nhân lưu thẻ vào đó). Form đăng nhập cũng cần token.
- **Header Spring Security trả mặc định** (7.0.5, đã chạy): `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 0` (XSS Auditor của trình duyệt đã bị gỡ, bật lên còn tạo lỗ), `Cache-Control: no-cache, no-store, max-age=0, must-revalidate`, `X-Frame-Options: DENY`, và `Strict-Transport-Security: max-age=31536000 ; includeSubDomains` chỉ khi request là HTTPS ([[hsts|HSTS]]: bài TLS & HTTPS). **Không có CSP** mặc định.
- **CSP**:
  - Cách hiệu quả là [[csp-nonce|nonce]]: `script-src 'nonce-<ngẫu nhiên mỗi response>' 'strict-dynamic'; object-src 'none'; base-uri 'none'`. Chỉ script có đúng nonce chạy; `strict-dynamic` cho script đó nạp tiếp script khác; trình duyệt hỗ trợ nonce bỏ qua `'unsafe-inline'` và allowlist tên miền.
  - Allowlist kiểu `script-src cdn.example.net` dễ bị vượt nếu CDN đó có thư viện cũ hay endpoint JSONP.
  - Trong Spring: `headers(h -> h.contentSecurityPolicy(csp -> csp.policyDirectives(...)))` chỉ đặt header cố định, không sinh nonce. Muốn nonce thì viết filter sinh 16 byte từ `SecureRandom` cho mỗi request, đặt vào request attribute và header CSP; template đọc attribute đó ra `<script th:attr="nonce=${cspNonce}">`. Response bị cache (CDN) không dùng được nonce, khi đó dùng hash của script.
  - Triển khai bằng `Content-Security-Policy-Report-Only` kèm `report-to` để thu vi phạm trước khi chặn. CSP là lớp giảm thiệt hại, không thay escape đầu ra (bài OWASP Top 10).
- **[[clickjacking|Clickjacking]]**: trang độc nhúng ứng dụng vào iframe trong suốt để người dùng bấm nhầm nút "Xác nhận". Chống bằng `X-Frame-Options: DENY` hoặc CSP `frame-ancestors 'self' https://partner.example.net` (linh hoạt hơn; không dùng được trong thẻ `<meta>`).
- **[[referrer-policy|Referrer-Policy]]**: thiếu header thì trình duyệt hiện nay dùng `strict-origin-when-cross-origin`: cùng origin gửi URL đầy đủ, sang origin khác chỉ gửi origin, từ HTTPS xuống HTTP không gửi gì. Token, mã đơn, email trong query vẫn lọt nguyên văn sang trang cùng origin và vào log. Spring Security không gửi header này mặc định; bật `headers(h -> h.referrerPolicy(...))` thì writer mặc định ghi `no-referrer` (đã chạy 7.0.5). Trang có token trong URL như đặt lại mật khẩu: `no-referrer`, phòng khi trình duyệt cũ hay cấu hình lỏng gửi đủ URL; gốc vấn đề vẫn là đừng để token trong URL (bài Secure SDLC).
- **[[coop|COOP]]** (`Cross-Origin-Opener-Policy`): cắt liên hệ giữa cửa sổ của bạn và cửa sổ khác origin đã mở nó hoặc do nó mở.
  - Đo Chrome 156 headless, hai origin `localhost:8701` và `localhost:8702`. Không header: popup khác origin thấy `window.opener` và `postMessage` về được. Popup trả `same-origin`: `window.opener` thành `null`. Trang mở popup trả `same-origin`: popup khác origin cũng mất opener; `same-origin-allow-popups` thì giữ.
  - Lợi ích: trang lạ không giữ được tham chiếu tới cửa sổ của bạn để dò trạng thái của nó (XS-Leaks, tức rò thông tin giữa các site, như đếm số frame để đoán người dùng đã đăng nhập chưa) hay đổi URL của nó sang trang giả (tabnabbing). Link `target=_blank` nay mặc định `noopener` nên kiểu tabnabbing cổ điển đã giảm; COOP còn che cả trường hợp trang lạ là bên mở bạn.
  - Bẫy: đăng nhập OAuth2 hay thanh toán bằng popup chờ `postMessage` từ popup về. Đặt `same-origin` trên trang ứng dụng làm luồng đó hỏng lặng lẽ; dùng `same-origin-allow-popups` hoặc chuyển sang redirect.
  - COOP `same-origin` cùng `Cross-Origin-Embedder-Policy: require-corp` (COEP: chỉ nhúng tài nguyên khác origin nào cho phép) làm trang được cô lập hẳn khỏi origin khác, điều kiện để dùng `SharedArrayBuffer` (bộ nhớ chung giữa các worker).
  - Spring Security có `crossOriginOpenerPolicy(...)` trong `headers`, không bật mặc định.
- **[[third-party-cookie|Cookie bên thứ ba]]**: Safari và Firefox chặn hoặc phân vùng mặc định. Chrome giữ cookie bên thứ ba và lựa chọn của người dùng (quyết định 4/2025), rồi bỏ phần lớn Privacy Sandbox (10/2025), giữ CHIPS (`Partitioned`). Widget nhúng iframe đăng nhập bằng cookie riêng sẽ hỏng trên một phần người dùng; dùng luồng redirect của OAuth2/OIDC (bài OAuth2 & OpenID Connect).
- **Trang công khai gọi IP nội bộ**: Chrome 142 hỏi quyền Local Network Access khi trang trên internet gọi tới IP private hay `localhost`. Đừng dựa vào nó để bảo vệ admin nội bộ: vẫn cần xác thực và CSRF.
- **Liên quan**: WebSocket không áp CORS, phải kiểm `Origin` (bài gRPC, WebSocket, SSE & long polling); nơi lưu token của SPA (bài JWT chuyên sâu); file người dùng tải lên phục vụ từ tên miền đăng ký riêng (bài Thiết kế lưu trữ file / video).
