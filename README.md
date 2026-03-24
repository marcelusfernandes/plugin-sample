# AI CoE — Cursor Plugins

Plugins oficiais do time para o Cursor. Rules, skills e o Augmentation Blueprint.

## Plugins disponíveis

### [Augmentation Blueprint](./augmentation-blueprint)

Assistente pessoal autônomo com memória persistente e gestão de conhecimento via QMD.

- **Rules:** Soul (identidade do assistente) + Manual de Augmentation (workflow operacional)
- **Skills:** Setup, Memory Curator, Researcher, M365 Assistant
- **[Detalhes →](./augmentation-blueprint/README.md)**

### [AI CoE Plugins](./ai-coe-plugins)

Rules de coding standards e skill de code review para o time.

- **Rules:** `prefer-const`, `meaningful-names`
- **Skills:** `code-reviewer`

## Como instalar

1. No Cursor, vá em **Settings > Plugins** (aba "teams")
2. Cole o link do repositório:
   ```
   https://github.com/marcelusfernandes/plugin-sample
   ```
3. Selecione os plugins que deseja instalar
4. Os rules e skills ficam disponíveis automaticamente

## Pré-requisitos

- [Cursor](https://cursor.com) (editor)
- [Node.js](https://nodejs.org) >= 22 ou [Bun](https://bun.sh) >= 1.0 (para QMD)
- [QMD](https://github.com/tobi/qmd) — `npm install -g @tobilu/qmd` (para o Augmentation Blueprint)

## Estrutura do repositório

```
├── .cursor-plugin/
│   └── marketplace.json           # Manifesto do marketplace
├── augmentation-blueprint/        # Plugin: Augmentation Blueprint
│   ├── .cursor-plugin/
│   │   └── plugin.json
│   ├── rules/
│   │   ├── soul.mdc
│   │   └── augmentation-manual.mdc
│   ├── skills/
│   │   ├── setup-augmentation/
│   │   ├── memory-curator/
│   │   ├── researcher/
│   │   └── m365-assistant/
│   └── README.md
├── ai-coe-plugins/                # Plugin: Coding Standards
│   ├── .cursor-plugin/
│   │   └── plugin.json
│   ├── rules/
│   ├── skills/
│   └── assets/
└── README.md
```

## License

MIT
