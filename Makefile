SHELL := /usr/bin/env bash
PY := python
PKG := provenance-recorder

.PHONY: help fmt test lint build clean version-bump commit release

help:
	@echo "Targets:"
	@echo "  fmt                 - ruff format"
	@echo "  test                - pytest"
	@echo "  build               - build sdist+wheel"
	@echo "  clean               - remove build artifacts"
	@echo "  version-bump        - bump version (VERSION=x.y.z required)"
	@echo "  release             - fmt+test+build+tag+push (VERSION=x.y.z required)"
	@echo ""
	@echo "Example:"
	@echo "  make release VERSION=0.1.2"

fmt:
	@ruff format prov/*.py tests/*.py

test:
	@$(PY) -m pytest -q

build: clean
	@$(PY) -m pip install -q build
	@$(PY) -m build

clean:
	@rm -rf dist build *.egg-info .pytest_cache

version-bump:
	@if [[ -z "$(VERSION)" ]]; then echo "VERSION is required, e.g. VERSION=0.1.2"; exit 2; fi
	@$(PY) - <<'PY'
import re, pathlib, sys
ver = "$(VERSION)".strip()
if not re.fullmatch(r"\d+\.\d+\.\d+", ver):
    raise SystemExit(f"Invalid VERSION: {ver} (expected x.y.z)")
# pyproject.toml
pp = pathlib.Path("pyproject.toml")
txt = pp.read_text(encoding="utf-8")
txt2, n = re.subn(r'(?m)^version\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"\s*$$', f'version = "{ver}"', txt)
if n != 1:
    raise SystemExit("Could not update version in pyproject.toml (expected exactly one match).")
pp.write_text(txt2, encoding="utf-8")
# prov/version.py fallback
pv = pathlib.Path("prov/version.py")
vtxt = pv.read_text(encoding="utf-8")
vtxt2, n2 = re.subn(r'(?m)^__version__\s*=\s*"[0-9]+\.[0-9]+\.[0-9]+"\s*$$', f'__version__ = "{ver}"', vtxt)
if n2 != 1:
    raise SystemExit("Could not update __version__ in prov/version.py (expected exactly one match).")
pv.write_text(vtxt2, encoding="utf-8")
print(f"Bumped version to {ver}")
PY

release: version-bump fmt test build
	@if [[ -n "$$(git status --porcelain)" ]]; then \
	  echo "Working tree is dirty; commit or stash before release."; exit 2; \
	fi
	@echo "Tagging v$(VERSION)"
	@git tag -a "v$(VERSION)" -m "v$(VERSION)"
	@git push origin main
	@git push origin "v$(VERSION)"
	@echo "Done: v$(VERSION)"

