from pathlib import Path
import pandas as pd

root = Path("data/rcaeval_hf")

cases = {
    "re1ob_currencyservice_loss_1": 16933142,
    "re1ob_productcatalogservice_cpu_3": 1685373255,
}

for case, manifest_time in cases.items():
    folder = root / case
    inject_path = folder / "inject_time.txt"
    metrics_path = folder / "metrics.parquet"

    print("\n" + "=" * 75)
    print("CASE:", case)
    print("=" * 75)

    if not inject_path.exists() or not metrics_path.exists():
        print("ERROR: Missing injection-time or metrics file.")
        continue

    raw_text = inject_path.read_text(errors="replace").strip()
    print("Raw injection-time text:", repr(raw_text))
    print("Manifest injection time:", manifest_time)

    try:
        file_time = int(raw_text)
        print("File/manifest match:", file_time == manifest_time)
    except ValueError:
        file_time = None
        print("Injection-time file is not a plain integer.")

    df = pd.read_parquet(metrics_path)

    print("Telemetry shape:", df.shape)
    print("Time column dtype:", df["time"].dtype)

    times = pd.to_numeric(df["time"], errors="coerce").dropna()

    if times.empty:
        print("ERROR: No valid numeric timestamps.")
        continue

    start = int(times.min())
    end = int(times.max())

    print("Telemetry start:", start)
    print("Telemetry end:", end)
    print("Telemetry rows:", len(times))
    print("Seconds before injection:", (
        file_time - end if file_time is not None else "unknown"
    ))
    print("Injection within telemetry:", (
        start <= file_time <= end if file_time is not None else "unknown"
    ))

    if file_time is not None:
        nearest = int((times - file_time).abs().idxmin())
        print("Nearest telemetry timestamp:", int(df.loc[nearest, "time"]))
        print("Distance to nearest timestamp:", abs(
            int(df.loc[nearest, "time"]) - file_time
        ))

    print("First 5 timestamps:", times.head(5).tolist())
    print("Last 5 timestamps:", times.tail(5).tolist())

print("\nVerification finished. No files were modified.")
