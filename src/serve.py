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