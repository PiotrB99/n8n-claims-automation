import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(os.environ["TEMP"], "opencode", "mcp", "results5")
EXPECTED_DIR = os.path.join(REPO, "datasets", "expected")

GROUPS = [("A", 1, 5), ("B", 6, 10), ("C", 11, 15), ("D", 16, 20),
          ("E", 21, 25), ("F", 26, 30), ("G", 31, 35), ("H", 36, 40)]


def group_of(case_id):
    n = int(case_id.split("-")[1])
    return next(g for g, lo, hi in GROUPS if lo <= n <= hi)


results, expected = {}, {}
for f in sorted(os.listdir(RESULTS_DIR)):
    r = json.load(open(os.path.join(RESULTS_DIR, f), encoding="utf-8"))
    results[r["case_id"]] = r
for n in range(1, 41):
    cid = f"CASE-{n:04d}"
    e = json.load(open(os.path.join(EXPECTED_DIR, f"{cid}.json"), encoding="utf-8"))
    expected[cid] = e

assert len(results) == 40 and len(expected) == 40

ok_cases, tf_cases, mismatches = [], [], []
for cid in sorted(expected):
    e, r = expected[cid], results[cid]
    got = r.get("final_decision")
    if got == e["expected_decision"]:
        ok_cases.append(cid)
    elif got == "TECHNICAL_FAIL":
        tf_cases.append(cid)
    else:
        mismatches.append({
            "case_id": cid, "group": group_of(cid), "category": e["category"],
            "expected": e["expected_decision"], "got": got,
            "confidence": r.get("confidence"), "gate_reason": r.get("gate_reason"),
        })

human_ok = sum(
    1 for cid in expected
    if (results[cid].get("final_decision") == "HUMAN_REVIEW") == bool(expected[cid]["requires_human"])
)

per_group = {}
for g, lo, hi in GROUPS:
    ids = [f"CASE-{i:04d}" for i in range(lo, hi + 1)]
    per_group[g] = {"total": len(ids),
                    "ok": sum(1 for c in ids if results[c]["final_decision"] == expected[c]["expected_decision"])}

decided_at = max(r["decided_at"] for r in results.values())
out = {
    "generated_at": decided_at,
    "path": "batch-eval (harness) — wyniki z plikow outbox",
    "config": {"rag_top_k": 10, "model": results["CASE-0001"].get("model")},
    "run_started_at": min(r["decided_at"] for r in results.values()),
    "total_cases": 40,
    "decision_accuracy_pct": round(100 * len(ok_cases) / 40, 1),
    "human_path_accuracy_pct": round(100 * human_ok / 40, 1),
    "technical_failures": len(tf_cases),
    "technical_fail_cases": tf_cases,
    "per_group": per_group,
    "mismatches": mismatches,
    "comparison": {
        "run3_full_kb_batch_harness": 95.0,
        "run4_rag_top6_native_harness": 82.5,
        "run5_rag_top10_batch_harness": round(100 * len(ok_cases) / 40, 1),
    },
}
dest = os.path.join(REPO, "datasets", "outbox", "eval-run-005-rag-top10.json")
with open(dest, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)

print(json.dumps(out, indent=1, ensure_ascii=False))
