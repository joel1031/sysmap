# Project Principles

## The Problem
LLM-assisted coding makes it dangerously easy to be passive. When you defer to the model — whether because you're mentally drained, don't understand the system deeply enough, or haven't thought through the tradeoffs — you ship lower quality work and your value as an engineer declines. The model has knowledge but no taste, no judgment, and no understanding of your specific system. That gap is yours to fill, and right now there's nothing helping you fill it.

## The Product
A system design thinking tool for developers working with AI coding assistants. It has three layers:

**Layer 1 — Codebase Visualization:** A traversable, meaningful visual map of your codebase — built using Tree-sitter parsing and Leiden clustering — that shows you how your system's subsystems actually relate to each other. Not AI slop like CodeViz. Something that paints a genuinely clear picture of your architecture.

**Layer 2 — Decision Support:** When you're about to implement something, the tool surfaces the relevant parts of your system, shows you how similar decisions were made elsewhere in your codebase, presents tradeoffs neutrally and without bias, and prompts you to think through options — including ones the model wouldn't think to suggest, like your "why not do it the same way the existing flow does it?" moment.

**Layer 3 — Agent Orchestration:** Once you've made an informed decision, the tool executes — with Claude Code or similar — but constrained by the understanding you just built, not the model's default assumptions.

## Vocabulary
Terms in this project are defined in `CONTEXT.md` and are used precisely. A **group** is what a grouping algorithm returns; it becomes a **subsystem** once it is named. A **dependency** is a directed arrow between two subsystems, and it is backed by one or more **crossings** — the individual file-to-file edges that cross the boundary. The **subsystem graph** is data; the **map** is the picture drawn from it. Prefer these words over "module", "component", "cluster", or "bridge", each of which already means something else.

Per-layer documentation lives in `docs/`.

## No Jargon

A term is either **defined in `CONTEXT.md` and used precisely**, or it is **plain English**. There is no third option.

This applies to everything — conversation, plans, code comments, docs. When explaining an idea that comes from an academic field (graph drawing, information visualization, cognitive science, compilers), do not import that field's vocabulary. Say the thing in ordinary words. "Boxes are stacked in rows so the arrows all point downward" is the explanation; "layered Sugiyama layout" is a label for it that carries no meaning to a reader who does not already know.

If a borrowed term is genuinely worth keeping — it names something we will refer to repeatedly and no plain phrase is shorter — then propose adding it to `CONTEXT.md` first, with a definition, and only use it after it is written down. Never use a term and define it in passing. Never use a term you have not defined.

Names of specific tools and libraries (`Leiden`, `ELK`, `React Flow`, `tree-sitter`) are fine — they are proper nouns, not concepts. What they *do* must still be described in plain English.

## The North Star
I'm not building a tool to code faster. You're building a tool that keeps developers genuinely dangerous — sharp, informed, and irreplaceable — in a world where AI makes it easy to become a passive passenger in your own codebase.

## Cognitive Load Theory — Key Points & Product Application

1. **Worked examples reduce cognitive load for novices.** The research is unambiguous — for someone early in their skill acquisition, showing a worked example is superior to asking them to solve the problem themselves. In your tool, this means when a developer is trying to understand an architectural decision, don't just show them the graph and ask them to figure it out. Show them a worked example: here's a similar decision that was already made in your codebase, here's why, here's what it looks like.

2. **The integration problem — don't split attention.** This is the most critical design constraint. Worked examples fail when they force the learner to mentally integrate multiple sources of information simultaneously. If your tool shows a visual graph in one panel, the code in another, and an explanation in a third, you've recreated the exact cognitive burden you're trying to eliminate. The visualization must consolidate — the explanation, the code reference, and the visual relationship need to live together at the point of attention, not across tabs.

3. **Timing matters — early stage only.** Worked examples are most effective at the beginning of skill acquisition. As someone gets more experienced, they stop paying attention to them and they become noise. This tells you something important about your tool's design: it should detect or adapt to the developer's familiarity with a given part of the codebase. First time touching the auth module? Show the worked example. Fifth time? Get out of the way.

4. **Extraneous tasks kill learning.** The research notes that removing extraneous tasks — like having to remember how to do something mechanical — frees up cognitive resources for the actual learning. This maps directly to your end-of-day problem. The more mechanical cognitive work the tool handles (finding the relevant files, mapping the relationships, surfacing similar patterns), the more mental bandwidth the developer has left for the actual judgment call.

5. **Examples build transferable schemas, not just solutions.** This is the compounding value you mentioned. Worked examples don't just teach you how to solve this problem — they build abstract schemas that help you recognize and solve related problems. Over time, your tool isn't just helping you implement features, it's building your intuition about system design patterns. That's the long-term value — the muscle you're training.
