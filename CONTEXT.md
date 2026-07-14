# System Design Thinking Tool

A tool that keeps developers sharp while working with AI coding assistants, by making a codebase's
architecture visible, navigable, and understandable. This glossary covers Layer 1 — the codebase map.

## Language

### The units

**Group**:
The raw output of a grouping method — a set of files the algorithm decided belong together. Two
different methods produce different groups from identical code.
_Avoid_: cluster, community, partition

**Subsystem**:
A group interpreted as an architectural unit — named, described, and placed in the subsystem graph.
A group becomes a subsystem when it is named.
_Avoid_: module, component, cluster, service

**Grouping Method**:
An algorithm that turns a file graph into groups. Distinct from a signal, which is what a method reads.
_Avoid_: clustering algorithm, partitioner

### The relationships

**Signal**:
Evidence that two files are related. Three exist: structural (one imports or calls the other), lexical
(they share vocabulary), and evolutionary (they change together in git history). Signals are consumed by
grouping methods to form groups; they are not themselves relationships between subsystems.
_Avoid_: feature, metric, weight

**Dependency**:
A directed relationship between two subsystems: one reaches into the other. Only the structural signal
produces dependencies, because only it has direction. Drawn as an arrow.
_Avoid_: edge, link, relation

**Crossing**:
A single file→file edge whose two files sit in different subsystems. A dependency is backed by one or
more crossings; the count of crossings is the dependency's weight. Crossings are the drill-in list — the
concrete places two subsystems touch.
_Avoid_: bridge, bridge file (a bridge is a cut edge in graph theory — a different concept), connector, seam, port

**Major Dependency**:
A dependency that carries a meaningful share of the crossings leaving its source subsystem. Majors are
drawn on the map. Every dependency is exactly one of major or minor.
_Avoid_: strong edge, primary edge

**Minor Dependency**:
A dependency graded below the share threshold. It stays in the subsystem graph and is reported as a
count per subsystem, but is not drawn on the map. Nothing is silently absent.
_Avoid_: weak edge, filtered edge, hidden edge

**Backbone**:
The major dependencies of a subsystem graph, taken together — the arrows the map draws.
_Avoid_: skeleton, core graph

**Island**:
A subsystem with no dependencies in either direction but real internal wiring. Drawn on the map,
standing alone. Distinct from noise — an isolated group with no internal edges either, which goes to a
tray with a count.
_Avoid_: orphan, disconnected component

**Noise**:
An isolated group with no dependencies in either direction *and* no internal wiring — nothing to draw
an arrow to or from. Not shown as a box; swept into a tray at the map's edge with a count. Distinct from
an island, which is also isolated but has real wiring inside it and is drawn as its own box.
_Avoid_: orphan, junk, dead code (noise files are often live — config files and framework entry points
loaded by convention, not import)

**Connection**:
The drawn line joining a pair of boxes on the *map*, standing for the one or two dependencies between
that pair. The picture-level counterpart to a dependency, the same way the map is the picture-level
counterpart to the subsystem graph — a dependency is directed and lives in the data; a connection is
what you see.
_Avoid_: edge, link (those describe the data; use dependency or crossing there)

### The artifacts

**File Graph**:
The directed graph of every source file and every dependency between files. The raw material.
_Avoid_: import graph, call graph, AST graph

**Subsystem Graph**:
The graph whose nodes are subsystems and whose edges are dependencies, derived from the file graph and a
grouping. Formally the quotient graph of the file graph under that grouping. It is data, not a picture.
_Avoid_: rollup, module dependency graph, MDG, architecture map

**Map**:
The rendered, navigable picture of a subsystem graph. The thing a developer looks at and explores.
Distinct from the subsystem graph, which is the data behind it.
_Avoid_: visualization, diagram, graph

### Navigation

**Breadth**:
Movement across the map at one altitude — seeing how subsystems relate to their neighbours.
_Avoid_: panning, overview

**Depth**:
Movement down through one subsystem — into its sub-modules, then its files, then its code. Produced by
re-running a grouping method on only that subsystem's files.
_Avoid_: zoom, drill-down, expansion

**Altitude**:
How far down a depth descent you are. The map shows subsystems at the top altitude, code at the bottom.
_Avoid_: level, tier, layer (layer means something else — a position in dependency order)
