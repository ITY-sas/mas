"""Prueba E2E del orquestador LangGraph (ejecutar desde la raíz del repo)."""
import logging
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "orchestrator")
sys.path.insert(0, ".")

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")

from multi_agent.supervisor import run_pipeline  # noqa: E402

brief = {
    "client_id": 1,
    "content": (
        "Create a summer campaign for our new organic skincare line "
        "targeting young professionals"
    ),
}

print("Running LangGraph pipeline...")
result = run_pipeline(brief=brief, client_id=1)
print()
print("=" * 60)
print("RESULTADO:")
print("  idea_id:", result.get("idea_id"))
print("  publication_id:", result.get("publication_id"))
print("  log:", result.get("log"))
print("  idea (first 300):", (result.get("idea") or "")[:300])
print("  publication (first 300):", (result.get("publication") or "")[:300])
print("=" * 60)
