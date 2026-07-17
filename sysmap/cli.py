"""The `sysmap` command — map the repo you're standing in.

No path to pass and nothing to configure: the repo is found by walking up to
the nearest .git, the same way git itself decides what you mean. One process
serves both the map and the page that draws it, so there is one port and
nothing to start alongside it.
"""
from __future__ import annotations
import argparse
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path


def find_repo(start: Path) -> Path | None:
    """The nearest enclosing git repository, or None."""
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
    return None


def free_port(preferred: int) -> int:
    """`preferred` if nothing holds it, otherwise whatever the OS hands out.

    Two of these can run at once — two repos, two windows — and the second
    should not die over a number nobody chose deliberately.
    """
    for port in (preferred, 0):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return preferred


def _open_when_ready(url: str, port: int) -> None:
    """Open the browser once the server answers, not before."""
    for _ in range(200):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                webbrowser.open(url)
                return
        time.sleep(0.05)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sysmap", description=__doc__.splitlines()[0])
    p.add_argument("repo", nargs="?", default=".",
                   help="a repo, or a directory inside one (default: here)")
    p.add_argument("--port", type=int, default=8642)
    p.add_argument("--no-open", action="store_true", help="don't open a browser")
    args = p.parse_args(argv)

    start = Path(args.repo).expanduser().resolve()
    if not start.is_dir():
        print(f"sysmap: not a directory: {start}", file=sys.stderr)
        return 1
    repo = find_repo(start)
    if repo is None:
        print(f"sysmap: {start} is not inside a git repository.\n"
              f"        The map is built from what git tracks, so there has to "
              f"be a repo to read.", file=sys.stderr)
        return 1

    from sysmap.server.app import WEB
    if not (WEB / "index.html").exists():
        print("sysmap: the page isn't built, so there would be nothing to look "
              "at.\n        This happens in a source checkout — use bin/map, "
              "which runs Vite.", file=sys.stderr)
        return 1

    port = free_port(args.port)
    url = f"http://127.0.0.1:{port}/?repo={urllib.parse.quote(str(repo))}"
    # flush: these say where to look, and the next thing this process does is
    # block in uvicorn. Piped anywhere but a terminal they would sit in the
    # buffer until the server stops, which is exactly too late to be useful.
    print(f"sysmap: mapping {repo}", flush=True)
    print(f"        {url}", flush=True)
    print("        first run parses the whole repo — minutes on a big one; "
          "Ctrl+C to stop", flush=True)
    if not args.no_open:
        threading.Thread(target=_open_when_ready, args=(url, port),
                         daemon=True).start()

    import uvicorn
    try:
        uvicorn.run("sysmap.server.app:app", host="127.0.0.1", port=port,
                    log_level="warning")
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
