from pathlib import Path
import pandas as pd

cases = [
    "re1ob_currencyservice_loss_1",
    "re1ob_productcatalogservice_cpu_3",
]

root = Path("data/rcaeval_hf")

for case in cases:
    print("\n" + "=" * 80)
    print("CASE:", case)
    print("=" * 80)

    matches = [
        p for p in root.rglob("*")
        if p.is_dir() and p.name == case
    ]

    if not matches:
        print("No directory named exactly:", case)
        print("Searching for files containing the case name...")
        for p in root.rglob("*"):
            if p.is_file() and case in str(p):
                print("FILE:", p)
        continue

    for folder in matches:
        print("\nFolder:", folder.resolve())

        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue

            print("FILE:", path.relative_to(folder))

            if path.name.lower() in {
                "inject_time.txt",
                "injection_time.txt",
                "inject_time"
            }:
                print("  CONTENT:", repr(
                    path.read_text(errors="replace").strip()
                ))

            elif path.name == "metrics.parquet":
                try:
                    df = pd.read_parquet(path)
                    print("  Shape:", df.shape)
                    print("  Columns:", df.columns.tolist())

                    for col in df.columns:
                        name = col.lower()
                        if name in {
                            "timestamp", "time", "ts",
                            "time_stamp", "datetime"
                        }:
                            print("  Time column:", col)
                            print("  Minimum:", df[col].min())
                            print("  Maximum:", df[col].max())
                            print("  First values:",
                                  df[col].head(5).tolist())
                except Exception as exc:
                    print("  Could not read parquet:", repr(exc))

print("\nInspection complete. No source files were changed.")
