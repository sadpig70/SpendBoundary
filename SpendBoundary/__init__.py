"""SpendBoundary — AI Agent Context-Boundary Spend Gate.

Vetoes AI agent spends that cross context boundaries without re-authorization.
Recombination: ContextCreep (boundary-crossing path ranking) + SpendMesh (treasury control)
               + VetoEscrow (interruptible clearing gate for high-risk decisions).
"""

from SpendBoundary.engine import evaluate_spend
from SpendBoundary.report import render_report

__all__ = ["evaluate_spend", "render_report"]
__version__ = "1.0.0"
