## Quick

Điều tra sự cố trên máy Linux là đi theo từng tài nguyên (CPU, bộ nhớ, đĩa, mạng) và với mỗi cái hỏi ba câu của [[use-method|USE method]]: dùng bao nhiêu, có xếp hàng ([[saturation|bão hoà]]) không, có lỗi không. Bộ lệnh tối thiểu: `uptime`, `dmesg`, [[vmstat|`vmstat`]], `mpstat`, `pidstat`, [[iostat|`iostat`]], `free`, `ss`, `lsof`, rồi mới tới [[strace|`strace`]] và [[tcpdump|`tcpdump`]] khi cần nhìn từng lời gọi hệ thống hay từng gói tin. **Đọc số liệu theo khoảng thời gian (`vmstat 1`, không phải dòng đầu tiên), tìm tài nguyên đang bão hoà trước khi đoán, và nhớ rằng công cụ càng chi tiết thì càng tốn cho máy đang có sự cố.**

## Interview

**Một phút đầu**:
- `uptime`: [[load-average|load average]] 1, 5, 15 phút; so với số core, và xem đang tăng hay giảm.
- `dmesg -T | tail`: OOM killer, lỗi đĩa, `nf_conntrack: table full`.
- `vmstat 1`: `r` (thread chờ CPU) so với số core, `b` (thread chờ I/O, trạng thái `D`), `si`/`so` (swap), CPU `us sy id wa st`.
- `mpstat -P ALL 1`: một core 100% còn lại rảnh là nút cổ chai đơn luồng.
- `pidstat 1`, `pidstat -d 1`: process nào ăn CPU, process nào đọc ghi đĩa.
- `iostat -xyz 1` (`-y` bỏ báo cáo đầu tính từ lúc khởi động): `r_await`/`w_await` (ms mỗi I/O), `aqu-sz` (hàng đợi), `%util`.
- `free -m`: nhìn cột `available`, không phải `free`; phần còn lại là [[page-cache|page cache]] trả lại được.
- `ss -s`, `ss -tanp`: số kết nối theo trạng thái, process nào giữ.

**Đọc CPU**: `us` cao là code ứng dụng (sang bài Ứng dụng Java CPU 100% để tìm thread), `sy` cao là kernel (nhiều syscall, context switch, khoá), [[iowait|`wa`]] cao là CPU rảnh trong khi có I/O đang chờ, [[steal-time|`st`]] cao là máy ảo bị hypervisor lấy CPU.

**Đọc đĩa**: `r_await`/`w_await` tăng so với bình thường cùng `aqu-sz` dài ra là đĩa bão hoà; `%util` 100% chỉ có nghĩa đó với đĩa xử lý một request mỗi lúc.

**Khi cần đào sâu**: `lsof -p <pid>` xem file và socket đang mở; `strace -f -T -p <pid>` xem syscall chậm; `tcpdump -i any -nn -w /tmp/cap.pcap port 5432` ghi gói tin để đọc bằng Wireshark.

**Bẫy hay gặp**: đọc dòng đầu của `vmstat` (trung bình từ lúc khởi động); thấy `free` thấp tưởng hết RAM; tin `%util` của SSD; chạy `strace` trên process production đang quá tải; quên rằng trong container, `top` và `free` hiện số của cả node.

**Cách làm đúng**: ghi lại số liệu kèm thời gian trước khi sửa gì, đi theo checklist, và đối chiếu với metric lịch sử (`sar`, Prometheus) để biết cái gì đã đổi.

## Deep

- **`vmstat` dòng đầu**: là trung bình từ lúc khởi động, không phải hiện tại; luôn đọc từ dòng thứ hai của `vmstat 1`. `r` lớn hơn số core kéo dài là thiếu CPU; `b` lớn cùng `wa` cao là I/O; `cs` cao bất thường kèm `sy` cao là quá nhiều thread tranh nhau (đo theo process bằng `pidstat -w`, ở bài Process, thread & bộ nhớ của hệ điều hành).
- **`wa` không đo được độ bận của đĩa**: `wa` là thời gian CPU rảnh trong khi có I/O chưa xong. Máy bận CPU thì `wa` thấp dù đĩa đang nghẽn; máy nhiều core thì một tiến trình chờ đĩa chỉ làm `wa` nhích lên chút. Kết luận về đĩa phải dựa vào `iostat` (`await`, `aqu-sz`) và trạng thái `D` của thread.
- **`%util` lừa trên SSD, NVMe, EBS**: tài liệu `iostat` ghi rõ với thiết bị phục vụ song song (RAID, SSD), 100% không có nghĩa là bão hoà, chỉ là lúc nào cũng có ít nhất một I/O đang chạy. Nhìn `await` so với bình thường, `aqu-sz`, và so `rkB/s + wkB/s`, `r/s + w/s` với giới hạn throughput và [[iops|IOPS]] của volume (trên cloud, giới hạn của volume thường chạm trước giới hạn của thiết bị).
- **`st` trên cloud**: máy ảo bị hypervisor lấy CPU cho máy khác, hoặc instance loại burstable đã hết CPU credit và bị giới hạn về baseline. Trong container thì không thấy `st` mà thấy [[cpu-throttling|CPU throttling]] (`nr_throttled`, `throttled_usec` trong `/sys/fs/cgroup/cpu.stat`); chi tiết ở bài Ứng dụng Java CPU 100%.
- **Đĩa đầy mà `du` không thấy**: file log bị xoá (logrotate, xoá tay) trong khi Java vẫn mở nó, nên dung lượng chưa được trả. `df` báo 100% còn `du` cộng không ra. `lsof +L1` liệt kê file đã xoá vẫn mở (`(deleted)`); trả dung lượng bằng cách để ứng dụng mở lại file, hoặc cắt ngắn qua `/proc/<pid>/fd/<n>` (chép ra chỗ khác trước nếu postmortem còn cần nội dung; chỉ an toàn khi ứng dụng mở file ở chế độ append, như Logback mặc định, nếu không file thành sparse và lại phình). Inode cạn (`df -i`) cũng báo "No space left on device" dù còn dung lượng.
- **Bộ nhớ**: `available` (có từ kernel 3.14) là ước lượng bộ nhớ dùng được mà không swap; page cache lớn là bình thường. Dấu hiệu thật sự thiếu bộ nhớ là `si`/`so` khác 0 kéo dài, major page fault tăng (`pidstat -r`), và dòng OOM trong `dmesg`. OOM killer, cgroup và RSS so với heap ở bài Process, thread & bộ nhớ của hệ điều hành và bài Bộ nhớ tăng dần & OOM.
- **Mạng**: `ss -tni` cho từng kết nối có `rtt`, `cwnd`, `retrans`; `nstat -az | grep -i retrans` hay `sar -n ETCP 1` cho tỉ lệ [[tcp-retransmission|retransmit]] toàn máy. `ss -lnt` cột `Recv-Q` của socket đang listen là accept queue. Đọc `TIME_WAIT`, `CLOSE_WAIT` và cạn port ở bài TCP chuyên sâu; lỗi kết nối từ Java ở bài Mạng máy tính cơ bản.
- **`strace` rất đắt**: dựa trên ptrace, mỗi syscall dừng process hai lần; process gọi nhiều syscall có thể chậm đi hàng chục lần. Trên production, ưu tiên `strace -c -w` trong vài giây (bảng số lần gọi và thời gian theo syscall; không có `-w` thì `-c` chỉ cộng thời gian CPU trong kernel, nên syscall đang chờ như `futex` hay `write` bị chặn trông gần như bằng 0), lọc hẹp (`-e trace=network`, `-e trace=%file`), hoặc dùng công cụ dựa trên [[ebpf|eBPF]] (`bpftrace`, `perf trace`, bộ `bcc` như `biolatency`, `tcpretrans`, `opensnoop`) có overhead thấp hơn nhiều. Với Java, `strace -f` thấy hàng trăm thread GC, JIT, nên lọc theo TID từ `top -H`.
- **`tcpdump` đúng cách**: luôn có bộ lọc (`host`, `port`) và ghi ra file (`-w`), xoay vòng bằng `-C 100 -W 5` để không đầy đĩa; `-nn` tránh tra DNS ngược làm chậm và gây thêm traffic. TLS thì chỉ thấy handshake, SNI và kích thước, không thấy nội dung, nhưng vẫn đủ để thấy SYN không được trả lời, RST, retransmit, hay khoảng trống giữa request và response.
- **Trong Kubernetes**: image thường không có công cụ. `kubectl debug -it <pod> --image=nicolaka/netshoot --target=<container>` thêm [[ephemeral-container|ephemeral container]] dùng chung namespace process và mạng (stable từ Kubernetes 1.25); từ node, `nsenter -t <pid> -n ss -tanp` chạy `ss` trong network namespace của pod. `top`, `free` (và `nproc` khi không có cpuset) trong container hiện tài nguyên của cả node, không phải limit; với cgroup v2 đọc `/sys/fs/cgroup/memory.current`, `memory.max`, `cpu.max` (cgroup v1 dùng `memory.usage_in_bytes`, `memory.limit_in_bytes`).
- **`/proc` khi không có công cụ**: `/proc/<pid>/status` (RSS, số thread, trạng thái), `/proc/<pid>/limits` (`Max open files` thật của process), `/proc/<pid>/fd` (đếm fd), `/proc/<pid>/task/<tid>/stat`, `/proc/<pid>/task/<tid>/stack` và `wchan` (thread ở trạng thái `D` đang chờ hàm nào trong kernel, như `balance_dirty_pages` khi bị chặn ghi vì dirty page; xem stack cần root), `/proc/loadavg`, `/proc/pressure/{cpu,memory,io}` (PSI, Pressure Stall Information, kernel 4.20+: phần trăm thời gian có task phải chờ tài nguyên, rõ hơn load average).
- **Lịch sử**: sự cố đã qua thì lệnh tức thời vô dụng. `sar` (gói sysstat, khi đã bật thu thập) lưu CPU, I/O, mạng mỗi 10 phút mặc định; `sar -u -f /var/log/sysstat/sa27` đọc lại ngày 27 (đường dẫn khác nhau theo distro). Trên cloud và Kubernetes, node exporter và metric của nhà cung cấp là nguồn chính, lệnh Linux dùng để xác nhận và đào sâu.
- **Thứ tự với một service Java**: máy có bão hoà gì không (checklist trên) → process Java dùng gì (`pidstat -p <pid> 1`, `-d`, `-r`) → thread nào (`top -H`, thread dump, ở bài Ứng dụng Java CPU 100%) → lời gọi nào (async-profiler ở bài Profiling, `strace` lọc hẹp). Đi ngược thứ tự này (mở profiler ngay) dễ bỏ qua nguyên nhân nằm ngoài JVM như đĩa, node láng giềng, hay throttling.
