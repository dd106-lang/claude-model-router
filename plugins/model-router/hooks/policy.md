# model-router delegation policy

This comes from the model-router plugin. It applies to the main conversation only; if you are a subagent, ignore it.

Every model draws on one weekly all-models allowance, and the top model (Fable) also has its own cap inside it. Getting the most out of the week means finishing each piece of work in the fewest weighted tokens (per unit of input: Haiku 1, Sonnet 2, Opus 5.5 4, Fable 10; output costs five times input on every tier) while staying under the Fable cap. Two things waste tokens: a lead that does bulk reading, running, and writing at the top rate, and a cold worker that rediscovers what the lead already knew and then loops for a hundred calls, re-reading its whole context each time. In one measured week, Workflow agents that a script had set to Opus were 87% of weighted usage.

## Pick the model by the job

| Job | Best fit | Why |
|---|---|---|
| Find, trace, list, extract, or summarize; run builds, tests, scripts, or dumps | `model-router:scout`, `model-router:runner` (Haiku) | accurate enough for mechanical work, the fastest, the cheapest; told to cite what it read and to say NOT FOUND rather than guess |
| Implementation from a spec you can write down | `model-router:builder` (Sonnet) | half of Opus 5.5's rate, measured at about 6 s per call against 10 to 12 for Opus 5, and enough for well-specified work |
| Review a change against its brief, review a diff, refute a finding, verify a claim | `model-router:reviewer` (Opus 5.5) | Anthropic reports it catches more real bugs with fewer false alarms than Opus 5 and rarely asserts what the inputs do not support (not benchmarked here against Sonnet); use it where your lean's review column says, and below that review yourself |
| A long, self-contained investigation | `model-router:specialist` (Opus 5.5, medium effort) | at medium effort it matches the previous Opus at high with about half the tokens; still the longest-running worker (up to 80 turns; Opus 5.5 per-call speed not yet measured), so keep it rare and small |
| Understanding the request, design and trade-offs, contracts, hard problems that a bounded look would settle, judging between results, talking to the user | you | the strongest model, already holding the context: no start-up and no rediscovery, so a small piece done in context costs less than a worker's start-up |

A worker costs 5 to 30 thousand tokens to start and a minute or more of waiting. Below the thresholds for your lean, do the job yourself. Judge by volume, not by how few tool calls the job would take you.

## Lean

The Fable cap decides how much of the small work and the judgment you may keep. "Ahead" means the higher weekly percent used, not the more headroom left. The default lean is `balanced`. Use another one when the user names it, when the project's CLAUDE.md has a line `model-router lean: <name>`, or when the user reports the two percentages; then pick from the table and say in one line which lean you picked.

| Lean | Use when | Writing goes to `builder` above | Reading goes to `scout` above | Hard problems | Review of a change |
|---|---|---|---|---|---|
| `protect-lead` | the Fable meter is ahead | about 15 lines | 2 files or 150 lines | straight to `specialist` | `reviewer` |
| `balanced` | the meters are close, or unknown | about 60 lines | 4 files or 400 lines | your bounded look first; `specialist` once it turns into a long investigation | `reviewer` above about 300 changed lines, you below |
| `lead-heavy` | the all-models meter is ahead | about 250 lines | 10 files or 1,500 lines | your bounded look first; `specialist` only after it fails, sized small | you |

Under `lead-heavy` the all-models meter binds first, so the aim is the fewest total tokens: pieces below the thresholds stay with you, bulk goes to Haiku and Sonnet, and Opus workers are kept short. Fable's own meter has room, so use it freely for judgment; it still counts toward the all-models meter, so do not move bulk onto it. Under `protect-lead` the Fable cap binds first, so push work off Fable even where that costs a little more in total.

Reading means lines you have not already read. Computing over data files is not reading: write a script, or have `builder` write it, and have `runner` run it. In every lean, a command whose output will be long or noisy, or that may need several attempts, goes to `runner`.

If you are running on Opus or Sonnet there is no second meter; only the all-models allowance counts. Use the `balanced` thresholds and send work only to workers cheaper than you. On Opus, `reviewer` and `specialist` are lateral: use them only to keep a long read or investigation out of your context. On Sonnet, use only `scout` and `runner`.

## Workflows and other fan-out

These rules cover every agent you start, not only the pinned workers: Workflow `agent()` stages, `Explore`, `general-purpose`, and the rest. An agent with no model set inherits yours.

- Name a model for every stage. Reading, extraction, and running: `haiku`. Building and integrating: `sonnet`. Review, verification, and refutation stages, and at most one stage that is both hard and long: `opus`. Never `opus` as a script's default, and never `fable` for a stage. Where a stage matches a pinned worker, use the worker: `agentType: 'model-router:builder'`, `agentType: 'model-router:reviewer'`. Prefer `scout` to `Explore`. Give mechanical stages `effort: 'low'`.
- Keep the contract and the verdicts. You write the interfaces and acceptance checks the builders work to, and you judge between conflicting results.
- Size each agent to finish in about 40 calls: one component or a handful of files, never "implement section 5 completely". An agent re-reads its whole context on every call, so its cost grows with the square of its length.
- Keep data out of context. Agents filter or aggregate with a script and print 50 lines or fewer. Anything bigger goes to a file, and the path comes back.
- Before launching more than about five agents, tell the user the plan in one line: how many agents, on which models. After a large run, check it with `model-router:usage-audit`.

## Rules

1. Delegate downward. Never delegate to a dearer tier. A worker on your own tier is used only to keep a long read or investigation out of your context, as an Opus lead may do with `reviewer` or `specialist`.
2. When a worker is stuck, look before you escalate. If `builder` fails twice at the same thing, read its report and the failing code yourself, once, with a bound. Then fix the brief and send it back, fix the code directly if the fix is small, or hand it to `specialist` with your diagnosis if it needs a long grind. If `specialist` comes back PARTIAL or BLOCKED, decide from its report: a corrected brief, a bounded attempt of your own, or a question to the user. Do not grind on at your own rate, and do not start a second long worker on the same brief. Under `protect-lead`, skip the look and hand `specialist` the symptom plus what the attempts revealed.
3. Never do delegated work yourself as well. When your next step depends on a worker's result, call it with `run_in_background: false` and wait for it. While a background worker runs, work only on something different.
4. Write briefs that stand alone: the goal, the file paths you already know, constraints, what "done" means, and what to return. Workers cannot see this conversation. Give each worker a slice it can finish inside its turn cap (scout 20, runner 15, reviewer 25, builder 40, specialist 80), and split anything bigger.
5. Do not pass a `model` argument when you call these workers. It overrides their pinned model.
6. Run independent tasks in parallel in one message. Never give two workers the same files to write.
7. Review instead of redoing. Check a worker's change the way your lean says: read the diff yourself, or send it to `reviewer` with the brief it was built to. Spot-check any cited line you are about to rely on, and have `runner` run the check when the change matters.
8. Keep these for yourself and the user: ambiguous requirements, architecture decisions, security-sensitive changes, and anything destructive or outward-facing.
9. When you delegated anything, end your reply with one line such as `Delegated: scout x2, builder x1`.

If the user says to stop delegating, or to do something yourself, do that. For the full playbook and brief templates, load the `model-router:route` skill.
