import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix, classification_report

EVAL_THRESHOLD = 0.68

def train(
    params: dict,
    data_path: str = "data/train_phase1.csv",
    eval_path: str = "data/eval.csv",
) -> float:
    """
    Huấn luyện mô hình và ghi nhận kết quả vào MLflow.
    """

    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    X_train = df_train.drop(columns=["target"])
    y_train = df_train["target"]
    X_eval = df_eval.drop(columns=["target"])
    y_eval = df_eval["target"]

    with mlflow.start_run():
        mlflow.log_params(params)

        model = RandomForestClassifier(**params, random_state=42)
        model.fit(X_train, y_train)

        preds = model.predict(X_eval)
        acc = accuracy_score(y_eval, preds)
        f1 = f1_score(y_eval, preds, average="weighted")
        precision = precision_score(y_eval, preds, average="weighted")
        recall = recall_score(y_eval, preds, average="weighted")

        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("precision", precision)
        mlflow.log_metric("recall", recall)

        mlflow.sklearn.log_model(model, "model")

        print(f"Accuracy: {acc:.4f} | F1: {f1:.4f} | Precision: {precision:.4f} | Recall: {recall:.4f}")

        os.makedirs("outputs", exist_ok=True)
        
        # Lưu metrics ra file json
        with open("outputs/metrics.json", "w") as f:
            json.dump({
                "accuracy": acc, 
                "f1_score": f1,
                "precision": precision,
                "recall": recall
            }, f)
            
        # Tạo report.txt (Bonus 3)
        with open("outputs/report.txt", "w") as f:
            f.write("=== Confusion Matrix ===\n")
            f.write(str(confusion_matrix(y_eval, preds)))
            f.write("\n\n=== Classification Report ===\n")
            f.write(classification_report(y_eval, preds))

        # Lưu model
        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/model.pkl")

    return acc

if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)
