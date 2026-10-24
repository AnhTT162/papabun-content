## Quick

`LIKE '%áo khoác%'` không dùng được B-tree nên phải quét cả bảng, và không biết kết quả nào "liên quan" hơn. Search engine dựng **[[inverted-index|inverted index]]**: mỗi từ trỏ tới danh sách tài liệu chứa nó, sau khi văn bản đi qua **[[analyzer|analyzer]]** (tách từ, chữ thường, bỏ dấu...). Kết quả được xếp theo độ liên quan (**[[bm25|BM25]]**). Elasticsearch **không phải database chính**: dữ liệu đồng bộ từ database qua [[cdc|CDC]], chỉ tìm thấy được sau khoảng 1 giây (**[[near-real-time|near real-time]]**), và phải dựng lại được từ đầu. Dữ liệu vừa phải thì full-text search của PostgreSQL thường đã đủ.

## Interview

**Vì sao `LIKE` không đủ**: `LIKE 'áo%'` dùng được index, `LIKE '%áo%'` thì không ([[sargable|không sargable]]), nên quét mọi dòng. Nó cũng không hiểu "ao khoac" là "áo khoác", không chịu lỗi gõ, không xếp hạng.

**Inverted index**: lúc ghi, văn bản qua analyzer gồm ba phần:
- character filter, ví dụ bỏ thẻ HTML;
- tokenizer tách thành từ;
- token filter: chữ thường, bỏ dấu (`asciifolding`), từ đồng nghĩa.

Mỗi từ lưu danh sách tài liệu và vị trí. Lúc tìm, câu hỏi đi qua **cùng analyzer** rồi tra các từ. Analyzer lúc ghi và lúc tìm lệch nhau là nguyên nhân số một của "tìm không ra".

**Xếp hạng BM25** cộng điểm theo ba yếu tố:
- Từ xuất hiện nhiều trong tài liệu được cộng thêm, nhưng có trần.
- Từ hiếm trong cả tập được nhiều điểm hơn (IDF).
- Trường ngắn được ưu tiên hơn trường dài.

Thêm boost theo trường (tên sản phẩm quan trọng hơn mô tả) và theo tín hiệu nghiệp vụ (bán chạy, còn hàng).

**Kiến trúc Elasticsearch**:
- Mỗi index chia thành primary shard (cố định khi tạo) cộng replica.
- Mỗi shard là một index Lucene gồm các [[lucene-segment|segment]] bất biến.
- Tài liệu mới chỉ tìm thấy sau **refresh** (mặc định 1 giây).
- Update thực chất là xoá rồi ghi lại.
- Không có transaction.

**Đồng bộ từ database**: database là nguồn sự thật. Ghi thẳng vào cả hai là [[dual-write|dual write]]; thay vào đó, thay đổi đi qua [[outbox|outbox]] hoặc CDC tới consumer ghi vào Elasticsearch, idempotent theo id. Đổi mapping hay analyzer thì phải reindex sang index mới rồi chuyển [[index-alias|alias]], không có `ALTER`.

**Khi nào không cần**: vài triệu dòng, tìm theo tên với bộ lọc đơn giản. PostgreSQL với `tsvector` + [[gin-index|GIN]], hoặc [[trigram-index|trigram index]] (`pg_trgm`) cho `LIKE '%...%'` và lỗi gõ, tránh được một hệ thống phải đồng bộ và vận hành thêm.

## Deep

- **Tiếng Việt**:
  - Bỏ dấu để "ca phe" khớp "cà phê": Elasticsearch có `asciifolding` hoặc `icu_folding` (plugin ICU); PostgreSQL có extension `unaccent`. Cả hai đều chuyển `đ` thành `d`.
  - Nên giữ cả hai bản: một trường có dấu và một trường đã bỏ dấu (multi-field), chấm điểm cao hơn khi khớp đúng dấu, để "bán" không ngang hàng với "bạn".
  - Từ tiếng Việt nhiều âm tiết ("điện thoại") bị tách thành từng âm tiết. Tìm theo cụm (`match_phrase`, hoặc shingle) giúp kết quả đúng thứ tự xếp cao hơn; tách từ đúng nghĩa cần plugin tách từ tiếng Việt.
  - PostgreSQL không có cấu hình tiếng Việt: dùng `to_tsvector('simple', unaccent(name))`.
- **Mapping**:
  - `text` được phân tích để tìm kiếm; `keyword` giữ nguyên để lọc, sắp xếp, gom nhóm.
  - Trường cần cả hai thì khai báo multi-field (`name` là `text`, `name.raw` là `keyword`).
  - Dynamic mapping đoán kiểu từ tài liệu đầu tiên: một chuỗi `"2026-10-24"` thành `date`, rồi tài liệu sau có chuỗi khác bị từ chối. Production nên khai báo mapping tường minh và đặt `dynamic: strict`.
  - Quá nhiều trường động (mapping explosion) bị chặn ở `index.mapping.total_fields.limit` (mặc định 1.000).
- **Mảng object bị làm phẳng**: `variants: [{color: đỏ, size: M}, {color: xanh, size: L}]` với kiểu `object` thành `color: [đỏ, xanh]`, `size: [M, L]`, nên tìm "đỏ và L" vẫn khớp. Dùng kiểu `nested` (truy vấn `nested`, tốn hơn) khi cần khớp trong cùng một phần tử.
- **Near real-time và đọc lại ngay**: refresh mặc định mỗi giây (khi không đặt `refresh_interval` tường minh, shard không có lượt tìm trong 30 giây thì tạm ngừng refresh định kỳ, và lượt tìm đầu tiên sau đó phải chờ refresh nên chậm hơn). Cần tìm thấy ngay sau khi ghi thì gửi kèm `refresh=wait_for`, đừng dùng `refresh=true` liên tục vì mỗi lần tạo một segment nhỏ. Độ bền nằm ở translog, không phụ thuộc refresh.
- **Segment và merge**: segment bất biến; xoá và update chỉ đánh dấu tài liệu cũ là đã xoá, tới khi merge mới thật sự dọn. Dữ liệu update liên tục (tồn kho, giá) sinh nhiều tài liệu chết và nhiều merge. Cân nhắc chỉ đẩy sang Elasticsearch những thay đổi ảnh hưởng tìm kiếm (ví dụ chuyển `in_stock` từ có sang hết), còn số tồn chính xác thì đọc từ database cho trang kết quả.
- **Shard**:
  - Số primary shard cố định khi tạo; muốn đổi thì `_split`, `_shrink` hoặc reindex.
  - Hướng dẫn của Elastic: mỗi shard khoảng 10–50GB, và tránh rất nhiều shard nhỏ vì mỗi shard tốn heap và tài nguyên của cluster.
  - Mỗi shard tính IDF trên dữ liệu của riêng nó, nên với dữ liệu ít, điểm có thể lệch giữa các shard; `search_type=dfs_query_then_fetch` tính lại thống kê chung, đổi lại thêm một vòng gọi.
- **Phân trang sâu**: `from + size` bị chặn ở `index.max_result_window` (10.000), vì mỗi shard phải trả `from + size` kết quả để node điều phối trộn, giống scatter-gather của bài Sharding. Dùng [[search-after|`search_after`]] với point in time (PIT), giống [[keyset-pagination|keyset pagination]] của SQL, để duyệt sâu hoặc xuất dữ liệu; `scroll` không còn được khuyên cho phân trang sâu.
- **Reindex không downtime**:
  1. Tạo `products_v2` với mapping mới; khi nạp đặt `refresh_interval: -1` và `number_of_replicas: 0`, xong thì bật lại.
  2. Nạp từ database (hoặc `_reindex` từ index cũ nếu `_source` đủ).
  3. Trong lúc nạp, consumer CDC ghi vào cả hai index (hoặc ghi lại các thay đổi từ thời điểm bắt đầu nạp).
  4. Chuyển alias `products` sang `products_v2` trong một lệnh `_aliases` nguyên tử.
  Ứng dụng luôn đọc qua alias, không bao giờ đọc tên index thật.
- **Thứ tự và trùng lặp khi đồng bộ**:
  - Dùng id của database làm `_id`, và ghi bằng thao tác `index` (ghi đè cả tài liệu) kèm phiên bản tăng dần (cột `version` hoặc LSN) với `version_type=external`. Thao tác `update` (kể cả `doc_as_upsert`) không hỗ trợ version external, nên cập nhật một phần cũng phải dựng lại cả tài liệu.
  - Bản có phiên bản cũ hơn bị từ chối với `409 version_conflict_engine_exception`; indexer phải coi 409 là thành công, nếu không sẽ retry mãi.
  - Sự kiện xoá phải được đồng bộ như một thay đổi. Sau khi xoá, Elasticsearch chỉ nhớ phiên bản trong `index.gc_deletes` (mặc định 60 giây): một sự kiện cũ đến muộn hơn thế sẽ làm tài liệu đã xoá sống lại. Cách chắc hơn là soft delete (`deleted: true` kèm phiên bản, lọc ra khi tìm) rồi dọn định kỳ.
  - Tài liệu gộp sẵn tên thương hiệu hay danh mục thì đổi tên một thương hiệu kéo theo cập nhật hàng nghìn tài liệu: indexer cần luồng reindex theo `brand_id`, hoặc chỉ lưu id rồi tra tên lúc hiển thị.
- **Cụm Elasticsearch**: ba node master-eligible để bầu chọn theo đa số; từ 7.x cluster tự quản lý cấu hình bầu chọn nên lỗi split brain do cấu hình `minimum_master_nodes` sai không còn. Bản 8.x tự tính heap theo vai trò node và RAM, nên thường để mặc định; nếu đặt tay thì tối đa khoảng 50% RAM và dưới khoảng 31GB để giữ compressed oops; phần RAM còn lại để hệ điều hành cache file của Lucene.
- **Java**: client chính thức hiện tại là Elasticsearch Java API Client (`co.elastic.clients`); High Level REST Client bị deprecated từ 7.15. Spring Data Elasticsearch có repository và mapping bằng annotation. OpenSearch là bản tách ra từ Elasticsearch 7.10 sau khi Elastic đổi giấy phép năm 2021 (năm 2024 Elastic thêm lựa chọn AGPL), có client riêng; hai bên API khác dần theo thời gian.
- **PostgreSQL full-text đi sâu**:
  - Cột sinh tự động `search tsvector GENERATED ALWAYS AS (to_tsvector('simple', unaccent(name || ' ' || coalesce(brand, '')))) STORED` cộng index GIN. `unaccent` không phải hàm `IMMUTABLE`, nên muốn dùng trong cột sinh hoặc index phải bọc nó trong một hàm `IMMUTABLE` của mình.
  - `websearch_to_tsquery` hiểu cú pháp kiểu Google (dấu ngoặc kép, dấu trừ).
  - `ts_rank` không phải BM25 và phải tính trên mọi dòng khớp, nên chậm khi một từ phổ biến khớp hàng triệu dòng.
  - `pg_trgm`: `CREATE INDEX ... USING gin (name gin_trgm_ops)` cho `LIKE '%...%'` và `ILIKE`, toán tử `%` và `similarity()` cho lỗi gõ.
- **Autocomplete**: `search_as_you_type` hoặc analyzer `edge_ngram` khi index (không dùng ở lúc tìm), hoặc completion suggester cho gợi ý rất nhanh. Bài Thiết kế autocomplete đi sâu phần hệ thống.
- **Tìm theo nghĩa**: Elasticsearch 8 có trường `dense_vector` và tìm kNN (HNSW); PostgreSQL có `pgvector`. Kết hợp điểm từ khoá và điểm vector (hybrid search, ví dụ bằng reciprocal rank fusion) thường cho kết quả tốt hơn từng cách riêng.
