# Vendored nomenclator

Complete snapshot of [`talmago/nomenclator`](https://github.com/talmago/nomenclator) (`dspy-nomenclator`, MIT).

| Path | Role |
|---|---|
| `src/nomenclator/` | Live Python package (byte-for-byte from upstream `src/nomenclator`) |
| `tests/nomenclator/` | Upstream unit + integration tests |
| this directory | Upstream README, architecture, AGENTS, LICENSE, pyproject, poetry.lock, CI, `vscode.settings.json` |

Upstream commit: see `UPSTREAM_COMMIT`.

Install the extra, then classify:

```bash
pip install 'arancel-mx[hs]'
arancel-mx nomenclator "Men's cotton knitted shirts"
nomenclator "Fresh bananas"
```

HS6 from WCO 2022 English + GIR is a **suggestion**, not Mexican legal identity. Look up the code in a verified `data-*` release (`arancel-mx compare 610510`).
