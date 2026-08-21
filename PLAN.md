# Kế Hoạch Hoàn Thành Lab MLOps

Kế hoạch này liệt kê các bước cần thực hiện để hoàn thành lab MLOps: "Từ Thực Nghiệm Cục Bộ Đến Triển Khai Liên Tục".

## Bước 1: Thực Nghiệm Cục Bộ và Theo Dõi Thí Nghiệm
1. **Tải Dữ Liệu:** Chạy script `python generate_data.py` để lấy dữ liệu.
2. **Cài Đặt Thư Viện:** Cài đặt các thư viện cần thiết qua `pip install -r requirements.txt`.
3. **Cấu Hình MLflow:** Khai báo biến môi trường cho MLflow (`MLFLOW_TRACKING_URI`, `MLFLOW_ARTIFACT_ROOT`).
4. **Viết `params.yaml`:** Khai báo các siêu tham số cho mô hình `RandomForestClassifier`.
5. **Viết `src/train.py`:** Hoàn thành các TODO trong script huấn luyện: đọc dữ liệu, log siêu tham số, huấn luyện mô hình, log metrics (`accuracy`, `f1_score`), và lưu model cùng metrics.
6. **Thực Nghiệm:** Chạy script huấn luyện ít nhất 3 lần với các giá trị khác nhau trong `params.yaml`.
7. **Phân Tích Kết Quả:** Dùng giao diện MLflow UI (ở `localhost:5000`) để so sánh, chọn ra bộ siêu tham số tốt nhất và cập nhật lại vào `params.yaml`. Chụp màn hình MLflow UI.

## Bước 2: Pipeline CI/CD Tự Động
1. **Tạo Cloud Storage Bucket:** Tạo bucket lưu trữ dữ liệu và mô hình (GCP/AWS/Azure).
2. **Tạo Cloud Credentials:** Tạo Service Account/Role/Connection String và xuất key để cấp quyền cho DVC truy cập bucket (không được commit file key lên git).
3. **Cấu Hình DVC:** Khởi tạo DVC, thêm remote trỏ về bucket vừa tạo, theo dõi các file CSV, lưu con trỏ DVC và push dữ liệu lên bucket.
4. **Tạo VM Trên Cloud:** Khởi tạo máy ảo (GCE/EC2/Azure VM) và mở cổng 8000.
5. **Cấu Hình VM:** Truy cập SSH vào VM, cài đặt thư viện cần thiết và copy file cấu hình/credentials từ local lên VM.
6. **Viết `src/serve.py`:** Hoàn thành code FastAPI để xây dựng API server suy luận cho mô hình. API cần các endpoint `/health` và `/predict`, đồng thời có tính năng tải mô hình từ cloud về tự động.
7. **Cấu Hình Systemd Service Trên VM:** Cài đặt FastAPI server như một service hệ thống trên VM để nó tự động chạy và khởi động lại cùng hệ thống.
8. **Tạo SSH Key Để GitHub Actions Deploy:** Sinh cặp khóa SSH, đưa public key lên VM và private key vào GitHub Secrets để tự động hóa deploy.
9. **Thêm GitHub Secrets:** Cấu hình các secret cần thiết trên GitHub Repo (credentials cloud, IP của VM, private key, thông tin người dùng).
10. **Viết Unit Test (`tests/test_train.py`):** Hoàn thiện các bài kiểm thử cơ bản (kiểm tra tỷ lệ dữ liệu, kiểm tra luồng train).
11. **Viết Workflow (`.github/workflows/mlops.yml`):** Cấu hình toàn bộ quy trình CI/CD qua 4 jobs: Test, Train, Eval (chặn nếu `accuracy` < 0.70), Deploy (restart service trên VM).
12. **Triển Khai:** Push code lên GitHub, chờ Actions chạy hoàn tất 4 jobs. Kiểm tra kết quả qua curl tới IP của VM. Chụp màn hình Actions và curl kết quả.

## Bước 3: Huấn Luyện Liên Tục Khi Có Dữ Liệu Mới
1. **Thêm Dữ Liệu Mới:** Chạy script `python add_new_data.py` để nối tập dữ liệu huấn luyện mới vào file `train_phase1.csv`.
2. **Cập Nhật DVC:** Chạy lại `dvc add`, commit các file `.dvc` thay đổi và `dvc push` dữ liệu mới lên cloud.
3. **Kích Hoạt Pipeline:** Push các thay đổi lên GitHub để CI/CD tự động chạy theo quy trình: Tải dữ liệu mới -> Train lại -> Kiểm tra accuracy -> Deploy model mới (nếu qua ngưỡng).
4. **Xác Nhận & So Sánh:** Gọi `/predict` kiểm tra kết quả, so sánh model mới với model cũ qua MLflow UI hoặc báo cáo metrics.

## Bước Mở Rộng (Bonus)
Để đạt điểm tối đa, có thể thực hiện thêm các nhiệm vụ nâng cao:
1. **Bonus 1:** Chuyển đổi MLflow backend từ file local sang tracking server đám mây trên DagsHub.
2. **Bonus 2:** Bổ sung hỗ trợ nhiều thuật toán (như Gradient Boosting, Logistic Regression) vào file `train.py` và cấu hình qua `params.yaml`.
3. **Bonus 3:** Tự động tạo báo cáo hiệu suất chi tiết (precision, recall, confusion matrix) và lưu dưới dạng GitHub Artifacts.
4. **Bonus 4:** Thay đổi luồng Eval trong GitHub Actions để chỉ triển khai khi mô hình mới có hiệu suất bằng hoặc tốt hơn mô hình cũ.
5. **Bonus 5:** Kiểm tra sự lệch lạc dữ liệu, cảnh báo và lưu log nếu nhãn bị mất cân bằng mạnh (< 10% cho 1 lớp).

## Hoàn Thiện & Nộp Bài
1. Đảm bảo repo GitHub public chứa toàn bộ mã nguồn.
2. Tổng hợp các ảnh chụp màn hình (MLflow UI, Github Actions, cURL kết quả, Cloud Storage Console).
3. Viết báo cáo ngắn gọn về siêu tham số đã chọn và các trở ngại/giải pháp thực tế (tối đa 1 trang A4).
4. Nộp link repo, hình ảnh và báo cáo.
