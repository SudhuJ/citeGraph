#!/usr/bin/env bash
# Publish dashboard/dist to the gh-pages branch (GitHub Pages: https://sudhuj.github.io/citeGraph/).
# Builds in a throwaway repo so the working tree and other branches are never touched.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f dashboard/dist/index.html ] || { echo "run 'make site' first" >&2; exit 1; }
rev=$(git rev-parse --short HEAD)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp -r dashboard/dist/. "$tmp/"
touch "$tmp/.nojekyll"   # keep Framework's _npm/_file/_observablehq folders (Jekyll drops "_" paths)
git -C "$tmp" init -q -b gh-pages
git -C "$tmp" add -A
git -C "$tmp" commit -q -m "Deploy dashboard ($rev)"
git -C "$tmp" push -q -f "$(git remote get-url origin)" gh-pages
echo "deployed $rev -> https://sudhuj.github.io/citeGraph/"
