from pathlib import Path

root = Path("data/rcaeval_hf")

targets = [
    "re1ob_currencyservice_loss_1",
    "re1ob_productcatalogservice_cpu_3",
]

for target in targets:
    print("\n" + "=" * 70)
    print("SEARCH:", target)
    print("=" * 70)

    found = False

    for path in root.rglob("*"):
        if ".cache" in path.parts:
            continue

        if target in path.name:
            found = True
            print(path, "[directory]" if path.is_dir() else "[file]")

            if path.is_dir():
                for child in sorted(path.iterdir()):
                    if child.is_file():
                        print("  ", child.name, child.stat().st_size, "bytes")

    if not found:
        print("No matching non-cache file or folder found.")
