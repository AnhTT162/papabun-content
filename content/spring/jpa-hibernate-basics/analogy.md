Một giao dịch viên ngân hàng bắt đầu ca làm việc. Khách cần sửa thông tin nào, chị lấy hồ sơ gốc từ kho đặt lên bàn. Chị sửa thẳng trên hồ sơ đang ở trên bàn, không cần điền phiếu "đề nghị cập nhật": cuối ca, chị so từng hồ sơ trên bàn với lúc mới lấy ra và nhập mọi chỗ khác vào hệ thống một lượt. Trong ca, ai hỏi hồ sơ số 42 thì chị đưa đúng tờ đang nằm trên bàn, không lấy thêm bản thứ hai.

Hết ca, bàn được dọn sạch. Khách mang về một **bản photo**. Sửa trên bản photo không thay đổi gì trong hệ thống. Muốn cập nhật, khách mang bản photo lên quầy hôm sau; giao dịch viên lấy hồ sơ gốc ra, **chép các thay đổi từ bản photo sang hồ sơ gốc**, rồi trả lại bản photo y như cũ.

Đó là [[jpa|JPA]]: bàn làm việc trong ca là [[persistence-context|persistence context]], hồ sơ đang trên bàn là entity [[entity-state|managed]], việc so và nhập cuối ca là [[dirty-checking|dirty checking]] lúc flush, bản photo là entity detached, còn mang bản photo lên quầy là `merge()`.
