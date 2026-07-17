"""Build the page into the wheel.

The map is drawn by a React app that has to be compiled before anyone can look
at it. This runs that compile during the install and puts the result inside the
package, so the installed tool has one process serving both the map and the
page, and nobody needs Node to *run* it — only to install it.

That is the deliberate trade: nothing can ever be stale, and someone without
Node gets a failed install rather than a working tool with an older page. The
error below is written to be read by that person.
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).parent
WEB = ROOT / "web"
DEST = ROOT / "sysmap" / "server" / "_web"


class BuildPage(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version, build_data):
        if not WEB.exists():          # an sdist of the package alone
            return
        npm = shutil.which("npm")
        if npm is None:
            raise RuntimeError(
                "sysmap needs Node and npm to build its page.\n"
                "Install Node (https://nodejs.org, or `brew install node`) and "
                "try again.\nThey are needed to install sysmap, not to run it."
            )
        print("building the page (npm)…", file=sys.stderr)
        # `npm ci` when there's a lockfile: it installs exactly what was locked
        # and fails rather than quietly resolving something newer.
        install = ["ci"] if (WEB / "package-lock.json").exists() else ["install"]
        subprocess.run([npm, *install], cwd=WEB, check=True)
        subprocess.run([npm, "run", "build"], cwd=WEB, check=True)

        dist = WEB / "dist"
        if not (dist / "index.html").exists():
            raise RuntimeError(f"the page didn't build — nothing at {dist}")
        if DEST.exists():
            shutil.rmtree(DEST)
        shutil.copytree(dist, DEST)
        # Ship what we just built, wherever the wheel is being assembled from.
        build_data["force_include"][str(DEST)] = "sysmap/server/_web"
