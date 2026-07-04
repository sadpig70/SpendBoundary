"""SpendBoundary -- AI Agent Context-Boundary Spend Gate.

Usage:
    python -m SpendBoundary sample [--out examples/]
    python -m SpendBoundary evaluate --spend examples/cleared_spend.json
    python -m SpendBoundary report --input verdict.json [--out report.md]
"""

from SpendBoundary.cli import main

if __name__ == "__main__":
    main()
