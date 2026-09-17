---
name: route
description: Multi-model delegation playbook. Keeps the expensive lead model (Fable or Opus) on planning and review, and routes well-defined work to cheaper pinned workers - scout and runner on Haiku, builder on Sonnet, specialist on Opus. Use when the user asks to save tokens or usage, to delegate, or to use subagents or cheaper models, and when starting a multi-step coding, file-generation, or research task that contains routine work.
argument-hint: "[task to plan and delegate]"
---

# Route work to the cheapest model that can do it well

Task from the user, if one was given: $ARGUMENTS

If no task was given, apply this playbook to the work already under way in the conversation.

The idea is simple. You, the lead, are the most expensive model in the session. Every file you read and every line you write is billed at your rate, and it stays in your context for the rest of the session. Workers run on cheaper models in their own context windows and hand back a short report. So you spend your tokens where they change the outcome: understanding what the user wants, deciding how to do it, and checking that it was done right.

## 1. Split the task

Break the work into pieces and label each piece with one of these:

| Piece looks like | Send to | Model |
|---|---|---|
| Find, trace, list, extract, or summarize across more than two or three files, logs, docs, or web pages | `model-router:scout` | Haiku |
| Run a build, test suite, script, or dump whose output will be long or noisy | `model-router:runner` | Haiku |
| Build something whose spec you can write down: a feature that follows existing patterns, tests, a mechanical refactor, config, a script, a data conversion, a generated document or report | `model-router:builder` | Sonnet |
| A hard, self-contained problem: unknown root cause, intricate algorithm or numerical code, timing or concurrency, protocol or binary decoding, or something builder failed at twice | `model-router:specialist` | Opus |
| Unclear requirements, architecture and trade-offs, security-sensitive changes, destructive or outward-facing actions, final review, talking with the user | You | Lead |

Three checks before you delegate a piece:

- **Is the worker actually cheaper than you?** The order is Haiku, then Sonnet, then Opus, then Fable. If you are running on Sonnet, builder saves nothing, so do routine work yourself and use only scout and runner. If you are on Opus, specialist saves nothing. A same-tier worker is still useful when the point is to keep a long investigation or bulky output out of your context.
- **Is the piece big enough?** Starting a worker has a fixed cost, because it loads its own system prompt and tools: roughly 5 to 10 thousand tokens for scout and runner, and about 30 thousand for builder and specialist, at the worker's cheaper rate. Judge the piece by volume, and not by how few tool calls it would take you, since you can write hundreds of lines in a single call and every one of them is billed at your output rate. Delegate writing above about 40 lines of code, tests, or document text. Delegate reading above about five files or 500 lines that you have not read yet. Below that, do it yourself.
- **Can you write the spec?** If you cannot say what "done" means, the piece is not ready to delegate. Do the thinking first, or use scout to gather what you need to decide.

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

Do not pass a `model` argument when calling these four workers. A per-call `model` overrides the model pinned in the worker's definition, which defeats the purpose.

## 3. Run workers well

- Never do delegated work yourself as well. The most common way to lose the saving is to start a worker in the background and then carry out the same investigation or edit while you wait, which pays for the work twice. When your next step depends on the result, call the worker with `run_in_background: false` and wait. While a background worker runs, work only on something different.
- Launch independent pieces in parallel, in a single message. Typical shape: several scouts at once, then one builder per independent area.
- Never give two workers overlapping files to write. Split by file or directory, or run them one after the other.
- Sequence dependent work: scout, then you decide, then builder, then runner, then you review.
- Workers cannot spawn their own subagents, so give each one a piece it can finish alone.

## 4. Review instead of redoing

The saving disappears if you redo the work. Check it instead:

- For builder and specialist: read the changed files or the diff, confirm the verification they reported, and run the check yourself when it is cheap and the change matters.
- For scout: spot-check the cited lines that your next decision depends on. Haiku is fast and usually right, but it can state a guess as a fact. Anything load-bearing gets a look.
- For runner: trust the pass or fail result and the quoted errors. Open the log file only if you need more.

If a result is wrong, send a short corrective brief back to the same worker with the specific problem. After two failed attempts at the same thing, escalate: builder to specialist, specialist to you.

## 5. When not to delegate

- The user asked you to do it yourself, or told you to stop delegating.
- The piece needs the conversation's nuance, and writing that into a brief would cost more than doing the work.
- The change is security-sensitive, destructive, or outward-facing. Workers prepare; you and the user decide and execute.
- You are already on the cheapest tier that can do the job.

## 6. Tell the user what ran where

End your reply with one line such as `Delegated: scout x2, builder x1`. If the user wants proof of which models actually ran and what they used, run the `model-router:usage-audit` skill.

## If the pinned workers are not available

If `model-router:scout` and the others are not in your agent list (for example, this skill file was copied somewhere without the rest of the plugin), you can still route by passing `model` for a single call: use the built-in `Explore` agent with `model: "haiku"` for lookups, and `general-purpose` with `model: "sonnet"` for routine implementation or `model: "opus"` for hard problems. Put the matching working rules from this playbook into the brief, since those built-in agents do not carry them.
