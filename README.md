# Tra cứu video Bác sĩ Phúc

Công cụ tìm từ khóa trong phụ đề các video của kênh YouTube **"Bác sĩ Trần Văn Phúc Official"**, nhảy thẳng đến đúng phút trên YouTube. Trang chạy hoàn toàn trong trình duyệt, không cần server.

## Cấu trúc

- `crawl_phuc.py` — script Python chạy trên máy bạn, lấy phụ đề từ YouTube và ghi ra `data.json`.
- `index.html` — trang tra cứu (tĩnh, mở trực tiếp bằng trình duyệt hoặc host trên GitHub Pages / Cloudflare Pages).
- `data.json` — dữ liệu phụ đề do `crawl_phuc.py` tạo ra (chưa có sẵn, phải chạy script trước). File này không commit sẵn vì có thể lớn và là nội dung bản quyền của chủ kênh — tự quyết định có đưa lên repo công khai hay không.
- `update.bat` — chạy crawler rồi tự `git commit` + `git push` nếu có video mới. Dùng với Task Scheduler để tự động cập nhật.

## Cài đặt lần đầu

```powershell
cd D:\Code\tim-kiem-video-bs-phuc
pip install -U yt-dlp youtube-transcript-api
python crawl_phuc.py --limit 3     # chạy thử 3 video
python crawl_phuc.py               # lấy toàn bộ kênh
```

Nên chạy từ mạng nhà (IP dân dụng). IP máy chủ/VPN hay bị YouTube chặn; script sẽ tự lưu phần đã lấy và dừng, chạy lại sau là tiếp tục được.

## Xem trang

Mở `index.html` trực tiếp bằng trình duyệt (double-click, hoặc kéo vào Chrome) là chạy ngay — trang tự đọc `data.json` cùng thư mục. Không có `data.json` thì trang hiện dữ liệu mẫu.

Để xem tiện trên điện thoại, xem phần "Đưa lên internet" dưới đây.

## Cập nhật video mới

```powershell
python crawl_phuc.py
```

Script chỉ lấy các video chưa có, nên chạy lại rất nhanh sau lần đầu.

## Đưa lên internet (tùy chọn)

Trang là file tĩnh nên có thể host miễn phí:

- **GitHub Pages** — đơn giản nhất, nhưng bắt buộc repo và trang đều **công khai** (bất kỳ ai có link đều xem được `data.json`, tức toàn bộ phụ đề).
- **Cloudflare Pages + Cloudflare Access** — vẫn miễn phí, nhưng có thể khóa bằng đăng nhập email, phù hợp nếu muốn giữ riêng tư.

Cấu hình Pages (cả hai dịch vụ): build command để trống, thư mục xuất bản là gốc repo (`/`).

## Tự động hóa (tùy chọn)

Mở Task Scheduler (Windows) → Create Basic Task → chạy `update.bat` mỗi tối. Mỗi lần có video mới, dữ liệu sẽ tự cập nhật và (nếu đã đưa lên Pages) trang sẽ tự deploy lại.
