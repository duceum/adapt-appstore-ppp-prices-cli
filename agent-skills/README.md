# Agent skills

Drop-in instructions that teach a coding agent to drive `ppp-pricing` correctly —
including the parts it would otherwise get wrong: always previewing before applying,
and asking about existing subscribers before changing a subscription price.

Install the CLI first:

```
uv tool install appstore-ppp-prices
```

## Claude Code

Copy the skill directory into your skills folder — `~/.claude/skills/` for every
project, or `.claude/skills/` inside one repository:

```
mkdir -p ~/.claude/skills
curl -fsSL https://raw.githubusercontent.com/duceum/appstore-ppp-pricing-agent-skill/main/agent-skills/claude-code/appstore-ppp-pricing/SKILL.md \
  --create-dirs -o ~/.claude/skills/appstore-ppp-pricing/SKILL.md
```

It activates on its own when you ask for anything about regional App Store prices, or
explicitly with `/appstore-ppp-pricing`.

## Cursor

Project rules live in `.cursor/rules/`:

```
curl -fsSL https://raw.githubusercontent.com/duceum/appstore-ppp-pricing-agent-skill/main/agent-skills/cursor/appstore-ppp-pricing.mdc \
  --create-dirs -o .cursor/rules/appstore-ppp-pricing.mdc
```

The rule is `alwaysApply: false`, so Cursor pulls it in when the conversation is about
pricing rather than loading it into every request.

## Codex, and most other agents

`AGENTS.md` in your repository root is read by OpenAI Codex, and also by GitHub Copilot,
Cursor, Aider, Jules, VS Code and Devin. Append the section rather than overwriting
whatever you already have there:

```
curl -fsSL https://raw.githubusercontent.com/duceum/appstore-ppp-pricing-agent-skill/main/agent-skills/codex/AGENTS.md \
  >> AGENTS.md
```

## Why a skill and not just `--help`

`--help` lists the flags. It does not tell an agent the two things that actually matter:

- **Apply is irreversible and hits real customers** in up to 174 territories. The skill
  makes `--dry-run` → show → confirm → apply a hard sequence, so an agent does not go
  straight to applying because you said "just do it".
- **A subscription price change hits existing subscribers by default.** `--preserved`
  grandfathers them. An agent that misses this can trigger churn across your whole
  subscriber base. The skill makes it a question to ask before applying, not a flag to
  discover afterwards.

All three files also tell the agent never to read or echo your `.p8` key.
