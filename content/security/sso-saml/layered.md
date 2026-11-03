## Quick

[[sso|SSO]] doanh nghiệp: nhân viên đăng nhập một lần ở [[identity-provider|IdP]] của công ty, mọi ứng dụng tin danh tính mà IdP xác nhận. Hai giao thức chính: [[saml|SAML 2.0]] (XML, [[saml-assertion|assertion]] có chữ ký đi qua trình duyệt bằng form POST) và [[oidc|OIDC]] (JSON, đổi code lấy token qua kênh sau). **Ứng dụng mới chọn OIDC, nhưng SaaS bán cho doanh nghiệp vẫn phải nhận SAML.** Với SAML, **chỉ tin phần XML mà chữ ký thật sự phủ**, và dùng thư viện đã kiểm chứng thay vì tự parse.

## Interview

**Các vai**: IdP (Entra ID, Okta, AD FS, Keycloak) xác thực người dùng và giữ phiên đăng nhập của nó. Ứng dụng là [[saml-service-provider|service provider]] (SP; bên OIDC gọi là relying party). Hai bên trao đổi [[saml-metadata|metadata]] trước: entityID, URL, chứng chỉ ký.

**Luồng SP-initiated**: người dùng mở app chưa có phiên. SP tạo `AuthnRequest` có ID, lưu lại, chuyển trình duyệt sang IdP. IdP đăng nhập người dùng, hoặc thấy phiên sẵn có thì không hỏi lại (đó chính là SSO), rồi trả trang tự submit `SAMLResponse` bằng POST tới [[assertion-consumer-service|ACS]] của SP. SP kiểm chữ ký bằng chứng chỉ trong metadata, rồi `Issuer`, `Destination`, `Audience` là entityID của mình, thời hạn, và `InResponseTo` khớp request đã gửi. Hợp lệ thì tạo session riêng của app.

**SAML hay OIDC**: OIDC gọn hơn, dùng được cho app di động và SPA, có access token để gọi API. SAML chỉ lo đăng nhập web, nhưng là thứ nhiều khách hàng doanh nghiệp đã cấu hình sẵn. SaaS B2B thường đặt một [[identity-broker|identity broker]] ở giữa: app chỉ nói OIDC với broker, broker nói SAML hay OIDC với IdP của từng khách hàng.

**Bẫy hay gặp**: [[xml-signature-wrapping|signature wrapping]] (kiểm "có chữ ký hợp lệ" rồi đọc dữ liệu từ một assertion khác); định danh người dùng bằng email; nhận [[idp-initiated-sso|IdP-initiated SSO]] khi không cần; cookie session [[samesite|SameSite]] làm mất `AuthnRequest` khi IdP POST về; chứng chỉ ký của IdP hết hạn làm cả một khách hàng không đăng nhập được; [[jit-provisioning|JIT provisioning]] tạo tài khoản nhưng không bao giờ khoá.

**Đăng xuất**: có ít nhất hai lớp phiên, của app và của IdP. Xoá session app không đăng xuất khỏi IdP. [[single-logout|Single logout]] của SAML chuyền qua trình duyệt nên dễ đứt; OIDC có [[back-channel-logout|back-channel logout]] gọi thẳng từ IdP tới server của app. Muốn chắc người nghỉ việc mất quyền thì dựa vào session app có hạn và [[scim|SCIM]] khoá tài khoản, không dựa vào logout.

## Deep

- **SAML 2.0 (OASIS, 2005) gồm bốn phần**: assertion (ai, xác thực lúc nào bằng cách gì, thuộc tính), protocol (`AuthnRequest`/`Response`, `LogoutRequest`), binding (cách chở message), profile (Web Browser SSO là profile dùng nhiều nhất).
  - HTTP-Redirect binding: XML được DEFLATE, Base64 rồi đặt vào query `SAMLRequest`; chữ ký là các tham số `SigAlg` và `Signature` của query, không nằm trong XML. Dùng cho `AuthnRequest` vì nhỏ.
  - HTTP-POST binding: form ẩn tự submit, chữ ký XML nằm trong tài liệu. Dùng cho `Response` vì quá dài cho URL.
  - Artifact binding: trình duyệt chỉ chở một tham chiếu, SP lấy message qua kênh sau. Ít gặp.
- **Kiểm Response**: Spring Security 7 (`OpenSaml5AuthenticationProvider`) làm theo thứ tự:
  - Kiểm chữ ký của Response, giải mã `EncryptedAssertion`, kiểm `Issuer` và `Destination`, kiểm chữ ký từng assertion. Response lẫn assertion đều không ký thì từ chối.
  - Kiểm `NotBefore`/`NotOnOrAfter` (lệch giờ cấu hình được), `SubjectConfirmation` (`Recipient` là ACS, `InResponseTo`), `AudienceRestriction`.
  - Tài liệu ghi rõ đây là kiểm tối thiểu: không có danh sách ID assertion đã dùng để chống phát lại, điều kiện `OneTimeUse` phải tự thêm validator. Lớp chặn phát lại chính là `InResponseTo` gắn với request lưu trong session, cùng thời hạn assertion ngắn.
- **Signature wrapping (đã chạy với XML Digital Signature API của JDK 27)**:
  - Chữ ký XML trỏ tới phần được ký qua `Reference URI="#_a1"`. `validate()` trả `true` chỉ có nghĩa "phần tử có ID `_a1` chưa bị sửa", không nói gì về phần tử mà code của bạn sẽ đọc.
  - Thử: lấy response hợp lệ, chèn một assertion giả không ký có NameID `admin@shop.example.com` lên trước assertion thật. `validate()` vẫn `true`; code lấy "assertion đầu tiên" đọc ra `admin@shop.example.com`.
  - Sửa: chỉ đọc đúng phần tử mà reference trỏ tới, và phần tử đó phải là assertion đang xử lý; từ chối response có nhiều assertion; kiểm schema trước. Nghiên cứu "On Breaking SAML" (Somorovsky và cộng sự, USENIX Security 2012) thấy 11 trên 14 framework SAML dính lỗi này.
- **Comment trong NameID (đã chạy)**:
  - Exclusive C14N bỏ qua comment khi tính chữ ký, nên chèn `<!---->` vào text sau khi IdP ký thì chữ ký vẫn hợp lệ.
  - Kẻ tấn công đăng ký `ceo@shop.example.com.evil.example` ở một IdP cho tự khai email, chèn comment thành `ceo@shop.example.com<!---->.evil.example`. DOM có hai node text: `getFirstChild().getNodeValue()` ra `ceo@shop.example.com`, `getTextContent()` ra đủ chuỗi.
  - Duo công bố năm 2018, dính nhiều thư viện (python-saml, ruby-saml và các thư viện khác).
- **Hai parser hiểu khác nhau**: ruby-saml CVE-2024-45409 cho giả chữ ký (ảnh hưởng GitLab); CVE-2025-25291 và CVE-2025-25292 do thư viện kiểm chữ ký bằng một parser XML và đọc dữ liệu bằng parser khác. Bài học: kiểm và đọc trên cùng một cây, theo đúng tham chiếu; coi bản vá thư viện SAML là bản vá bảo mật khẩn.
- **XML nói chung**: tắt DTD và external entity để chặn XXE (thư viện SAML làm sẵn, tự parse thì bật `disallow-doctype-decl`). Không nhận chữ ký SHA-1. Mã hoá assertion (`EncryptedAssertion`) khi thuộc tính nhạy cảm, vì assertion đi qua trình duyệt và có thể nằm trong log của proxy.
- **Chứng chỉ ký và metadata**:
  - SP tin chứng chỉ có trong metadata của IdP, thường là chứng chỉ tự ký; niềm tin đến từ việc trao metadata, không từ chuỗi CA như TLS.
  - Entra ID tự tạo chứng chỉ ký SAML có hạn 3 năm cho ứng dụng thêm từ gallery. Đến hạn, IdP đổi chứng chỉ; SP nhập chứng chỉ bằng tay sẽ từ chối mọi response, cả công ty khách hàng không đăng nhập được.
  - Nạp metadata theo URL và làm mới định kỳ (`RelyingPartyRegistrations.fromMetadataLocation`), cho phép hai chứng chỉ cùng lúc trong giai đoạn chuyển, cảnh báo trước khi hết hạn.
- **Định danh người dùng**:
  - Khoá tài khoản là cặp (IdP, NameID dạng persistent) hoặc một thuộc tính bất biến như object ID của Entra, không phải email. Email đổi khi người dùng đổi tên. NameID dạng transient đổi mỗi lần đăng nhập.
  - Mỗi IdP khách hàng tự quyết giá trị email. Nối tài khoản theo email giữa các IdP thì IdP của tenant A phát assertion `ceo@tenant-b.example` là vào được tài khoản của tenant B. Tài khoản phải gắn với (tenant, IdP, subject).
- **SameSite và `AuthnRequest` bị mất**:
  - Spring Security lưu `AuthnRequest` trong `HttpSession` để kiểm `InResponseTo`. IdP trả response bằng form POST từ site khác.
  - Cookie session khai `SameSite=Lax` hay `Strict` thì không đi kèm POST khác site, request đã lưu mất, đăng nhập lỗi mọi lần.
  - Cookie không khai `SameSite` thì Chrome vẫn gửi kèm POST cấp cao nếu cookie mới đặt chưa quá 2 phút (bài Bảo mật phía trình duyệt). Người dùng đăng nhập nhanh thì được, ai mất hơn 2 phút ở IdP ([[mfa|MFA]], quên mật khẩu) thì lỗi: một lỗi "thỉnh thoảng" rất khó tái hiện.
  - Sửa: cookie session `SameSite=None; Secure` và giữ CSRF token; hoặc `CacheSaml2AuthenticationRequestRepository` tra request theo `RelayState`. Cách sau mất lớp chống login fixation mà session cho: response do kẻ tấn công đưa cho nạn nhân không còn bị buộc vào phiên đã bắt đầu đăng nhập.
  - OIDC mặc định trả code bằng redirect GET cấp cao nên cookie `Lax` vẫn đi; chỉ `response_mode=form_post` gặp chuyện này.
- **IdP-initiated SSO**: người dùng bấm biểu tượng app trong cổng của IdP (My Apps, Okta dashboard), IdP gửi response không có `InResponseTo`. SP không gắn được response với phiên nào, nên dễ bị login CSRF và phát lại assertion lộ ra trong thời hạn. Không cần thì tắt; khách hàng đòi thì để cổng IdP mở một URL của app, app bắt đầu luồng SP-initiated (OIDC có `initiate_login_uri` cho việc này).
- **Federation và broker**:
  - Mỗi khách hàng một IdP. Broker (Keycloak identity brokering, Entra External ID, Auth0, Cognito) gom lại: app chỉ có một client OIDC, thêm khách hàng là cấu hình ở broker.
  - [[home-realm-discovery|Home realm discovery]]: trang đăng nhập hỏi email trước rồi chọn IdP theo tên miền. Tên miền phải được xác minh (bản ghi DNS TXT) trước khi dùng để định tuyến, nếu không tenant nào cũng khai được `bigbank.example`.
  - Broker có phiên riêng, thêm một lớp phải đăng xuất, và thành phụ thuộc đăng nhập của mọi khách hàng. API kiểm [[jwt|JWT]] tại chỗ bằng [[jwks|JWKS]] đã cache để broker ngừng thì chỉ đăng nhập mới bị ảnh hưởng.
- **Provisioning**:
  - JIT tạo tài khoản ở lần đăng nhập đầu từ thuộc tính trong assertion. Nó không biết ai đã nghỉ: người nghỉ không đăng nhập mới được, nhưng session app còn hạn, refresh token, API token vẫn chạy, tài khoản vẫn chiếm license.
  - SCIM 2.0 (RFC 7643, 7644): IdP gọi API của app (`POST /Users`, `PATCH` với `active: false`, `/Groups`). Khi nhận lệnh khoá, app phải huỷ session và token của người đó, không chỉ đặt cờ. Không phải IdP nào cũng đẩy ngay: Entra ID chạy provisioning theo chu kỳ, AD FS không có SCIM.
- **Đăng xuất chi tiết**:
  - OIDC RP-Initiated Logout: app chuyển trình duyệt tới `end_session_endpoint` với `id_token_hint` và `post_logout_redirect_uri` đã đăng ký. Spring: `OidcClientInitiatedLogoutSuccessHandler`.
  - Front-Channel Logout: IdP mở iframe tới URL logout của từng app. Iframe cần cookie của app trong ngữ cảnh bên thứ ba, nên trình duyệt chặn cookie bên thứ ba là cách này hỏng; chính spec có mục nói về việc đó.
  - Back-Channel Logout 1.0 (final 9/2022): IdP POST `logout_token` tới app. Token là JWT ký, có claim `events` loại back-channel logout, có `sub` hoặc `sid`, có `jti`, và cấm `nonce`. App trả `200`.
  - Spring Security `oidcLogout(l -> l.backChannel(...))` mở `/logout/connect/back-channel/{registrationId}`. Liên kết `sid` với session của app mặc định nằm **trong bộ nhớ**: chạy nhiều instance thì logout token tới instance không giữ liên kết và không ai bị đăng xuất. Phải cài `OidcSessionRegistry` dùng chung; dùng Spring Session (cookie `SESSION`) thì đổi tên cookie trong handler.
  - SAML Single Logout: IdP chuyền `LogoutRequest` qua trình duyệt lần lượt tới từng SP, cần `SessionIndex`. Một SP chậm hay lỗi là chuỗi đứt và người dùng đứng ở trang lỗi. Spring: `saml2Logout()`, cần khoá ký của SP.
- **Spring Security và SAML**: module `spring-security-saml2-service-provider` dựa trên OpenSAML 5, phải thêm repo Maven của Shibboleth vì OpenSAML 5 không có trên Maven Central. Endpoint mặc định: `/saml2/authenticate/{registrationId}`, ACS `/login/saml2/sso/{registrationId}`, SLO `/logout/saml2/slo`; entityID mặc định `{baseUrl}/saml2/service-provider-metadata/{registrationId}`. Principal là `Saml2AuthenticatedPrincipal`, `getName()` là NameID của assertion đầu; authority mặc định chỉ có `ROLE_USER` (kèm một authority đánh dấu yếu tố SAML), group và role phải tự ánh xạ từ attribute. Extension cũ `spring-security-saml` 1.x đã ngừng.
- **Mức xác thực**: app biết người dùng đã qua MFA hay chưa qua `AuthnContextClassRef` (SAML) hoặc `acr`/`amr` (OIDC); thao tác nhạy cảm yêu cầu đăng nhập lại bằng `ForceAuthn="true"` hay `prompt=login`/`max_age`. Giữ một tài khoản quản trị cục bộ cho mỗi tenant để vào được khi IdP của khách hàng hỏng ([[break-glass-access|break-glass]], bài Kiến trúc bảo mật).
- **Liên quan**: luồng authorization code, [[pkce|PKCE]], [[id-token|ID token]]: bài OAuth2 & OpenID Connect; cookie, SameSite, login CSRF: bài Bảo mật phía trình duyệt; chữ ký số: bài Mật mã cho kỹ sư; phân quyền sau khi đã biết người dùng là ai: bài Mô hình phân quyền.
