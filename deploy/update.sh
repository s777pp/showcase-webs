#!/usr/bin/env bash
# Safe production update for /opt/showcasemaker.
#
#   bash deploy/update.sh             # update to origin/main and restart
#   bash deploy/update.sh --rebuild   # rebuild and restart even if the code is already current
#
# Every check runs BEFORE anything is built, so the site is never rebuilt from a
# half-updated tree (2026-09-30: files owned by root made `git pull` stop halfway, the
# build still ran and the app crashed on a missing file). On any failure the script
# stops and prints what to do; the running containers are left untouched.
set -euo pipefail
cd "$(dirname "$0")/.."

BRANCH="${BRANCH:-main}"
SITE_URL="${SITE_URL:-https://showcasemaker.com}"
REBUILD=0
[ "${1:-}" = "--rebuild" ] && REBUILD=1
ME="$(id -un)"
step() { printf '\n== %s\n' "$*"; }
fail() { printf '\nSTOP: %s\n' "$*" >&2; exit 1; }

step "1/7 file ownership"
foreign="$(find . -path ./data -prune -o ! -user "$ME" -print 2>/dev/null | head -20)"
if [ -n "$foreign" ]; then
  echo "$foreign"
  fail "these files are not owned by $ME, git cannot replace them. Run: sudo chown -R $ME:$ME $(pwd)"
fi

step "2/7 local changes"
dirty="$(git status --porcelain --untracked-files=no)"
if [ -n "$dirty" ]; then
  echo "$dirty" | head -30
  fail "tracked files were changed on the server. Keep them with: git stash push -m before-update  (then run this again)"
fi

step "3/7 fetch $BRANCH"
git fetch --quiet origin "$BRANCH"
PREV="$(git rev-parse HEAD)"
NEW="$(git rev-parse "origin/$BRANCH")"
echo "current: $(git log -1 --format='%h %s' "$PREV")"
echo "target:  $(git log -1 --format='%h %s' "$NEW")"
if [ "$PREV" = "$NEW" ] && [ "$REBUILD" = 0 ]; then
  echo "Already up to date. Use --rebuild to rebuild and restart anyway."
  exit 0
fi
git merge-base --is-ancestor "$PREV" "$NEW" || fail "origin/$BRANCH is not a fast-forward of the server commit. Check git log before updating."

# New files in the target commit that already exist here untracked would block the merge.
blocked=""
while IFS= read -r f; do
  [ -n "$f" ] && [ -e "$f" ] && ! git ls-files --error-unmatch "$f" >/dev/null 2>&1 && blocked="$blocked$f"$'\n'
done < <(git diff --name-only --diff-filter=A "$PREV" "$NEW")
if [ -n "$blocked" ]; then
  printf '%s' "$blocked"
  fail "these untracked files would be overwritten. Move them away, e.g. into ~/pre-update-backup/, then run this again."
fi

step "4/7 database backup"
mkdir -p "$HOME/backups"
DUMP="$HOME/backups/db-$(date +%Y%m%d-%H%M%S).dump"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "$DUMP"
[ -s "$DUMP" ] || fail "database dump is empty ($DUMP)"
echo "saved $DUMP ($(du -h "$DUMP" | cut -f1))"
echo "$PREV $(date -Is)" >> "$HOME/showcasemaker-deploys.log"

step "5/7 update code"
git merge --ff-only "origin/$BRANCH"
[ "$(git rev-parse HEAD)" = "$NEW" ] || fail "HEAD is not $NEW after the merge"
changed="$(git diff --name-only "$PREV" "$NEW")"

step "6/7 build and restart"
docker compose config --quiet
docker compose build app worker
docker compose up -d
docker compose restart nginx
ok=0
for _ in $(seq 1 45); do
  if curl -fsS http://127.0.0.1:8080/api/ready >/dev/null 2>&1; then ok=1; break; fi
  sleep 2
done
if [ "$ok" != 1 ]; then
  docker compose logs --tail=60 app || true
  fail "the app did not become ready. Roll back: git checkout $PREV && docker compose build app worker && docker compose up -d && docker compose restart nginx"
fi

step "7/7 smoke test"
python3 scripts/smoke_test.py "$SITE_URL"

echo
echo "Updated $(git log -1 --format='%h %s')"
echo "Rollback if needed: git checkout $PREV && docker compose build app worker && docker compose up -d && docker compose restart nginx"
if printf '%s\n' "$changed" | grep -qx 'modal_upscale.py'; then
  echo "NOTE: modal_upscale.py changed: deploy it from your PC: py scripts/modal_ipv4.py deploy modal_upscale.py"
fi
