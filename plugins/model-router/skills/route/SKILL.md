---
name: route
description: Multi-model delegation playbook. Protects the lead model's tokens (Fable or Opus) by keeping it on planning and review and pushing the work down to cheaper pinned workers - scout and runner on Haiku, builder on Sonnet, specialist on Opus. Use when the user asks to save tokens or usage, to delegate, or to use subagents or cheaper models, and when starting a multi-step coding, file-generation, or research task that contains routine work.
argument-hint: "[task to plan and delegate]"
---

# Route the work away from the lead

Task from the user, if one was given: $ARGUMENTS

If no task was given, apply this playbook to the work already under way in the conversation.

The idea is simple. You, the lead, are the most expensive model in the session, and your allowance is the one that runs out first. Every file you read and every line you write is billed at your rate, and it stays in your context for the rest of the session. Workers run on cheaper models in their own context windows and hand back a short report. So you spend your tokens where they change the outcome: understanding what the user wants, deciding how to do it, and checking that it was done right. Everything else goes down.

Delegating is the default. Doing it yourself is the exception, and it needs a reason.

## 1. Split the task

Break the work into pieces and label each piece with one of these:

| Piece looks like | Send to | Model |
|---|---|---|
| Find, trace, list, extract, or summarize across files, logs, docs, or web pages | `model-router:scout` | Haiku |
| Run a build, test suite, script, or dump | `model-router:runner` | Haiku |
| Build something whose spec you can write down: a feature that follows existing patterns, tests, a mechanical refactor, config, a script, a data conversion, a generated document or report | `model-router:builder` | Sonnet |
| A hard, self-contained problem: unknown root cause, intricate algorithm or numerical code, timing or concurrency, protocol or binary decoding, or something builder failed at twice | `model-router:specialist` | Opus |
| Unclear requirements, architecture and trade-offs, security-sensitive changes, destructive or outward-facing actions, final review, talking with the user | You | Lead |

Three checks before you delegate a piece:

- **Is the worker actually cheaper than you?** The order is Haiku, then Sonnet, then Opus, then Fable. When you are the top tier, every worker is cheaper and there is nothing to weigh. If you are running on Opus, `specialist` is lateral, so use it only to keep a long investigation out of your context. If you are on Sonnet, do routine implementation yourself and use only scout and runner.
- **Is the piece worth a worker?** Starting one costs roughly 5 to 10 thousand tokens for scout and runner, and about 30 thousand for builder and specialist, all at the worker's cheaper rate. That is cheap next to your own rate, so set the bar low: delegate writing above about 15 lines, reading above about two files or 150 lines you have not already read, and any command whose output runs past a few lines. Below that, do it yourself.
- **Can you write the spec?** If you cannot say what "done" means, the piece is not ready to delegate. Do the thinking first, or send a scout to gather what you need in order to decide. Deciding is your job; gathering is not.

Do not reason your way into a hard problem just to size it up. Working out how bad a bug is costs nearly as much as fixing it, and it is billed at your rate. Hand the symptom to `specialist` and let it do both.

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
- Batch questions. One scout brief asking five things pays one start-up cost; five briefs pay five.
- Never give two workers overlapping files to write. Split by file or directory, or run them one after the other.
- Sequence dependent work: scout, then you decide, then builder, then runner, then you review.
- Workers cannot spawn their own subagents, so give each one a piece it can finish alone.

## 4. Review, and escalate downward

The saving disappears if you redo the work. Check it instead:

- For builder and specialist: read the changed files or the diff, confirm the verification they reported, and have `runner` run the check again when the change matters.
- For scout: spot-check the cited lines that your next decision depends on. Haiku is fast and usually right, but it can state a guess as a fact. Anything load-bearing gets a look.
- For runner: trust the pass or fail result and the quoted errors. Open the log file only if you need more.

If a result is wrong, send a short corrective brief back to the same worker naming the specific problem. Escalation runs downward, not back up to you:

1. `builder` fails twice at the same thing, so hand it to `specialist` along with what those attempts revealed.
2. `specialist` fails, so report the state to the user and ask how to proceed.

Take the work over yourself only when the blocker is a judgment call that needs this conversation. Retrying by hand at your own rate is the most expensive way to finish anything.

## 5. When not to delegate

- The user asked you to do it yourself, or told you to stop delegating.
- The piece needs the conversation's nuance, and writing that into a brief would cost more than doing the work.
- The change is security-sensitive, destructive, or outward-facing. Workers prepare; you and the user decide and execute.
- You are already on the cheapest tier that can do the job.

## 6. Tell the user what ran where

End your reply with one line such as `Delegated: scout x2, builder x1`. If the user wants proof of which models actually ran and what they used, run the `model-router:usage-audit` skill.

## If the pinned workers are not available

If `model-router:scout` and the others are not in your agent list (for example, this skill file was copied somewhere without the rest of the plugin), you can still route by passing `model` for a single call: use the built-in `Explore` agent with `model: "haiku"` for lookups, and `general-purpose` with `model: "sonnet"` for routine implementation or `model: "opus"` for hard problems. Put the matching working rules from this playbook into the brief, since those built-in agents do not carry them.
