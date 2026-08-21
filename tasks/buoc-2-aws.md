# Bước 2 - Pipeline CI/CD Tự Động (Phiên bản AWS)

Mục tiêu: Mỗi khi bạn push code hoặc thay đổi dữ liệu, GitHub Actions tự động huấn luyện mô hình, kiểm tra accuracy có đạt ngưỡng >= 0.70 không, và triển khai lên EC2 nếu đạt yêu cầu.

---

## Lựa Chọn Cloud Provider

Hướng dẫn này đã được điều chỉnh chuyên biệt cho **AWS**. Các công cụ tương ứng được sử dụng:
- Object Storage: **Amazon S3**
- VM: **EC2**
- CLI: **aws-cli**
- DVC storage extra: **dvc[s3]**
- Cloud SDK Python: **boto3**
- Credentials: **IAM User Access Key**

---

## 2.1 Tạo Cloud Storage Bucket (S3)

Tên bucket phải là duy nhất trên toàn bộ AWS. Thay thế `<BUCKET_NAME>` bằng giá trị của bạn.

```bash
export BUCKET=<BUCKET_NAME>
export AWS_REGION=us-east-1

aws s3 mb s3://$BUCKET --region $AWS_REGION
```

---

## 2.2 Tạo Cloud Credentials (IAM User)

Tạo một người dùng IAM có quyền truy cập vào Bucket vừa tạo để DVC và GitHub Actions có thể đọc/ghi dữ liệu.

```bash
# Tạo IAM user
aws iam create-user --user-name mlops-lab-user

# Cấp quyền thao tác trên S3 bucket của bạn
aws iam put-user-policy --user-name mlops-lab-user --policy-name S3Access --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::'"$BUCKET"'",
                "arn:aws:s3:::'"$BUCKET"'/*"
            ]
        }
    ]
}'

# Lấy Access Key (Lưu lại hai thông số AccessKeyId và SecretAccessKey)
aws iam create-access-key --user-name mlops-lab-user
```

**Lưu ý:** Không bao giờ commit Access Key lên Git!

---

## 2.3 Cài Đặt DVC Với S3 Remote

```bash
dvc init

# Trỏ DVC đến S3 bucket
dvc remote add -d myremote s3://$BUCKET/dvc

# Cấu hình credentials (dùng cờ --local để lưu vào .dvc/config.local, file này đã bị gitignore nên an toàn)
dvc remote modify --local myremote access_key_id <YOUR_ACCESS_KEY_ID>
dvc remote modify --local myremote secret_access_key <YOUR_SECRET_ACCESS_KEY>

# Theo dõi các file dữ liệu bằng DVC
dvc add data/train_phase1.csv
dvc add data/eval.csv
dvc add data/train_phase2.csv

# Commit các file con trỏ DVC vào git (KHÔNG phải file CSV)
git add data/train_phase1.csv.dvc data/eval.csv.dvc data/train_phase2.csv.dvc \
        .gitignore .dvc/config
git commit -m "feat: track datasets with DVC"

# Đẩy các file CSV lên S3
dvc push
```

Xác nhận trên AWS S3 Console rằng các file dữ liệu đã xuất hiện dưới thư mục `dvc/` trong bucket.

---

## 2.4 Tạo VM Trên Cloud (EC2)

Đảm bảo bạn đã có sẵn một Key Pair trên AWS (ví dụ: `my-key-pair.pem`).

```bash
# Tạo Security Group để mở cổng 22 (SSH) và 8000 (API)
aws ec2 create-security-group --group-name mlops-sg --description "MLOps SG"
aws ec2 authorize-security-group-ingress --group-name mlops-sg --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-name mlops-sg --protocol tcp --port 8000 --cidr 0.0.0.0/0

# Tìm AMI ID của Ubuntu 22.04 LTS
AMI_ID=$(aws ec2 describe-images --owners 099720109477 --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" --query 'sort_by(Images, &CreationDate)[-1].ImageId' --output text --region $AWS_REGION)

# Tạo EC2 instance
aws ec2 run-instances \
  --image-id $AMI_ID \
  --count 1 \
  --instance-type t2.micro \
  --key-name <YOUR_KEY_PAIR_NAME> \
  --security-groups mlops-sg \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=mlops-serve}]' \
  --region $AWS_REGION

# Lấy IP công khai của EC2 (lưu lại, cần dùng cho GitHub Secrets)
aws ec2 describe-instances --filters "Name=tag:Name,Values=mlops-serve" --query "Reservations[0].Instances[0].PublicIpAddress" --output text
```

---

## 2.5 Cấu Hình VM (Thực Hiện Một Lần, Thủ Công)

SSH vào EC2 (user mặc định của Ubuntu là `ubuntu`):

```bash
ssh -i /path/to/your/key.pem ubuntu@<EC2_PUBLIC_IP>
```

Bên trong VM, cài đặt các thư viện cần thiết:

```bash
sudo apt update && sudo apt install -y python3-pip
pip3 install fastapi uvicorn scikit-learn joblib boto3

mkdir -p ~/models ~/src
```

---

## 2.6 Viết `src/serve.py`

Tạo file `src/serve.py` theo khung dưới đây. File này chạy trên VM và cung cấp REST API để nhận yêu cầu suy luận, sử dụng thư viện `boto3` của AWS.

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
import joblib
import os

app = FastAPI()

# Đọc tên bucket từ biến môi trường
S3_BUCKET = os.environ["S3_BUCKET"]
S3_MODEL_KEY = "models/latest/model.pkl"
MODEL_PATH = os.path.expanduser("~/models/model.pkl")

def download_model():
    """Tải file model.pkl từ S3 về máy khi server khởi động."""
    s3 = boto3.client('s3')
    print(f"Downloading model from s3://{S3_BUCKET}/{S3_MODEL_KEY}...")
    s3.download_file(S3_BUCKET, S3_MODEL_KEY, MODEL_PATH)
    print("Download complete.")

# Gọi hàm này khi server khởi động
download_model()
model = joblib.load(MODEL_PATH)


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    if len(req.features) != 12:
        raise HTTPException(status_code=400, detail="Expected 12 features (wine quality)")
        
    preds = model.predict([req.features])
    label_map = {0: "thap", 1: "trung_binh", 2: "cao"}
    return {"prediction": int(preds[0]), "label": label_map.get(int(preds[0]), "unknown")}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Upload file `serve.py` lên VM từ máy cá nhân của bạn:

```bash
scp -i /path/to/your/key.pem src/serve.py ubuntu@<EC2_PUBLIC_IP>:~/src/serve.py
```

---

## 2.7 Cấu Hình Systemd Service Trên VM

SSH trở lại vào VM và tạo file service:

```bash
sudo tee /etc/systemd/system/mlops-serve.service > /dev/null <<EOF
[Unit]
Description=MLOps Model Inference Server
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu
Environment="S3_BUCKET=<YOUR_BUCKET_NAME>"
Environment="AWS_ACCESS_KEY_ID=<YOUR_ACCESS_KEY_ID>"
Environment="AWS_SECRET_ACCESS_KEY=<YOUR_SECRET_ACCESS_KEY>"
Environment="AWS_DEFAULT_REGION=us-east-1"
ExecStart=/usr/bin/python3 /home/ubuntu/src/serve.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable mlops-serve
```

Thay các giá trị bằng Access Key của bạn để service có quyền kéo model từ S3 về. Tạm thời chưa start service vội vì model chưa có trên S3.

---

## 2.8 Tạo SSH Key Để GitHub Actions Deploy

Chạy trên máy tính cá nhân:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/mlops_deploy -N "" -C "github-actions-deploy"
```

Thêm public key vào VM:

```bash
cat ~/.ssh/mlops_deploy.pub | ssh -i /path/to/your/key.pem ubuntu@<EC2_PUBLIC_IP> "cat >> ~/.ssh/authorized_keys"
```

---

## 2.9 Thêm GitHub Secrets

Vào repo GitHub: Settings > Secrets and variables > Actions > New repository secret.
Thêm chính xác 5 secrets sau:

| Tên secret | Giá trị |
|---|---|
| CLOUD_CREDENTIALS | `{"aws_access_key_id":"<KEY>","aws_secret_access_key":"<SECRET>"}` |
| CLOUD_BUCKET | Tên bucket S3 (ví dụ: `my-mlops-bucket`) |
| VM_HOST | IP công khai của EC2 |
| VM_USER | `ubuntu` |
| VM_SSH_KEY | Dán toàn bộ nội dung file `~/.ssh/mlops_deploy` (private key) |

---

## 2.10 Viết `tests/test_train.py`

*(Nội dung giống hệt file `tasks/buoc-2.md` gốc, vì bài test chỉ chạy cục bộ và không tương tác với AWS)*

---

## 2.11 Viết `.github/workflows/mlops.yml`

Tạo file `.github/workflows/mlops.yml` đã được điều chỉnh cho AWS:

```yaml
name: MLOps Pipeline

on:
  push:
    branches: [main]
    paths:
      - 'data/**.dvc'
      - 'src/**.py'
      - 'params.yaml'
  workflow_dispatch:

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v

  train:
    name: Train
    needs: test
    runs-on: ubuntu-latest
    outputs:
      accuracy: ${{ steps.read_metrics.outputs.accuracy }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      
      - name: Install dependencies
        run: pip install -r requirements.txt
        
      - name: Authenticate to AWS
        run: |
          echo '${{ secrets.CLOUD_CREDENTIALS }}' > aws_creds.json
          echo "AWS_ACCESS_KEY_ID=$(jq -r .aws_access_key_id aws_creds.json)" >> $GITHUB_ENV
          echo "AWS_SECRET_ACCESS_KEY=$(jq -r .aws_secret_access_key aws_creds.json)" >> $GITHUB_ENV
          echo "AWS_DEFAULT_REGION=us-east-1" >> $GITHUB_ENV

      - name: Pull data with DVC
        run: dvc pull

      - name: Train model
        run: python src/train.py

      - name: Read metrics
        id: read_metrics
        run: |
          acc=$(python -c 'import json; print(json.load(open("outputs/metrics.json"))["accuracy"])')
          echo "accuracy=$acc" >> $GITHUB_OUTPUT

      - name: Upload model to S3
        run: |
          python - <<'EOF'
          import boto3, os
          s3 = boto3.client('s3')
          s3.upload_file("models/model.pkl", os.environ["CLOUD_BUCKET"], "models/latest/model.pkl")
          EOF
        env:
          CLOUD_BUCKET: ${{ secrets.CLOUD_BUCKET }}

      - name: Save metrics as artifact
        uses: actions/upload-artifact@v4
        with:
          name: metrics
          path: outputs/metrics.json

  eval:
    name: Eval
    needs: train
    runs-on: ubuntu-latest
    steps:
      - name: Check eval gate
        run: |
          python - <<'EOF'
          import sys
          acc = float("${{ needs.train.outputs.accuracy }}")
          if acc < 0.70:
              print(f"Accuracy {acc} is below threshold 0.70. Deployment blocked.")
              sys.exit(1)
          print(f"Accuracy {acc} >= 0.70. Ready for deploy.")
          EOF

  deploy:
    name: Deploy
    needs: eval
    runs-on: ubuntu-latest
    steps:
      - name: SSH deploy to VM
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VM_HOST }}
          username: ${{ secrets.VM_USER }}
          key: ${{ secrets.VM_SSH_KEY }}
          script: |
            sudo systemctl restart mlops-serve
            sleep 5
            curl -f http://localhost:8000/health || exit 1
```

---

## 2.12 Lần Chạy Pipeline Đầu Tiên

*(Nội dung giống với bản gốc: push code lên GitHub và kiểm tra tab Actions)*
```bash
touch src/__init__.py tests/__init__.py
git add .
git commit -m "feat: setup AWS CI/CD pipeline"
git push origin main
```

Chạy EC2 và start service:
```bash
ssh -i /path/to/your/key.pem ubuntu@<EC2_PUBLIC_IP> "sudo systemctl start mlops-serve"
```

Dùng `curl` để gọi API như đã hướng dẫn trong `tasks/buoc-2.md`.
