# Augmentation Blueprint — Cursor Plugin

Assistente pessoal autônomo com memória persistente e gestão de conhecimento via QMD.

## Como instalar

1. No Cursor, vá em **Settings > Plugins** (aba "teams")
2. Cole o link do repositório:
   ```
   https://github.com/marcelusfernandes/plugin-sample
   ```
3. O plugin será instalado e ficará disponível automaticamente

## O que inclui

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

## Quick Start

1. Instale o plugin no Cursor
2. Peça ao assistente: **"set up augmentation"**
3. Edite `memory/user-profile.md` com suas informações
4. Instale QMD: `npm install -g @tobilu/qmd`
5. Configure: `qmd collection add knowledge knowledge/ && qmd update && qmd embed`

## Como funciona

O sistema organiza informação em três camadas:

- **memory/** — Verdade atual (hot). Lido em toda sessão. Perfil, contextos ativos, feedback, tools.
- **knowledge/** — Base de conhecimento (cold). Indexado pelo QMD. Journals, meetings, research, decisions, learnings.
- **config/** — Credenciais e acessos (gitignored).

## Pré-requisitos

- [Cursor](https://cursor.com)
- [Node.js](https://nodejs.org) >= 22 ou [Bun](https://bun.sh) >= 1.0
- [QMD](https://github.com/tobi/qmd) — `npm install -g @tobilu/qmd`

## Estrutura

```
├── .cursor-plugin/
│   └── marketplace.json
├── augmentation-blueprint/
│   ├── .cursor-plugin/plugin.json
│   ├── rules/
│   │   ├── soul.mdc
│   │   └── augmentation-manual.mdc
│   ├── skills/
│   │   ├── setup-augmentation/
│   │   ├── memory-curator/
│   │   ├── researcher/
│   │   └── m365-assistant/
│   └── README.md
└── README.md
```

## License

MIT
