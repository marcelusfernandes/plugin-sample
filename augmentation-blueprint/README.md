# Augmentation Blueprint

Assistente pessoal autônomo com memória persistente e gestão de conhecimento via QMD.

## O que este plugin inclui

### Rules

| Rule | Descrição |
|------|-----------|
| `soul` | Identidade, personalidade e limites do assistente |
| `augmentation-manual` | Workflow operacional — modelo de memória em três camadas, QMD, protocolo capture-first |

### Skills

| Skill | Descrição |
|-------|-----------|
| `setup-augmentation` | Cria a estrutura de workspace (memory/, knowledge/, config/) |
| `memory-curator` | Decide onde salvar informação (hot memory vs cold knowledge) |
| `researcher` | Busca profunda no QMD + web |
| `m365-assistant` | Integração com Microsoft 365 (email, calendar, Teams, SharePoint) |

## Como funciona

O sistema organiza informação em três camadas:

- **memory/** — Verdade atual (hot). Lido em toda sessão. Perfil, contextos ativos, feedback, tools.
- **knowledge/** — Base de conhecimento (cold). Indexado pelo QMD. Journals, meetings, research, decisions, learnings.
- **config/** — Credenciais e acessos (gitignored).

O assistente lê `memory/` no início de cada sessão, busca em `knowledge/` via QMD quando precisa de histórico, e persiste informação nova nos lugares certos.

## Quick Start

1. Instale o plugin no Cursor (Settings > Plugins > cole o link do repositório)
2. Peça ao assistente: **"set up augmentation"** — a skill `setup-augmentation` cria toda a estrutura
3. Edite `memory/user-profile.md` com suas informações
4. Instale QMD: `npm install -g @tobilu/qmd`
5. Configure a collection: `qmd collection add knowledge knowledge/ && qmd update && qmd embed`

## Princípio

> Capture first, organize second. O QMD encontra o que você precisa — mesmo com organização imperfeita.
