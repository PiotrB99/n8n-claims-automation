import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = json.load(open(os.path.join(os.environ["TEMP"], "opencode", "mcp", "rows.json"),
                      encoding="utf-8-sig"))
assert len(rows) == 40, f"expected 40 rows, got {len(rows)}"

GROUPS = [("A", 1, 5), ("B", 6, 10), ("C", 11, 15), ("D", 16, 20),
          ("E", 21, 25), ("F", 26, 30), ("G", 31, 35), ("H", 36, 40)]


def group_of(case_id):
    n = int(case_id.split("-")[1])
    return next(g for g, lo, hi in GROUPS if lo <= n <= hi)


def category_of(case_id):
    p = os.path.join(REPO, "datasets", "expected", f"{case_id}.json")
    return json.load(open(p, encoding="utf-8")).get("category")


ok = [r for r in rows if r["decision_ok"]]
tf = [r for r in rows if r["got_decision"] == "TECHNICAL_FAIL"]
mism = [r for r in rows if not r["decision_ok"] and r["got_decision"] != "TECHNICAL_FAIL"]

per_group = {}
for g, lo, hi in GROUPS:
    sub = [r for r in rows if group_of(r["case_id"]) == g]
    per_group[g] = {"total": len(sub),
                    "ok": sum(1 for r in sub if r["decision_ok"])}

out = {
    "generated_at": max(r["updatedAt"] for r in rows),
    "path": "n8n-native-evaluation",
    "workflow": "claims-demo-eval-native",
    "total_cases": len(rows),
    "decision_accuracy_pct": round(100 * len(ok) / len(rows), 1),
    "technical_failures": len(tf),
    "per_group": per_group,
    "technical_fail_cases": [
        {"case_id": r["case_id"], "group": group_of(r["case_id"]),
         "category": category_of(r["case_id"]), "expected": r["expected_decision"]}
        for r in tf],
    "mismatches": [
        {"case_id": r["case_id"], "group": group_of(r["case_id"]),
         "category": category_of(r["case_id"]), "expected": r["expected_decision"],
         "got": r["got_decision"]}
        for r in mism],
    "notes": {
        "decision_ok_definition": "final_decision == expected_decision",
        "rag_context": "top-6 (happy path z RAG), nie pelna baza wiedzy",
        "baseline_comparison": "run #3 (pelna baza): 95% / 0 TECHNICAL_FAIL",
        "exported_from": "Data Table eval_dataset_v0 (sqlite read-only)",
    },
}
dest = os.path.join(REPO, "datasets", "outbox", "eval-run-004-native.json")
with open(dest, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print(json.dumps({"accuracy": out["decision_accuracy_pct"],
                  "tech_fails": [t["case_id"] for t in out["technical_fail_cases"]],
                  "mismatches": [m["case_id"] for m in out["mismatches"]],
                  "written": dest}, indent=1))
