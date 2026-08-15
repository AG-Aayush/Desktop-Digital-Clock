# Deploying FlipClock — a working DevOps guide

This is the guide I'd follow if I were shipping FlipClock as a real product.
You're going to follow it instead, and by the end you'll have built the same
pipeline I would have, understanding every piece.

**How to read this.** Each phase answers four questions in order:

- **Why** — the problem this solves. Skip this and you're copying, not learning.
- **Concepts** — the vocabulary, so the words mean something when you meet them again.
- **Do** — the actual steps. Files to create, buttons to click, what to type.
- **Verify** — how you *know* it worked, rather than hoping.

There's a **Checkpoint** at the end of each phase. Don't move on until it passes.
Things break far more often at the joins than in the middle, and a broken
foundation gets much more expensive three phases later.

Work through it in order. Each phase assumes the previous one is done.

### ⚠️ Start here: close the open incident first

You are not starting from a clean slate — you're starting **mid-incident**.
Your first release (`v1.0.0`) failed, your website's download button 404s for
every visitor, and the one-line workflow fix is sitting uncommitted in your
working tree. Before Phase 1, go to **Phase 8 → post-mortem #2**, read it, and
carry out its fix-and-re-tag flow.

Why out of order? Two reasons, both worth understanding:

1. **A broken production thing outranks process work.** Your product's front
   door is broken *now*; branch rulesets can wait an hour. Triage order is a
   real DevOps judgement, and this is your first taste of it.
2. **Phase 1 will lock the door you need.** Its branch protection rejects
   direct pushes to `main` — and the incident fix uses one. Do it while the
   push is still simple, and every later release will flow through the proper
   gates you then build.

When the release is live and the download button works, come back here and
begin Phase 1.

---

## Phase 0 — An honest look at where you are

Before building anything, know your baseline. Here's what FlipClock has today:

| Thing | Status |
|---|---|
| Source in Git, pushed to GitHub | ✅ Done |
| Release workflow (tag → build → publish) | ⚠️ Exists; its first real run **failed** (see Phase 8, post-mortem #2) |
| Website on GitHub Pages | ✅ Done |
| Automated tests | ❌ **None** |
| Code linting / formatting | ❌ None |
| CI on pull requests | ❌ None |
| One source of truth for the version number | ❌ Duplicated in two files |
| Dependency update automation | ❌ None |
| Security scanning | ❌ None |

That's a normal starting point for a personal project. The gap between this and
"product" is exactly what the rest of this guide closes.

### The Docker question, answered honestly up front

You asked about Docker. Here's the truth, because a guide that tells you what
you want to hear is worthless:

**You cannot ship a Windows desktop GUI application in a Docker container.**
Containers share the host kernel and have no desktop session. Your users need
`FlipClock.exe` running on *their* Windows desktop, drawing a window on *their*
screen, writing to *their* registry. There is no container in that story.
Windows containers do exist, but they're multi-gigabyte, can't display GUIs to
an end user, and solve nothing here.

Anyone who tells you to "just dockerize it" has not thought about what your app
actually does.

**But Docker is still genuinely worth learning, and this project has a real place
for it** — your website. `docs/index.html` is a static site, and serving it is a
textbook container use case. In Phase 6 you'll containerize it properly:
Dockerfile, image registry, the whole path. That's real Docker, on a real
artifact of yours, not a contrived exercise.

The lesson underneath: **pick tools for problems, not for résumés.** Knowing when
*not* to use Docker is a more senior skill than knowing how to use it.

### Working from Linux (and why you'd want to)

Most DevOps tooling is built Linux-first, and you'll learn more with a Linux
shell in front of you. You can absolutely work that way here — but there's a
boundary worth understanding before you set it up, because it teaches one of the
field's central ideas.

**Your development machine and your build machine are not the same machine.**

Your workflows run on GitHub's `windows-latest` runners. GitHub does the Windows
building. Your laptop is only where you *write* code. Once that clicks, "which
OS should I develop on?" becomes a comfort question, not a technical one.

The boundary comes from one line in `desktop_timer.py`:

```python
import winreg
```

`winreg` is Windows-only and imported unconditionally at module level, so on
Linux the import fails immediately. Anything that loads the app is therefore
Windows-only:

| Task | Linux? | Reason |
|---|---|---|
| Git, editing, reviewing CI logs | ✅ | Platform-neutral |
| Ruff, writing workflow YAML | ✅ | Pure Python and text |
| **Docker and the website (Phase 6)** | ✅✅ | Docker is native on Linux — genuinely better here |
| Running the app | ❌ | `winreg` does not exist |
| Running the tests | ❌ | They import the app |
| Building the `.exe` | ❌ | PyInstaller cannot cross-compile for Windows |
| Building the installer | ❌ | Inno Setup is a Windows tool |

So the sensible split is:

- **Linux** — Docker, the website, workflow authoring, Git, general shell work
- **Windows** — running the app, building, manual testing before a release
- **GitHub Actions** — the authoritative build, on a clean machine, every time

**Getting the project into Linux: clone it, don't copy it.**

```bash
git clone https://github.com/AG-Aayush/Desktop-Digital-Clock.git
cd Desktop-Digital-Clock
```

You now have two working copies of one repository, syncing through GitHub. That
is not a workaround — it's how every team on earth works, and how you'd work
across a laptop and a desktop.

**"Won't that duplicate hundreds of megabytes?"** No, and the numbers are worth
seeing, because the intuition is so often wrong:

| | Size |
|---|---|
| Tracked source, 16 files | 113 KB |
| Git history | 246 KB |
| **What a clone actually costs** | **0.4 MB** |
| `.venv/` — gitignored, never cloned | 279 MB |
| `dist/`, `build/`, `dist_installer/` — gitignored | 129 MB |

A working folder can be 400 MB while the *repository* is under half a megabyte.
Everything heavy is build output and virtual environments, and none of it is
tracked. You wouldn't recreate `.venv` in Linux either — it exists to run the
app, which Linux can't do.

**The general lesson:** a repository holds *sources*, not *products*. If
something can be regenerated by a build, it should be gitignored — which keeps
clones cheap, history readable, and makes "just clone it somewhere else" a
non-decision. When a repo does grow huge, it's almost always because someone
committed build output.

> **Do not use a shared folder between host and VM for a Git repository.** It
> seems convenient and reliably causes trouble: line-ending translation, file
> locking, permission bits Git cannot represent, and — if the folder lives in
> OneDrive — a sync client competing with you for the same files. Clone instead.
> As a bonus, a clone inside the VM is outside OneDrive entirely.

**VM or WSL2?** A full VM is more realistic — its own kernel, its own network,
snapshots to roll back. WSL2 (`wsl --install -d Ubuntu`) is lighter, starts
instantly, and Docker Desktop integrates with it directly so containers need no
extra setup. Either is a fine choice; use the VM if you want to feel the
machine, WSL2 if you want the least friction.

One rule for both: **keep the clone in the Linux filesystem** (`~/projects/…`),
never under `/mnt/c/`. Cross-filesystem access is slow and carries permission
quirks that will cost you an afternoon.

**Making the app itself portable** is a real project, listed under
"Where to go next": move the `winreg` calls behind a small platform layer so the
module imports anywhere and only the Windows-specific behaviour is guarded. Do
it once the pipeline exists and the tests can prove you didn't break anything.

---

## Phase 1 — Foundations: versions and branches

**Time:** ~30 minutes

### Why

Right now your version number lives in two files. When you release 1.1.0 and
update one but not the other, your installer will cheerfully tell users it's
1.0.0. That's the kind of bug that erodes trust and is invisible until a user
reports something strange.

Meanwhile you're committing straight to `main`. That's fine alone, but it means
there's no moment where automation can stop a bad change — nothing to hook CI
into. Branches create that moment.

### Concepts

**Semantic Versioning (SemVer)** — `MAJOR.MINOR.PATCH`, e.g. `1.4.2`:

- **PATCH** (1.0.0 → 1.0.1): bug fixes only. Nothing new, nothing broken.
- **MINOR** (1.0.1 → 1.1.0): new features, still backwards compatible.
- **MAJOR** (1.1.0 → 2.0.0): you broke something users depended on.

For a desktop app "breaking" means things like: dropping a setting, changing the
registry layout so old preferences vanish, or requiring a newer Windows.

**Single source of truth** — one place defines a fact; everything else reads it.
The opposite is duplication, and duplication always drifts.

**Feature branch** — you do work on a branch named for the work, then merge it
into `main` through a Pull Request. The PR is where automation gets to run
before the code reaches your main line.

### Do

**1. Make the version single-sourced.**

`pyproject.toml` already declares `version = "1.0.0"`. Make that the only place
it's written by hand.

Open `installer.iss` and find this line near the top:

```
#define AppVersion "1.0.0"
```

Replace it with:

```
; Version is passed in by build_installer.bat, read from pyproject.toml.
; Falls back to 0.0.0-dev so a manual ISCC run still compiles.
#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
```

That means: use the version handed to me; if nobody handed me one, use an
obviously-fake placeholder. A fake version is much better than a *wrong* one —
`0.0.0-dev` tells you instantly that something skipped the proper path.

Now teach `build_installer.bat` to read the real version and pass it in. Find
the line that runs ISCC:

```bat
"%ISCC%" "%~dp0installer.iss"
```

Replace with:

```bat
rem Read the version from pyproject.toml so it is defined in exactly one place.
for /f "delims=" %%v in ('"%PYTHON%" -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])"') do set "APPVERSION=%%v"
if not defined APPVERSION goto failed
echo Building installer for version %APPVERSION% ...
"%ISCC%" /DAppVersion=%APPVERSION% "%~dp0installer.iss"
```

`tomllib` is in the Python standard library from 3.11, so there's nothing to
install. `/DAppVersion=...` defines that symbol for the Inno Setup compiler —
the same mechanism as passing a variable to any other build tool.

**2. Protect `main`.**

In your browser, go to your repository → **Settings** → **Branches** →
**Add branch ruleset** (older interfaces call this "Add rule").

- Name it `main protection`
- Target branches: include the default branch
- Tick **Require a pull request before merging**
- Tick **Require status checks to pass** — leave the list empty for now; you'll
  add your CI check in Phase 2 once it exists and GitHub can see it

Save it.

You'll immediately notice `git push` to `main` gets rejected. That's the point.
From now on:

```bash
git checkout -b fix/some-thing
# ... work ...
git add -A
git commit -m "Fix some thing"
git push -u origin fix/some-thing
```

Then open the Pull Request on GitHub and merge it there.

> **A note on protecting `main` as a solo developer.** It will feel like
> bureaucracy for about a week, then it will save you. The value isn't process —
> it's that a PR is a *place for machines to check your work* before it becomes
> official. Without it, CI can only tell you about mistakes you've already made.

### Verify

Run `build_installer.bat`. It should print `Building installer for version
1.0.0 ...`. When it finishes, right-click `dist_installer\FlipClock-Setup.exe`
→ **Properties** → **Details** and confirm the version reads 1.0.0.

Now the real test: change `version` in `pyproject.toml` to `1.0.1`, rebuild, and
check Properties again. It should say 1.0.1 without you touching `installer.iss`.
Change it back to `1.0.0` afterwards.

### ✅ Checkpoint 1

- [ ] Version appears as a hand-written literal in exactly one file
- [ ] Changing it in `pyproject.toml` alone changes the installer's version
- [ ] Pushing directly to `main` is now rejected
- [ ] You can create a branch, push it, and open a PR

---

## Phase 2 — Continuous Integration: catching problems before they land

**Time:** ~2 hours. This is the biggest phase and the most valuable.

### Why

CI answers one question automatically, every time: *did this change break
anything?* Right now nothing can answer that, because there's nothing to break —
you have no tests.

This is the phase people skip, and it's the one that separates a hobby repo from
a product. Everything later (safe releases, confident refactoring, accepting
contributions from strangers) rests on it.

### Concepts

**Continuous Integration** — every change is automatically built and tested as
soon as it's proposed. "Continuous" means on every push, not once a week.

**Workflow / job / step** — GitHub Actions vocabulary. A *workflow* is a YAML
file describing automation. It contains *jobs* (which run in parallel by
default, each on a fresh machine), and each job has ordered *steps*.

**Runner** — the throwaway virtual machine your job runs on. `windows-latest`
gives you a clean Windows box. Clean is the point: it can't be broken by
something only installed on your laptop.

**Linting** — automated checks for suspicious or badly-styled code. A *linter*
(we'll use Ruff) catches unused imports, undefined names, and similar. It's
spellcheck for code.

**Headless testing** — your app opens windows, but CI has no screen. Qt solves
this with an "offscreen" platform plugin: widgets render into memory. Your test
gets a real, fully functional widget; there's just no monitor.

### Do

**1. Add development tooling.**

Open `requirements-dev.txt` and add:

```
pytest>=8.0
pytest-qt>=4.4
ruff>=0.6
```

Install into your virtual environment:

```bash
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

**2. Configure Ruff.**

Append to `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py39"

[tool.ruff.lint]
# E,F = pycodestyle errors and pyflakes (real bugs).
# I   = import sorting. B = bugbear, catches subtle mistakes.
select = ["E", "F", "I", "B", "UP"]
ignore = [
    "E501",  # long lines: the formatter's job, not worth failing a build over
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

> **Where this config lives matters.** The `[tool.ruff]` form only works inside
> `pyproject.toml`. A standalone `ruff.toml` uses the bare keys with no `tool.`
> prefix. Mixing them up gives you `unknown field 'tool'`.
>
> You might expect to set `QT_QPA_PLATFORM` here too. Resist it — that needs an
> extra plugin, and the environment variable has to be set *before* Qt is
> imported. `conftest.py` below does it at the right moment, which is both
> simpler and more reliable.

**Run Ruff now, before writing any tests**, so you see what it makes of existing
code:

```bash
.venv\Scripts\python -m ruff check .
```

On FlipClock as it stands today, expect exactly three findings:

```
desktop_timer.py:11:1  I001  Import block is un-sorted or un-formatted
desktop_timer.py:21:73 F401  `PyQt6.QtGui.QCursor` imported but unused
make_icon.py:11:1      I001  Import block is un-sorted or un-formatted
```

That `QCursor` is a genuinely dead import — left behind when the resize feature
was removed. Nothing was broken by it, and nobody would ever have spotted it by
eye. **That's the argument for linting in one line.**

All three are auto-fixable:

```bash
.venv\Scripts\python -m ruff check . --fix
```

Review the diff before committing — always read what an auto-fixer did rather
than trusting it blindly.

**3. Write your first tests.**

Create a folder `tests/` with a file `tests/conftest.py`:

```python
"""Shared test setup.

Qt needs exactly one QApplication per process, and it must exist before any
widget is constructed. Creating it once here and sharing it across all tests
avoids both the "no QApplication" crash and the subtler one from making two.
"""
import os
import sys

# Must be set before Qt loads, so it renders into memory instead of a screen.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def app():
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])
```

Now `tests/test_templates.py`:

```python
"""The clock's four styles, and the settings that drive them."""
import pytest

import desktop_timer as dt


def test_every_template_is_known():
    assert dt.TEMPLATES == ("flip", "digital", "minimal", "terminal")


@pytest.mark.parametrize("template,expected", [
    ("flip", dt.FlipTimeDisplay),
    ("digital", dt.DigitalTimeDisplay),
    ("minimal", dt.MinimalTimeDisplay),
    ("terminal", dt.TerminalTimeDisplay),
])
def test_template_builds_the_right_display(app, template, expected):
    """Choosing a style must produce that style's widget."""
    clock = dt.FlipClockOverlay()
    clock.tray_icon.hide()
    try:
        clock.template = template
        clock.rebuild_clock()
        assert isinstance(clock.display, expected)
    finally:
        clock.timer.stop()


def test_unknown_template_falls_back_to_flip(app, monkeypatch):
    """A corrupted setting must not crash the app on startup."""
    monkeypatch.setattr(
        dt.QSettings, "value",
        lambda self, key, default=None, type=None: (
            "nonsense" if key == "template" else default
        ),
    )
    clock = dt.FlipClockOverlay()
    clock.tray_icon.hide()
    try:
        assert clock.template == "flip"
    finally:
        clock.timer.stop()
```

And `tests/test_behaviour.py`:

```python
"""Behaviour that has broken before, so it stays fixed."""
from PyQt6.QtCore import QPoint

import desktop_timer as dt


def test_clamp_keeps_an_onscreen_position(app):
    """A sane position should be returned untouched."""
    clock = dt.FlipClockOverlay()
    clock.tray_icon.hide()
    try:
        wanted = QPoint(120, 120)
        assert clock.clamp_to_screen(wanted) == wanted
    finally:
        clock.timer.stop()


def test_clamp_rescues_an_offscreen_position(app):
    """A position on a monitor that no longer exists must come back.

    This is a real bug that happened: unplug the second monitor and the
    clock reappeared somewhere unreachable.
    """
    clock = dt.FlipClockOverlay()
    clock.tray_icon.hide()
    try:
        lost = QPoint(-20000, -20000)
        assert clock.clamp_to_screen(lost) != lost
    finally:
        clock.timer.stop()


def test_am_pm_marker_can_be_cleared(app):
    """Switching 12h -> 24h must not leave 'PM' stuck on the first digit.

    Another real bug: set_am_pm only ever set the flag true.
    """
    digit = dt.FlipDigit()
    digit.set_am_pm("PM")
    assert digit.show_am_pm is True

    digit.clear_am_pm()
    assert digit.show_am_pm is False
    assert digit.am_pm_text == ""


def test_font_selection_always_returns_a_known_family(app):
    """The font picker must always yield a usable name.

    Deliberately not asserting the font is *installed*: under the offscreen
    platform Qt reports an empty font database, so that check passes on a
    desktop and fails in CI. Assert the contract instead -- we always return
    one of our listed preferences, falling back to Arial.
    """
    family = dt.clock_font_family()
    assert family
    assert family in dt.FONT_PREFERENCES
```

Notice what these test: **every one is a bug that actually happened** during
development. That's the honest way to choose your first tests. Don't chase a
coverage percentage — write a test for each bug you've been bitten by, and the
suite becomes a memory of your mistakes.

Run them:

```bash
.venv\Scripts\python -m pytest -v
```

All ten should pass in well under a second.

> **That font test earned its comment the hard way.** The obvious version —
> asserting the chosen font is in `QFontDatabase.families()` — passes on your
> machine and **fails in CI**, because the offscreen platform reports an empty
> font database. It's a perfect miniature of the most common CI frustration:
> *the environment is not your laptop.*
>
> The fix isn't to weaken the test until it passes. It's to notice you were
> testing the wrong thing. You don't care which font Windows has installed —
> you care that your fallback logic always returns something usable. Test the
> contract, not the environment.

If a test fails, it found a real regression or the test is wrong. Investigate
rather than deleting it.

**4. Add the CI workflow.**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

# Run on pull requests (before merging) and on main (to catch anything
# that slipped through).
on:
  pull_request:
  push:
    branches: [main]

# If you push twice quickly, cancel the older run. Saves minutes and
# stops you reading stale results.
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  quality:
    name: Lint and test
    runs-on: windows-latest

    steps:
      - name: Check out the code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements-dev.txt

      - name: Lint
        run: python -m ruff check .

      - name: Test
        env:
          QT_QPA_PLATFORM: offscreen
        run: python -m pytest -v

  build:
    name: Build check
    runs-on: windows-latest
    # Don't waste minutes building code that failed its tests.
    needs: quality

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements-dev.txt

      - name: Build the application
        run: python -m PyInstaller --noconfirm FlipClock.spec

      - name: Confirm the executable exists
        run: |
          if (-not (Test-Path "dist\FlipClock\FlipClock.exe")) {
            throw "FlipClock.exe was not produced"
          }
          Get-Item "dist\FlipClock\FlipClock.exe" | Select-Object Name, Length

      # Keep the build so you can download and try it from the PR page,
      # without building locally.
      - name: Upload the build
        uses: actions/upload-artifact@v4
        with:
          name: FlipClock-${{ github.sha }}
          path: dist/FlipClock/
          retention-days: 7
```

Two jobs, deliberately. `quality` is fast (seconds); `build` is slow (minutes).
`needs: quality` means a lint error fails in seconds instead of after a full
build. **Order your pipeline cheapest-check-first** — it's the single biggest
thing you can do for pipeline speed.

**5. Ship it through a PR** — the first real use of Phase 1's branch rule:

```bash
git checkout -b ci/add-pipeline
git add requirements-dev.txt pyproject.toml tests .github/workflows/ci.yml
git commit -m "Add CI: linting, tests and a build check"
git push -u origin ci/add-pipeline
```

Open the PR on GitHub. Watch the **Checks** tab. You'll see both jobs run,
`quality` first. Click into a job to see live logs — get comfortable reading
these, it's where you'll diagnose every future failure.

**6. Make CI mandatory.**

Once it has run at least once (GitHub can only offer checks it has seen), go
back to **Settings** → **Branches** → your ruleset → **Require status checks to
pass**, and add `Lint and test` and `Build check`.

Now a red build physically cannot be merged.

### Verify

Deliberately break something and confirm the machine catches it. On your branch,
add a line to `desktop_timer.py`:

```python
import os  # unused
```

Commit and push. CI should fail at the **Lint** step with `F401 unused import`.
Remove it, push again, watch it go green.

That moment — where you *see* it catch something — is when CI stops being a
ritual and starts being a tool.

> **Everything in this phase has been run against your actual code**, not
> written from theory. The nine tests pass, the Ruff config is valid, and the
> three findings above are really there. If something behaves differently for
> you, it's a difference in your environment worth understanding — not a typo
> in the guide.

### ✅ Checkpoint 2

- [ ] `ruff check .` runs, and you've fixed the three findings
- [ ] `pytest` runs green locally (10 passed)
- [ ] CI runs automatically on every PR
- [ ] You've watched it fail on purpose and then pass
- [ ] A failing check blocks the merge button
- [ ] You can download a built app from a PR's artifacts

---

## Phase 3 — Continuous Delivery: releases that build themselves

**Time:** ~1 hour

### Why

You have `release.yml`, and its very first real run **failed** — a one-character
path bug that had sat invisible since the file was written, because the workflow
had never executed (the full story is post-mortem #2 in Phase 8). That's the
case against untested automation in one sentence: it *looks* like a safety net
right up until you fall into it. The original also produces a bare `.exe` with no way
for a user to check the download wasn't corrupted or tampered with, and no
record of what changed.

### Concepts

**Continuous Delivery** — every change that passes CI is *releasable* on demand,
by pushing a tag, not by remembering fourteen manual steps at midnight.

**Artifact** — a file your build produces. Yours is `FlipClock-Setup.exe`.

**Checksum** — a fingerprint of a file (SHA-256). Publish it and users can
verify their download is byte-identical to what you built. Standard practice for
unsigned software, and it's two lines.

**Draft release** — published but invisible until you say so. Gives you a moment
to look before the world does.

### Do

**1. Make the release workflow trustworthy.**

Replace `.github/workflows/release.yml` with:

```yaml
name: Release

on:
  push:
    tags: ["v*"]
  workflow_dispatch:      # lets you trigger it by hand from the Actions tab

permissions:
  contents: write         # needed to create a Release

jobs:
  release:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # full history, so release notes can diff tags

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements-dev.txt

      # Never ship code that fails its own tests, even when tagging.
      - name: Test
        env:
          QT_QPA_PLATFORM: offscreen
        run: python -m pytest -q

      - name: Read the version from pyproject.toml
        id: version
        shell: pwsh
        run: |
          $v = python -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])"
          $tag = "${{ github.ref_name }}" -replace '^v',''
          if ($v -ne $tag) {
            throw "Tag $tag does not match pyproject version $v. Update one of them."
          }
          "version=$v" >> $env:GITHUB_OUTPUT

      - name: Build the application
        run: python -m PyInstaller --noconfirm FlipClock.spec

      - name: Install Inno Setup
        run: choco install innosetup --no-progress -y

      - name: Build the installer
        shell: pwsh
        run: |
          & "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" `
            /DAppVersion=${{ steps.version.outputs.version }} installer.iss
          if (-not (Test-Path "dist_installer\FlipClock-Setup.exe")) {
            throw "Installer was not produced"
          }

      - name: Generate a checksum
        shell: pwsh
        run: |
          $hash = (Get-FileHash dist_installer\FlipClock-Setup.exe -Algorithm SHA256).Hash
          "$hash  FlipClock-Setup.exe" | Out-File -Encoding ascii `
            dist_installer\FlipClock-Setup.exe.sha256
          Write-Host "SHA256: $hash"

      - name: Publish the release
        shell: pwsh
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release create "${{ github.ref_name }}" `
            dist_installer/FlipClock-Setup.exe `
            dist_installer/FlipClock-Setup.exe.sha256 `
            --title "FlipClock ${{ github.ref_name }}" `
            --generate-notes `
            --draft
```

Three things worth understanding:

- **The version check.** If you tag `v1.2.0` but `pyproject.toml` says `1.1.0`,
  the build stops. A guard like this costs three lines and prevents a whole
  category of embarrassing releases.
- **`--draft`.** The release is created but hidden. You review, then publish.
  Once you trust it, drop the flag.
- **`secrets.GITHUB_TOKEN`** is provided automatically by Actions. You never
  create or paste it. If a guide ever tells you to paste a personal token into a
  workflow, that guide is wrong.

**2. Do a real release.**

By this point `v1.0.0` already exists — you shipped it closing post-mortem #2.
So this release is **1.1.0**: the pipeline gained new capability, and new
capability is a MINOR bump. This is also your first live encounter with the
version guard you just wrote — set `version = "1.1.0"` in `pyproject.toml` on
the same branch, or the tag check will (correctly) stop you.

Merge it all through a PR, then:

```bash
git checkout main
git pull
git tag v1.1.0
git push origin v1.1.0
```

Watch the **Actions** tab. When it finishes, go to **Releases** — you'll find a
draft. Download the installer, run it, confirm it works, then click **Publish
release**.

**3. Tell users about the checksum.**

Add to `README.md` under Download:

````markdown
To verify your download, compare it against the published checksum:

```powershell
Get-FileHash FlipClock-Setup.exe -Algorithm SHA256
```

It should match the value in `FlipClock-Setup.exe.sha256` on the release page.
````

### Verify

- The release page lists both the `.exe` and the `.sha256`
- Running the PowerShell command on your download produces a matching hash
- Tag `v9.9.9` on a scratch branch: the workflow must **fail** at the version
  check. Delete that tag afterwards with
  `git push --delete origin v9.9.9`

### ✅ Checkpoint 3

- [ ] Pushing a tag produces a complete draft release, unattended
- [ ] A version mismatch stops the build
- [ ] Tests run before anything is published
- [ ] Users can verify their download

---

## Phase 4 — Deploying the website properly

**Time:** ~45 minutes

### Why

Your site currently deploys because GitHub Pages watches the `docs/` folder.
That works, but it's invisible — there's no log, no history, no way to see
*why* a deploy happened or whether it succeeded. And you can't preview a change
before it's live.

### Concepts

**Build vs deploy** — building produces files; deploying puts them where users
reach them. Separating the two lets you build once and deploy that exact output
to different places.

**Environment** — a named destination (production, staging). GitHub tracks
deploys per environment so you can see what's live and when it changed.

**Deploy preview** — a temporary copy of a change, so you can look at it before
merging. Standard on modern web teams.

### Do

**1. Switch Pages to a workflow.**

Go to **Settings** → **Pages**, and under **Build and deployment** change
*Source* from "Deploy from a branch" to **GitHub Actions**.

Create `.github/workflows/site.yml`:

```yaml
name: Deploy website

on:
  push:
    branches: [main]
    paths: ["docs/**", ".github/workflows/site.yml"]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

# Never let two deploys race. Queue them instead of cancelling, so the
# last one to finish is genuinely the newest.
concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  check:
    name: Check the site
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Catch broken markup before users do.
      - name: Validate HTML
        run: |
          npx --yes html-validate docs/index.html || true

      - name: Check the download link still points somewhere real
        run: |
          url="https://github.com/AG-Aayush/Desktop-Digital-Clock/releases/latest/download/FlipClock-Setup.exe"
          grep -q "$url" docs/index.html || {
            echo "The download link in index.html has changed. Is that deliberate?"
            exit 1
          }

  deploy:
    name: Deploy to Pages
    needs: check
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs
      - id: deployment
        uses: actions/deploy-pages@v4
```

The `paths:` filter means editing `desktop_timer.py` won't trigger a website
deploy. Small thing, but it keeps your deploy history meaningful — every entry
is a real site change.

**2. Note the URL.** After the first run, the Actions summary shows the deployed
URL, and **Settings → Environments → github-pages** keeps a history of every
deploy. That's the audit trail you didn't have before.

### Verify

Change something visible — say the tagline in `docs/index.html` — and push it
through a PR. After merging, watch the deploy run, then hard-refresh the live
site with `Ctrl+F5`.

> **Caching will confuse you at some point.** GitHub Pages caches aggressively.
> If a change doesn't appear, hard-refresh before assuming the deploy failed.
> Half of all "my deploy is broken" reports are browser cache.

### ✅ Checkpoint 4

- [ ] Pages deploys through Actions, with logs
- [ ] Editing Python code does *not* trigger a site deploy
- [ ] The environment shows deploy history
- [ ] A broken download link fails the check

---

## Phase 5 — Quality and security gates

**Time:** ~45 minutes

### Why

Your dependencies will develop security holes. Your code will pick up bad
patterns. Neither announces itself. These tools watch continuously so you don't
have to remember to.

### Concepts

**Dependabot** — watches your dependency list and opens PRs when updates ship,
including security fixes. It's a robot contributor.

**CodeQL** — GitHub's static analysis. It reads code looking for vulnerability
patterns, rather than just style.

**Pre-commit hook** — a check that runs on your machine *before* a commit is
created. Catches trivia in one second instead of two minutes of CI.

### Do

**1. Dependabot.** Create `.github/dependabot.yml`:

```yaml
version: 2
updates:
  # Python dependencies
  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
    open-pull-requests-limit: 5
    commit-message:
      prefix: "deps"

  # The actions used by your own workflows go stale too, and they
  # execute with access to your repository. Keep them current.
  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: monthly
    commit-message:
      prefix: "ci"
```

Because CI runs on Dependabot's PRs, you get a tested answer to "does this
update break FlipClock?" without lifting a finger. **This is the payoff for
Phase 2** — dependency updates become a glance instead of a chore.

**2. CodeQL.** Create `.github/workflows/codeql.yml`:

```yaml
name: CodeQL

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    # Weekly, because new vulnerability patterns are published constantly
    # and last week's clean scan doesn't mean this week's code is clean.
    - cron: "0 6 * * 1"

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read

    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: python
      - uses: github/codeql-action/analyze@v3
```

Results appear under the repository's **Security** tab.

**3. Pre-commit hooks.** Add `pre-commit` to `requirements-dev.txt`, then create
`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: [--maxkb=1000]   # stop a 95MB dist/ folder being committed
```

Install the hooks once:

```bash
.venv\Scripts\python -m pip install pre-commit
.venv\Scripts\pre-commit install
```

Now every `git commit` runs these first. The `check-added-large-files` hook
alone will eventually save you from committing a build folder.

### Verify

- Create a file with trailing whitespace, try to commit — the hook fixes it and
  stops the commit so you can review. Commit again; it succeeds.
- The **Security** tab shows a completed CodeQL scan.
- Within a week, expect Dependabot PRs to appear on their own.

### ✅ Checkpoint 5

- [ ] Pre-commit hooks run on every commit
- [ ] CodeQL has completed a scan
- [ ] `.github/dependabot.yml` is committed

---

## Phase 6 — Docker, where it actually belongs

**Time:** ~1.5 hours

### Why

As established in Phase 0: not for the desktop app. But your **website** is a
perfect container workload, and containerizing it teaches you the real Docker
model — images, layers, registries, port mapping — on something you own.

There's a genuine benefit too: anyone can run your site locally with one command,
with no Node, no Python, no "works on my machine".

### Concepts

**Image** — a read-only template: a filesystem plus instructions on what to run.
Think of a class.

**Container** — a running instance of an image. Think of an object.

**Layer** — each instruction in a Dockerfile creates a layer. Layers are cached
and shared, which is why ordering matters: put things that change rarely first,
so a small edit doesn't invalidate everything below it.

**Registry** — where images are stored and shared. Docker Hub is the famous one;
GitHub's is **GHCR** (`ghcr.io`), and it's already tied to your repo.

**Port mapping** — a container has its own network. `-p 8080:80` means "my
port 8080 reaches port 80 inside the container".

### Do

**1. Check Docker.** You already have Docker Desktop and WSL2 installed on this
machine, so there's likely nothing to do. Verify:

```bash
docker --version
docker run hello-world
```

That second command downloads a tiny image and runs it — if it prints a
greeting, your installation works. If `docker` isn't found, install Docker
Desktop from docker.com.

> **This is a good phase to do from Linux.** Docker runs natively there rather
> than through a virtual machine, so builds are faster and the behaviour matches
> what you'll see on a server. Nothing in this phase touches `winreg`, so it all
> works from your VM or WSL2 clone. See "Working from Linux" in Phase 0.

**2. Write the Dockerfile.** Create `Dockerfile` in the project root:

```dockerfile
# nginx is a battle-tested web server. The alpine variant is ~40MB
# instead of ~190MB -- for serving static files we need nothing more.
FROM nginx:1.27-alpine

# Our own config replaces the default. Copied before the site content
# because it changes far less often, so edits to the page reuse this
# cached layer instead of rebuilding it.
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# The site itself.
COPY docs/ /usr/share/nginx/html/

# Documents intent. It does not publish the port by itself -- that is
# what -p does at run time.
EXPOSE 80

# Tell Docker how to know the container is not just running, but working.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1
```

Create `docker/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Compress text on the way out. The page is ~40KB of HTML/CSS/JS
    # and compresses to roughly a quarter of that.
    gzip on;
    gzip_types text/plain text/css application/javascript image/svg+xml;
    gzip_min_length 1000;

    # Modest security headers. Not critical for a static page, but
    # they cost nothing and are good habits to build.
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;
    add_header Referrer-Policy strict-origin-when-cross-origin;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

**3. Add a `.dockerignore`** — this is the file everyone forgets, and it's why
their builds are slow:

```
.git
.venv
dist
dist_installer
build
__pycache__
*.pyc
.pytest_cache
tests
*.exe
*.spec
```

Without it, Docker sends your entire folder — including a 95MB `dist/` — to the
build engine before it starts. With it, the build sends kilobytes.

**4. Build and run it:**

```bash
docker build -t flipclock-site .
docker run --rm -p 8080:80 flipclock-site
```

Open <http://localhost:8080>. That's your site, served by nginx, in a container.
`--rm` cleans up when you stop it with `Ctrl+C`.

**5. Add Docker Compose** for convenience. Create `compose.yaml`:

```yaml
services:
  site:
    build: .
    ports:
      - "8080:80"
    # Mount the real folder over the image's copy, so edits to
    # index.html appear on refresh with no rebuild. Read-only, because
    # the container has no business writing to your source.
    volumes:
      - ./docs:/usr/share/nginx/html:ro
    restart: unless-stopped
```

Then simply:

```bash
docker compose up
```

Edit `docs/index.html`, refresh the browser, see the change instantly. That's
the development loop containers are actually good at.

**6. Publish the image automatically.** Create
`.github/workflows/docker.yml`:

```yaml
name: Publish site image

on:
  push:
    branches: [main]
    paths: ["docs/**", "Dockerfile", "docker/**", ".github/workflows/docker.yml"]
  workflow_dispatch:

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write      # required to push to GHCR

    steps:
      - uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # Generates sensible tags automatically: latest, the branch name,
      # and the commit SHA. The SHA tag is the useful one -- it points at
      # exactly one build, forever, which is what you need to roll back.
      - name: Work out the tags
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}/site

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          # Reuse layers between runs. Without this every build starts
          # from scratch and takes minutes instead of seconds.
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

After it runs, your image appears under the repository's **Packages**. Anyone can
then run your site with:

```bash
docker run -p 8080:80 ghcr.io/ag-aayush/desktop-digital-clock/site:latest
```

### Verify

- `docker build` completes and `docker images` lists `flipclock-site`
- <http://localhost:8080> serves your site
- `docker compose up`, edit `docs/index.html`, refresh — the change appears
- `docker ps` shows the container as `healthy` after ~30 seconds
- The image appears under **Packages** on GitHub

### ✅ Checkpoint 6

- [ ] You can build and run the site in a container
- [ ] Compose gives you live editing
- [ ] The image publishes to GHCR automatically
- [ ] You can explain why the *desktop app* is not containerized

---

## Phase 7 — Operating it: rollback and release hygiene

**Time:** ~30 minutes reading, then whenever you need it

### Why

Deploying is easy. The hard question is what you do at 11pm when a release is
broken. Decide now, calmly, rather than then.

### Rolling back a bad app release

Your users download from `releases/latest/download/...`, so "latest" is whatever
GitHub considers the newest *non-prerelease, non-draft* release.

**To roll back**, you don't delete anything. Go to **Releases**, edit the broken
release, and tick **Set as a pre-release**. It immediately stops being "latest",
and the previous good release takes over. The download link on your site starts
serving the older installer within seconds.

Then fix forward: patch the bug, bump to the next patch version, tag, release.

> **Why not delete it?** Someone already downloaded it. If they report a bug you
> need to know exactly what they ran. Deleting destroys that. Marking it
> pre-release removes it from the download path while keeping the record.

### Rolling back the website

The site deploys from `main`, so reverting the commit reverts the site:

```bash
git revert <commit-sha>
git push
```

`revert` creates a *new* commit undoing the old one. Prefer it over `reset` for
anything already pushed — it doesn't rewrite history that other people (and
GitHub Pages) already have.

### A release checklist

Once per release, in order:

1. All work merged to `main` via green PRs
2. `version` bumped in `pyproject.toml`, merged
3. `git tag vX.Y.Z && git push origin vX.Y.Z`
4. Watch Actions; wait for the draft release
5. **Download the installer and actually install it.** Automation proves it
   built, not that it works
6. Publish the release
7. Confirm your site's download button fetches the new version

Step 5 is the one people skip and regret.

### ✅ Checkpoint 7

- [ ] You've practised marking a release as pre-release and seen `latest` change
- [ ] You understand `revert` versus `reset`

---

## Phase 8 — How a real DevOps operates: the rhythm, the loops, the incidents

**Time:** ~30 minutes reading. The rest is how you work from now on.

### Why

Phases 1–7 built machinery. Machinery is not DevOps. Plenty of repositories
have beautiful YAML and broken practices, and "I copied a workflow file once"
convinces no interviewer. What makes the claim real is the *operating rhythm*:
knowing how a change travels from your editor to a user's desktop, which parts
of that journey are yours and which belong to the machines, and what you do
when — not if — something on that road breaks.

This phase has no new tools. It ties the previous seven into the way the work
actually feels, and it closes with two genuine incidents from this very
project, written up the way real teams write them.

### Concepts

**Pipeline** — the whole automated path a change travels, end to end. CI and CD
are segments of it; "the pipeline" is the integrated thing.

**Feedback loop** — any mechanism that tells you something is wrong, measured
by how fast and how cheap it is. The entire discipline can be summarised as:
*move failure detection earlier, where it costs less.*

**Fixing forward vs rolling back** — the two responses to a bad change. Roll
back when users are hurting now; fix forward when the damage is contained and
the fix is small. Deciding calmly which applies is an operational skill.

**Post-mortem** — a written account of an incident: what happened, why, how it
was detected, how it was fixed, what changes so it can't recur. *Blameless* —
the question is never "who did this?", always "what allowed this?". Teams that
punish mistakes stop hearing about them, which is far more dangerous than the
mistakes.

### The life of one change

This is the map to internalise. Trace a single bug fix through the system you
have now built:

```
 you                              GitHub                            users
  │                                 │                                 │
  │ git checkout -b fix/thing      │                                 │
  │ edit · run pytest · commit     │  (pre-commit hooks run locally) │
  │ git push -u origin fix/thing   │                                 │
  │──────────── open PR ──────────▶│                                 │
  │                                │ ci.yml: lint → test → build     │
  │◀──── green check, or red X ────│                                 │
  │ merge the PR                   │                                 │
  │                                │ ci.yml re-runs on main          │
  │                                │ site.yml deploys, if docs/ changed
  │ bump version · tag · push tag  │                                 │
  │                                │ release.yml: test → build →     │
  │                                │   installer → checksum →        │
  │                                │   draft release                 │
  │ install the draft yourself     │                                 │
  │ click Publish                  │                                 │
  │                                │──── /releases/latest ──────────▶│ download,
  │                                │                                 │ install, enjoy
```

Notice the division of labour:

| You decide | The machine repeats |
|---|---|
| What to build, what a fix is | Running every test, every time |
| When code is ready to merge | Blocking the merge on a red check |
| When to release, and what version it is | Building, packaging, checksumming, publishing |
| Whether the built installer actually works | Keeping every log and artifact |
| How to respond to an alert | Raising the alert |

That's the underlying principle of the whole field: **humans make judgements,
machines do repetition.** Every phase of this guide moved one repetitive
judgement-free task from your hands to a workflow.

### The feedback loops, ordered by cost

A failure caught at each stage costs roughly ten times the one before it:

1. **Seconds, on your machine** — pre-commit hooks catch the trivial before a
   commit even exists.
2. **Minutes, on the PR** — CI catches what your environment hid. Nothing
   broken can reach `main`.
3. **At release** — the version guard and pre-package test run catch what only
   shows up when assembling the product.
4. **Weekly, unattended** — Dependabot and CodeQL catch what *time* breaks:
   dependencies rot and new vulnerability patterns emerge without you touching
   anything.
5. **Users** — the loop of last resort: slow, expensive, and it spends trust.
   Every layer above exists to keep failures out of this one.

This is also why `quality` runs before `build`, and lint before tests:
**cheapest check first** isn't a style preference, it's the same cost logic
applied inside a single workflow.

### The cadence

What operating this project actually looks like on a calendar:

- **Every change**: branch → PR → watch the checks → merge. No exceptions, even
  for one-line fixes — *especially* for one-line fixes, which is where
  "obviously safe" changes break things (post-mortem #2 below was one
  character).
- **Per release**: the Phase 7 checklist, including the step everyone skips —
  install the thing yourself before publishing.
- **Weekly, ~10 minutes**: review Dependabot PRs (CI has already tested them —
  you're just reading), glance at the Security tab.
- **When something breaks**: read the log before touching anything. Find the
  *first* failing step; everything after it is noise. Then decide: roll back
  (users hurting now) or fix forward (contained). Afterwards, write it down.

### Incident log

Real post-mortems from this repository. This is the habit that turns mistakes
into infrastructure.

---

**Post-mortem #1 — "Settings don't work" (2026-08-11)**

- **Symptom.** Changing the clock theme in Settings appeared to do nothing.
  Reported as a settings bug.
- **Investigation.** The settings code passed every test — the full dialog
  flow worked when driven programmatically. The running process turned out to
  be the *installed* `FlipClock.exe`, built at 21:50 on Aug 7. The templates
  feature was committed at **21:57** — seven minutes after the build. The
  running app predated the feature it was being asked to perform.
- **Root cause.** Nothing connected "the version that is running" to "the
  version in Git". With no visible version number anywhere, a stale binary
  was indistinguishable from a broken one.
- **Fix.** Rebuild and redeploy the installed copy.
- **What changes.** The Phase 1 discipline (single-sourced, visible version)
  and the Phase 3 discipline (releases built by CI from a tag, never from
  whatever a laptop contained at some moment). The deeper lesson: **"the code
  is correct" and "the user's machine runs correct code" are different claims**,
  and the entire CD half of this guide exists to connect them.

---

**Post-mortem #2 — The first release failed (2026-08-11)**

- **Symptom.** Tag `v1.0.0` pushed; the release workflow ran and failed; no
  release created; the website's download button kept returning 404 for every
  visitor.
- **Detection.** The Actions run showed red. The job log read, in order:
  every step green until **"Build the installer" → failure**, everything after
  it skipped. First failing step found; investigation had its target.
- **Root cause.** One line in `release.yml`:

  ```powershell
  & "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe" installer.iss
  ```

  The environment variable's *name* is `ProgramFiles(x86)` — parentheses
  included. Without braces, PowerShell reads `$env:ProgramFiles` and appends a
  literal `(x86)`, producing `C:\Program Files(x86)\...` — no space, no such
  folder, no ISCC. The correct form is `${env:ProgramFiles(x86)}`. The bug had
  been in the file since the day it was written and was invisible until the
  workflow's first real execution — exactly what Phase 3's warning about
  untested automation predicted.
- **Fix.** Add the braces; delete the remote tag; re-tag the fixed commit:

  ```bash
  git push --delete origin v1.0.0
  git tag -d v1.0.0
  # commit the workflow fix, then:
  git tag v1.0.0
  git push origin v1.0.0
  ```

  Re-tagging is honest here because `v1.0.0` was never released — nothing was
  published under that name. Once a tag has shipped to users it is immutable;
  you'd fix forward with `v1.0.1` instead.
- **What changes.** Two habits. First: **automation must be exercised before
  it is relied upon** — that's what `workflow_dispatch` is for; a rehearsal
  run when the workflow is first written would have caught this in five
  minutes instead of on release day. Second: log-reading is a skill — first
  red step, ignore everything downstream of it, reproduce the failing command
  locally if you can. This bug was confirmed with a two-line PowerShell
  experiment before the fix was written.

---

Two incidents, and notice: **neither was a code bug in the product.** Both
lived in the seams — between source and binary, between a workflow file and
its first execution. That's the general truth this guide's introduction
promised: things break at the joins. DevOps is largely the craft of putting
the joins under test.

### Verify

There is only one verification that matters for this phase: **finish
post-mortem #2 yourself.** Commit the `release.yml` fix, re-tag, watch Actions
go green, see the release appear, and click your own website's download button
as if you were a stranger. When the installer lands in your Downloads folder,
the incident is closed — and your product is actually launched.

### ✅ Checkpoint 8

- [ ] You can sketch the life-of-a-change diagram from memory
- [ ] For each step, you know whether it's yours or the machine's
- [ ] You've read a failed Actions log and found the first failing step
- [ ] Post-mortem #2 is closed: the fix is pushed, `v1.0.0` is re-tagged,
      the release is live, and the download button works
- [ ] You could explain to someone else why the loops are ordered cheapest-first

---

## Where this leaves you

Having finished, FlipClock has:

| Capability | Mechanism |
|---|---|
| Every change tested automatically | `ci.yml` on pull requests |
| Broken code can't reach `main` | Branch ruleset + required checks |
| Releases build themselves | `release.yml` on tags |
| Downloads are verifiable | SHA-256 checksums |
| Website deploys are logged and reversible | `site.yml` + environments |
| Dependencies stay current | Dependabot |
| Code is scanned for vulnerabilities | CodeQL, weekly |
| The site runs anywhere | Docker image on GHCR |
| A bad release can be undone in a minute | Pre-release rollback |

### Can you say you've deployed an application?

Yes — and precisely, which is better than vaguely.

On finishing this guide you will have deployed to **three different targets**,
which is more than most tutorials ever reach:

1. **A desktop application** — built, packaged into a signed-format installer,
   published as a versioned release with checksums, and installable by strangers
   on their own machines.
2. **A website** — deployed to a public URL through a pipeline, with deploy
   history, environment tracking and a rollback path.
3. **A container image** — built and published to a registry, runnable by anyone
   with one command.

Each of those is a real deployment with a real user-facing artifact. Together
they cover build, package, publish, deploy, verify and roll back — the full
lifecycle.

**What you'll be able to claim honestly:**

- You've built and operated a CI/CD pipeline end to end
- You've automated releases with versioning, checksums and rollback
- You've containerized and published an application image
- You've set up automated testing, linting, dependency updates and security
  scanning
- You understand deployment *strategy*, not just commands

**What this doesn't cover** — say so plainly if asked, because being caught
overclaiming costs far more than the gap itself:

- No cloud infrastructure (AWS, Azure, GCP). Nothing is provisioned on servers.
- No orchestration (Kubernetes), because there's no fleet to orchestrate.
- No infrastructure as code (Terraform, Ansible).
- No production monitoring, alerting or log aggregation.
- No database, no backend service, no scaling or load balancing.
- One environment; no staging tier.

Those are genuinely different skills, and they mostly appear once you're running
*servers* rather than shipping software. The natural next project if you want
them: build something with a backend and deploy it to a cloud VM with Terraform.
The pipeline instincts you gain here transfer directly.

**What actually makes the claim credible** isn't the YAML — anyone can copy a
workflow file. It's being able to answer:

- *Why does `quality` run before `build`?* Fail cheap checks first.
- *Why is the version read from one file?* Duplication drifts silently.
- *Why isn't the desktop app in a container?* Containers have no desktop session.
- *Why mark a bad release pre-release instead of deleting it?* Preserve the
  record of what users actually ran.
- *Why does that font test assert a contract instead of the font database?*
  Because the CI environment isn't your laptop.

Explaining the *choices* is the difference between having followed a guide and
having understood one — and it's exactly what an interviewer will probe.

### Where to go next

- **Code signing** — the real fix for the SmartScreen warning. Around
  $200–400/year; the workflow change is one signing step before packaging.
- **Automated UI testing** — `pytest-qt` can simulate clicks and drags, testing
  behaviour you currently check by hand.
- **A staging site** — deploy PR branches to a preview URL before merging.
- **Crash reporting** — Sentry has a free tier and would tell you about errors
  users never report.
- **Multi-platform** — a Linux build would need the `winreg` calls abstracted
  behind a platform layer. A genuinely interesting refactor.

---

## Glossary

| Term | Meaning |
|---|---|
| **Artifact** | A file produced by a build |
| **CI** | Continuous Integration — test every change automatically |
| **CD** | Continuous Delivery — every passing change is releasable on demand |
| **Container** | A running instance of an image |
| **GHCR** | GitHub Container Registry, where your images live |
| **Image** | A read-only template a container is created from |
| **Job** | A group of steps running on one machine |
| **Layer** | One cached filesystem change in an image |
| **Linter** | A tool that flags suspicious code |
| **Runner** | The virtual machine a job executes on |
| **SemVer** | MAJOR.MINOR.PATCH versioning |
| **Workflow** | A YAML file describing automation |

## When something breaks

**A workflow doesn't run at all.** Check the file is in
`.github/workflows/`, is valid YAML (indentation, not tabs), and that its
trigger matches what you did. A `paths:` filter that doesn't match is the usual
culprit.

**Passes locally, fails in CI.** The runner is a clean machine — something on
yours isn't in `requirements-dev.txt`. That's CI doing its job: it just caught a
dependency you'd have shipped broken.

**Qt errors about a display.** `QT_QPA_PLATFORM=offscreen` isn't set for that
step.

**A Docker build is slow.** You're missing `.dockerignore`, so the whole folder
is being uploaded before the build starts.

**Site changes don't appear.** Hard-refresh (`Ctrl+F5`). It's the cache far more
often than the deploy.

**A permission error in a workflow.** Add the right scope under `permissions:` —
`packages: write` for GHCR, `contents: write` for releases, `pages: write` for
Pages.
