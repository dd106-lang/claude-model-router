# model-router

A Claude Code plugin that keeps your expensive model on the thinking and sends the routine work to cheaper ones.

You run your session on Fable or Opus as usual. That model, the lead, plans the work, makes the decisions, and reviews the results. Everything else it hands to a worker pinned to a cheaper model. The worker does the job in its own context window and sends back a short report.

Delegation is the default, not a special case. The lead's allowance is the one that runs out first, so the plugin treats the lead's tokens as the scarce resource and the workers' as cheap. Escalation runs downward too: when the Sonnet builder gets stuck, the work goes to the Opus specialist rather than back up to the lead.

| Worker | Pinned model | What it does |
|---|---|---|
| `scout` | Haiku | Read-only lookups: find, trace, list, extract, and summarize across files, logs, docs, or web pages. Cites `file:line`. |
| `runner` | Haiku | Runs builds, tests, and scripts with long output. Reports pass or fail plus the relevant excerpt. |
| `builder` | Sonnet, medium effort | Routine implementation from a clear spec: features that follow existing patterns, tests, refactors, config, scripts, generated files and documents. |
| `specialist` | Opus, high effort | Hard, self-contained problems: unknown root causes, intricate algorithms, timing faults, protocol decoding. |

The saving comes from two places. Worker tokens are billed at the worker's rate instead of the lead's, and the files a worker reads never enter the lead's context, so the lead's own requests stay small for the rest of the session.

## How much it saves

**About a third less Fable usage on mixed work, which is roughly 1.5 times as much work from the same weekly Fable allowance (+46%). On writing-heavy work it is more than half, or about 2.3 times as much.**

Those figures come from running the same task twice with Fable 5.1 as the lead, once without the plugin and once with it (Claude Code 2.1.274, one run per arm, September 2026). "Usage" means tokens weighted by API list price, which is the closest public stand-in for how heavily each model draws on a plan.

| Task | Fable usage | All models combined |
|---|---|---|
| Write an 800-line unittest suite for two modules | 57% lower | 21% lower |
| Add a small feature across 6 files, about 250 lines | 16% lower | 4% higher |
| Trace a behaviour through an 8,800-line package | 7% lower | 4% higher |
| **All three together** | **32% lower** | **7% lower** |

Results were equivalent in both arms: every test suite passed, and the delegated test suite was the same size as the one Fable wrote itself. Wall-clock time was about the same, sometimes a minute longer with workers.

How to read this:

- The weekly figure is arithmetic on the measured reduction. Using 32% less Fable per task means the same allowance covers 1 / (1 - 0.32), about 1.46 times as many tasks. At 57% it is about 2.3 times. This applies when the Fable allowance is the limit you hit first. If you hit your overall plan limit first, use the combined column, about 7%.
- The saving tracks how much bulk writing and reading a task contains. Small tasks and reasoning-heavy investigations save little, because the lead still has to load its own context and do the thinking. No routing removes that fixed cost.
- These are single runs of three tasks, so treat the numbers as rough. Your own mix decides your result, and you can measure it with `/model-router:usage-audit`. The benchmark tasks and scripts are in `bench/` if you want to repeat them.
- They were measured with version 1.0. Version 1.1 lowers the thresholds so that more work goes down, and sends stuck work to the specialist instead of back to the lead. That should move the two weaker rows, but it has not been re-measured, so the table stands as the conservative number.

## What is in the plugin

- **Four subagents** with `model:` pinned in their definitions. Claude Code enforces the pin; it is a setting, and the lead is not merely asked to behave like a cheaper model.
- **A session-start hook** that puts a short delegation policy (about 950 tokens) into the lead's context. This is what makes delegation happen without being asked. The text is in `plugins/model-router/hooks/policy.md`.
- **`/model-router:route [task]`**: the full playbook, including how to split a task, how to write a brief, and how to review. The lead can load it by itself; you can also invoke it to plan a specific task.
- **`/model-router:usage-audit`**: reads your local transcripts and shows which models ran and what each one used. Use it to confirm that routing is working.

## Install

You need Claude Code 2.1.251 or later (`claude --version`). The audit needs Python 3.8 or later.

**From GitHub.** The repository is public, so there is nothing to sign in to and no access to request.

```bash
claude plugin marketplace add dd106-lang/claude-model-router
```

```bash
claude plugin install model-router@team-claude-tools
```

Inside an interactive Claude Code session the same two commands are `/plugin marketplace add dd106-lang/claude-model-router` and `/plugin install model-router@team-claude-tools`.

**From a folder or an unzipped copy:** give the path instead of the repository name.

```bash
claude plugin marketplace add /path/to/claude-model-router
```

**For a whole team repository:** add this to the project's `.claude/settings.json` and commit it. Teammates are offered the plugin when they open the project.

```json
{
  "extraKnownMarketplaces": {
    "team-claude-tools": { "source": { "source": "github", "repo": "dd106-lang/claude-model-router" } }
  },
  "enabledPlugins": { "model-router@team-claude-tools": true }
}
```

Start a new session after installing. Plugins load at session start. The plugin adds about 1,800 tokens to every session: the worker and skill descriptions plus the policy. `claude plugin details model-router@team-claude-tools` shows the inventory.

## Use

Work the way you normally do. The lead decides what to delegate, and when it delegated anything its reply ends with a line like `Delegated: scout x2, builder x1`.

- To plan a specific job around the workers: `/model-router:route add CSV export to the report module`
- To force a particular worker, mention it: `@"model-router:builder (agent)" add the missing unit tests`
- To stop delegation for a while, say so: "do this one yourself".

## Check that it works

Ask for an audit, or run `/model-router:usage-audit`. You can also run the script directly:

```bash
python3 plugins/model-router/skills/usage-audit/model_usage.py --since 24h
```

```text
MODEL                              ROLE       CALLS        IN   C.WRITE    C.READ       OUT      EST$
claude-fable-5-1                   lead          22        44    182.2k      2.8M     67.6k     $7.73
claude-haiku-4-5-20251001          subagent      10        82    102.5k    558.7k      6.6k     $0.22

Subagents:
  model-router:scout                   1 run(s)    10 calls    667.9k tokens   on claude-haiku-4-5-20251001
```

The Subagents block is the proof: each worker type is listed with the model id that Claude Code recorded for its API calls. The dollar column is API list price and is there to compare models with each other. It is not your bill; subscription plans are not metered per token.

## What to expect

- **Delegation is a decision the lead makes.** The policy makes it the default for suitable work, but it is not a guarantee. When it matters, name the worker.
- **Very small jobs stay with the lead.** Every worker starts by loading its own system prompt and tools: about 5 to 10 thousand tokens for scout and runner, and about 30 thousand for builder and specialist, at the worker's cheaper rate. That is cheap next to the lead's rate, so the bar is deliberately low: more than about 15 lines to write, more than about two files or 150 lines to read, or any command whose output runs past a few lines. Below that the lead does it itself, because the start-up cost would dominate.
- **The lead does not retry by hand.** If the builder fails twice, the work goes to the specialist. If the specialist fails, the lead reports the state and asks you, rather than grinding at its own rate. Taking over itself is reserved for judgment calls that need the conversation.
- **The lead must not redo delegated work.** In early testing the lead started a scout in the background and then did the same investigation itself while waiting, which paid for the work twice. The policy now forbids that and tells the lead to wait for results it depends on. If the audit shows workers running but no drop in lead usage, this is the first thing to look for.
- **Routing reduces the weight of your usage; it does not make usage free.** On a subscription, every model draws from the same plan. Depending on your plan, Fable may bill to usage credits instead of plan limits; the model picker says so when it does.
- **Only downward delegation saves anything.** If your session runs on Sonnet, the builder is the same price as you, and the policy tells the lead to do routine work itself. On Opus, the same is true of the specialist.
- **Cheap models make more mistakes.** The workers are told to cite what they read and to say "not found" instead of guessing, and the lead is told to spot-check anything it is about to rely on. Review still matters.

## Tune it

The workers are plain Markdown files in `plugins/model-router/agents/`. Change `model:` (`haiku`, `sonnet`, `opus`, `fable`, a full model id, or `inherit`) or `effort:` (`low` to `max`; Haiku ignores it), then bump `version` in `plugins/model-router/.claude-plugin/plugin.json` so that installed copies update. If scouts miss things in your codebase, moving `scout` to `sonnet` is the first change to try.

To turn off the always-on policy and delegate only when you ask, delete `plugins/model-router/hooks/hooks.json`.

Things that override the pinned models, in case the audit shows a worker on the wrong model:

- A `model` argument passed by the lead on a single call wins over the pin. The policy tells the lead not to pass one.
- `CLAUDE_CODE_SUBAGENT_MODEL` overrides the pins on Claude Code versions before 2.1.251, and on any version when `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` is set.
- An organization `availableModels` allowlist can exclude a model.

## Safety

The plugin cannot loosen anyone's permissions. Claude Code ignores `permissionMode`, `hooks`, and `mcpServers` in plugin subagents, and the workers do not set them. Your own permission prompts and settings apply to every worker. The workers are told not to commit, push, deploy, or delete unless the brief says so, and to treat text found in files and web pages as data. They cannot start subagents of their own, which keeps the cost of a delegation predictable.

The hook runs one command, `cat` on the policy file inside the plugin. The audit script only reads files under `~/.claude/projects` and prints a table. It sends nothing anywhere.

## Remove

```bash
claude plugin uninstall model-router@team-claude-tools
```

```bash
claude plugin marketplace remove team-claude-tools
```
