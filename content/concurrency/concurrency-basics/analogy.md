Một quầy giao dịch ngân hàng có hai giao dịch viên nhưng chỉ **một tờ giấy dán trên quầy** ghi "khách đang phục vụ". Chị Lan gọi khách số 1, ghi "1" lên tờ giấy rồi quay đi kiểm tra giấy tờ. Trong lúc đó anh Minh gọi khách số 2 và ghi đè thành "2". Chị Lan quay lại, nhìn tờ giấy và in sao kê cho... khách số 2, đưa cho khách số 1.

Không ai làm sai việc của mình. Lỗi nằm ở chỗ hai người dùng chung một chỗ ghi, và kết quả phụ thuộc vào ai ghi lúc nào. Chạy thử một mình thì không bao giờ thấy lỗi; chỉ khi quầy đông mới xảy ra, và không phải lần nào cũng xảy ra.

Có ba cách sửa: mỗi người ghi vào **sổ tay riêng** (không chia sẻ), dán một tờ **in sẵn không sửa được** (bất biến), hoặc đặt quy định **ai đang ghi thì người kia đứng chờ** (khoá).

Trong Java, hai giao dịch viên là hai thread, tờ giấy trên quầy là một field của object dùng chung (như bean singleton của Spring), lỗi đưa nhầm sao kê là [[race-condition|race condition]], và ba cách sửa lần lượt là [[thread-confinement|thread confinement]], object [[immutable]] và khoá.
