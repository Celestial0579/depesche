# {{NAME}} {{KENNUNG}}: compact messages between team lead (TL) and staff sessions

Use for every SendMessage between TL and staff sessions, and to read any message starting with `{{KENNUNG}}`. Never for text the human operator reads: chat, wrap_up recap, operator to-do lists, issues, PRs, commits stay normal language.

Format
- Line 1: `{{KENNUNG}} TYPE [status] [subject/refs] [!]`. Then one item per line: `field value` or `- item`.
- Free text: terse English. No greeting, filler, articles, hedging, restating known context. Fragments ok.
- Refs, not content: #n issue, !n PR, @sha commit, repo#n, vX.Y.Z, file path, session name (send by name, not id).
- ASCII only: -> then, + and, = is/set, ~ about, ? unknown. No emoji, unicode arrows or bullets (cost more tokens).
- Time HH:MM local, Z = UTC, date MMDD.
- Uniform records as table: `T col1,col2` then one CSV row per line.
- `R code,code`: stress standing rules. All rules always apply, R only reminds.

Behavior
1. One message per event, batch items. No ACK; silence = accepted.
2. At task end or when blocked: `REP status`, then did/now/next/need, max 6 lines. TL often reads only the first 400 chars.
3. Ask only when blocked. Other info goes into the next REP.
4. Line `!!`, then full clear sentences: security findings, destructive or irreversible steps, decisions for the operator, permissions. Exact beats short.
5. Verbatim: code, commands, paths, error text, IDs.
6. Unknown code: `{{KENNUNG}} ASK ?code`.

Example
```
{{KENNUNG}} REP blk #48
did key moved to Software\Celestial0579\App, uninstall cleans, 559 tests green
need vm window
```

Glossary
{{GLOSSAR}}
