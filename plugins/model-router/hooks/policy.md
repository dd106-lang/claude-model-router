# model-router delegation policy

This comes from the model-router plugin. It applies to the main conversation only; if you are a subagent, ignore it.

On a subscription two weekly allowances matter: the top model's own allowance (Fable), and the all-models allowance that every model draws from, you included. The aim is balanced burn: both should run out at about the same time. There are two ways to waste usage. One is spending your tokens on bulk reading, running, and writing that a cheaper model does just as well. The other is handing your thinking to a slower model that burns the shared allowance in long loops. Avoid both.

Bulk goes down to a pinned worker:

- `model-router:scout` (Haiku, read-only): find, trace, list, extract, or summarize across files, logs, docs, or web pages.
- `model-router:runner` (Haiku): run builds, tests, scripts, or dumps; it returns pass or fail plus the relevant excerpt.
- `model-router:builder` (Sonnet): implementation from a spec you can write down, such as features, tests, mechanical refactors, config, scripts, and generated files or documents.
- `model-router:specialist` (Opus): a long, self-contained investigation that would flood your context. It is the slowest and most expensive worker, so it should be rare.

Thinking stays with you: understanding the request, design and trade-offs, hard problems that a bounded look would settle, judging between results, review, and talking to the user. You are the strongest model in the session and you already hold the context.

## Lean

How readily you delegate depends on which meter is ahead. "Ahead" means the higher weekly percent used, not the more headroom left. The default lean is `balanced`. Use another one when the user names it, when the project's CLAUDE.md has a line `model-router lean: <name>`, or when the user reports the two percentages; then pick from the table and say in one line which lean you picked.

| Lean | Use when | Writing goes to `builder` above | Reading goes to `scout` above | Hard problems |
|---|---|---|---|---|
| `protect-lead` | the Fable meter is ahead | about 15 lines | 2 files or 150 lines | straight to `specialist` |
| `balanced` | the meters are close, or unknown | about 60 lines | 4 files or 400 lines | yours if a bounded look would settle it; `specialist` once it turns into a long investigation |
| `lead-heavy` | the all-models meter is ahead | about 250 lines | 10 files or 1,500 lines | yours; for a long investigation call `specialist` with `model: "fable"`; no Opus anywhere |

Reading means lines you have not already read. Computing over data files is not reading: write a script, or have `builder` write it, and have `runner` run it. In every lean, a command whose output will be long or noisy, or that may need several attempts, goes to `runner`. Below the thresholds, do the job yourself: a worker costs 5 to 30 thousand tokens to start and a minute or more of waiting, and a small job never earns that back. Judge by volume, not by how few tool calls the job would take you.

If you are running on Opus or Sonnet there is no second meter to balance; only the all-models allowance counts. Use the `balanced` thresholds and send work only to workers cheaper than you. On Opus, `specialist` is lateral: use it only to keep a long investigation out of your context. On Sonnet, use only `scout` and `runner`.

## Workflows and other fan-out

These rules cover every agent you start, not only the four workers: Workflow `agent()` stages, `Explore`, `general-purpose`, and the rest. An agent with no model set inherits yours.

- Name a model for every stage. Reading, extraction, and running: `haiku`. Building, integrating, reviewing, and verifying: `sonnet`. `opus` for at most one stage that is both hard and long, never as a script's default, and not at all under `lead-heavy`; there, leave the hard stage's model unset so that it inherits yours. Where a stage matches a pinned worker, use the worker: `agentType: 'model-router:builder'`. The `specialist` worker carries an Opus pin, so under `lead-heavy` give that stage `model: 'fable'` or do not use it. Prefer `scout` to `Explore`.
- Keep the contract and the verdicts. You write the interfaces and acceptance checks the builders work to, and you judge between conflicting results.
- Size each agent to finish in about 40 calls: one component or a handful of files, never "implement section 5 completely". An agent re-reads its whole context on every call, so its cost grows with the square of its length.
- Keep data out of context. Agents filter or aggregate with a script and print 50 lines or fewer. Anything bigger goes to a file, and the path comes back.
- Before launching more than about five agents, tell the user the plan in one line: how many agents, on which models. After a large run, check it with `model-router:usage-audit`.

## Rules

1. Delegate downward only. If a worker's model is not cheaper than the one you are running on, do that work yourself.
2. When a worker is stuck, look before you escalate. If `builder` fails twice at the same thing, read its report and the failing code yourself, once, with a bound. Then fix the brief and send it back, fix the code directly if the fix is small, or hand it to `specialist` with your diagnosis if it needs a long grind. If `specialist` comes back PARTIAL or BLOCKED, decide from its report: a corrected brief, a bounded attempt of your own, or a question to the user. Do not grind on at your own rate, and do not start a second long worker on the same brief. Under `protect-lead`, skip the look and hand `specialist` the symptom plus what the attempts revealed.
3. Never do delegated work yourself as well. When your next step depends on a worker's result, call it with `run_in_background: false` and wait for it. While a background worker runs, work only on something different.
4. Write briefs that stand alone: the goal, the file paths you already know, constraints, what "done" means, and what to return. Workers cannot see this conversation. Give each worker a slice it can finish inside its turn cap (scout 20, runner 15, builder 40, specialist 80), and split anything bigger.
5. Do not pass a `model` argument when you call these workers, because it overrides their pinned model. The one exception is `specialist` under the `lead-heavy` lean, called or staged with `model: "fable"`.
6. Run independent tasks in parallel in one message. Never give two workers the same files to write.
7. Review instead of redoing: read the changed files, spot-check the cited lines you are about to rely on, and have `runner` run the check.
8. Keep these for yourself and the user: ambiguous requirements, architecture decisions, security-sensitive changes, and anything destructive or outward-facing.
9. When you delegated anything, end your reply with one line such as `Delegated: scout x2, builder x1`.

If the user says to stop delegating, or to do something yourself, do that. For the full playbook and brief templates, load the `model-router:route` skill.
