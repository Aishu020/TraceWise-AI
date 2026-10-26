from pathlib import Path
import pandas as pd

root = Path("data/rcaeval_hf")

cases = [
    "re1ob_adservice_loss_2",
    "re1ob_currencyservice_loss_4",
    "re1ob_productcatalogservice_loss_4",
]

for case in cases:
    print("\n" + "=" * 75)
    print("CASE:", case)
    print("=" * 75)

    case_dir = root / case
    parquet_file = case_dir / "metrics.parquet"
    inject_file = case_dir / "inject_time.txt"

    if not parquet_file.exists():
        print("MISSING PARQUET:", parquet_file)
        continue

    if inject_file.exists():
        print("Injection timestamp text:", repr(
            inject_file.read_text(encoding="utf-8").strip()
        ))
    else:
        print("Injection timestamp file missing")

    try:
        df = pd.read_parquet(parquet_file)
    except Exception as exc:
        print("PARQUET READ ERROR:", repr(exc))
        continue

    print("Shape:", df.shape)
    print("Columns:", df.columns.tolist())
    print("\nData types:")
    print(df.dtypes.to_string())
    print("\nFirst 3 rows:")
    print(df.head(3).to_string(index=False))
    print("\nLast 3 rows:")
    print(df.tail(3).to_string(index=False))

    time_columns = [
        c for c in df.columns
        if any(term in str(c).lower()
               for term in ["time", "timestamp", "epoch", "date"])
    ]

    for col in time_columns:
        print(f"\nTime-like column: {col}")
        print("Minimum:", repr(df[col].min()))
        print("Maximum:", repr(df[col].max()))
        print("Unique values:", df[col].nunique())
        print("First values:", df[col].head(5).tolist())

