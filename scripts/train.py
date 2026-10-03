from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

DATA = Path("data/tickets.csv")


#where model file would be saved
MODEL_OUT = Path("models/classifier.joblib")

def build_pipeline()->Pipeline:
    return Pipeline([
        ("tfidf",TfidfVectorizer(
            lowercase=True,
            ngram_range=(1,2),
            min_df=2,
            sublinear_tf=True,
        )),
        ("clf",LogisticRegression(
            max_iter=100,
            class_weight="balanced",
            C=5.0,
        )),
    ])

def main() -> None:
    df = pd.read_csv(DATA)

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["category"],
        test_size=0.2,
        random_state=42,
        stratify=df["category"],     # keep class balance in both splits
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    preds = pipe.predict(X_test)
    print(classification_report(y_test, preds, digits=3))

    labels = sorted(df["category"].unique())
    cm = pd.DataFrame(
        confusion_matrix(y_test, preds, labels=labels),
        index=[f"true_{l}" for l in labels],
        columns=[f"pred_{l}" for l in labels],
    )
    print("\nConfusion matrix:")
    print(cm.to_string())

    MODEL_OUT.parent.mkdir(exist_ok=True)
    joblib.dump(pipe, MODEL_OUT)
    print(f"\nsaved -> {MODEL_OUT}")


if __name__ == "__main__":
    main()