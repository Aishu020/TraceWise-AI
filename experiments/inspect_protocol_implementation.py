from pathlib import Path

files = [
    Path("experiments/baseline_ranker_v2.py"),
    Path("experiments/aggregation_ablation_heldout_98.py"),
    Path("experiments/evaluate_heldout_99.py"),
    Path("experiments/results/heldout_98_aggregation_ablation_summary.csv"),
    Path("experiments/results/evaluation_split_audit_summary.csv"),
]

for path in files:
    print("\n" + "=" * 90)
    print(f"FILE: {path}")
    print("=" * 90)

    if not path.exists():
        print("MISSING")
        continue

    if path.suffix == ".py":
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        print(f"Total lines: {len(lines)}")

        # Show the complete implementation when reasonably sized.
        if len(lines) <= 220:
            for number, line in enumerate(lines, start=1):
                print(f"{number:4}: {line}")
        else:
            # Show definitions, evaluation logic, and relevant context.
            keywords = (
                "def ", "median", "mad", "scale", "aggregate",
                "rank", "hit@", "mrr", "tie", "inject",
                "pre_", "post_", "window", "read_csv",
                "to_csv", "mean(", "sort_values", "root_cause",
                "heldout", "argparse", "__main__"
            )
            selected = set()
            for i, line in enumerate(lines):
                if any(word in line.lower() for word in keywords):
                    selected.update(range(max(0, i - 2), min(len(lines), i + 3)))

            previous = -2
            for i in sorted(selected):
                if i > previous + 1:
                    print("     ...")
                print(f"{i+1:4}: {lines[i]}")
                previous = i
    else:
        print(path.read_text(encoding="utf-8-sig"))

print("\nInspection complete. No files were modified.")
