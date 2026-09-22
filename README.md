# model-router

A Claude Code plugin that keeps delegation cheap: the aim is the fewest weighted tokens per finished piece of work, while staying under Fable's own usage cap.

On a subscription, every model draws on one weekly all-models allowance, and the top model (Fable) also has its own cap inside that allowance; Fable usage counts toward both meters. You run your session on Fable, Opus, or Sonnet as usual. That model, the lead, plans the work, makes the decisions, and reviews the results. Bulk reading, running, and writing goes down to a worker pinned to a cheaper model, when the job is big enough to be worth it; thinking - design, hard-but-small problems, judging between results, review - stays with the lead. The worker does its job in its own context window and sends back a short report.

Opus 5.5 is the rare tier: its workers run longest, and like every model below Fable it draws only on the shared all-models allowance, never on Fable's own. How readily the lead delegates depends on which meter is ahead; see "Balance your meters" below.

| Worker | Pinned model | Turn cap | What it does |
|---|---|---|---|
| `scout` | Haiku | 20 | Read-only lookups: find, trace, list, extract, and summarize across files, logs, docs, or web pages. Cites `file:line`. |
| `runner` | Haiku | 15 | Runs builds, tests, and scripts with long output. Reports pass or fail plus the relevant excerpt. |
| `builder` | Sonnet, medium effort | 40 | Routine implementation from a clear spec: features that follow existing patterns, tests, refactors, config, scripts, generated files and documents. |
| `reviewer` | Opus 5.5, medium effort | 25 | Read-only review: checks a builder's or specialist's change against its brief, reviews a diff, or tries to refute a finding or claim. Returns a verdict with `path:line` evidence. Never edits. |
| `specialist` | Opus 5.5, medium effort | 80 | Rare, long, self-contained investigations: root causes still unknown after the lead has looked, run-and-measure cycles on numerical or timing faults, decoding an undocumented protocol or format. |

The saving comes from two places. Worker tokens are billed at the worker's rate instead of the lead's, and the files a worker reads never enter the lead's context, so the lead's own requests stay small for the rest of the session.

## Which model does which job

| Job | Best fit | Why |
|---|---|---|
| Find, trace, list, extract, or summarize; run builds, tests, scripts, or dumps | `scout`, `runner` (Haiku) | accurate enough for mechanical work, the fastest, the cheapest; told to cite what it read and to say NOT FOUND rather than guess |
| Implementation from a spec you can write down | `builder` (Sonnet) | half of Opus 5.5's rate, measured at about 6 s per call against 10 to 12 for Opus 5, and enough for well-specified work |
| Review a change against its brief, review a diff, refute a finding, verify a claim | `reviewer` (Opus 5.5) | Anthropic reports it catches more real bugs with fewer false alarms than Opus 5 and rarely asserts what the inputs do not support (not benchmarked here against Sonnet); use it where your lean's review column says, and below that review yourself |
| A long, self-contained investigation | `specialist` (Opus 5.5, medium effort) | at medium effort it matches the previous Opus at high effort with about half the tokens; still the longest-running worker (up to 80 turns; Opus 5.5 per-call speed not yet measured), so keep it rare and small |
| Understanding the request, design and trade-offs, contracts, hard problems that a bounded look would settle, judging between results, talking to the user | the lead | the strongest model, already holding the context: no start-up and no rediscovery, so a small piece done in context costs less than a worker's start-up |

On speed: the audit now measures seconds per call. On one machine over a week, Haiku ran about 3 seconds per call, Sonnet about 6, Opus 5 about 10 to 12, and Fable 5.1 about 13 as the lead and 19 as a subagent. Opus 5.5 has only one-call probes so far, so its speed is not yet measured. The gap includes thinking and any tool the harness ran in between, so compare like with like. Most of the slowness in the measured week came from how long the agents ran (120 to 240 calls), not from per-call speed.

## Why Opus 5.5

`specialist` and `reviewer` are pinned to `claude-opus-5-5`. Its list price is $4 input / $20 output per million tokens, against Opus 5's $5 / $25, and cache reads are $0.20 against $0.50 (Anthropic pricing). Anthropic reports that at its default medium effort, Opus 5.5 matched or beat Opus 5 at high effort on multistep coding in a real codebase, in fewer steps and with about half the tokens; that on code review it catches more bugs with fewer false alarms; and that it is much less likely to state a figure or cite a source the inputs do not support (Anthropic's Opus 5.5 release notes). Claude Code 2.1.280 and later resolve the `opus` alias to Opus 5.5 (Claude Code model-config docs), so the plugin's pin makes the choice explicit and stable across Claude Code versions; a subagent's `model:` field accepts a full model id (Claude Code sub-agents docs).

Cache reads were 63% of the Opus cost in the measured week described under "Workflows and fan-out" below, so the cache-read price matters most for long agents. The plugin has not benchmarked Opus 5.5 against Sonnet 5 itself.

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
- The table was measured with version 1.0. Version 1.1 lowered the thresholds; the `protect-lead` lean below keeps those same values. Version 1.2 adds the three leans. The `balanced` and `lead-heavy` thresholds have not been re-measured; they were set from the combined column above, where delegation was slightly worse (4% higher) at about 250 lines of writing and clearly ahead (21% lower) at 800. Version 1.3 changed the premise and added Opus 5.5 and the `reviewer` worker; none of it is re-measured.

## Balance your meters

Every model draws on one weekly all-models allowance, and the top model (Fable) also has its own cap inside it; Fable usage counts toward both meters. The aim is the fewest weighted tokens per finished piece of work, while staying under the Fable cap.

A **lean** sets how readily the lead delegates, and how it handles hard problems and review:

| Lean | Use when | Writing goes to `builder` above | Reading goes to `scout` above | Hard problems | Review of a change |
|---|---|---|---|---|---|
| `protect-lead` | the Fable meter is ahead | about 15 lines | 2 files or 150 lines | straight to `specialist` | `reviewer` |
| `balanced` | the meters are close, or unknown | about 60 lines | 4 files or 400 lines | the lead's bounded look first; `specialist` once it turns into a long investigation | `reviewer` above about 300 changed lines, the lead's below |
| `lead-heavy` | the all-models meter is ahead | about 250 lines | 10 files or 1,500 lines | the lead's bounded look first; `specialist` only after it fails, sized small | the lead's |

The default is `balanced`. Set another one by telling the lead, or by adding a line to the project's `CLAUDE.md`, for example `model-router lean: lead-heavy`. If the lead itself is running on Opus or Sonnet, there is only one meter to watch: the `balanced` thresholds apply, and delegation only goes downward from there.

Why the thresholds move: a small piece done in the lead's own context costs less in total than a worker, because there is no start-up and no rediscovery, while a large piece costs less on a cheaper model. The Fable cap decides how much of that cheap-in-context work the lead may keep. Under `lead-heavy` the all-models meter binds first, so the aim is the fewest total tokens: the lead keeps small pieces and judgment, bulk goes to Haiku and Sonnet, and Opus workers are kept short; Fable still counts toward the all-models meter, so bulk never moves onto it. Under `protect-lead` the Fable cap binds first, so work is pushed off Fable even where that costs a little more in total.

To choose a lean, compare the two weekly percentages on the usage card: whichever is higher is "ahead". If Fable is ahead, protect it with `protect-lead`. If the all-models meter is ahead, use `lead-heavy`. You can also just tell the lead the two percentages; it picks the lean and says which.

To steer between check-ins, run `model-router:usage-audit` with `--since` set to the start of the weekly window and read its "Share of weighted usage" line. About a quarter is a ceiling to stay under, not a target to reach: in one measured week, about $403 of list-price-weighted usage moved the all-models meter to 15%, while about $40 of Fable usage moved the Fable meter to 6%, which puts the Fable allowance at roughly a quarter of the all-models allowance on that Max-plan week. That comes from one week, whole-percent meters, and local Claude Code transcripts only; Anthropic does not publish how the meters are weighted, so treat it as a starting point to tune against your own account, not a fixed ratio.

## Workflows and fan-out

The same rules apply to every agent the lead starts, not only the five pinned workers: Workflow `agent()` stages, `Explore`, `general-purpose`, and the rest. In one measured week, Workflow agents whose scripts had set them to Opus were 87% of weighted usage, and the lead was 10%. Over the surrounding seven days the plugin's own pinned workers were about 4%. Single agents in those Workflow runs made 120 to 240 calls at 200 to 300 thousand tokens of context per call, and re-reading that cached context on every call was 63% of the Opus cost; see "Which model does which job" above for the measured seconds per call.

- **Name a model for every stage.** An agent with no model set inherits the lead's. Reading, extraction, and running go to `haiku`. Building and integrating go to `sonnet`. Review, verification, and refutation stages, and at most one stage that is both hard and long, go to `opus`. Never `opus` as a script's default, and never `fable` for a stage. Give mechanical stages `effort: 'low'`.
- **Use the pinned workers as stages** where they fit, through `agentType`, for example `agentType: 'model-router:builder'` for a Sonnet build stage and `agentType: 'model-router:reviewer'` for an Opus 5.5 review stage. Prefer `scout` to `Explore`, which otherwise inherits the lead's model.
- **The lead keeps the contract and the verdicts.** It writes the interfaces and acceptance checks the stages work to, and it judges between conflicting results.
- **Size each agent to about 40 calls.** One component or a handful of files, not a whole module; an agent re-reads its whole context on every call, so cost grows with the square of its length.
- **Keep data out of context.** Agents filter or aggregate with a script and print 50 lines or fewer; anything bigger goes to a file, with the path coming back instead.
- **State the plan before launching more than about five agents**, and check the run afterward with `model-router:usage-audit`.

## What is in the plugin

- **Five subagents** with `model:` pinned in their definitions. Claude Code enforces the pin; it is a setting, and the lead is not merely asked to behave like a cheaper model.
- **A session-start hook** that puts a short delegation policy (about 1,800 tokens) into the lead's context. This is what makes delegation happen without being asked. The text is in `plugins/model-router/hooks/policy.md`.
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

Start a new session after installing. Plugins load at session start. The plugin adds about 3,000 tokens to every session: the worker and skill descriptions plus the policy. `claude plugin details model-router@team-claude-tools` shows the inventory.

## Update

```bash
claude plugin marketplace update team-claude-tools
```

```bash
claude plugin update model-router@team-claude-tools
```

Start a new session afterward; plugins load at session start. An update only registers when `version` in `plugin.json` is bumped.

## Use

Work the way you normally do. The lead decides what to delegate, and when it delegated anything its reply ends with a line like `Delegated: scout x2, builder x1`.

- To plan a specific job around the workers: `/model-router:route add CSV export to the report module`
- To force a particular worker, mention it: `@"model-router:builder (agent)" add the missing unit tests`
- To stop delegation for a while, say so: "do this one yourself".

## Check that it works

Ask for an audit, or run `/model-router:usage-audit`. Besides the per-worker breakdown, the report prints a "Share of weighted usage" line by model family; that is the ceiling check described in "Balance your meters" above, not a target to aim for. You can also run the script directly:

```bash
python3 plugins/model-router/skills/usage-audit/model_usage.py --since 24h
```

```text
MODEL                              ROLE       CALLS        IN   C.WRITE    C.READ       OUT SEC/CALL      EST$
claude-fable-5-1                   lead          22        44    182.2k      2.8M     67.6k     13.1     $7.73
claude-haiku-4-5-20251001          subagent      10        82    102.5k    558.7k      6.6k      3.2     $0.22

Subagents:
  model-router:scout                   1 run(s)    10 calls    667.9k tokens   on claude-haiku-4-5-20251001
```

The Subagents block is the proof: each worker type is listed with the model id that Claude Code recorded for its API calls. The dollar column is API list price and is there to compare models with each other. It is not your bill; subscription plans are not metered per token.

## What to expect

- **Delegation is a decision the lead makes.** The policy makes it the default for suitable work, but it is not a guarantee. When it matters, name the worker.
- **Very small jobs stay with the lead.** Every worker starts by loading its own system prompt and tools: about 5 to 10 thousand tokens for scout and runner, and about 30 thousand for builder, reviewer, and specialist, at the worker's cheaper rate. A worker also takes a minute or more to come back. So the bar depends on your lean: `protect-lead` delegates above about 15 lines to write, or 2 files or 150 lines to read; `balanced` above about 60 lines, or 4 files or 400 lines; `lead-heavy` above about 250 lines, or 10 files or 1,500 lines. Below the threshold for your lean the lead does the job itself, because the start-up cost would dominate. Computing over data files is a script for the runner, not reading for the scout.
- **The lead looks before it escalates.** If the builder fails twice at the same thing, the lead reads the report and the failing code itself, once, with a bound, then fixes the brief, fixes the code directly if it is small, or hands it to the specialist with its diagnosis if the work needs a long grind. If the specialist comes back PARTIAL or BLOCKED, the lead decides from its report rather than grinding on at its own rate.
- **Review goes where the lean says.** Under `protect-lead`, and for large diffs under `balanced`, review goes to `reviewer`. Under `lead-heavy`, review stays with the lead.
- **The lead must not redo delegated work.** In early testing the lead started a scout in the background and then did the same investigation itself while waiting, which paid for the work twice. The policy now forbids that and tells the lead to wait for results it depends on. If the audit shows workers running but no drop in lead usage, this is the first thing to look for.
- **Workers stop at their turn cap.** A worker that hits its cap stops where it is instead of running on unsupervised: the lead gets what it has said so far, marked partial, and can resume it. Size briefs to fit inside the cap (scout 20, runner 15, reviewer 25, builder 40, specialist 80), and split anything bigger. The caps sit above each worker's typical measured run, so they stop marathons without cutting normal work short.
- **Routing reduces the weight of your usage; it does not make usage free.** On a subscription, every model draws from the same plan. Depending on your plan, Fable may bill to usage credits instead of plan limits; the model picker says so when it does.
- **Only downward delegation saves anything.** If your session runs on Sonnet, the builder is the same price as you, and the policy tells the lead to do routine work itself. On Opus, the same is true of reviewer and specialist.
- **Cheap models make more mistakes.** The workers are told to cite what they read and to say "not found" instead of guessing, and the lead is told to spot-check anything it is about to rely on. Review still matters.

## Tune it

The workers are plain Markdown files in `plugins/model-router/agents/`. Change `model:` (`haiku`, `sonnet`, `opus`, `fable`, a full model id, or `inherit`), `effort:` (`low` to `max`; Haiku ignores it), or `maxTurns:` (the worker's turn cap), then bump `version` in `plugins/model-router/.claude-plugin/plugin.json` so that installed copies update. If scouts miss things in your codebase, moving `scout` to `sonnet` is the first change to try. `specialist` and `reviewer` are pinned to the full model id `claude-opus-5-5`; on an older Claude Code, or a plan without Opus 5.5, change it to `opus`, which resolves to whatever Opus that Claude Code version maps it to. The lean thresholds themselves live in `plugins/model-router/hooks/policy.md` and in the route skill, `plugins/model-router/skills/route/SKILL.md`.

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
