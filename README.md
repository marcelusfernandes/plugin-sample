# Plugin Sample

Plugin de exemplo para o Cursor, demonstrando como estruturar e distribuir plugins para times.

## O que este plugin inclui

### Rules

| Rule | Descrição |
|------|-----------|
| `prefer-const` | Prefira `const` em vez de `let` para variáveis que não são reatribuídas |
| `meaningful-names` | Use nomes significativos e descritivos para variáveis, funções e classes |

### Skills

| Skill | Descrição |
|-------|-----------|
| `code-reviewer` | Revisa código buscando boas práticas, bugs potenciais e melhorias |

## Estrutura

```
plugin-sample/
├── .cursor-plugin/
│   └── plugin.json        # Manifesto do plugin (obrigatório)
├── rules/
│   ├── prefer-const.mdc
│   └── meaningful-names.mdc
├── skills/
│   └── code-reviewer/
│       └── SKILL.md
├── assets/
│   └── logo.svg
└── README.md
```

## Como usar no seu time

1. Vá em **Cursor Settings > Plugins** (aba "teams")
2. Cole o link do repositório no campo **"Search or Paste Link"**:
   ```
   https://github.com/marcelusfernandes/plugin-sample
   ```
3. O plugin será instalado e ficará disponível para todos do time

## Como criar seu próprio plugin

1. Use este repo como template
2. Edite `.cursor-plugin/plugin.json` com os dados do seu plugin
3. Adicione suas rules em `rules/` (arquivos `.mdc`)
4. Adicione suas skills em `skills/<nome>/SKILL.md`
5. Suba no GitHub e instale no time

## Referências

- [Cursor Plugins Docs](https://cursor.com/docs/plugins)
- [Plugins Reference](https://cursor.com/docs/reference/plugins)
- [Plugin Template Oficial](https://github.com/cursor/plugin-template)

## License

MIT
