"""Compare benchmark arms: the same task with and without model-router, Fable as lead.

Usage: python compare.py <path to model_usage.py> <bench dir> <task> [<task> ...]
For each task it expects <task>-base.sid and <task>-router.sid in the bench dir.
"""
import importlib.util
import json
import os
import sys

script, bench = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("model_usage", script)
mu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mu)

prices = mu.load_prices(os.path.join(os.path.dirname(script), "prices.json"))
root = mu.projects_dir(None)
everything = mu.find_transcripts(root, None)
FABLE = ("claude-fable", "claude-mythos")


def arm(name):
    sid = open(os.path.join(bench, name + ".sid")).read().strip()
    calls, _ = mu.read_calls([t for t in everything if t[2] == sid], None)
    s = mu.summarize(calls, prices, None)
    fable = [r for r in s["rows"] if r["model"].startswith(FABLE)]
    out = {
        "fable_cost": sum(r["cost"] or 0 for r in fable),
        "fable_out": sum(r["out"] for r in fable),
        "fable_calls": sum(r["calls"] for r in fable),
        "total_cost": sum(r["cost"] or 0 for r in s["rows"]),
        "workers": ", ".join("%s x%d" % (a["agent"].split(":")[-1], a["runs"]) for a in s["agents"]) or "-",
    }
    try:
        raw = open(os.path.join(bench, name + ".json"), encoding="utf-8-sig").read()
        if raw[:1] not in "{[":
            raw = open(os.path.join(bench, name + ".json"), encoding="utf-16").read()
        res = json.loads(raw)
        out["ok"] = not res.get("is_error")
        out["minutes"] = round((res.get("duration_ms") or 0) / 60000.0, 1)
    except Exception:
        out["ok"], out["minutes"] = None, None
    return out


def pct(a, b):
    return 100.0 * (a - b) / a if a else 0.0


rows = []
for task in sys.argv[3:]:
    # "build" means build-base vs build-router; "build-base,build-router2" names both arms.
    names = task.split(",") if "," in task else [task + "-base", task + "-router"]
    base, router = arm(names[0]), arm(names[1])
    rows.append((task, base, router))
    print("== %s" % task)
    for label, r in (("without", base), ("with", router)):
        print("  %-8s fable $%.2f (%d calls, %s out)  total $%.2f  ok=%s  %s min  workers: %s" % (
            label, r["fable_cost"], r["fable_calls"], mu.short(r["fable_out"]), r["total_cost"], r["ok"], r["minutes"], r["workers"]))
    print("  Fable usage change: %+.0f%%   total weighted usage change: %+.0f%%" % (
        -pct(base["fable_cost"], router["fable_cost"]), -pct(base["total_cost"], router["total_cost"])))

fb = sum(b["fable_cost"] for _, b, _ in rows)
fr = sum(r["fable_cost"] for _, _, r in rows)
tb = sum(b["total_cost"] for _, b, _ in rows)
tr = sum(r["total_cost"] for _, _, r in rows)
x = pct(fb, fr)
print("\nAll tasks: Fable usage %.0f%% lower; total weighted usage %.0f%% lower." % (x, pct(tb, tr)))
if 0 < x < 100:
    print("Work per fixed Fable allowance: %.2fx  (+%.0f%%)" % (fb / fr, 100.0 * (fb / fr - 1)))
