from pathlib import Path
import sys

# Make the backend package importable when pytest is launched from the backend folder.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
