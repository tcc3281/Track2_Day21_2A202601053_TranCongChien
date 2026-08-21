import os
import json
import numpy as np
import pandas as pd
from src.train import train


FEATURE_NAMES = [
    "fixed_acidity", "volatile_acidity", "citric_acid", "residual_sugar",
    "chlorides", "free_sulfur_dioxide", "total_sulfur_dioxide", "density",
    "pH", "sulphates", "alcohol", "wine_type",
]


def _make_temp_data(tmp_path):
    """
    Tạo dataset nhỏ với cùng schema Wine Quality để sử dụng trong test.

    pytest cung cấp `tmp_path` là một thư mục tạm thời, tự động được xóa sau khi test kết thúc.
    """
    rng = np.random.default_rng(0)
    n = 200
    # 2.10.1: Tạo mảng X có kích thước (n, len(FEATURE_NAMES)) với giá trị ngẫu nhiên [0, 1)
    X = rng.random((n, len(FEATURE_NAMES)))
    
    # 2.10.2: Tạo mảng y có n phần tử, mỗi phần tử là số nguyên ngẫu nhiên trong [0, 3)
    y = rng.integers(0, 3, size=n)
    
    # 2.10.3: Tạo DataFrame từ X với các cột là FEATURE_NAMES, thêm cột "target" = y
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["target"] = y
    
    # 2.10.4: Lưu 160 dòng đầu vào file train.csv và 40 dòng cuối vào file eval.csv tại tmp_path
    train_path = os.path.join(tmp_path, "train.csv")
    eval_path = os.path.join(tmp_path, "eval.csv")
    
    df.iloc[:160].to_csv(train_path, index=False)
    df.iloc[160:].to_csv(eval_path, index=False)
    
    # 2.10.5: Trả về (train_path, eval_path)
    return str(train_path), str(eval_path)


def test_train_returns_float(tmp_path):
    """Kiểm tra hàm train() trả về một số thực trong khoảng [0, 1]."""
    train_path, eval_path = _make_temp_data(tmp_path)
    # 2.10.6: Gọi hàm train() với siêu tham số nhỏ (n_estimators=10, max_depth=3)
    acc = train(
        {"n_estimators": 10, "max_depth": 3},
        data_path=train_path,
        eval_path=eval_path,
    )
    # 2.10.7: assert kết quả trả về là float và nằm trong [0.0, 1.0]
    assert isinstance(acc, float)
    assert 0.0 <= acc <= 1.0


def test_metrics_file_created(tmp_path):
    """Kiểm tra file outputs/metrics.json được tạo sau khi huấn luyện."""
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "max_depth": 3},
        data_path=train_path,
        eval_path=eval_path,
    )
    # 2.10.8: assert file "outputs/metrics.json" tồn tại
    assert os.path.exists("outputs/metrics.json")
    
    # 2.10.9: Đọc file metrics.json và assert nó chứa cả "accuracy" và "f1_score"
    with open("outputs/metrics.json", "r") as f:
        metrics = json.load(f)
    assert "accuracy" in metrics
    assert "f1_score" in metrics


def test_model_file_created(tmp_path):
    """Kiểm tra file models/model.pkl được tạo sau khi huấn luyện."""
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "max_depth": 3},
        data_path=train_path,
        eval_path=eval_path,
    )
    # 2.10.10: assert file "models/model.pkl" tồn tại
    assert os.path.exists("models/model.pkl")
