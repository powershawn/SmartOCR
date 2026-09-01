# SmartOCR Tech Favicon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact technology-themed SVG favicon to SmartOCR and deploy only the rebuilt frontend service to EC2.

**Architecture:** Vite copies a static `frontend/public/favicon.svg` asset into the production root, while `frontend/index.html` declares it explicitly. A Python standard-library test validates the HTML link, SVG structure, required brand colors, and absence of active or externally loaded SVG content before the frontend Docker build and targeted Compose deployment.

**Tech Stack:** SVG, HTML, Python `pytest` and `xml.etree.ElementTree`, Vue 3/Vite, Docker Compose, Nginx

---

## File map

- Create `frontend/tests/test_favicon.py`: real-file regression tests for favicon linkage and SVG safety/design invariants.
- Create `frontend/public/favicon.svg`: the standalone scan-frame and circuit-node vector favicon.
- Modify `frontend/index.html`: declare `/favicon.svg` as the browser favicon.

### Task 1: Add the favicon through TDD

**Files:**
- Create: `frontend/tests/test_favicon.py`
- Create: `frontend/public/favicon.svg`
- Modify: `frontend/index.html`

- [ ] **Step 1: Write the failing real-file tests**

Create `frontend/tests/test_favicon.py`:

```python
from pathlib import Path
from xml.etree import ElementTree


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
FAVICON_PATH = FRONTEND_ROOT / "public" / "favicon.svg"
INDEX_PATH = FRONTEND_ROOT / "index.html"


def test_index_declares_svg_favicon() -> None:
    index = INDEX_PATH.read_text(encoding="utf-8")

    assert '<link rel="icon" type="image/svg+xml" href="/favicon.svg" />' in index


def test_favicon_is_safe_standalone_svg() -> None:
    root = ElementTree.parse(FAVICON_PATH).getroot()
    local_name = root.tag.rsplit("}", 1)[-1]
    forbidden = {"script", "image", "foreignObject", "use"}
    element_names = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
    linked_attributes = {
        attribute.rsplit("}", 1)[-1]
        for element in root.iter()
        for attribute in element.attrib
        if attribute.rsplit("}", 1)[-1] == "href"
    }
    source = FAVICON_PATH.read_text(encoding="utf-8")

    assert local_name == "svg"
    assert root.attrib["viewBox"] == "0 0 64 64"
    assert forbidden.isdisjoint(element_names)
    assert not linked_attributes
    assert "#07111f" in source
    assert "#22d3b6" in source
```

- [ ] **Step 2: Run the focused test and verify RED**

Run from the repository root:

```powershell
python -m pytest frontend/tests/test_favicon.py -v
```

Expected: two failed tests. The HTML assertion fails because no favicon link exists, and SVG parsing fails with `FileNotFoundError` because `frontend/public/favicon.svg` does not exist.

- [ ] **Step 3: Create the approved SVG asset**

Create `frontend/public/favicon.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-labelledby="title">
  <title id="title">SmartOCR scanning circuit</title>
  <rect x="4" y="4" width="56" height="56" rx="14" fill="#07111f"/>
  <rect x="5" y="5" width="54" height="54" rx="13" fill="none" stroke="#16324a" stroke-width="2"/>
  <g fill="none" stroke="#22d3b6" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
    <path d="M20 14h-6v7"/>
    <path d="M44 14h6v7"/>
    <path d="M20 50h-6v-7"/>
    <path d="M44 50h6v-7"/>
  </g>
  <g fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round">
    <path d="M8 26h6M8 38h6M50 26h6M50 38h6"/>
  </g>
  <g fill="#38bdf8">
    <circle cx="8" cy="26" r="2"/>
    <circle cx="8" cy="38" r="2"/>
    <circle cx="56" cy="26" r="2"/>
    <circle cx="56" cy="38" r="2"/>
  </g>
  <rect x="21" y="18" width="22" height="28" rx="4" fill="#0a1b2b" stroke="#38bdf8" stroke-width="2"/>
  <g fill="none" stroke="#22d3b6" stroke-width="3" stroke-linecap="round">
    <path d="M26 26h12"/>
    <path d="M26 32h9"/>
    <path d="M26 38h12"/>
  </g>
</svg>
```

- [ ] **Step 4: Declare the favicon in the document head**

Add the following immediately after the existing `theme-color` meta element in `frontend/index.html`:

```html
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
```

- [ ] **Step 5: Run the focused tests and verify GREEN**

```powershell
python -m pytest frontend/tests/test_favicon.py -v
```

Expected: `2 passed`.

- [ ] **Step 6: Verify XML, formatting, and production build**

```powershell
python -c "from xml.etree import ElementTree; ElementTree.parse(r'frontend/public/favicon.svg'); print('SVG_OK')"
git diff --check
docker build --target build -t smartocr-frontend-favicon-verify ./frontend
```

Expected: `SVG_OK`, no whitespace errors, and Docker build exits 0 after `vue-tsc --noEmit` and Vite build.

- [ ] **Step 7: Commit the favicon implementation**

```powershell
git add -- frontend/tests/test_favicon.py frontend/public/favicon.svg frontend/index.html
git commit -m "feat: add SmartOCR tech favicon"
```

Expected: one commit containing only the three implementation files.

### Task 2: Publish the reviewed favicon to GitHub main

**Files:**
- Verify only; no new files

- [ ] **Step 1: Run the final focused and frontend build verification**

```powershell
python -m pytest frontend/tests/test_favicon.py -v
docker build --target build -t smartocr-frontend-favicon-verify ./frontend
git diff --check
git status --short
```

Expected: two tests pass, Docker build exits 0, no whitespace errors, and the worktree is clean.

- [ ] **Step 2: Prove the push is a fast-forward**

```powershell
$remoteMain = (git ls-remote --heads origin main).Split()[0]
git merge-base --is-ancestor $remoteMain HEAD
git rev-parse HEAD
```

Expected: the ancestry command exits 0. If it does not, stop without pushing.

- [ ] **Step 3: Push without force using the repository-owner credential selection**

```powershell
git -c credential.username=powershawn push origin HEAD:main
git ls-remote --heads origin main
git rev-parse HEAD
```

Expected: GitHub `main` and local `HEAD` print the same commit SHA. No stored credentials are modified.

### Task 3: Deploy only the frontend service on EC2

**Files:**
- Update remote checkout: `/home/ubuntu/docker/smartocr`
- Preserve remote `.env` and all named volumes

- [ ] **Step 1: Verify the remote checkout is safe to fast-forward**

```bash
cd /home/ubuntu/docker/smartocr
test -f .env
test -z "$(git status --short)"
git fetch origin main
git merge-base --is-ancestor HEAD origin/main
```

Expected: `.env` exists, checkout is clean, and the current deployed commit is an ancestor of `origin/main`. Do not print `.env`.

- [ ] **Step 2: Fast-forward the checkout**

```bash
git pull --ff-only origin main
git rev-parse HEAD
```

Expected: pull succeeds and the SHA matches GitHub `main` from Task 2.

- [ ] **Step 3: Build and replace only frontend**

```bash
docker compose build frontend
docker compose up -d --no-deps frontend
docker compose ps
```

Expected: frontend is rebuilt and running on `0.0.0.0:80`; backend and healthy database remain running, and no volumes are deleted or recreated.

- [ ] **Step 4: Verify the deployed asset**

```bash
curl --fail --silent --show-error --output /dev/null --write-out '%{http_code} %{content_type}\n' http://127.0.0.1/favicon.svg
curl --fail --silent --show-error http://127.0.0.1/ | grep -F '<link rel="icon" type="image/svg+xml" href="/favicon.svg">'
```

Expected: favicon responds `200 image/svg+xml`, and the deployed HTML contains the favicon link. Services remain running after verification.
