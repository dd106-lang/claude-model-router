---
name: usage-audit
description: Shows which Claude models actually ran and how many tokens each used, split into the lead and its subagents, for the current session or a time window. Reads the local Claude Code transcripts. Use to check that delegation to cheaper models is really happening, or when the user asks where their tokens or usage went by model.
argument-hint: "[session | latest | 24h | 7d | all] [project-name]"
---

# Audit which models ran

Request from the user, if any: $ARGUMENTS

A model cannot reliably report which model it is, and a lead saying "I used Sonnet for that" proves nothing. Claude Code records the model id and token usage of every API call in its local transcripts, including each subagent's. The bundled script reads those files, so its answer is evidence.

## Run it

The script needs Python 3.8 or later and nothing else. Try `python3` first, then `python`, then `py -3` on Windows.

Pick the scope from the request:

| The user wants | Command |
|---|---|
| This session (the default) | `python3 "${CLAUDE_SKILL_DIR}/model_usage.py" --session ${CLAUDE_SESSION_ID}` |
| The most recent session on this machine | `python3 "${CLAUDE_SKILL_DIR}/model_usage.py" --session latest` |
| A time window | `python3 "${CLAUDE_SKILL_DIR}/model_usage.py" --since 24h` (also `12h`, `7d`, or an ISO date) |
| One project only | add `--project <part of the folder name>` |
| Everything on disk | `python3 "${CLAUDE_SKILL_DIR}/model_usage.py" --all` |

Add `--json` if you need to work with the numbers. If the session id above did not get filled in, use `--session latest`.

The current session's numbers lag a little, because a call is written to the transcript when it finishes. Subagents that are still running will be incomplete.

## Read the output

- Each row is one model in one role. `lead` is the main conversation; `subagent` is everything that was delegated.
- The **Subagents** block lists each worker type, how many times it ran, and the model it ran on. This is where you confirm that `model-router:scout` and `model-router:runner` ran on Haiku, `model-router:builder` on Sonnet, and `model-router:reviewer` and `model-router:specialist` on Opus 5.5 (`claude-opus-5-5`).
- **Share of weighted usage** splits list-price-weighted usage by model family, lead and subagents together. Fable's share is bounded by its own cap: in one measured Max-plan week the Fable allowance came out at roughly a quarter of the all-models allowance (one week, whole-percent meters; tune against your own account), so a Fable share above about a quarter means the Fable meter will run out first (lean `protect-lead`), and a share well below it with Opus taking most of the rest means long Opus loops are doing the lead's thinking (lean `lead-heavy`, and check that Workflow scripts name their models). Run it with `--since` set to the start of the current weekly window. The share is a ceiling to stay under, not a target to reach: Fable usage counts toward the all-models meter too.
- **SEC/CALL** is measured speed: the mean gap between one API call's transcript entry and the entry before it, so it includes the model's thinking and any tool the harness ran in between. Compare models with each other on the same kind of work. On one machine over a week: Haiku about 3 s, Sonnet about 6 s, Opus 5 about 10 to 12 s, Fable 5.1 about 13 s as the lead and 19 s as a subagent; Opus 5.5 not yet measured.
- **Output tokens produced by models cheaper than the lead** is the quickest health check. If it is near zero over a working session, the lead is doing everything itself.
- The dollar figures are API list prices, used to compare models with each other. Subscription plans are not billed per token, so present them as relative weight and never as the user's bill.

## Report back

Tell the user, briefly:

1. Which model led, and which models the subagents ran on. Note whether `opus` workers ran on `claude-opus-5-5` or on an older Opus id.
2. The share of output tokens that ran on cheaper models, and the rough saving the script estimated.
3. The share of weighted usage by model family, and which lean it points to.
4. One observation, if there is one. Examples: a worker type that ran on the lead's model (it was called with a `model` override, or the pinned definitions are not installed); `workflow-subagent`, `Explore`, or `general-purpose` runs on Opus or on the lead's model, which means a fan-out did not name its models; one agent type taking most of the tokens; many tiny delegations where the fixed start-up cost outweighs the saving; no delegation at all in a session full of routine work.

Keep the script's caveat: the saving assumes another model would have used the same number of tokens, which is only roughly true.

## If the script cannot run

If Python is not available, do the same thing by hand on a small scope. Transcripts are under `~/.claude/projects/<project>/<session>.jsonl`, and subagent transcripts are under `<session>/subagents/`. Each line with `"type": "assistant"` has `message.model` and `message.usage`. Several lines share one `requestId`; count each `requestId` once and keep the largest `output_tokens`. The format is internal to Claude Code and can change, so if the fields are missing, say so instead of guessing.
