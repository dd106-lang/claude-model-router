---
name: route
description: Multi-model delegation playbook. Balances usage between the lead model's own allowance (Fable) and the shared all-models allowance - the lead keeps the thinking, bulk work goes to cheaper pinned workers (scout and runner on Haiku, builder on Sonnet), and Opus is kept for rare long investigations. Use when the user asks to save tokens or usage, to balance or pace their usage meters, to delegate, or to use subagents, cheaper models, or a Workflow, and when starting a multi-step coding, file-generation, or research task that contains routine work.
argument-hint: "[task to plan and delegate]"
---

# Route each piece of work to the right tier

Task from the user, if one was given: $ARGUMENTS

If no task was given, apply this playbook to the work already under way in the conversation.

On a subscription two weekly allowances matter. The top model (Fable) has its own, and every model, the lead included, draws from the all-models allowance. The aim is balanced burn: both run out at about the same time, and neither is wasted. Usage gets wasted in two ways:

- **The lead does bulk work.** Every file you read and every line you write is billed at your rate, and it stays in your context for the rest of the session. A cheaper worker does routine reading, running, and writing just as well, in its own context, and hands back a short report.
- **A slower model does the lead's thinking.** A worker that starts cold on a hard problem has to rediscover what you already know, and it does so in a long loop that re-reads its whole context on every call. In one measured week, Workflow agents that a script had set to Opus were 87% of weighted usage, and the lead was 10%.

So the bulk goes down, the thinking stays with you, and Opus, which is the slowest tier and draws only on the shared allowance, is the one you use least.

## 0. Pick the lean

The lean sets how readily you delegate. Default to `balanced`. Use another when the user says so, or when the project's CLAUDE.md has a line `model-router lean: <name>`.

| Lean | Use when | Writing goes to `builder` above | Reading goes to `scout` above | Hard problems |
|---|---|---|---|---|
| `protect-lead` | the Fable meter is ahead | about 15 lines | 2 files or 150 lines | straight to `specialist` |
| `balanced` | the meters are close, or unknown | about 60 lines | 4 files or 400 lines | yours if a bounded look would settle it; `specialist` once it turns into a long investigation |
| `lead-heavy` | the all-models meter is ahead | about 250 lines | 10 files or 1,500 lines | yours; for a long investigation call `specialist` with `model: "fable"`; no Opus anywhere |

"Ahead" means the higher weekly percent used on the usage card, not the more headroom left. When the user reports the two percentages, pick the lean from the table and say in one line which one you picked. If all-models shows 15% and Fable shows 6%, the all-models meter is ahead, and the lean is `lead-heavy`. If you cannot see the meters, ask the user or stay on `balanced`. The `model-router:usage-audit` skill prints each model's share of weighted usage, which is the number to steer by: when the two meters burn at the same rate, Fable's share equals the ratio of the two allowances. About a quarter is a reasonable first target on a Max plan; the user should adjust it to what their own meters do.

If you are running on Opus or Sonnet there is no second meter; only the all-models allowance counts. Use the `balanced` thresholds and delegate only to workers cheaper than you. On Opus, `specialist` is lateral: use it only to keep a long investigation out of your context. On Sonnet, use only `scout` and `runner`.

## 1. Split the task

Break the work into pieces and label each piece with one of these:

| Piece looks like | Send to | Model |
|---|---|---|
| Find, trace, list, extract, or summarize across files, logs, docs, or web pages | `model-router:scout` | Haiku |
| Run a build, test suite, script, or dump | `model-router:runner` | Haiku |
| Build something whose spec you can write down: a feature that follows existing patterns, tests, a mechanical refactor, config, a script, a data conversion, a generated document or report | `model-router:builder` | Sonnet |
| Compute over data: statistics, baselines, or conversions across many data or log files | A script, written by you or by `model-router:builder` depending on its size, and run by `model-router:runner` | Sonnet, Haiku |
| A long, self-contained investigation: a cause that is still unknown after your bounded look, repeated run-and-measure cycles, decoding an undocumented protocol or binary format, or something builder failed at twice that you have diagnosed as a long grind | `model-router:specialist` | Opus |
| Unclear requirements, architecture and trade-offs, hard problems that a bounded look would settle, judging between results, security-sensitive changes, destructive or outward-facing actions, final review, talking with the user | You | Lead |

Three checks before you delegate a piece:

- **Is the worker actually cheaper than you?** The order is Haiku, then Sonnet, then Opus, then Fable. If you are running on Opus, `specialist` is lateral, so use it only to keep a long investigation out of your context. If you are on Sonnet, do routine implementation yourself and use only scout and runner.
- **Is the piece worth a worker?** Starting one costs roughly 5 to 10 thousand tokens for scout and runner, and about 30 thousand for builder and specialist. It also costs time: a scout or runner call takes a minute or two, a builder about five, a specialist ten or more. Measured on combined usage, delegation was slightly worse (4% higher) at about 250 lines of writing and paid off clearly (21% lower) at 800; on the small job it moved usage from the lead to the workers without reducing the total. That is why the thresholds rise as the all-models meter gets ahead. Use the thresholds for your lean, and below them do the job yourself.
- **Can you write the spec?** If you cannot say what "done" means, the piece is not ready to delegate. Do the thinking first, or send a scout to gather what you need in order to decide. Deciding is your job; gathering is not.

Hard problems: think first. You are the strongest model in the session and you already hold the context, so a problem that looks hard is often one bounded look away from solved: a few files, one hypothesis, one test. Take that look. Send it to `specialist` when it turns into a long investigation, and put what you found into the brief so that the specialist does not start cold. Under `protect-lead`, skip the look and hand over the symptom.

## 2. Write a brief that stands alone

A worker sees only your brief, the repository, and the project's CLAUDE.md. It does not see this conversation. Most failed delegations are really thin briefs. Include:

```
Goal: <one or two sentences on what to produce and why it matters>
Context: <file paths you already know, the pattern to follow, relevant decisions already made>
Constraints: <what not to touch, libraries or style to use, compatibility needs>
Done when: <the check that must pass, or the observable result>
Return: <what you need back; the worker's default report format is usually enough>
```

Pass along paths and facts you already have, so that the worker does not pay to rediscover them. Do not paste large file contents into the brief; give the path.

Size the piece to the worker's turn cap: scout 20, runner 15, builder 40, specialist 80. A worker that hits its cap stops where it is: you get what it has said so far, marked partial, and you can resume it, but there is no final report. One component or a handful of files is a builder-sized piece; a whole module is several. Smaller pieces are also cheaper, because a worker re-reads its whole context on every call, so its cost grows with the square of its length.

For data work, say in the brief how the data should be handled: filter or aggregate with a script, print 50 lines or fewer, and write anything bigger to a file. A worker that prints raw logs or telemetry into its own context pays to re-read them on every later call.

Do not pass a `model` argument when calling these four workers. A per-call `model` overrides the model pinned in the worker's definition, which defeats the purpose. The one exception is the `lead-heavy` lean, where a long investigation goes to `specialist` with `model: "fable"`.

## 3. Run workers well

- Never do delegated work yourself as well. The most common way to lose the saving is to start a worker in the background and then carry out the same investigation or edit while you wait, which pays for the work twice. When your next step depends on the result, call the worker with `run_in_background: false` and wait. While a background worker runs, work only on something different.
- Launch independent pieces in parallel, in a single message. Typical shape: several scouts at once, then one builder per independent area.
- Batch questions. One scout brief asking five things pays one start-up cost; five briefs pay five.
- Never give two workers overlapping files to write. Split by file or directory, or run them one after the other.
- Sequence dependent work: scout, then you decide, then builder, then runner, then you review.
- Workers cannot spawn their own subagents, so give each one a piece it can finish alone.

## 4. Workflows and other fan-out

The same tiers apply to every agent you start: Workflow `agent()` stages, `Explore`, `general-purpose`, and anything else. An agent with no model set inherits yours, and a script that names `opus` for every stage is the most expensive thing this plugin has seen anyone do. A fan-out multiplies whatever choice you make, so make it deliberately.

- **Name a model for every stage.** Reading, extraction, and running: `haiku`. Building, integrating, reviewing, and verifying: `sonnet`. `opus` for at most one stage that is both hard and long, and never as the script's default. Under `lead-heavy`, no `opus` at all: leave the hard stage's model unset so that it inherits yours.
- **Use the pinned workers as stages** where they fit. `agentType: 'model-router:builder'` brings the Sonnet pin, the turn cap, and the working rules with it. The `specialist` worker brings an Opus pin, so under `lead-heavy` give that stage `model: 'fable'` or do not use it. Prefer `scout` to `Explore`, which inherits your model.
- **Keep the contract and the verdicts.** You write the interfaces and the acceptance checks that parallel builders work to, before the fan-out starts. When results conflict, or reviewers disagree, you decide. Those are the two places where the strongest model changes the outcome.
- **Size each agent to about 40 calls.** One component or a handful of files, never "implement section 5 completely". If context grows steadily, four 40-call agents re-read about a quarter as much as one 160-call agent, and they finish sooner because they run side by side.
- **Keep data out of context.** Agents filter or aggregate with a script and print 50 lines or fewer. Anything bigger goes to a file, and the path comes back.
- **Say the plan, then check it.** Before launching more than about five agents, tell the user in one line how many agents will run and on which models. After a large run, check it with `model-router:usage-audit`.

```js
// One builder per slice on Sonnet, each checked by a cheap verifier. The lead wrote CONTRACT first.
const slices = [ /* one component or a few files each */ ]
const results = await pipeline(
  slices,
  s => agent(buildBrief(s, CONTRACT), { agentType: 'model-router:builder' }),
  (r, s) => agent(verifyBrief(s, r), { model: 'sonnet', effort: 'low', schema: VERDICT })
)
```

## 5. Review, and look before you escalate

The saving disappears if you redo the work. Check it instead:

- For builder and specialist: read the changed files or the diff, confirm the verification they reported, and have `runner` run the check again when the change matters.
- For scout: spot-check the cited lines that your next decision depends on. Haiku is fast and usually right, but it can state a guess as a fact. Anything load-bearing gets a look.
- For runner: trust the pass or fail result and the quoted errors. Open the log file only if you need more.

If a result is wrong, send a short corrective brief back to the same worker naming the specific problem. When a worker is stuck:

1. `builder` fails twice at the same thing. Read its report and the failing code yourself, once, with a bound. Most of the time the cause is a gap in the brief or a wrong assumption in the spec, and you can see it quickly because you know what was meant. Fix the brief and send it back, fix the code directly if the fix is small, or hand it to `specialist` with your diagnosis if it needs a long grind.
2. `specialist` comes back PARTIAL or BLOCKED. Decide from its report: a corrected brief, a bounded attempt of your own, or a question to the user.

Two things to avoid: grinding on at your own rate once your bounded look has failed, and starting a second long worker on the same brief. Under `protect-lead`, skip the look in step 1 and send the work to `specialist` with what the attempts revealed.

## 6. When not to delegate

- The user asked you to do it yourself, or told you to stop delegating.
- The piece is below the thresholds for your lean.
- The piece needs the conversation's nuance, and writing that into a brief would cost more than doing the work.
- The change is security-sensitive, destructive, or outward-facing. Workers prepare; you and the user decide and execute.
- You are already on the cheapest tier that can do the job.

## 7. Tell the user what ran where

End your reply with one line such as `Delegated: scout x2, builder x1`. If the user wants proof of which models actually ran and what they used, run the `model-router:usage-audit` skill.

## If the pinned workers are not available

If `model-router:scout` and the others are not in your agent list (for example, this skill file was copied somewhere without the rest of the plugin), you can still route by passing `model` for a single call: use the built-in `Explore` agent with `model: "haiku"` for lookups, and `general-purpose` with `model: "sonnet"` for routine implementation. Put the matching working rules from this playbook into the brief, since those built-in agents do not carry them, and state a turn budget, since they have no cap.
