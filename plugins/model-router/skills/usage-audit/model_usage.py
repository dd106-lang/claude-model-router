#!/usr/bin/env python3
"""model_usage.py - which Claude models actually ran, and what each one used.

Reads Claude Code's local transcripts (~/.claude/projects/**/*.jsonl) and
reports tokens per model, split into the lead (main conversation) and
subagents. Standard library only; Python 3.8+. Output is plain ASCII.

Usage:
  python model_usage.py --session <id-or-prefix>     one session
  python model_usage.py --session latest             most recent session
  python model_usage.py --since 24h                  time window: 12h, 7d, or an ISO date
  python model_usage.py --since 7d --project myrepo  only projects whose folder name contains "myrepo"
  python model_usage.py --all                        everything on disk
  python model_usage.py ... --json                   machine-readable

How the transcripts are read (the format is internal to Claude Code and can
change between releases; if numbers look wrong after an update, check here):
  - Each API response is written as several "assistant" lines, one per content
    block. They share a requestId / message.id, and only the last line has the
    final output_tokens. Calls are de-duplicated on that id, keeping the
    largest output_tokens, otherwise usage is over-counted several times.
  - Subagent transcripts are <project>/<session>/subagents/**/agent-*.jsonl,
    with a sibling agent-*.meta.json that holds {"agentType": ...}.
  - Resumed or forked sessions can replay earlier lines into a new file. The
    id de-duplication is global, and main files are read first, so replayed
    calls stay attributed to the conversation that made them.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- arguments

def parse_args():
    p = argparse.ArgumentParser(description="Tokens per Claude model, lead vs. subagents, from local transcripts.")
    p.add_argument("--session", help="session id, id prefix, or 'latest'")
    p.add_argument("--since", help="window such as 12h or 7d, or an ISO date/time")
    p.add_argument("--all", action="store_true", help="no time limit")
    p.add_argument("--project", help="only project folders whose name contains this text")
    p.add_argument("--lead", help="model id to treat as the lead for the savings estimate")
    p.add_argument("--dir", help="projects directory (default: ~/.claude/projects)")
    p.add_argument("--prices", default=os.path.join(HERE, "prices.json"), help="price table (default: prices.json next to this script)")
    p.add_argument("--json", action="store_true", help="print JSON instead of a table")
    return p.parse_args()


def projects_dir(arg):
    if arg:
        return arg
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "projects")


def parse_since(text):
    m = re.fullmatch(r"(\d+)\s*([hd])", text.strip().lower())
    if m:
        n = int(m.group(1))
        return datetime.now(timezone.utc) - (timedelta(hours=n) if m.group(2) == "h" else timedelta(days=n))
    try:
        d = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        sys.exit("Could not read --since %r. Use 12h, 7d, or an ISO date such as 2026-01-31." % text)
    return d if d.tzinfo else d.astimezone()


def parse_ts(text):
    if not isinstance(text, str):
        return None
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------- discovery

def find_transcripts(root, project_filter):
    """Return [(path, project, session, kind)] with kind 'main' or 'sub'."""
    found = []
    if not os.path.isdir(root):
        return found
    for project in sorted(os.listdir(root)):
        pdir = os.path.join(root, project)
        if not os.path.isdir(pdir):
            continue
        if project_filter and project_filter.lower() not in project.lower():
            continue
        for dirpath, _dirs, files in os.walk(pdir):
            rel = os.path.relpath(dirpath, pdir)
            parts = [] if rel == "." else rel.split(os.sep)
            for name in files:
                if not name.endswith(".jsonl"):
                    continue
                path = os.path.join(dirpath, name)
                if "subagents" in parts:
                    i = parts.index("subagents")
                    session = parts[i - 1] if i > 0 else "?"
                    found.append((path, project, session, "sub"))
                elif not parts:
                    found.append((path, project, name[:-len(".jsonl")], "main"))
    return found


def agent_type_for(path):
    meta = path[:-len(".jsonl")] + ".meta.json"
    try:
        with open(meta, encoding="utf-8") as f:
            value = json.load(f).get("agentType")
        if value:
            return str(value)
    except (OSError, ValueError, AttributeError):
        pass
    return "unknown"


# ------------------------------------------------------------------ reading

def read_calls(transcripts, since):
    """De-duplicated API calls: {id: record}."""
    calls = {}
    skipped = 0
    ordered = sorted(transcripts, key=lambda t: (t[3] != "main", os.path.getmtime(t[0])))
    for path, project, session, kind in ordered:
        if since and datetime.fromtimestamp(os.path.getmtime(path), timezone.utc) < since:
            continue
        agent = agent_type_for(path) if kind == "sub" else None
        try:
            handle = open(path, encoding="utf-8", errors="replace")
        except OSError:
            skipped += 1
            continue
        with handle:
            for line in handle:
                if '"assistant"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or entry.get("type") != "assistant":
                    continue
                msg = entry.get("message")
                if not isinstance(msg, dict):
                    continue
                model, usage = msg.get("model"), msg.get("usage")
                if not model or model == "<synthetic>" or not isinstance(usage, dict):
                    continue
                when = parse_ts(entry.get("timestamp"))
                if since and when and when < since:
                    continue
                key = entry.get("requestId") or msg.get("id") or entry.get("uuid")
                if not key:
                    continue
                out = int(usage.get("output_tokens") or 0)
                known = calls.get(key)
                if known is not None and out <= known["out"]:
                    continue
                created = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else {}
                cw_total = int(usage.get("cache_creation_input_tokens") or 0)
                cw_1h = int(created.get("ephemeral_1h_input_tokens") or 0)
                cw_5m = int(created.get("ephemeral_5m_input_tokens") or 0)
                if cw_1h + cw_5m != cw_total:
                    cw_5m, cw_1h = cw_total, 0
                numbers = {"in": int(usage.get("input_tokens") or 0), "cw5m": cw_5m, "cw1h": cw_1h,
                           "cr": int(usage.get("cache_read_input_tokens") or 0), "out": out}
                if known is not None:
                    known.update(numbers)
                    continue
                sidechain = kind == "sub" or bool(entry.get("isSidechain"))
                record = {"model": model, "role": "subagent" if sidechain else "lead",
                          "agent": agent or ("sidechain" if sidechain else None),
                          "run": path if kind == "sub" else None,
                          "project": project, "session": session, "when": when}
                record.update(numbers)
                calls[key] = record
    return calls, skipped


# ------------------------------------------------------------------ pricing

def load_prices(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def price_for(prices, model):
    if not prices:
        return None
    best = None
    for prefix, row in (prices.get("models") or {}).items():
        if model.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, row)
    return best[1] if best else None


def cost(prices, row, tokens):
    """List-price cost in dollars of `tokens` at the price row `row`."""
    if not row:
        return None
    pin, pout = float(row["input"]), float(row["output"])
    read = float(row["cache_read"]) if "cache_read" in row else pin * float(prices.get("cache_read_multiplier", 0.1))
    per_million = (tokens["in"] * pin
                   + tokens["cw5m"] * pin * float(prices.get("cache_write_5m_multiplier", 1.25))
                   + tokens["cw1h"] * pin * float(prices.get("cache_write_1h_multiplier", 2.0))
                   + tokens["cr"] * read
                   + tokens["out"] * pout)
    return per_million / 1e6


# ---------------------------------------------------------------- reporting

FIELDS = ("in", "cw5m", "cw1h", "cr", "out")


def short(n):
    n = float(n)
    for unit, size in (("M", 1e6), ("k", 1e3)):
        if abs(n) >= size:
            return "%.1f%s" % (n / size, unit)
    return "%d" % n


def money(x):
    return "n/a" if x is None else "$%.2f" % x


def summarize(calls, prices, lead_override):
    rows = defaultdict(lambda: dict(calls=0, **{f: 0 for f in FIELDS}))
    agents = defaultdict(lambda: {"runs": set(), "models": set(), "calls": 0, "tokens": 0, "out": 0})
    sessions, first, last = set(), None, None
    for c in calls.values():
        r = rows[(c["model"], c["role"])]
        r["calls"] += 1
        for f in FIELDS:
            r[f] += c[f]
        sessions.add((c["project"], c["session"]))
        if c["when"]:
            first = c["when"] if first is None or c["when"] < first else first
            last = c["when"] if last is None or c["when"] > last else last
        if c["role"] == "subagent":
            a = agents[c["agent"] or "unknown"]
            a["runs"].add(c["run"] or c["session"])
            a["models"].add(c["model"])
            a["calls"] += 1
            a["tokens"] += sum(c[f] for f in FIELDS)
            a["out"] += c["out"]

    table = []
    for (model, role), r in rows.items():
        row = dict(model=model, role=role, **r)
        row["cost"] = cost(prices, price_for(prices, model), r)
        table.append(row)
    table.sort(key=lambda x: (x["role"] != "lead", -(x["cost"] or 0), -x["out"]))

    leads = [x for x in table if x["role"] == "lead"]
    lead = lead_override or (max(leads, key=lambda x: x["out"])["model"] if leads else None)
    lead_price = price_for(prices, lead) if lead else None

    total_out = sum(x["out"] for x in table) or 1
    cheaper_out, actual, at_lead, unpriced = 0, 0.0, 0.0, 0
    for x in table:
        own = price_for(prices, x["model"])
        if lead_price and own and float(own["output"]) < float(lead_price["output"]):
            cheaper_out += x["out"]
        if x["role"] != "subagent":
            continue
        if x["cost"] is None or not lead_price:
            unpriced += x["calls"]
            continue
        actual += x["cost"]
        at_lead += cost(prices, lead_price, x)

    return {
        "sessions": len(sessions),
        "first": first.isoformat() if first else None,
        "last": last.isoformat() if last else None,
        "lead_model": lead,
        "rows": table,
        "agents": [dict(agent=k, runs=len(v["runs"]), models=sorted(v["models"]), calls=v["calls"],
                        tokens=v["tokens"], out=v["out"])
                   for k, v in sorted(agents.items(), key=lambda kv: -kv[1]["tokens"])],
        "pct_output_on_cheaper_models": round(100.0 * cheaper_out / total_out, 1) if lead_price else None,
        "subagent_cost_actual": round(actual, 4) if lead_price else None,
        "subagent_cost_if_on_lead": round(at_lead, 4) if lead_price else None,
        "unpriced_subagent_calls": unpriced,
        "prices_as_of": (prices or {}).get("as_of"),
    }


def print_report(s, scope):
    print("Model usage - %s" % scope)
    if s["first"]:
        print("%d session(s), %s to %s UTC" % (s["sessions"], s["first"][:16].replace("T", " "), s["last"][:16].replace("T", " ")))
    print("calls = de-duplicated API requests; in = uncached input; c.write / c.read = prompt cache; est$ = list price")
    print("")
    head = "%-34s %-9s %6s %9s %9s %9s %9s %9s" % ("MODEL", "ROLE", "CALLS", "IN", "C.WRITE", "C.READ", "OUT", "EST$")
    print(head)
    print("-" * len(head))
    for x in s["rows"]:
        print("%-34s %-9s %6d %9s %9s %9s %9s %9s" % (
            x["model"][:34], x["role"], x["calls"], short(x["in"]), short(x["cw5m"] + x["cw1h"]),
            short(x["cr"]), short(x["out"]), money(x["cost"])))
    print("")

    if s["agents"]:
        print("Subagents:")
        for a in s["agents"]:
            print("  %-34s %3d run(s) %5d calls %9s tokens   on %s" % (
                a["agent"][:34], a["runs"], a["calls"], short(a["tokens"]), ", ".join(a["models"])))
    else:
        print("Subagents: none ran in this scope, so every token above was spent by the lead.")
    print("")

    print("Lead model: %s" % (s["lead_model"] or "none found"))
    if s["pct_output_on_cheaper_models"] is not None:
        print("Output tokens produced by models cheaper than the lead: %.1f%%" % s["pct_output_on_cheaper_models"])
    if s["subagent_cost_if_on_lead"]:
        a, b = s["subagent_cost_actual"], s["subagent_cost_if_on_lead"]
        if b > a:
            print("Subagent work cost about %s at list price; the same tokens on the lead model would be about %s (%.0f%% less)."
                  % (money(a), money(b), 100.0 * (b - a) / b))
        else:
            print("Subagent work cost about %s at list price; on the lead model it would be about %s, so routing saved nothing here."
                  % (money(a), money(b)))
    if s["unpriced_subagent_calls"]:
        print("%d subagent call(s) used a model that is not in prices.json and are left out of the estimate." % s["unpriced_subagent_calls"])
    print("")
    print("Notes: est$ is API list price (prices.json, as of %s), for comparing models only." % (s["prices_as_of"] or "unknown"))
    print("Subscription plans meter usage differently and are not billed per token. The estimate assumes")
    print("a different model would have used the same number of tokens, which is only roughly true.")


def main():
    args = parse_args()
    root = projects_dir(args.dir)
    transcripts = find_transcripts(root, args.project)
    if not transcripts:
        sys.exit("No transcripts found under %s%s." % (root, " matching --project %r" % args.project if args.project else ""))

    since, scope = None, "all sessions on disk"
    if args.session:
        mains = [t for t in transcripts if t[3] == "main"]
        if args.session.lower() == "latest":
            if not mains:
                sys.exit("No main session transcripts found.")
            wanted = max(mains, key=lambda t: os.path.getmtime(t[0]))[2]
        else:
            matches = sorted({t[2] for t in transcripts if t[2].startswith(args.session)})
            if not matches:
                sys.exit("No session id starts with %r. Try --session latest, or --since 24h." % args.session)
            if len(matches) > 1:
                sys.exit("%r matches %d sessions; give more of the id: %s" % (args.session, len(matches), ", ".join(m[:13] for m in matches[:6])))
            wanted = matches[0]
        transcripts = [t for t in transcripts if t[2] == wanted]
        scope = "session %s" % wanted
    elif not args.all:
        text = args.since or "7d"
        since = parse_since(text)
        scope = "since %s" % text
    if args.project:
        scope += ", project contains %r" % args.project

    calls, skipped = read_calls(transcripts, since)
    if not calls:
        sys.exit("No model usage found for %s. The transcript format may have changed, or nothing ran in that scope." % scope)

    summary = summarize(calls, load_prices(args.prices), args.lead)
    if args.json:
        print(json.dumps(dict(scope=scope, **summary), indent=2))
    else:
        print_report(summary, scope)
        if skipped:
            print("(%d transcript file(s) could not be opened and were skipped.)" % skipped)


if __name__ == "__main__":
    main()
