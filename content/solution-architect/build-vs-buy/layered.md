## Quick

Build hay buy là quyết định đặt người giỏi nhất vào đâu, không chỉ là so giá. **Tự xây phần tạo khác biệt ([[core-domain|core domain]]), mua hoặc dùng sẵn phần chung; so các phương án bằng [[tco|TCO]] nhiều năm (cả công người, tích hợp, vận hành và chi phí thoát), chọn vendor bằng tiêu chí đặt trước và [[proof-of-concept|PoC]] trên dữ liệu thật, và ký hợp đồng như thể sẽ có ngày phải rời đi.**

## Interview

Câu hỏi đầu tiên của tôi là phần này có làm sản phẩm khác đối thủ không. Chấm điểm tín dụng của công ty cho vay là core: tự xây, vì đó là nơi đáng đặt người giỏi. Đăng nhập, gửi email, kế toán chuẩn là bài toán chung: mua [[saas|SaaS]] hoặc dùng open source, vì tự xây chỉ lặp lại thứ người khác đã làm tốt hơn và phải bảo trì mãi.

Sau đó tôi so [[tco|tổng chi phí sở hữu]] trong 3 đến 5 năm, không so giá license với ước lượng code. Tự xây gồm công làm ban đầu, người bảo trì và trực sự cố hằng năm, hạ tầng, kiểm thử bảo mật. Mua gồm phí theo người dùng hay theo lượng dùng khi tải tăng, mức tăng giá khi gia hạn, công tích hợp và chuyển dữ liệu, người quản trị, và chi phí thoát. Phí theo lượng dùng thường rẻ lúc nhỏ nhưng vượt tự vận hành khi lớn, nên tôi tính theo kịch bản tăng trưởng và tìm điểm cắt.

Chọn vendor thì tiêu chí và trọng số chốt trước khi xem demo, tiêu chí bắt buộc là cổng loại. Hai, ba ứng viên vào PoC có tiêu chí đạt, chạy trên dữ liệu và tải của mình chứ không trên demo của họ. Tôi kiểm phần phi chức năng: [[sla|SLA]] và mức đền bù, nơi lưu dữ liệu, chứng nhận bảo mật, [[sso|SSO]], giới hạn API, cách xuất dữ liệu.

Bẫy hay gặp là bỏ qua [[vendor-lock-in|lock-in]] lúc ký. Tôi giảm nó bằng kiến trúc: ứng dụng chỉ nói chuẩn mở như [[oidc|OIDC]], hoặc gọi vendor qua một lớp adapter của mình. Hợp đồng ghi rõ định dạng xuất dữ liệu khi chấm dứt, trần tăng giá khi gia hạn, thời hạn báo huỷ. Và tôi viết sẵn [[exit-plan|kế hoạch thoát]] kèm điều kiện xem lại trong [[adr|ADR]], ví dụ khi phí năm vượt chi phí tự vận hành.

## Deep

- **Phổ lựa chọn, không chỉ hai cửa**: tự xây; mua SaaS; mua phần mềm đóng gói tự cài ([[cots|COTS]]); open source tự vận hành; open source dạng managed (Amazon MSK, Amazon RDS, các nhà cung cấp Kafka hay PostgreSQL managed); mua lõi rồi mở rộng qua API, plugin, webhook; thuê ngoài xây. Phần lớn hệ thống thật là hỗn hợp: mua lõi chung, tự xây lớp tạo khác biệt bên trên.
- **Phần nào nên tự xây**:
  - Theo DDD chiến lược (bài DDD chiến lược): core thì xây và đầu tư; supporting thì xây đơn giản hoặc mua nếu có sản phẩm vừa; generic thì mua.
  - [[wardley-map|Wardley map]] (Simon Wardley) xếp mỗi thành phần theo độ trưởng thành: genesis (mới lạ), custom-built, product, commodity. Thứ đã thành product hay commodity mà vẫn tự xây là lãng phí; thứ còn ở genesis thì chưa có gì để mua.
  - Câu hỏi kiểm tra: nếu đối thủ dùng đúng sản phẩm này, mình có mất lợi thế không? Không thì đó là generic.
  - Vị trí có thể đổi theo thời gian: thứ từng phải tự xây (message queue, search) giờ là dịch vụ managed; ngược lại, phần từng mua có thể thành điểm khác biệt khi sản phẩm lớn lên.
- **[[tco|TCO]] gồm những gì** (tính 3–5 năm, cùng đơn vị tiền mỗi năm):
  - Tự xây: công xây ban đầu (thường bị ước thấp vì quên phần cuối: màn hình quản trị, phân quyền, audit log, báo cáo, đa ngôn ngữ, tuân thủ), người bảo trì và trực sự cố hằng năm, hạ tầng, kiểm thử bảo mật, nâng cấp thư viện. Chi phí cơ hội: các kỹ sư đó không làm core.
  - Mua: phí subscription theo mô hình giá, mức tăng khi gia hạn, công tích hợp và chuyển dữ liệu, cấu hình và đào tạo, người quản trị phía mình, gói support, các add-on tính riêng (SSO, audit log, môi trường sandbox thường nằm ở gói cao), và chi phí thoát.
  - Open source tự vận hành: không có phí license nhưng có công vận hành, nâng cấp, vá bảo mật, và thường cần người có chuyên môn sâu về chính sản phẩm đó. Có thể mua support thương mại.
  - Mô hình giá quyết định hình dạng đường chi phí: theo người dùng (seat), theo người dùng hoạt động mỗi tháng ([[mau|MAU]]), theo lượng dùng (sự kiện, GB, lời gọi API), theo host hay core. Hỏi vendor đếm thế nào: MAU có tính người chỉ refresh token không, token máy-với-máy có tính riêng không, log có tính cả bản trùng không.
  - Giá theo lượng dùng tăng tuyến tính với tải, còn tự vận hành có phần lớn là chi phí cố định (người): luôn có điểm cắt. Tính theo vài kịch bản tăng trưởng (thấp, kỳ vọng, cao) và đổi giả định nhạy nhất để xem kết luận có lật không ([[sensitivity-analysis|phân tích độ nhạy]] ở bài Ra quyết định & trade-off).
  - Các khoản giá cloud, license, support và công vận hành trên hoá đơn ở bài Ước tính chi phí & FinOps.
- **Bẫy license theo core khi ảo hoá**: chính sách phân vùng của Oracle không công nhận soft partitioning (ví dụ giới hạn vCPU của VM trên VMware), nên có thể bị tính license cho mọi core của cụm mà VM có thể chạy tới. Trên cloud được Oracle chấp thuận (AWS, Azure, và Google Cloud từ 2024), license theo processor (Enterprise Edition) tính 2 vCPU có hyper-threading là một processor; Standard Edition tính theo socket với quy đổi riêng. Hỏi kỹ quy tắc đếm trước khi thiết kế cụm; các khoản license khác trên hoá đơn ở bài Ước tính chi phí & FinOps.
- **Quy trình chọn vendor**:
  1. Viết yêu cầu theo kết quả cần đạt, không theo tính năng của một sản phẩm đã nhắm sẵn.
  2. Danh sách dài từ thị trường, gửi [[rfi|RFI]] (request for information) để lọc; danh sách ngắn 3–5 vendor nhận [[rfp|RFP]] có kịch bản cụ thể.
  3. Chấm bằng ma trận có trọng số, tiêu chí bắt buộc là cổng loại, chấm độc lập trước khi bàn (cách làm ở bài Ra quyết định & trade-off).
  4. PoC hoặc pilot 2–4 tuần với 2–3 vendor: dữ liệu và tải của mình, tiêu chí đạt viết trước, người dùng thật thử. Demo của vendor được chuẩn bị cho đường đẹp; PoC phải thử đường khó (dữ liệu bẩn, chuyển dữ liệu cũ, tích hợp với hệ thống của mình, lỗi và khôi phục).
  5. Gọi khách hàng tham chiếu có quy mô giống mình, tự tìm thêm ngoài danh sách vendor đưa.
  6. Đàm phán thương mại song song với kỹ thuật, để vẫn còn phương án thay thế khi mặc cả.
  7. Ghi ADR: phương án, điểm, giả định, điều kiện xem lại.
- **Tiêu chí phi chức năng hay bị bỏ sót**:
  - SLA đo cái gì, ở đâu, loại trừ gì (bảo trì có báo trước thường bị loại). [[service-credit|Service credit]] khi vi phạm thường chỉ 10–30% phí tháng của dịch vụ đó (có bậc tới 100% khi ngừng rất lâu, nhưng luôn giới hạn trong phí đã trả), không bù thiệt hại kinh doanh; SLA là động lực cho vendor, không phải bảo hiểm cho mình. Nếu availability của mình phụ thuộc vendor, thiết kế cho lúc vendor ngừng (bài Độ tin cậy & SRE).
  - Bảo mật và tuân thủ: [[soc-2|SOC 2]] Type II (kiểm cả hiệu quả vận hành trong một khoảng thời gian, khác Type I chỉ một thời điểm), ISO 27001, kết quả pentest, mã hoá và quản lý khoá, nơi lưu dữ liệu và subprocessor, hỗ trợ SSO/[[scim|SCIM]] (bài Kiến trúc bảo mật).
  - Tích hợp: API có phiên bản và chính sách ngừng hỗ trợ, giới hạn tốc độ, [[webhook|webhook]] có ký và retry, môi trường sandbox, xuất dữ liệu đầy đủ bằng API.
  - Vận hành: trang trạng thái, kênh support và thời gian phản hồi theo mức độ, báo trước thay đổi, region.
  - Sức khoẻ vendor: tài chính, khả năng bị mua lại, lộ trình sản phẩm, số khách hàng cỡ mình. Vendor nhỏ có sản phẩm tốt vẫn là rủi ro nếu sản phẩm đó giữ dữ liệu cốt lõi.
- **[[vendor-lock-in|Lock-in]] có nhiều dạng**: dữ liệu (định dạng riêng, xuất không đủ), tích hợp (code gọi API riêng ở khắp nơi), quy trình (workflow và quy tắc nghiệp vụ cấu hình trong sản phẩm), kỹ năng, và hợp đồng (nhiều năm, tự gia hạn nếu không báo huỷ trước 60–90 ngày).
  - Giảm bằng kiến trúc: gọi vendor qua [[port|port]] và adapter của mình hoặc [[anti-corruption-layer|anti-corruption layer]], để mô hình của vendor không lan vào core (bài Clean & Hexagonal architecture). Ưu tiên chuẩn mở: OIDC/[[saml|SAML]] cho đăng nhập, SQL, [[opentelemetry|OpenTelemetry]] cho telemetry, API tương thích S3. Định kỳ xuất dữ liệu về kho của mình.
  - Giảm bằng hợp đồng: định dạng và thời hạn xuất dữ liệu khi chấm dứt, hỗ trợ chuyển giao, trần tăng giá khi gia hạn, quyền chấm dứt khi vendor bị mua lại hay vi phạm SLA nhiều lần. Phần mềm tự cài quan trọng có thể dùng [[source-code-escrow|source code escrow]].
  - Lock-in vẫn có thể là lựa chọn đúng: tính năng riêng đem lại nhiều hơn chi phí thoát (bài Ra quyết định & trade-off). Điều cần là biết chi phí thoát lúc ký, không phải lúc muốn rời.
  - Bẫy chuyển dữ liệu có thật: dịch vụ định danh có thể không cho xuất hash mật khẩu (Amazon Cognito là ví dụ), nên khi rời đi phải chuyển dần lúc người dùng đăng nhập hoặc buộc đặt lại mật khẩu. Đây là câu hỏi cho PoC, không phải cho năm thứ ba.
- **Open source không miễn phí, và license có thể đổi**:
  - Permissive (Apache 2.0, MIT) gần như không ràng buộc. [[copyleft-license|Copyleft]] (GPL) buộc mở mã khi phân phối phần mềm dẫn xuất; AGPL thêm điều khoản mạng: cung cấp dịch vụ qua mạng từ bản đã sửa cũng phải mở mã. Nhiều công ty cấm AGPL trong sản phẩm.
  - [[source-available-license|Source-available]] (SSPL, BSL, RSAL) cho xem mã nhưng hạn chế dùng, thường cấm cung cấp dạng dịch vụ cạnh tranh. BSL có ngày chuyển đổi (change date): mỗi phiên bản tự thành license open source sau một thời hạn định trước, tối đa 4 năm. Các lần đổi license đáng nhớ: Elasticsearch sang SSPL và Elastic License năm 2021 (AWS fork thành OpenSearch; Elastic thêm lựa chọn AGPL năm 2024), Terraform sang BSL năm 2023 (fork OpenTofu), Redis sang RSAL/SSPL năm 2024 (fork Valkey; Redis 8 thêm AGPL năm 2025).
  - Rủi ro nguồn cung: dự án do một hai người duy trì có thể bị bỏ hoặc bị chiếm quyền. Vụ backdoor trong xz utils (CVE-2024-3094, 2024) do một người đã đóng góp khoảng hai năm để chiếm lòng tin của người duy trì cài vào. Đánh giá số người duy trì, tần suất phát hành, ai tài trợ; quy trình kiểm dependency thuộc track Security.
  - Chọn dự án thuộc tổ chức trung lập (Apache, CNCF, Linux Foundation) giảm rủi ro một công ty đổi license, không triệt tiêu.
- **Mua rồi tuỳ biến nặng là kiểu tệ nhất của cả hai**: phân biệt configure (dùng tính năng có sẵn) với customize (sửa mã, script riêng, trường riêng chồng lên). Customize nặng làm mỗi lần nâng cấp thành một dự án, như các hệ ERP bị kẹt ở phiên bản cũ nhiều năm. Với phần generic, đổi quy trình theo sản phẩm. Phải tuỳ biến nặng là dấu hiệu chọn sai sản phẩm hoặc phần đó thật ra là core.
- **Bẫy khi tự xây**: not-invented-here (không tin thứ gì không do mình làm), chọn công nghệ để làm đẹp CV, và ước công 3 tháng cho một thứ người khác đã làm 10 năm. Hỏi: ai sẽ trực sự cố cho nó lúc 3 giờ sáng sau khi người viết đã nghỉ?
- **Bẫy khi mua**: chọn theo demo, mua theo danh sách tính năng rồi dùng 20%, ước thấp tích hợp, license mua dư không dùng (shelfware, phần mềm nằm trên giá), và không ai sở hữu vendor sau khi ký.
- **Sau khi ký**: một người sở hữu quan hệ với vendor; lịch gia hạn và hạn báo huỷ trong lịch chung; review định kỳ với vendor về SLA, sự cố, lộ trình; theo dõi số license dùng thật so với đã mua; diễn tập kế hoạch thoát ở mức tối thiểu (xuất dữ liệu thật và đọc được nó).
- **Quyết định có thể quay lại**: build sang buy khi sản phẩm trên thị trường đã trưởng thành; buy sang build khi phần đó thành lợi thế cạnh tranh hoặc chi phí theo lượng dùng vượt xa tự vận hành ở quy mô lớn. Ghi điều kiện xem lại đo được trong ADR (bài ADR, C4 model & tài liệu kiến trúc).
