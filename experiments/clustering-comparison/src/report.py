"""Render a static, self-contained HTML report of the grouping + subsystem graph."""
from __future__ import annotations
import html
from pathlib import Path

PALETTE = ["#4f6df5", "#e8833a", "#3aa675", "#c0497f", "#7d5bd0", "#2f9bbf",
           "#b0913a", "#d0574f", "#5b8c3a", "#8a6d5b", "#7a7f8c", "#5f9ea0"]


def _short(f):
    p = f.split("/")
    return "/".join(p[-2:]) if len(p) > 1 else f


def _chip(f, color):
    return (f'<span class="chip" style="border-color:{color}">'
            f'{html.escape(_short(f))}</span>')


def _group_cols(groups, names=None):
    out = []
    for i, g in enumerate(groups):
        c = PALETTE[i % len(PALETTE)]
        chips = "".join(_chip(f, c) for f in g)
        nm = names.get(i) if names else None
        if nm:
            head = (f'{html.escape(nm.name)} · {len(g)} files'
                    f'<div class="grp-desc">{html.escape(nm.description)}</div>')
        else:
            head = f'group {i + 1} · {len(g)} files'
        out.append(f'<div class="grp"><div class="grp-h" style="background:{c}">'
                   f'{head}</div>{chips}</div>')
    return f'<div class="grid">{"".join(out)}</div>'


def _sname(i, names):
    nm = names.get(i) if names else None
    return nm.name if nm else f"subsystem {i}"


def _sg_matrix(sg, groups, names):
    n = sg["n_subsystems"]
    deps = sg["deps"]
    head = "".join(f'<th class="mx-n">{j}</th>' for j in range(n))
    rows = ""
    for i in range(n):
        c = PALETTE[i % len(PALETTE)]
        cells = ""
        for j in range(n):
            if i == j:
                cells += '<td class="mx-d">·</td>'
                continue
            cr = deps.get((i, j))
            if not cr:
                cells += '<td class="mx-0"></td>'
            else:
                cyc = " mx-cyc" if (j, i) in deps else ""
                cells += (f'<td class="mx-v{cyc}" style="color:{c}">{len(cr)}</td>')
        rows += (f'<tr><th class="mx-r"><span class="dot" style="background:{c}"></span>'
                 f'[{i}] {html.escape(_sname(i, names))}</th>{cells}</tr>')
    return (f'<div class="mx-wrap"><table class="mx"><tr><th class="mx-r"></th>{head}</tr>'
            f'{rows}</table></div>'
            '<p class="hint">Row depends on column; the number is how many crossings back that '
            'dependency. Numbers on <b>both sides of the diagonal</b> mean the two subsystems '
            'depend on each other.</p>')


def _sg_deps(sg, groups, names, cap=6):
    items = sorted(sg["deps"].items(), key=lambda kv: -len(kv[1]))
    out = ""
    for (i, j), cr in items:
        c = PALETTE[i % len(PALETTE)]
        cyc = '<span class="cyc"> ↔ circular</span>' if (j, i) in sg["deps"] else ""
        lines = "".join(
            f'<div class="cx">{html.escape(_short(a))} <span class="ar">→</span> '
            f'{html.escape(_short(b))}</div>' for a, b in cr[:cap])
        more = f'<div class="cx more">… {len(cr) - cap} more</div>' if len(cr) > cap else ""
        out += (f'<div class="dep"><div class="dep-h" style="border-color:{c}">'
                f'{html.escape(_sname(i, names))} <span class="ar">→</span> '
                f'{html.escape(_sname(j, names))}'
                f'<span class="tag">{len(cr)} crossings</span>{cyc}</div>{lines}{more}</div>')
    return f'<div class="deps">{out}</div>'


def _sg_section(sg, groups, names):
    meta = (f'{sg["n_subsystems"]} subsystems · {len(sg["deps"])} dependencies · '
            f'{sg["n_crossings"]} crossings · {len(sg["bidirectional"])} circular pairs · '
            f'{len(sg["isolated"])} isolated · '
            f'{sg["intra_edges"]} edges kept inside subsystems')
    return (f'<div class="meta">{meta}</div>'
            + _sg_matrix(sg, groups, names) + _sg_deps(sg, groups, names))


CSS = """
*{box-sizing:border-box} body{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;
margin:0;background:#0f1115;color:#e6e8ee} .wrap{max-width:1180px;margin:0 auto;padding:32px}
h1{font-size:24px;margin:0 0 4px} h2{font-size:18px;margin:34px 0 6px}
h3{font-size:14px;margin:22px 0 2px;color:#c6cbd5;font-weight:600}
.sub-hd{color:#9aa0ad;margin:0 0 20px}
.meta{color:#9aa0ad;font-size:13px;margin:2px 0 14px}
.grid{display:flex;flex-wrap:wrap;gap:12px}
.grp{background:#171a21;border:1px solid #262b36;border-radius:10px;padding:0 0 10px;
min-width:210px;max-width:340px;overflow:hidden}
.grp-h{color:#fff;font-weight:600;font-size:12px;padding:7px 11px;letter-spacing:.02em}
.grp-desc{font-weight:400;font-size:11px;opacity:.9;margin-top:2px}
.chip{display:inline-block;margin:6px 0 0 8px;padding:2px 8px;border:1px solid;
border-radius:20px;font-size:12px;background:#0f1115}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle}
.hint{color:#9aa0ad;font-size:12px;margin-top:8px}
.layers{display:flex;flex-direction:column;gap:8px}
.layer{background:#171a21;border:1px solid #262b36;border-radius:10px;padding:8px 12px}
.layer b{color:#8fb0ff} .cyc{color:#e8833a}
.tag{display:inline-block;background:#20242e;border-radius:6px;padding:1px 7px;font-size:12px;margin-left:8px;color:#9aa0ad}
.mx-wrap{overflow-x:auto;margin-top:8px}
table.mx{border-collapse:collapse;font-size:12px}
.mx th,.mx td{border:1px solid #262b36;padding:4px 7px;text-align:center}
.mx th.mx-r{text-align:left;white-space:nowrap;color:#c6cbd5;font-weight:500;background:#171a21}
.mx th.mx-n{color:#9aa0ad;background:#171a21;min-width:30px}
.mx td.mx-d{background:#20242e;color:#4b515e}
.mx td.mx-0{color:#333a46}
.mx td.mx-v{font-weight:700;background:#151922}
.mx td.mx-cyc{outline:1px solid #e8833a}
.deps{margin-top:18px;display:flex;flex-wrap:wrap;gap:10px}
.dep{background:#171a21;border:1px solid #262b36;border-radius:10px;padding:9px 12px;min-width:300px}
.dep-h{border-left:3px solid;padding-left:8px;font-weight:600;font-size:13px;margin-bottom:6px}
.cx{font-family:ui-monospace,monospace;font-size:11px;color:#9aa0ad;padding-left:11px}
.cx.more{color:#5f6672}
.ar{color:#5f9ea0}
"""


def render(methods, meta, out_path: Path):
    parts = [f'<div class="wrap"><h1>Subsystem graph</h1>'
             f'<p class="sub-hd">{html.escape(meta)}</p>']

    for m in methods:
        parts.append(f'<h2>{html.escape(m["name"])}'
                     + (f'<span class="tag">{html.escape(m["metric"])}</span>'
                        if m.get("metric") else "") + '</h2>')
        if "groups" in m:
            parts.append(f'<div class="meta">{len(m["groups"])} groups</div>')
            parts.append(_group_cols(m["groups"], m.get("names")))
            if m.get("zoom"):
                parts.append('<div class="meta">zoom-out (coarser):</div>')
                parts.append(_group_cols(m["zoom"]["coarse"]))
            if m.get("subsystem_graph"):
                parts.append('<h3>subsystem graph — dependencies between these subsystems</h3>')
                parts.append(_sg_section(m["subsystem_graph"], m["groups"], m.get("names")))
        elif "layers" in m:
            rows = ""
            names = m.get("names")
            for i, lyr in enumerate(m["layers"]):
                chips = " ".join(_short(f) for f in lyr)
                nm = names.get(i) if names else None
                if nm:
                    label = (f'{html.escape(nm.name)} '
                             f'<span class="tag">layer {len(m["layers"]) - i}</span>'
                             f'<div class="grp-desc">{html.escape(nm.description)}</div>')
                else:
                    pos = "top/UI" if i == 0 else "bottom/infra" if i == len(m["layers"]) - 1 else "mid"
                    label = f'layer {len(m["layers"]) - i} ({pos})'
                rows += f'<div class="layer"><b>{label}</b> — {html.escape(chips)}</div>'
            parts.append(f'<div class="layers">{rows}</div>')
            if m["cycles"]:
                parts.append('<div class="meta cyc">cycles (mutual dependencies): '
                             + "; ".join(" ↔ ".join(_short(f) for f in c) for c in m["cycles"])
                             + '</div>')
            else:
                parts.append('<div class="meta">no dependency cycles found ✓</div>')

    parts.append("</div>")
    doc = f"<!doctype html><meta charset=utf-8><title>Grouping comparison</title><style>{CSS}</style>" + "".join(parts)
    out_path.write_text(doc)
    return out_path
