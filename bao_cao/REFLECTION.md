# Báo Cáo Thực Hành Lab MLOps
**Học viên:** Trần Công Chiến
**Mã số:** 2A202601053

---

## 1. Bộ Siêu Tham Số Đã Chọn
Dựa trên kết quả thử nghiệm và so sánh trực tiếp trên MLflow UI ở Bước 1, bộ siêu tham số tốt nhất mang lại hiệu suất tối ưu trên tập đánh giá (eval.csv) được tôi lựa chọn là:
- `n_estimators`: 200
- `max_depth`: 20
- `min_samples_split`: 2

**Lý do:** Mô hình RandomForest với số lượng cây lớn (200) kết hợp với độ sâu cây mở rộng (20) giúp mô hình học được nhiều đặc trưng phức tạp hơn của dữ liệu chất lượng rượu vang, từ đó tránh được hiện tượng Underfitting. Sự kết hợp này mang lại Accuracy và F1-score cao nhất so với các bộ thông số mặc định hoặc nông hơn.

---

## 2. So Sánh Kết Quả Trước Và Sau Khi Thêm Dữ Liệu
Dưới đây là bảng so sánh hiệu suất thu được từ `metrics.json` của 2 lần chạy trên GitHub Actions:

| Chỉ số | Bước 2 (2998 mẫu) | Bước 3 (5996 mẫu) | Nhận xét |
|---|---|---|---|
| **Accuracy** | 0.684 | 0.754 | Độ chính xác tăng vọt, vượt ngưỡng cấu hình (0.68). |
| **F1_score** | 0.683 | 0.753 | F1-score cũng cải thiện rõ rệt. |

**Kết luận:** Việc thêm lượng dữ liệu mới (gấp đôi) đã giúp mô hình học được đa dạng phân phối hơn, giảm thiểu nhiễu và cải thiện hiệu suất phân loại đáng kể.

---

## 3. Khó Khăn Gặp Phải Và Cách Giải Quyết

Trong quá trình triển khai thực tế, tôi đã gặp một số lỗi về môi trường và hệ thống, nhưng đã xử lý thành công:

1. **Lỗi `ModuleNotFoundError: No module named 'pkg_resources'` khi chạy MLflow:**
   - **Nguyên nhân:** Công cụ quản lý môi trường ảo tự động cập nhật `setuptools` lên phiên bản 84.0.0 (phiên bản này đã loại bỏ hoàn toàn `pkg_resources` mà MLflow 2.13.0 yêu cầu).
   - **Cách giải quyết:** Hạ cấp thư viện bằng lệnh `uv pip install "setuptools<70"` để phục hồi module.

2. **Lỗi `PermissionError: [Errno 13] Permission denied: '/data'` trên GitHub Actions:**
   - **Nguyên nhân:** Do chạy thử nghiệm nội bộ, MLflow đã tạo thư mục `mlruns` ghi đường dẫn tuyệt đối (trên máy cá nhân của tôi). Do vô tình commit thư mục này lên Git, khi CI/CD chạy, MLflow cố gắng ghi vào `/data/vinai/...` trên máy chủ GitHub (nơi không tồn tại/không có quyền truy cập).
   - **Cách giải quyết:** Chạy lệnh `git rm -r --cached mlruns/` để xóa khỏi Git, thêm `mlruns/` vào `.gitignore` và push lên lại.

3. **Lỗi Service `mlops-serve` bị sập (Crash) trên EC2 với lỗi `404 Not Found` từ S3:**
   - **Nguyên nhân:** Service khởi động và cố tải file `model.pkl` từ S3 về, tuy nhiên bước này được chạy khi Job Train chưa hoàn tất việc đẩy mô hình lên S3.
   - **Cách giải quyết:** Chỉ khởi động/restart Service sau khi chắc chắn Pipeline GitHub Actions đã đẩy thành công file model lên S3 thông qua `boto3`. Đảm bảo luồng Deploy phải phụ thuộc vào (needs) luồng Eval/Train.

---
*(Xem các ảnh chứng minh hệ thống trong thư mục `screenshots/`)*
