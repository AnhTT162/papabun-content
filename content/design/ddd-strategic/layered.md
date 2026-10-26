## Quick

DDD chiến lược chia một hệ thống lớn theo [[bounded-context|bounded context]]: ranh giới mà bên trong đó một mô hình và một [[ubiquitous-language|ubiquitous language]] nhất quán. [[context-map|Context map]] mô tả các context quan hệ và dịch dữ liệu cho nhau thế nào. Phân loại subdomain (core, supporting, generic) quyết định **đầu tư người giỏi và code tự viết vào đâu**. **Không cố tạo một mô hình `Customer` dùng chung cho cả công ty.**

## Interview

**Subdomain và bounded context**: subdomain thuộc không gian bài toán (doanh nghiệp làm gì), bounded context thuộc không gian giải pháp (code và mô hình). Lý tưởng là gần 1:1; một context có thể phủ vài subdomain supporting hay generic, nhưng core nên có context riêng. Ba loại subdomain:
- *[[core-domain|Core]]*: làm nên khác biệt (định giá động, chấm điểm tín dụng). Tự xây, giao người giỏi nhất, mô hình kỹ.
- *Supporting*: cần cho doanh nghiệp nhưng không tạo khác biệt. Tự xây, giữ đơn giản.
- *Generic*: bài toán chung (xác thực, gửi email, kế toán chuẩn). Mua hoặc dùng sản phẩm có sẵn.

**Tìm ranh giới**: lắng nghe chỗ từ ngữ đổi nghĩa ("đơn hàng" của bán hàng khác "đơn hàng" của kho), dùng [[event-storming|event storming]] với người nghiệp vụ để thấy các nhóm sự kiện, nhìn ai sở hữu quyết định, và nhìn cấu trúc đội ([[conways-law|Conway's law]]).

**Các kiểu quan hệ trong context map** (upstream là bên mà mô hình của nó ảnh hưởng tới bên kia, downstream là bên chịu ảnh hưởng):
- *Partnership*: hai đội cùng thành công hoặc cùng thất bại, lên kế hoạch tích hợp chung.
- *Customer–supplier*: downstream nêu nhu cầu, upstream lên kế hoạch đáp ứng.
- *Conformist*: downstream chấp nhận nguyên mô hình của upstream (như API của một đối tác lớn).
- *[[anti-corruption-layer|Anti-corruption layer]]*: downstream dịch mô hình upstream sang mô hình của mình.
- *Open host service + published language*: upstream mở API hoặc event có schema công bố cho nhiều bên.
- *Shared kernel*: hai đội dùng chung một phần mô hình nhỏ, đổi phải thống nhất.
- *Separate ways*: không tích hợp, mỗi bên tự làm.

**Bounded context và microservice**: một microservice không nên trải qua nhiều context, nhưng một context có thể là một module trong [[modular-monolith|modular monolith]]. Tách service theo context chứ không theo bảng (`CustomerService` cho cả công ty là anti-pattern "entity service").

## Deep

- **Cùng một thực thể, nhiều mô hình**: `Product` trong Catalog (tên, ảnh, thuộc tính), Pricing (giá, quy tắc khuyến mãi), Inventory (tồn kho theo kho). Chúng nối với nhau bằng `productId`, không bằng một object hay bảng chung. Bảng `products` 80 cột mà mọi đội cùng sửa là dấu hiệu rõ nhất của context bị trộn.
- **Database dùng chung là coupling ẩn**: hai context đọc ghi cùng bảng thì đổi schema phải phối hợp mọi đội. Mỗi context sở hữu dữ liệu của mình; context khác hỏi qua API hoặc giữ bản sao cục bộ cập nhật bằng event.
- **Published language cần quản lý phiên bản**: event `OrderPlaced` mà nhiều context nghe là một hợp đồng công khai. Thêm trường tuỳ chọn là tương thích; đổi nghĩa hay xoá trường cần phiên bản mới và thời gian chuyển đổi (bài Event schema evolution).
- **Conformist hay anti-corruption layer**: conformist rẻ khi mô hình upstream hợp với bạn hoặc tích hợp nhỏ. Mô hình upstream xấu, hay đổi, hoặc là hệ thống cũ thì ACL đáng chi phí, vì nó chặn mô hình xấu lan vào core domain.
- **Shared kernel dễ thành nút thắt**: chỉ hợp khi hai đội gần nhau và phần dùng chung rất nhỏ, ổn định (ví dụ [[value-object|value object]] `Money`). Một thư viện "common-domain" lớn mà mọi service phụ thuộc là shared kernel đã mất kiểm soát: đổi một class là mọi service phải build lại.
- **Conway's law hai chiều**: kiến trúc phản chiếu cách các đội giao tiếp. Ranh giới context nên khớp với ranh giới đội; một context do ba đội cùng sửa sẽ dần bị trộn. Có thể chủ động đổi cấu trúc đội để có kiến trúc mong muốn (inverse Conway maneuver).
- **Event storming ba mức**: big picture (cả doanh nghiệp, tìm context và điểm đau), process level (một luồng nghiệp vụ, thêm command, policy, read model), design level (tới mức aggregate, xem bài DDD chiến thuật). Mức big picture là công cụ chính của DDD chiến lược.
- **Ranh giới đổi theo thời gian**: doanh nghiệp đổi, context cũng có thể cần tách hoặc gộp. Dấu hiệu cần tách: một context có hai nhóm thuật ngữ mâu thuẫn, hoặc hai đội luôn chờ nhau. Dấu hiệu gộp nhầm thành hai: hai service luôn deploy cùng nhau và gọi nhau đồng bộ cho mọi thao tác.
- **Big ball of mud**: hệ thống không có ranh giới rõ. Không cần viết lại: vẽ context map của hiện trạng (kể cả xấu), chọn core domain, dựng ACL quanh nó, rồi tách dần ([[strangler-fig|strangler fig]]).
