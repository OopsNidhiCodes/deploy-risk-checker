import sys
from pathlib import Path

# Makes `engine/` importable as top-level packages (models, reasoning,
# analyzers, ...) for every test file, regardless of which file pytest
# happens to collect first. Centralizing this here removes the previous
# accidental dependency on test collection order, where some test files
# inserted this path themselves and others silently relied on that having
# already happened.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "engine"))