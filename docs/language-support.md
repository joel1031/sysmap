# Language support

What the engine actually reads, measured rather than assumed (2026-07-16). One
real repo per language, run from a non-symlinked path.

The pipeline does not resolve references through imports. graphify builds a
symbol's id from the path of the file that defines it, and `extract.py`'s
`resolve()` recovers that file by longest-prefix match. So a language works or
fails on whether that id-matching lands, not on whether the language has
file-level imports — which is why Swift's module-wide visibility doesn't stop
it producing edges, and why those edges are wrong anyway.

## Measured

Edges per file is coverage, **not correctness**. Read the confidence column.

| language | repo | files | edges | per file | confidence |
|---|---|---|---|---|---|
| Java | gson | 262 | 1542 | 5.89 | **verified** — 3/3 by eye |
| Swift | alamofire | 98 | 413 | 4.21 | **bad** — density is fabricated |
| C# | newtonsoft | 945 | 3515 | 3.72 | mixed — calls good, `using` bad |
| TypeScript | hono | 356 | 1089 | 3.06 | **verified** — what we ship |
| C | hiredis | 52 | 152 | 2.92 | **verified** — 5/5 by eye |
| Python | requests | 37 | 99 | 2.68 | **verified** — 3/3 by eye |
| C++ | fmt | 71 | 151 | 2.13 | unmeasured for quality |
| Go | gin | 99 | 197 | 1.99 | **verified** — 3/3 by eye |
| Kotlin | okio | 323 | 522 | 1.62 | unmeasured for quality |
| PHP | guzzle | 89 | 141 | 1.58 | unmeasured for quality |
| Rust | ripgrep | 100 | 117 | 1.17 | mixed — saw a mis-attribution |
| Scala | upickle | 145 | 116 | 0.80 | too thin to draw |
| Ruby | sinatra | 147 | 75 | 0.51 | too thin, and garbage |
| Dart | dart-lang/http | 324 | 163 | 0.50 | too thin to draw |
| Elixir | ecto | 126 | 42 | 0.33 | too thin to draw |

**Use:** C, Go, Java, Python, TypeScript/JS.
**Don't claim:** Swift, Ruby, Scala, Dart, Elixir.
**Unproven:** C#, C++, Kotlin, PHP, Rust.

## Why density lies

Three times in one session a dense result turned out to be fabrication:

- **Ruby, 3.39/file** — in Ruby a bare identifier parses as a method call, so
  parameters became "calls", and every stdlib method (`.compact`, `.to`) matched
  any same-named repo method. Roughly 0/6 real.
- **Swift, 4.21/file** — `import Foundation` and `import Dispatch` name Apple's
  frameworks. They resolve to an arbitrary repo file, so every file importing
  Foundation draws an edge to the same innocent bystander.
- **Go, `http.ResponseWriter`** — the receiver is discarded, leaving
  `ResponseWriter`, which matches gin's own type.

All three are the same shape: **a name that belongs to something outside the
repo, matched to a file inside it.**

## Two known bugs

**Symlinked paths produce an empty map, silently.** `extract.py` compares
`_abs(p)` (which calls `.resolve()`) against `keep` (which doesn't), so any repo
reached through a symlink — anything under `/tmp` on macOS, a symlinked home, a
work mount — has *every* edge dropped by `if a not in keep`. Not counted in
`unresolved`, not reported. This invalidated a full session of measurements
before it was noticed.

**`really_there()` validates the name, not the target.** It checks the name sits
on the line it claims. For `import Foundation`, "Foundation" *is* on that line,
so the check passes while the target file is arbitrary. Its blind spot is
exactly "right name, wrong file" — which is Swift's whole failure mode. A filter
for references whose target is a module rather than a repo file would likely
lift Swift and C# considerably.

## Caveats

One repo per language — the same weakness this project criticised in the
Codebase-Memory paper. Quality was spot-checked at ~5 samples, not measured.
Everything outside the verified row should be treated as unproven.
