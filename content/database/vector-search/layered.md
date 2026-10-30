## Quick

[[embedding|Embedding]] biến một đoạn văn thành một vector vài trăm tới vài nghìn số, sao cho hai câu gần nghĩa có hai vector gần nhau. [[vector-search|Vector search]] tìm k vector gần câu hỏi nhất ([[knn|kNN]]). So với mọi vector thì chậm khi có hàng triệu, nên dùng chỉ mục [[ann|ANN]] như [[hnsw|HNSW]]: nhanh hơn nhiều lần, đổi lại có thể sót kết quả. **Ba quy tắc: tài liệu và câu hỏi phải dùng cùng một model; đo [[recall-at-k|recall]] so với tìm chính xác trước khi chỉnh tham số; trộn với [[bm25|BM25]] ([[hybrid-search|hybrid search]]) vì vector bỏ sót mã sản phẩm và từ hiếm.**

## Interview

Tôi bắt đầu từ vấn đề: BM25 chỉ khớp từ, nên "đồ cho bé đi học" không ra "balo tiểu học". Một model embedding biến câu thành vector, ví dụ 768 số; hai câu gần nghĩa có [[cosine-similarity|cosine similarity]] cao. Tìm theo nghĩa là tìm k vector gần câu hỏi nhất.

Tìm chính xác phải so với mọi vector: 5 triệu × 768 phép nhân cho mỗi truy vấn. Vì vậy dùng ANN, phổ biến nhất là HNSW: một đồ thị nhiều tầng, mỗi vector nối với vài chục hàng xóm gần nó. Truy vấn đi tham lam từ tầng trên xuống và giữ một hàng đợi ứng viên. Hàng đợi càng lớn (`num_candidates` của Elasticsearch, `hnsw_ef_search` của Doris) thì recall càng cao và càng chậm. Tôi đo trên 100.000 vector 384 chiều bằng Lucene: 10 ứng viên cho recall 0,89, 50 ứng viên cho 0,999, vẫn dưới 1 ms.

Ràng buộc chính là bộ nhớ: HNSW cần vector và đồ thị nằm trong RAM ([[page-cache|page cache]]). 5 triệu vector 768 chiều dạng float là 15 GB. [[vector-quantization|Lượng tử hoá]] xuống int8 còn khoảng 4 GB, xuống 1 bit còn khoảng 0,55 GB, đổi lại phải lấy dư ứng viên rồi tính lại điểm bằng vector gốc.

Bẫy hay gặp: lọc sau khi tìm (lấy 100 gần nhất rồi mới lọc còn hàng) làm mất gần hết kết quả, phải lọc ngay trong lúc tìm. Đổi model là phải tính lại toàn bộ vector, vì vector của hai model không so được với nhau. Và vector kém với mã sản phẩm, số model, tên riêng hiếm.

Nên tôi chọn hybrid: chạy BM25 và kNN song song, trộn thứ hạng bằng [[rrf|RRF]]. Elasticsearch có sẵn `dense_vector`, kNN có pre-filter và retriever `rrf`. Doris 4 có ANN index khi vector cần đi cùng truy vấn phân tích. Cuối cùng tôi đo chất lượng bằng bộ câu hỏi có đáp án, không chỉ đo recall của ANN.

## Deep

- **Embedding và độ gần**: model được huấn luyện để câu gần nghĩa có vector gần nhau. Số chiều thường từ 384 tới 3.072. Ba cách đo: cosine (góc giữa hai vector), dot product, khoảng cách L2. Vector đã chuẩn hoá về độ dài 1 thì cosine bằng dot product và xếp hạng giống L2, nên chuẩn hoá một lần lúc ghi rồi dùng dot product. Elasticsearch mặc định `cosine`; chọn `dot_product` nhanh hơn một chút nhưng bắt buộc mọi vector có độ dài 1. Doris không có cosine, chỉ có `l2_distance` và `inner_product`, nên phải chuẩn hoá rồi dùng `inner_product`.
- **Cùng model, cùng phiên bản**: vector của model khác (kể cả cùng model khác phiên bản) nằm ở không gian khác. Nếu cùng số chiều thì so với nhau vẫn chạy, không báo lỗi, chỉ ra kết quả vô nghĩa. Lưu `model_version` cạnh vector. Đổi model thì dựng index mới, tính lại toàn bộ vector, so chất lượng, rồi chuyển [[index-alias|alias]]; câu hỏi phải được embed bằng đúng model của index đang phục vụ. Tính trước chi phí: 5 triệu tài liệu, giả sử embed được 500 câu mỗi giây, mất gần 3 giờ.
- **Tài liệu dài**: model giới hạn độ dài đầu vào, và một vector cho cả bài dài thì bị loãng nghĩa. Cắt thành đoạn (chunk) vài trăm từ, các đoạn chồng lên nhau một chút, mỗi đoạn một vector, rồi gộp kết quả theo tài liệu. Đây cũng là bước tìm của RAG: lấy các đoạn liên quan để đưa cho LLM trả lời. Field `semantic_text` của Elasticsearch (GA từ 9.0) tự cắt đoạn và gọi model qua inference endpoint, cả lúc index lẫn lúc tìm.
- **Tìm chính xác không phải lúc nào cũng tệ**: chi phí tỉ lệ với N × d. Vài chục nghìn vector, hoặc khi bộ lọc chỉ còn vài nghìn tài liệu, quét hết vẫn nhanh và recall bằng 1. Lucene tự chuyển sang quét chính xác khi bộ lọc đủ hẹp: trong lab, lọc còn 1% của 100.000 tài liệu cho recall 1,0 trong khoảng 1,5 ms. Elasticsearch có kiểu index `flat`, `int8_flat` và `script_score` để tìm chính xác.
- **HNSW hoạt động thế nào**: tầng trên thưa (ít điểm, cạnh dài) giống đường cao tốc, tầng dưới cùng chứa mọi điểm. Truy vấn vào từ một điểm ở tầng trên cùng, đi tham lam sang hàng xóm gần câu hỏi hơn, hết đường thì xuống tầng dưới. Ở tầng dưới cùng nó giữ một hàng đợi `ef` ứng viên tốt nhất và dừng khi không còn tìm được ai tốt hơn. Thêm một vector cũng là một lần tìm như vậy để chọn hàng xóm, nên dựng chỉ mục tốn CPU: 100.000 vector 384 chiều, một luồng, Lucene 10.5 trên M4 mất khoảng 80 giây.
- **Tham số**:
  - `m`, số hàng xóm tối đa mỗi điểm ở các tầng trên (tầng dưới cùng của Lucene cho tới 2 × m): Lucene và Elasticsearch mặc định 16, Doris (`max_degree`) 32, pgvector 16.
  - `ef_construction`, hàng đợi lúc dựng: 100, 40 và 64 theo cùng thứ tự.
  - Hàng đợi lúc tìm: `num_candidates` của Elasticsearch, `hnsw_ef_search` của Doris (mặc định 32), `hnsw.ef_search` của pgvector (mặc định 40).
  - `m` và `ef_construction` cố định lúc dựng, đổi thì phải dựng lại. Doris không cho sửa tham số của ANN index: phải xoá rồi tạo lại.
- **Số đo trên Lucene 10.5.2**: 100.000 vector 384 chiều sinh từ 1.000 cụm, đã chuẩn hoá, dot product, `m` 16, `ef_construction` 100, gộp còn 1 [[lucene-segment|segment]], so top-10 với quét chính xác (JDK 27, M4, một luồng). Đây là dữ liệu tổng hợp, không phải embedding thật: dùng để thấy xu hướng, còn con số thật phải đo trên dữ liệu của mình.
  - 10 ứng viên: recall 0,887, khoảng 0,2 ms.
  - 15 ứng viên (bằng mặc định 1,5 × k của Elasticsearch): 0,944.
  - 50 ứng viên: 0,999, khoảng 0,3 ms. 100 ứng viên: 1,0, khoảng 0,5 ms. 500 ứng viên: 1,0, khoảng 3,3 ms.
  - Qua một mức, tăng ứng viên chỉ tốn thêm thời gian.
- **Segment**: mỗi segment Lucene có đồ thị riêng, và truy vấn phải tìm trên từng segment rồi trộn. Cùng dữ liệu, cùng lúc chạy, để 3 segment thì chậm hơn 1 segment khoảng 1,5–3 lần ở mọi mức ứng viên (recall lại cao hơn, vì segment nào cũng trả đủ số ứng viên). Elasticsearch khuyên tạo segment lớn ngay từ đầu (tăng `index.merge.policy.max_merged_segment` từ 5 GB lên 10–20 GB, tắt refresh khi nạp lớn) thay vì force merge. Doris khuyên tối đa khoảng 5 segment mỗi [[tablet|tablet]], nạp theo lô; với dữ liệu lớn thì cho [[compaction|compaction]] chạy xong rồi mới `BUILD INDEX`. Gộp segment cũng phải dựng lại đồ thị, nên ghi liên tục với tốc độ cao sẽ tranh CPU với truy vấn.
- **Cập nhật và xoá**: cập nhật một tài liệu trong Lucene là xoá cộng thêm mới. Tài liệu bị xoá chỉ được đánh dấu, vẫn nằm trong đồ thị và vẫn bị duyệt qua cho tới khi segment được merge. Nhiều xoá thì tìm chậm hơn và recall có thể giảm. Đổi hàng loạt (đổi model, đổi cách cắt đoạn) thì dựng index mới thay vì cập nhật tại chỗ.
- **Bộ nhớ**, theo công thức trong docs Elasticsearch:
  - Mỗi vector float tốn 4 × d byte, bản int8 d + 16 byte, int4 ⌈d/2⌉ + 16, bbq (1 bit) ⌈d/64⌉ × 8 + 14. Đồ thị tốn 4 × m byte mỗi vector.
  - 5 triệu vector 768 chiều, mỗi bản sao: float 15,4 GB, int8 3,9 GB, bbq 0,55 GB, đồ thị 0,32 GB.
  - Lab khớp công thức (bản 1 bit chỉ gần đúng, vì định dạng 1 bit của Lucene không hẳn là bbq của Elasticsearch): 100.000 × 384 cho file vector gốc 153,6 MB, int8 40 MB, int4 20,8 MB, 1 bit 6,4 MB, đồ thị 6,3 MB.
  - Dữ liệu này nằm ngoài heap JVM: Lucene [[memory-mapped-file|mmap]] file và đọc qua page cache. Không vừa page cache thì mỗi bước đi trên đồ thị là một lần đọc đĩa ngẫu nhiên, độ trễ tăng vọt. Đừng tăng heap tới mức lấn RAM của page cache. Ở Doris, HNSW phải nằm hẳn trong bộ nhớ của BE.
- **Lượng tử hoá, đo bằng lab**: index lưu thêm bản nén của vector để duyệt đồ thị và chấm điểm, vector gốc vẫn nằm trên đĩa.
  - Không tính lại điểm thì recall dừng ở một mức dù tăng ứng viên lên 500: int8 0,976, int4 0,828, 1 bit 0,417. Điểm xấp xỉ làm sai thứ tự giữa các vector gần nhau.
  - Lấy dư ứng viên rồi tính lại điểm bằng vector gốc: 1 bit với 50 ứng viên cho top-10 (dư 5 lần) lên 0,938, 100 ứng viên lên 1,0; int4 với 50 ứng viên lên 1,0.
  - Elasticsearch 9.1 trở đi mặc định `bbq_hnsw` cho vector float từ 384 chiều và `int8_hnsw` cho vector ngắn hơn. Từ 9.4, khi license cho phép (Enterprise), mặc định là `bbq_disk`: không phải HNSW mà chia vector thành cụm bằng k-means rồi chỉ so các cụm gần câu hỏi, đặc tính độ trễ khác hẳn. Muốn chắc chắn thì ghi rõ `index_options.type`, đừng dựa vào mặc định.
  - Với `bbq_hnsw`, Elasticsearch tự lấy dư 3 lần rồi tính lại bằng vector gốc. Với `int8_hnsw` hay `int4_hnsw` thì tự đặt `rescore_vector.oversample` (lớn hơn 1, nhỏ hơn 10; 0 là tắt). Doris có `quantizer` `sq8`, `sq4` và `pq`.
- **Lọc trong lúc tìm, không lọc sau**: lấy 100 gần nhất rồi bỏ cái không khớp, với bộ lọc chỉ giữ 1% tài liệu, trung bình còn 1,1 kết quả và recall 0,106 (lab). Pre-filter thì vẫn đi đồ thị nhưng chỉ nhận tài liệu khớp, nên luôn đủ k.
  - Elasticsearch: `filter` đặt **bên trong** `knn` là pre-filter; `bool.filter` bọc ngoài truy vấn `knn` là post-filter, có thể trả ít hơn k.
  - pgvector lọc sau: với `hnsw.ef_search` 40 và điều kiện khớp 10% dòng, trung bình chỉ còn khoảng 4 dòng. Từ 0.8.0 có `hnsw.iterative_scan` để quét tiếp tới khi đủ.
  - Doris lọc trước, nhưng cột lọc cần [[inverted-index|inverted index]], không thì rơi về quét toàn bộ.
- **Hybrid và RRF**: điểm BM25 (từ 0, không có trần) và điểm kNN (Elasticsearch đổi cosine về 0 tới 1) không cùng thang đo, cộng thẳng thì một bên lấn át. RRF chỉ dùng thứ hạng: mỗi danh sách cho tài liệu 1/(60 + hạng), rồi cộng lại.
  - Tài liệu đứng hạng 1 ở một danh sách được 1/61 ≈ 0,0164. Tài liệu hạng 3 bên BM25 và hạng 2 bên kNN được 1/63 + 1/62 ≈ 0,0320, nên thắng.
  - Elasticsearch có retriever `rrf`: `rank_constant` mặc định 60, `rank_window_size` mặc định bằng `size`. Không dùng chung được với `sort`, `scroll`, `rescore`; `from + size` vượt `rank_window_size` thì ra rỗng.
  - Retriever `linear` cộng điểm có trọng số sau khi chuẩn hoá (`minmax`, `l2_norm`), dùng khi đã có bộ câu hỏi có đáp án để chỉnh trọng số.
  - Doris 4 chấm BM25 bằng `score()` nhưng không có hàm `rrf()` dựng sẵn. Docs hướng dẫn viết RRF bằng SQL: hai subquery (một bên `MATCH_ANY` xếp theo `score()`, một bên `..._approximate`), mỗi bên đánh hạng bằng `ROW_NUMBER()`, `FULL OUTER JOIN` theo id, cộng 1/(60 + hạng). Lấy đủ ứng viên mỗi bên (ví dụ 100), nếu không thì tài liệu hạng 11 bên BM25 trông như chỉ có ở bên vector.
- **Vì sao cần cả hai**: vector giỏi đồng nghĩa và câu mô tả. Vector kém với mã ("SM-S931B"), con số ("256GB"), tên riêng hiếm và phủ định ("không đường"). BM25 thì ngược lại.
- **Elasticsearch cụ thể**:
  - `dense_vector`: tối đa 4.096 chiều; `element_type` là `float` (mặc định), `bfloat16`, `byte` hoặc `bit`; mặc định được index.
  - Truy vấn `knn` có `k` và `num_candidates`. `num_candidates` tính theo **mỗi shard**, mặc định 1,5 × k, tối đa 10.000, và `k` phải nhỏ hơn hoặc bằng nó.
  - Mỗi shard trả k kết quả rồi trộn lại, nên nhiều shard nhỏ tốn hơn ít shard lớn.
  - Index tạo từ 9.2 mặc định không giữ vector trong `_source` (`index.mapping.exclude_source_vectors`), nên `_source` nhỏ hơn mà reindex vẫn chạy được.
- **Doris cụ thể** (từ 4.0; bảng Duplicate, hoặc Unique merge-on-write từ 4.1.4; không hỗ trợ bảng Aggregate):

```sql
CREATE TABLE product_vec (
  product_id BIGINT,
  shop_id INT,
  title TEXT,
  embedding ARRAY<FLOAT> NOT NULL,
  INDEX idx_shop (shop_id) USING INVERTED,
  INDEX idx_title (title) USING INVERTED PROPERTIES("parser" = "unicode"),
  INDEX idx_emb (embedding) USING ANN PROPERTIES(
    "index_type" = "hnsw", "metric_type" = "inner_product",
    "dim" = "768", "quantizer" = "sq8")
) DUPLICATE KEY(product_id)
DISTRIBUTED BY HASH(product_id) BUCKETS 16;

SELECT product_id, title
FROM product_vec
WHERE shop_id = 42 AND title MATCH_ANY 'balo'
ORDER BY inner_product_approximate(embedding, [0.12, -0.03, ...]) DESC
LIMIT 10;
```

  - Hàm phải khớp `metric_type`: `inner_product_approximate` đi với `DESC`, `l2_distance_approximate` đi với `ASC`. Dùng hàm không có hậu tố `_approximate` thì không đi qua index mà quét toàn bộ.
  - Mỗi segment có chỉ mục riêng; Doris lấy top-k ở từng segment rồi trộn qua các tablet.
  - HNSW phải nằm hẳn trong RAM của BE. `index_type` `ivf_on_disk` để danh sách vector trên đĩa có cache, tốn ít RAM hơn, đổi lại recall và độ trễ khác.
  - Chọn Doris khi vector phải đi cùng dữ liệu phân tích: lọc theo nhiều cột, tính hàng loạt "sản phẩm tương tự" cho cả catalog, hoặc đã có sẵn cụm Doris (bài OLAP & Apache Doris). Tìm kiếm cho người dùng cần chỉnh relevance kỹ thì Elasticsearch vẫn hợp hơn.
- **pgvector và vector database riêng**: dưới vài triệu vector và đã có PostgreSQL thì pgvector là ít phải vận hành nhất (HNSW `m` 16, `ef_construction` 64; index được tối đa 2.000 chiều với `vector`, 4.000 với `halfvec`). Vector database riêng (Milvus, Qdrant...) đáng cân nhắc khi chủ yếu chỉ tìm vector ở quy mô rất lớn, đổi lại có thêm một hệ phải đồng bộ dữ liệu.
- **Đo chất lượng hai lớp**: recall của ANN (so với quét chính xác) chỉ cho biết chỉ mục xấp xỉ có tốt không. Kết quả có đúng ý người tìm không thì đo bằng bộ câu hỏi có đáp án (vài trăm câu có người chấm) với chỉ số như [[ndcg|nDCG@10]], rồi [[ab-testing|A/B test]]. Đổi model hay đổi cách cắt đoạn thì đo lại cả hai lớp.
- **Đường online**: embed câu hỏi là một lời gọi model cho mỗi truy vấn. Cache theo câu đã chuẩn hoá, đặt timeout, và khi model lỗi thì trả kết quả BM25 thay vì báo lỗi.
