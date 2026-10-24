## Quick

[[n-plus-one|N+1]] là khi một query lấy N bản ghi, rồi mỗi bản ghi kéo thêm một query để lấy dữ liệu liên quan. Từng query đều nhanh nhưng độ trễ cộng dồn theo N. **Lấy dữ liệu liên quan trong cùng một query ([[fetch-join|JOIN FETCH]], [[entity-graph|entity graph]], [[dto-projection|DTO projection]]) hoặc theo lô ([[batch-fetching|batch fetching]])**, và viết test đếm số query.

## Interview

Trong JPA/Hibernate, quan hệ `@OneToMany` và `@ManyToMany` mặc định là [[lazy-loading|LAZY]]: entity con chỉ được tải khi code truy cập lần đầu. `@ManyToOne` và `@OneToOne` mặc định là [[eager-loading|EAGER]], nhưng EAGER không chữa được N+1. `em.find()` join quan hệ EAGER vào cùng query, còn với query [[jpql|JPQL]] như `select o from Order o`, Hibernate vẫn chạy thêm một query cho mỗi khách hàng chưa có trong [[persistence-context|persistence context]].

N+1 khó thấy vì:
- Nó nằm trong một dòng getter trông vô hại, thường ở mapper, `toString()` hoặc lúc Jackson serialize entity ra JSON.
- Mỗi query chỉ mất vài mili giây, nên không lọt vào slow query log.
- Với dữ liệu test nhỏ (3 bản ghi) thì không ai thấy chậm.

Cách phát hiện: bật log SQL hoặc `hibernate.generate_statistics` khi chạy local, xem số span DB trong một trace của [[apm|APM]], và viết test khẳng định số query của các endpoint quan trọng.

Cách sửa, theo thứ tự hay dùng:
1. **[[dto-projection|DTO projection]]**: query chỉ lấy đúng các cột màn hình cần, join sẵn. Gọn nhất cho API chỉ đọc.
2. **[[fetch-join|JOIN FETCH]] hoặc `@EntityGraph`**: tải entity cha cùng quan hệ trong một query. Hợp với quan hệ `@ManyToOne`.
3. **[[batch-fetching|Batch fetching]]** (`hibernate.default_batch_fetch_size`): khi chạm tới quan hệ lazy, Hibernate tải luôn tối đa `size` bản ghi cùng loại đang chờ trong một query, biến N+1 thành 1 + ⌈N/size⌉. Đặt một lần cho cả ứng dụng như lưới an toàn.

Cẩn thận với JOIN FETCH một collection: kết hợp với phân trang thì Hibernate cắt trang **trong bộ nhớ** sau khi tải hết dữ liệu. Fetch hai `List` (bag) cùng lúc thì ném `MultipleBagFetchException`; đổi sang `Set` thì hết lỗi nhưng sinh [[cartesian-product|tích Descartes]]. Cách đúng là fetch từng collection trong một query riêng, hoặc dùng batch fetching.

## Deep

- **Phân trang + collection**: Hibernate 6 cảnh báo `HHH90003004: firstResult/maxResults specified with collection fetch; applying in memory`. Cách đúng là hai query: lấy một trang id trước, rồi `JOIN FETCH ... WHERE o.id IN :ids`. Hoặc dùng batch fetching cho collection. Bật `hibernate.query.fail_on_pagination_over_collection_fetch=true` để lỗi này làm test fail thay vì âm thầm tải cả bảng.
- **[[open-session-in-view|Open Session in View]]**: Spring Boot mặc định bật `spring.jpa.open-in-view=true` (và log cảnh báo khi khởi động). Session còn mở tới lúc render response, nên Jackson chạm vào quan hệ lazy sẽ sinh N+1 ngoài tầm mắt của service. Tắt nó đi thì lỗi thành `LazyInitializationException` rõ ràng, buộc bạn tải dữ liệu có chủ đích.
- **Persistence context là cache cấp 1**: trong cùng transaction, mỗi id chỉ được tải một lần. 50 đơn của 4 khách hàng chỉ sinh 4 query thêm, không phải 50. Vì vậy số query thật phụ thuộc dữ liệu, và test với dữ liệu quá đều có thể che lỗi.
- **Batch fetching sinh SQL gì**: Hibernate 6.3+ trên PostgreSQL sinh `where id = any (?)` với một tham số mảng. Database khác dùng `in (?, ?, ...)` có độ dài cố định, phần thừa bind `null`. Số query vẫn là ⌈N/size⌉.
- **`@Fetch(FetchMode.SUBSELECT)`** cho collection: tải con của mọi cha trong một query dùng lại query gốc làm subquery. Hữu ích khi danh sách cha không phân trang.
- **N+1 không chỉ có ở ORM**: gọi repository, Redis hay HTTP API trong vòng lặp cũng là N+1. Cách sửa tương tự: API theo lô (`findAllById`, `MGET`, endpoint nhận danh sách id).
- **Đếm query trong test**: dùng datasource-proxy hoặc `Statistics.getPrepareStatementCount()` của Hibernate để khẳng định số query của endpoint. Test này rẻ và bắt được N+1 ngay khi có người thêm một getter vào mapper.
- **Đừng đổi mọi thứ sang EAGER**: EAGER áp cho mọi lần tải entity, kể cả chỗ không cần, và vẫn không gộp query khi dùng JPQL. Nên khai báo `fetch = FetchType.LAZY` cho cả `@ManyToOne`, rồi tải có chủ đích ở từng use case.
