## Quick

[[conways-law|Conway's law]]: hệ thống sẽ mang hình dạng của đường giao tiếp trong tổ chức xây nó. Vì vậy cấu trúc team là một quyết định kiến trúc. **Thiết kế team và kiến trúc cùng lúc: mỗi phần của hệ thống có đúng một team sở hữu (xây và vận hành), team được chia theo dòng giá trị với [[cognitive-load|tải nhận thức]] vừa sức, và tương tác giữa các team được chọn có chủ đích thay vì để mọi thay đổi chờ nhau.**

## Interview

Melvin Conway viết năm 1968 rằng tổ chức thiết kế hệ thống sẽ tạo ra thiết kế sao chép cấu trúc giao tiếp của chính nó. Hệ quả thực tế: nếu team chia theo tầng, frontend, backend, DBA, thì mỗi tính năng đi qua ba team và ba hàng đợi, và kiến trúc thành ba tầng dính chặt. Muốn kiến trúc nào thì phải có cấu trúc team tương ứng; đổi team trước để kiến trúc đi theo gọi là [[inverse-conway-maneuver|inverse Conway maneuver]].

Tôi dùng khung Team Topologies của Skelton và Pais. Phần lớn team là [[stream-aligned-team|stream-aligned]]: sở hữu trọn một dòng giá trị, từ giao diện tới database và trực sự cố. [[platform-team|Platform team]] cung cấp hạ tầng tự phục vụ để các team đó không phải làm lại. [[enabling-team|Enabling team]] giúp các team học một năng lực mới trong thời gian có hạn. [[complicated-subsystem-team|Complicated-subsystem team]] giữ phần cần chuyên môn sâu như mô hình định giá. Tương tác có ba kiểu: collaboration trong thời gian ngắn, [[x-as-a-service|X-as-a-Service]] qua giao diện rõ, và facilitating.

Ranh giới sở hữu là quy tắc tôi giữ chặt: một service có đúng một team sở hữu; một team có thể giữ vài service, nhưng không quá sức hiểu và trực của 5–9 người. Service mà ai cũng sửa là service không ai chịu trách nhiệm.

Bẫy hay gặp: chia [[microservices]] nhiều hơn số team có thể sở hữu, tổ chức lại team mà không gán lại service, và tăng người để chạy nhanh hơn trong khi nút thắt là phụ thuộc giữa các team. Tôi đo bằng số tính năng phải chạm nhiều team, thời gian chờ team khác, và [[dora-metrics|DORA metrics]] trước và sau khi đổi.

## Deep

- **Conway's law có bằng chứng**:
  - Conway viết trong bài "How Do Committees Invent?" (Datamation, 1968); Fred Brooks đặt tên "Conway's law" trong *The Mythical Man-Month* (1975).
  - MacCormack, Rusnak và Baldwin (Research Policy, 2012) so các cặp sản phẩm cùng chức năng: sản phẩm do tổ chức phân tán, gắn kết lỏng (nhiều dự án open source) có code module hoá hơn sản phẩm do một team gắn chặt làm ra. Kết quả ủng hộ [[mirroring-hypothesis|mirroring hypothesis]]: cấu trúc sản phẩm phản chiếu cấu trúc tổ chức.
  - Nghiên cứu của Microsoft Research trên Windows Vista (Nagappan và cộng sự, ICSE 2008): các chỉ số tổ chức (bao nhiêu người, bao nhiêu nhóm cùng sửa một binary, người rời đi) dự đoán binary dễ lỗi tốt hơn các chỉ số code như độ phức tạp hay độ phủ test.
  - Nghĩa thực tế: một module do ba team cùng sửa sẽ dần mất ranh giới (bài DDD chiến lược); hai service do một team giữ sẽ dần gọi nhau trực tiếp, chung database, vì chẳng ai phải xin phép ai.
- **[[inverse-conway-maneuver|Inverse Conway maneuver]]** (Jonny LeRoy và Matt Simons đặt tên năm 2010): đổi cấu trúc team theo kiến trúc mong muốn trước, để giao tiếp mới đẩy kiến trúc theo. Không làm được khi kiến trúc hiện tại buộc mọi team phải sửa chung một chỗ: cần tách dần phần đó song song ([[strangler-fig|strangler fig]], [[modular-monolith|modular monolith]]). Ngược lại, khi không đổi được tổ chức, chọn kiến trúc vừa với nó: 2 team thì đừng làm 30 microservices (bài Chọn kiểu kiến trúc).
- **Bốn kiểu team** (Team Topologies, Skelton và Pais 2019, bản 2 năm 2025):
  - [[stream-aligned-team|Stream-aligned]]: theo một dòng giá trị (một sản phẩm, một hành trình người dùng, một nhóm khách hàng). Đủ kỹ năng để đưa thay đổi ra production và vận hành nó mà không chờ team khác. Đây là đa số; các kiểu còn lại tồn tại để giảm tải cho kiểu này.
  - [[platform-team|Platform]]: cung cấp dịch vụ nội bộ tự phục vụ (pipeline, môi trường, observability, database theo mẫu). Platform là một sản phẩm: có người dùng (các team khác), có lộ trình, đo mức dùng; team sản phẩm được quyền không dùng nếu platform không tốt hơn tự làm.
  - [[enabling-team|Enabling]]: chuyên gia giúp team khác có năng lực mới (test tự động, observability, bảo mật), làm việc kèm trong vài tuần tới vài tháng rồi rút. Enabling team làm thay mãi thì thành nút thắt mới.
  - [[complicated-subsystem-team|Complicated-subsystem]]: giữ phần cần chuyên môn hiếm (mô hình định giá, engine video, thuật toán định tuyến), để team stream-aligned không phải mang tải đó. Chỉ lập khi thật sự cần chuyên môn sâu, không phải để chia hệ thống theo thành phần.
- **Ba kiểu tương tác**:
  - Collaboration: hai team làm sát nhau để khám phá điều mới; tốn băng thông giao tiếp nên phải có thời hạn.
  - [[x-as-a-service|X-as-a-Service]]: một bên dùng dịch vụ của bên kia qua giao diện rõ, ít trao đổi. Đây là đích của quan hệ với platform.
  - Facilitating: một team giúp team khác học hoặc gỡ vướng; kiểu của enabling team.
  - Kiểu tương tác đổi theo thời gian: collaboration khi đang dựng một dịch vụ platform mới, chuyển sang X-as-a-Service khi nó ổn định. Hai team mãi ở collaboration là dấu hiệu ranh giới sai.
- **[[cognitive-load|Tải nhận thức]]** (lý thuyết của John Sweller): tải nội tại (độ khó của chính bài toán), tải ngoại lai (môi trường, công cụ, quy trình rườm rà), tải liên quan (phần học để làm tốt hơn). Platform và tự động hoá giảm tải ngoại lai để team dồn sức cho tải nội tại của miền nghiệp vụ. Dấu hiệu quá tải: team không giải thích nổi hệ thống của mình, trực sự cố cho thứ không ai hiểu, mọi thay đổi chậm. Cách đo đơn giản: hỏi team định kỳ họ có hiểu và tự tin thay đổi từng phần mình giữ không.
- **Cỡ team và giao tiếp**:
  - Team ổn định 5–9 người ([[two-pizza-team|two-pizza team]] của Amazon cùng ý). Số cặp giao tiếp là n(n−1)/2: 8 người có 28 cặp, 14 người có 91, 46 người có 1.035.
  - [[brooks-law|Brooks's law]]: thêm người vào dự án đang trễ làm nó trễ hơn, vì người mới cần được kèm và đường giao tiếp tăng theo bình phương (góc nhìn trong một team ở bài Vai trò Tech Lead). Thêm team chỉ giúp khi ranh giới cho phép các team làm độc lập.
  - Team là đơn vị giao hàng, không phải cá nhân: giữ team ổn định và đưa việc tới team, thay vì lập team mới cho mỗi dự án rồi giải tán (mất hiểu biết về hệ thống, không ai sở hữu sau khi xong).
- **Ranh giới sở hữu**:
  - Mỗi service, thư viện dùng chung, topic, database, dashboard có đúng một team sở hữu, ghi trong [[service-catalog|service catalog]] (Backstage là một ví dụ phổ biến) và [[codeowners|CODEOWNERS]]. Sở hữu nghĩa là quyết định thay đổi, review, và trực sự cố ([[you-build-it-you-run-it|you build it, you run it]], câu của Werner Vogels năm 2006).
  - Team khác cần thay đổi gấp thì mở PR vào repo của team sở hữu (internal open source); team sở hữu review và giữ trách nhiệm sau đó.
  - Sau mỗi lần tổ chức lại, rà danh sách service: service không có chủ (orphan) là rủi ro vận hành và bảo mật, sẽ không ai vá thư viện của nó.
  - [[team-api|Team API]]: mỗi team công bố cái họ cung cấp (API, tài liệu, SLO), cách liên hệ, lịch làm việc, và cách nhận yêu cầu. Giảm câu hỏi lặt vặt chen vào giữa việc.
- **Tìm ranh giới ([[fracture-plane|fracture plane]])**: theo [[bounded-context|bounded context]] là tốt nhất (bài DDD chiến lược); ngoài ra theo yêu cầu tuân thủ (phần thanh toán chịu [[pci-dss|PCI DSS]] tách riêng), nhịp thay đổi (phần đổi hằng ngày tách khỏi phần ổn định), vị trí và múi giờ, mức rủi ro, yêu cầu hiệu năng riêng, công nghệ, hay nhóm người dùng. Chia theo công nghệ (team frontend, team database) thường là lựa chọn tệ nhất vì mọi tính năng phải đi qua nhiều team.
- **[[component-team|Component team]] và team theo tầng**: team frontend, backend, DBA, QA, ops riêng biệt nghĩa là mỗi tính năng có nhiều lần bàn giao và hàng đợi. Lead time dài nhưng thời gian làm thật ngắn: [[flow-efficiency|flow efficiency]] (thời gian làm thật chia cho lead time) thường dưới 20%. Đưa các kỹ năng vào cùng team stream-aligned; chuyên gia hiếm thì thành enabling hoặc platform.
- **Platform engineering**:
  - [[internal-developer-platform|Internal developer platform]] gom các dịch vụ tự phục vụ; [[golden-path|golden path]] (tên do Spotify dùng; Netflix gọi là paved road) là đường mặc định được hỗ trợ tốt: template service, pipeline, dashboard, cảnh báo sẵn. Không bắt buộc, nhưng đi đường khác thì team tự chịu.
  - [[thinnest-viable-platform|Thinnest viable platform]]: platform nhỏ nhất đủ giúp các team, có khi chỉ là một trang tài liệu và vài template. Bắt đầu từ nỗi đau của team sản phẩm, không bắt đầu bằng việc dựng một cổng nội bộ lớn.
  - Bẫy: platform team xây thứ không ai yêu cầu, hoặc thành bộ phận nhận ticket (mọi deploy chờ họ), tức một component team mới.
- **Mô hình hay bị chép sai**: bài "Scaling Agile @ Spotify" (Kniberg và Ivarsson, 2012) với squad, tribe, chapter, guild bị nhiều công ty sao chép tên gọi mà không có quyền tự chủ, kiến trúc tách rời và văn hoá đi kèm. Chính tác giả nói đó là ảnh chụp cách một công ty làm ở một thời điểm, không phải khuôn mẫu. Đổi tên team không đổi đường giao tiếp.
- **Team ngoài công ty và nhiều múi giờ**: ranh giới hợp đồng với vendor cũng là đường giao tiếp; đừng chia một bounded context giữa team nội bộ và team thuê ngoài theo hợp đồng giá cố định, vì mỗi thay đổi thành một change request. Team ở các múi giờ xa nhau nên được chia theo ranh giới ít trao đổi.
- **Đo trước và sau khi đổi**: [[dora-metrics|DORA metrics]] (lead time, tần suất deploy, tỉ lệ thay đổi gây lỗi, thời gian khôi phục), tỉ lệ tính năng phải chạm nhiều hơn một team, thời gian chờ team khác, số service trên mỗi team, khảo sát tải nhận thức. Tổ chức lại có giá (mất hiểu biết, năng suất giảm vài tháng), nên làm theo từng bước, thử với một dòng giá trị trước.
- **Vai trò SA**: đề xuất kiến trúc nên kèm bản đồ team sở hữu từng phần, và chỉ ra chỗ kiến trúc buộc nhiều team phải phối hợp. Quyết định tổ chức thuộc về lãnh đạo kỹ thuật và quản lý, nhưng SA phải nói rõ hệ quả kiến trúc của mỗi phương án tổ chức (bài Vai trò Solution Architect).
