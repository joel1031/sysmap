# sysmap

**A map of your codebase you can walk around in — what its parts are, and how they actually
connect.**

Point it at a repo and it draws one box per part of your system, with arrows for what depends on
what. You can click any box to see what it touches, open any arrow to see the exact lines of code
that justify it, and go inside any box to see what it's made of.

It works out the parts by reading what your code imports and calls. It does not read your folder
tree, and it will often disagree with it.

```bash
cd any-git-repo
uvx --from git+https://github.com/joel1031/sysmap sysmap
```

You need [uv](https://docs.astral.sh/uv/), and [Node](https://nodejs.org) to build the page. There
is no path to pass and nothing to configure — the repo is wherever you're standing. It opens a
browser. The first run reads the whole repo: seconds for a small one, minutes for a big one. After
that it's instant until you commit something.

## What it looks like

This is [umami](https://github.com/umami-software/umami) — 924 files, mapped in about twenty
seconds. Nobody told it what "Analytics & Reporting" or "Data Collection & Storage" were; it
worked them out and then named them.

![The map of umami: boxes named Analytics & Reporting, Data Collection & Storage, API & Backend Logic and others, with lines drawn between the ones that depend on each other](docs/images/map.png)

Go inside a box and the map redraws to show what that box is made of. Here's what's inside umami's
admin area — and around the edge, faded, the parts outside it that its insides still reach:

![Inside umami's admin area: smaller boxes named Team Management, Websites & Users, Goals & Funnels and Data Queries & Hooks, with the parts outside drawn faintly at the edge](docs/images/inside.png)

Names come from a model, and it's optional. Without a key, each box is named after the words that
are common in its own files and rare everywhere else. This is
[OpenCut](https://github.com/OpenCut-app/OpenCut) with no key at all:

![OpenCut mapped with no key: boxes named from their own vocabulary, like data · name, route · router and sidebar · skeleton](docs/images/names.png)

The boxes and the arrows are worked out before any model is involved, so a key changes nothing
about the shape of the map — only what the boxes are called. And the words-only names are hit and
miss: `route · router` tells you something, `data · name` doesn't. Set a key and you get names like
umami's above:

```bash
export ANTHROPIC_API_KEY=...
```

One request per map, plus one for each arrow you actually open. Both are remembered.

## Why I built it

Working with an AI assistant makes it very easy to stop thinking. Not because you're lazy — because
it's late, or you don't know that part of the system well enough to push back, or the answer sounds
right and checking it is work. So you accept it. Do that enough times and you're a passenger in
your own codebase.

The model has enormous knowledge and no judgment. It doesn't know why your payment code is shaped
the way it is, or that you already solved this exact problem two directories over. That gap is
yours to fill. But you can't fill it if you can't see your own system — and past a few thousand
files, nobody can.

So this is the part that lets you see it. Not to code faster. To stay dangerous: sharp, informed,
and hard to replace.

Two more layers are planned on top of this one — one that surfaces the relevant parts of your
system when you're about to change something and shows you how you solved it last time, and one
that hands an agent the understanding you just built instead of letting it guess. Neither exists
yet. This one does.

## How it works

**1. Read every file.** [tree-sitter](https://tree-sitter.github.io), via
[graphify](https://pypi.org/project/graphifyy/), parses each file that git tracks and finds what it
defines and what it uses from elsewhere. Those become one box per file, joined when one file uses
something another file defines.

Working out *which* file a name came from is the hard part, and it's where this can be wrong.
`JSON.stringify` will happily attach itself to a type of yours called `Json`, inventing a link
between two files that have never met. So every link is checked against the source: if the name
isn't really on the line it's claimed to be on, the link is thrown away. That catches 9 of them in
a 56-file repo and 122 in umami.

**2. Weigh each link three ways.** How strongly do two files belong together?

- one uses the other, and how often
- they share unusual words — words common in both files and rare across the repo
- they get changed in the same commits

Each is scored from 0 to 1 and averaged. The three disagree usefully: imports say what the code
*says*, shared words say what it's *about*, and history says what actually moves together.

**3. Find the parts.** [Leiden](https://github.com/vtraag/leidenalg) pulls out knots of files that
connect to each other far more than they connect to anything else. That's the whole trick — a
"part of your system" is just a set of files that mostly talk among themselves.

It's good at it. Across every repo measured, 60–79% of all dependencies end up *inside* a box
rather than crossing between boxes, which is why there are few enough arrows to read. Repo size
barely changes the box count: 757 files and 2046 files both come out around 18–20 boxes.

**4. Name them.** A model gets the file paths in each box and writes a name and a sentence. It
never decides what goes in which box — it only labels what step 3 already found, so it can't invent
structure that isn't there. Without a key, step 2's shared words do the naming instead.

**5. Draw the important arrows.** Two parts can be joined by dozens of file-to-file links. The map
draws the pairs that matter and lists the rest, so you get a picture instead of a hairball. Every
arrow can be opened down to the exact line that uses a thing and the line that defines it.

The grouping cuts across your directory tree on purpose. That a part of your system doesn't match
your folders is usually the most interesting thing the map has to say.

## What it reads

**C, Go, Java, Python, TypeScript/JavaScript.** Those five were checked by hand against real repos.
See [docs/language-support.md](docs/language-support.md) for what each was checked against.

graphify parses many more languages and this doesn't claim them, because a lot of links turned out
to be dense and wrong. Ruby looked rich until you looked: a bare word parses as a method call, so
parameters became calls and nearly every link was fiction. Swift looked rich because
`import Foundation` pointed at some arbitrary file in the repo. Both are written up with numbers.

## What it won't do yet

- **Nothing crosses a language boundary.** A Python backend and a TypeScript frontend in one repo
  draw as two separate islands with no arrows between them, because working out that a name in one
  refers to a thing in the other isn't something this does. It isn't pretending otherwise — in one
  1252-file repo, all twelve of the links it drew between the two languages were false, and
  removing them was a bug fix.
- **A shallow clone quietly weakens it.** The history signal reads your commits, so `--depth 1`
  leaves it with nothing to read, and nothing tells you.
- **Tests group with the code they test.** Correct, and usually not what you wanted to look at.
- **Vue and Svelte aren't read**, so Nuxt and SvelteKit apps map only their plain TypeScript.
- **It needs a key to name things well.** Without one you get real structure and vague labels.

Words like *subsystem*, *dependency*, *crossing* and *reference* are used precisely throughout the
code and docs; [CONTEXT.md](CONTEXT.md) defines them. [docs/](docs/) covers how each piece was
built and what was tried and rejected.

## License

MIT.
