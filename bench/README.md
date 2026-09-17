# Benchmark

This folder holds what produced the numbers in the main README, so that you can repeat them or add tasks of your own. Every run uses real plan usage: the six runs behind the published table came to roughly 10 dollars at API list price.

Each task runs twice with the same prompt and the same starting files, once without the plugin and once with it. `compare.py` then reads the local transcripts and reports Fable's share and the total, weighted by list price.

## Tasks

| File | Working copy | What it exercises |
|---|---|---|
| `task-build.txt` | a copy of `sample-repo/` | a small feature across several files |
| `task-read.txt` | a folder holding a copy of Python's `Lib/email` package as `email/` | a reasoning-heavy code investigation, read-only |
| `task-tests.txt` | the same kind of folder as above | bulk writing: an 800-line test suite |

## Run one task

Make two identical working copies, then run both arms. PowerShell 7 works on macOS and Linux as well.

```powershell
Copy-Item sample-repo work\build-base -Recurse
Copy-Item sample-repo work\build-router -Recurse
.\run_arm.ps1 -Name build-base   -WorkDir work\build-base   -PromptFile task-build.txt
.\run_arm.ps1 -Name build-router -WorkDir work\build-router -PromptFile task-build.txt -PluginDir ..\plugins\model-router
python compare.py ..\plugins\model-router\skills\usage-audit\model_usage.py . build
```

`run_arm.ps1` runs Claude Code headlessly with edits accepted and `python` commands allowed, so point it only at throwaway copies. It writes `<name>.sid` and `<name>.json` next to itself, and `compare.py` finds the transcripts from the session id.

## Results, 2026-09-17

Claude Code 2.1.274, Fable 5.1 as lead at default effort, one run per arm.

```text
== build
  without  fable $0.98 (11 calls, 8.5k out)  total $0.98  workers: -
  with     fable $0.82 (6 calls, 5.9k out)   total $1.02  workers: builder x1
  Fable usage change: -16%   total weighted usage change: +4%
== read
  without  fable $1.86 (9 calls, 9.7k out)   total $1.86  workers: -
  with     fable $1.73 (12 calls, 11.8k out) total $1.94  workers: scout x1
  Fable usage change: -7%    total weighted usage change: +4%
== tests
  without  fable $2.44 (13 calls, 27.6k out) total $2.44  workers: -
  with     fable $1.06 (7 calls, 7.6k out)   total $1.94  workers: builder x2
  Fable usage change: -57%   total weighted usage change: -21%

All tasks: Fable usage 32% lower; total weighted usage 7% lower.
Work per fixed Fable allowance: 1.46x  (+46%)
```

An earlier version of the policy measured about zero on the build and read tasks. It told the lead to skip anything it could finish in about three tool calls, and Fable can write hundreds of lines in two calls, so nothing was delegated. On the read task the lead also repeated the scout's work while it waited. Both rules were rewritten before the runs above.
