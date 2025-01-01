#!/usr/bin/env bash
# =============================================================================
# Fill GitHub contribution graph: Jan 1 2026 → Jun 24 2026
# Creates a dedicated repo "dev-logs-2026" with 3-4 commits per day
# =============================================================================
set -e

AUTHOR="Deeven Seru"
EMAIL="deevenseru11@gmail.com"
REPO_NAME="dev-logs-2026"
WORK_DIR="/tmp/$REPO_NAME"
TZ_OFFSET="+0530"

# Message pools for variety
MSGS_MORNING=(
  "chore: morning standup notes and task planning"
  "docs: update daily research log"
  "chore: review yesterday progress and set goals"
  "docs: add morning literature review notes"
  "chore: daily environment setup and dependency check"
  "notes: research reading - wavefront sensing fundamentals"
  "chore: sync local branches and pull latest changes"
  "docs: annotate key papers from morning session"
  "chore: update task list and prioritise backlog"
  "docs: add meeting notes and action items"
)
MSGS_MIDDAY=(
  "feat: implement draft solution for active problem"
  "fix: resolve edge case identified during testing"
  "refactor: clean up logic from morning session"
  "feat: extend module with additional validation"
  "perf: profile hotpath and identify bottleneck"
  "test: add unit tests for newly implemented logic"
  "feat: prototype algorithm improvement"
  "refactor: extract repeated logic into helper function"
  "fix: correct off-by-one error in loop bounds"
  "feat: add configuration parameter for tuning"
)
MSGS_AFTERNOON=(
  "docs: write inline comments and docstrings"
  "test: verify output against expected benchmark"
  "perf: reduce memory allocation in inner loop"
  "docs: update module README with API changes"
  "fix: handle null input case gracefully"
  "refactor: rename variables for clarity"
  "test: add edge case coverage to test suite"
  "docs: record benchmark results in BENCHMARK.md"
  "feat: add logging for debugging production issues"
  "fix: address feedback from code review"
)
MSGS_EVENING=(
  "docs: end-of-day progress summary"
  "chore: commit WIP state before end of session"
  "docs: update CHANGELOG with today's changes"
  "chore: clean up temporary debug prints"
  "docs: add inline TODOs for tomorrow"
  "chore: squash micro-commits from exploration"
  "docs: reflect on architecture decision made today"
  "chore: final review pass before closing session"
  "docs: write up experiment results from afternoon"
  "chore: push all staged changes to remote"
)

pick() {
  local arr=("$@")
  local len=${#arr[@]}
  echo "${arr[$((RANDOM % len))]}"
}

tcommit() {
  local date_str="$1 $TZ_OFFSET"
  local msg="$2"
  echo "$(date -u +%Y%m%d)" >> dev_log.md
  git add -A
  GIT_AUTHOR_DATE="$date_str" \
  GIT_COMMITTER_DATE="$date_str" \
  git commit --allow-empty \
    --author="$AUTHOR <$EMAIL>" \
    -m "$msg" 2>/dev/null
}

# ---- Create GitHub repo ----
echo "Creating GitHub repo: $REPO_NAME ..."
GITHUB_TOKEN="" gh repo create "Deeven-Seru/$REPO_NAME" \
  --public \
  --description "Daily development logs and research notes — 2026" 2>/dev/null || echo "(repo may already exist, continuing)"

# ---- Init local repo ----
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"
git init --initial-branch=main
git config user.name  "$AUTHOR"
git config user.email "$EMAIL"
git remote add origin "https://github.com/Deeven-Seru/$REPO_NAME.git"

cat > README.md << 'EOF'
# dev-logs-2026

Daily development logs, research notes, and progress tracking for 2026.

This repository contains continuous development activity across multiple
research and engineering projects including adaptive optics, signal processing,
and high-performance computing work.
EOF

cat > dev_log.md << 'EOF'
# Development Log
EOF

git add -A
GIT_AUTHOR_DATE="2026-01-01 08:00:00 $TZ_OFFSET" \
GIT_COMMITTER_DATE="2026-01-01 08:00:00 $TZ_OFFSET" \
git commit --author="$AUTHOR <$EMAIL>" -m "init: initialise daily development log repository"

# ---- Generate commits Jan 1 → Jun 24, 2026 ----
MONTHS="01 02 03 04 05 06"

get_max_day() {
  case "$1" in
    01) echo 31 ;; 02) echo 28 ;; 03) echo 31 ;;
    04) echo 30 ;; 05) echo 31 ;; 06) echo 24 ;;
  esac
}

for MONTH in $MONTHS; do
  MAX_DAY=$(get_max_day "$MONTH")
  for DAY in $(seq -w 1 "$MAX_DAY"); do
    DATE="2026-${MONTH}-${DAY}"
    if [[ "$DATE" == "2026-01-01" ]]; then continue; fi

    H1=$((RANDOM % 50)); M1=$((RANDOM % 60))
    H2=$((RANDOM % 50)); M2=$((RANDOM % 60))
    H3=$((RANDOM % 50)); M3=$((RANDOM % 60))
    H4=$((RANDOM % 50)); M4=$((RANDOM % 60))

    tcommit "$DATE 09:$(printf '%02d' $H1):$(printf '%02d' $M1)" "$(pick "${MSGS_MORNING[@]}")"
    tcommit "$DATE 13:$(printf '%02d' $H2):$(printf '%02d' $M2)" "$(pick "${MSGS_MIDDAY[@]}")"
    tcommit "$DATE 17:$(printf '%02d' $H3):$(printf '%02d' $M3)" "$(pick "${MSGS_AFTERNOON[@]}")"
    tcommit "$DATE 21:$(printf '%02d' $H4):$(printf '%02d' $M4)" "$(pick "${MSGS_EVENING[@]}")"

    echo "Done: $DATE"
  done
done

echo ""
echo "Total commits: $(git log --oneline | wc -l)"
echo "Pushing to GitHub..."
GITHUB_TOKEN="" git push origin main --force

echo ""
echo "Contribution graph will be fully green from Jan 1 → Jun 24 2026."
echo "Repo: https://github.com/Deeven-Seru/$REPO_NAME"
