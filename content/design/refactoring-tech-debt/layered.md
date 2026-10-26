## Quick

[[refactoring|Refactoring]] là **đổi cấu trúc mà không đổi hành vi quan sát được**, làm từng bước nhỏ và có test bảo vệ. [[technical-debt|Nợ kỹ thuật]] là phần chi phí thay đổi tăng thêm vì code hiện tại, giống tiền lãi: chỉ đáng trả ở chỗ hay phải sửa. **Ưu tiên theo hotspot (vừa phức tạp vừa đổi nhiều)**, và không trộn refactor với thay đổi hành vi trong cùng một commit.

## Interview

**[[code-smell|Code smell]] hay gặp và cách refactor**:
- Long method, large class: Extract Method, Extract Class theo trách nhiệm.
- Feature envy (method dùng dữ liệu của class khác nhiều hơn của mình): Move Method về nơi có dữ liệu.
- Shotgun surgery (một thay đổi chạm mười file) và divergent change (một file đổi vì nhiều lý do): gom lại theo lý do thay đổi.
- [[primitive-obsession|Primitive obsession]]: `String phone`, `long amount` khắp nơi; thay bằng [[value-object|value object]] `PhoneNumber`, `Money` có validate.
- Câu lệnh `switch` theo loại lặp ở nhiều chỗ: polymorphism hoặc `sealed` + `switch` (bài SOLID).

**Refactor an toàn**:
1. Có test bảo vệ hành vi **hiện tại**. Code cũ chưa có test thì viết [[characterization-test|characterization test]]: ghi lại output thật với dữ liệu thật, kể cả hành vi trông như bug.
2. Dùng refactoring tự động của IDE (rename, extract, inline, change signature) thay vì sửa tay.
3. Mỗi bước nhỏ, test xanh, commit. Commit refactor riêng với commit đổi hành vi để review và revert dễ.

**Thay đổi lớn mà không dừng hệ thống**: [[strangler-fig|strangler fig]] (chuyển dần từng luồng sang code mới, phía trước đặt một lớp định tuyến), [[branch-by-abstraction|branch by abstraction]] (đặt interface trước cài đặt cũ, viết cài đặt mới, chuyển dần bằng [[feature-flag|feature flag]]), và [[expand-contract|expand-contract]] cho API và schema (chi tiết ở bài Schema migration).

**Thuyết phục làm việc trả nợ**: nói bằng hậu quả đo được (lead time của tính năng ở module đó, số sự cố, thời gian onboard), không nói "code xấu". Gắn việc trả nợ với tính năng sắp làm ở đúng chỗ đó, hoặc giữ một tỉ lệ cố định mỗi sprint.

## Deep

- **[[hotspot|Hotspot]] từ lịch sử git**: `git log --format=format: --name-only --since=12.month | grep -v '^$' | sort | uniq -c | sort -rn` cho file đổi nhiều nhất; kết hợp với độ phức tạp (cognitive complexity của SonarQube) để chọn chỗ trả nợ. File phức tạp mà một năm không ai sửa thì nợ đó chưa tốn lãi.
- **Phân loại nợ** (Martin Fowler): cố ý hay vô tình, thận trọng hay liều lĩnh. Nợ cố ý và thận trọng ("ra mắt trước, ghi lại để trả sau") là quyết định kinh doanh hợp lệ nếu được ghi lại; nợ liều lĩnh ("không có thời gian viết test") thì lãi tăng nhanh nhất.
- **Refactor có thể đổi hành vi mà không ai để ý**: thay vòng lặp bằng Stream (`Collectors.toMap` ném exception khi key trùng), đổi `ArrayList` sang `Set` (mất thứ tự, mất phần tử trùng), đổi `collect(Collectors.toList())` sang `Stream.toList()` (Java 16+, list không sửa được). `Collectors.toMap` còn ném `NullPointerException` khi value là `null`, trong khi vòng lặp `put` chấp nhận. Đây là lý do characterization test dùng dữ liệu giống thật.
- **Test có bảo vệ được không**: coverage cao chưa chắc assert đúng. [[mutation-testing|Mutation testing]] (PIT) cố tình sửa code (đổi `>` thành `>=`) và kiểm tra test có đỏ không; module sắp refactor lớn đáng để chạy nó trước.
- **Migration hàng loạt bằng công cụ**: OpenRewrite có recipe cho nâng Spring Boot 2 lên 3, `javax.*` sang `jakarta.*`, JUnit 4 sang 5. Chạy recipe trên nhánh riêng, review diff, chạy toàn bộ test.
- **Deprecation có lộ trình**: `@Deprecated(since = "2.4", forRemoval = true)` kèm Javadoc chỉ API thay thế; compiler cảnh báo mạnh hơn với `forRemoval`. Theo dõi số chỗ gọi còn lại trước khi xoá.
- **Code cũ không viết test được**: class tự `new` dependency hay gọi singleton tĩnh thì tìm seam (chỗ thay được hành vi mà không sửa code xung quanh): thêm constructor nhận dependency, giữ constructor cũ gọi sang. Code mới thêm vào thì viết thành method hoặc class riêng có test (sprout method/class) rồi gọi từ code cũ, thay vì viết chen vào giữa method 300 dòng. Characterization test cho output lớn (file, báo cáo) có thể làm dạng golden master: lưu output lần đầu làm mẫu, các lần sau so khớp.
- **Viết lại từ đầu hiếm khi đúng**: code cũ chứa nhiều quy tắc nghiệp vụ không ai còn nhớ; bản viết lại phải đuổi theo hệ thống đang chạy mà vẫn đổi mỗi tuần. Strangler fig thường thắng vì giao giá trị từng phần và rủi ro nhỏ mỗi bước.
- **Boy scout rule có giới hạn**: dọn một chút ở chỗ đang sửa là tốt, nhưng refactor lớn "tiện tay" trong PR tính năng làm PR khó review. Tách thành PR refactor riêng, merge trước.
- **Đo kết quả**: [[dora-metrics|chỉ số DORA]] (lead time, deployment frequency, change failure rate, failed deployment recovery time, trước đây gọi là time to restore) của nhóm, hoặc đơn giản là thời gian làm một loại thay đổi quen thuộc trước và sau.
