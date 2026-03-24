---
name: setup-augmentation
description: Scaffold a new augmentation workspace with memory, knowledge, and QMD. Use when the user wants to set up a new augmentation project or initialize the augmentation system in an existing workspace.
---

# Setup Augmentation

Scaffolds a complete augmentation workspace in the current directory. Creates the three-layer memory system (memory/, knowledge/, config/) and configures QMD for knowledge search.

## When to use

- User asks to "set up augmentation" or "initialize my assistant"
- User clones a new project and wants the augmentation workflow
- Current workspace is missing the augmentation structure (no `memory/` or `knowledge/` directories)

## Instructions

### 1. Check existing structure

Before creating anything, check if `memory/` or `knowledge/` already exist. If they do, ask the user if they want to overwrite or skip.

### 2. Create memory/ templates

Create the following files:

**`memory/user-profile.md`**
```markdown
---
name: user-profile
description: Who the user is, how to work with them, professional context
type: profile
updated: YYYY-MM-DD
---

# User Profile

## Identity
- **Name:** [Your name]
- **Company:** [Your company]
- **Role:** [Your role]
- **Timezone:** [Your timezone, e.g. America/Sao_Paulo]
- **Languages:** [pt-BR, en-US, etc]

## Professional Context
- **Area:** [e.g. Tech Lead, Product Manager, etc]
- **Main stack:** [technologies you work with]
- **Responsibilities:** [main responsibilities at work]

## Work Preferences
- **Communication style:** [direct/detailed, formal/informal]
- **Preferred hours:** [when you work best]
- **Favorite tools:** [editors, CLIs, etc]

## How to Help Me Best
- **Current priorities:** [what matters most right now]
- **Watch out for:** [things to be careful about]
- **Expectations:** [how you expect me to help]
```

**`memory/active-contexts.md`**
```markdown
---
name: active-contexts
description: Active contexts — projects, recurring activities, support, ongoing themes
type: context
updated: YYYY-MM-DD
---

# Active Contexts

Not everything is a project. A context is anything that demands recurring attention:
own projects, third-party support, investigations, routine responsibilities.

## [Context Name] (priority: high/medium/low)
- **Type:** project / support / investigation / routine
- **Status:** [current situation]
- **Goal:** [what you want to achieve]
- **Next steps:** [immediate actions]
```

**`memory/feedback-log.md`**
```markdown
---
name: feedback-log
description: Behavioral corrections and validated approaches
type: feedback
updated: YYYY-MM-DD
---

# Feedback Log

## Validated
- [Approaches and behaviors that worked well]

## Corrections
- [Behaviors to avoid]
```

**`memory/tools.md`**
```markdown
---
name: tools
description: Environment config — tools, MCP servers, CLIs and setup details
type: tools
updated: YYYY-MM-DD
---

# Tools & Environment

## QMD
- **CLI:** `qmd query`, `qmd search`, `qmd get`, `qmd multi-get`, `qmd status`
- **MCP:** tools `query`, `get`, `multi_get`, `status`
- **Collection:** `knowledge` → knowledge/
- **IMPORTANT:** After creating/modifying files in `knowledge/`, run `qmd update && qmd embed`

## MCP Servers
- **QMD** — knowledge search
- [Add other MCP servers you configure]

## Environment Notes
- **Editor:** [VS Code, Cursor, etc]
- **Terminal:** [zsh, bash, etc]
- **OS:** [macOS, Linux, Windows]
```

**`memory/references.md`**
```markdown
---
name: references
description: Links, resources and frequent references
type: references
updated: YYYY-MM-DD
---

# References

## Reference Projects
- **[Project Name]:** [URL] — [brief description]

## Frequent Documentation
- **[Tech/Framework]:** [URL] — [what you consult]

## Tools & Services
- **[Tool Name]:** [URL] — [what you use it for]
```

### 3. Create knowledge/ structure

Create these directories with template files:

**`knowledge/journal/_template.md`**
```markdown
---
title: Journal — YYYY-MM-DD
date: YYYY-MM-DD
tags: [journal]
---

## What happened

-

## What I thought

-

## Next steps

-
```

**`knowledge/meetings/_template.md`**
```markdown
---
title: Meeting — Title
date: YYYY-MM-DD
participants: []
tags: [meeting]
---

## Agenda

-

## Notes

-

## Action Items

- [ ]
```

**`knowledge/research/_template.md`**
```markdown
---
title: Research — Topic
date: YYYY-MM-DD
tags: [research]
---

## Context

Why I'm researching this.

## Findings

-

## Sources

-

## Conclusion

-
```

**`knowledge/decisions/_template.md`**
```markdown
---
title: ADR-NNN — Decision Title
date: YYYY-MM-DD
status: proposed | accepted | deprecated | superseded
tags: [decision]
---

## Context

What problem or need motivated this decision.

## Decision

What was decided.

## Alternatives Considered

-

## Consequences

What changes as a result of this decision.
```

**`knowledge/learnings/_template.md`**
```markdown
---
title: TIL — Title
date: YYYY-MM-DD
tags: [learning]
---

## What I Learned

-

## Context

How/where I discovered this.

## Application

When this is useful.
```

Also create `knowledge/notes/` as an empty directory (with a `.gitkeep` if needed).

### 4. Create .gitignore

```
memory/
!memory/*.template.md
config/
.cache/
.DS_Store
```

### 5. Create config/ directory

```bash
mkdir -p config
```

### 6. Set up QMD (if available)

Check if `qmd` is available on PATH:

```bash
qmd --version
```

If available:
```bash
qmd collection add knowledge knowledge/
qmd update && qmd embed
```

If not available, inform the user:
> QMD is not installed. Install it with `npm install -g @tobilu/qmd` and then run `qmd collection add knowledge knowledge/ && qmd update && qmd embed`.

### 7. After setup

Tell the user:
1. Edit `memory/user-profile.md` with your information
2. Configure `memory/active-contexts.md` with your current projects
3. If QMD was configured, your knowledge base is ready to use
4. Start capturing: journals, meetings, research, decisions, learnings

### Important

- Copy `.template.md` files as reference but create the actual `memory/` files WITHOUT the `.template` suffix
- Do NOT commit `memory/` files (they contain personal data) — the `.gitignore` handles this
- The `knowledge/` directory IS committed (templates and knowledge base content)
