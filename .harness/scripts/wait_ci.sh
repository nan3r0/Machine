#!/bin/sh
# Waits until every check on a PR has finished, then prints one line per check. Run from the repo.
# Usage (in the background): wait_ci.sh <pr-number>
pr="$1"
sleep 60
while gh pr checks "$pr" --json bucket --jq '.[].bucket' 2>/dev/null | grep -q pending; do
  sleep 60
done
gh pr checks "$pr" --json name,bucket,link --jq '.[] | "\(.bucket) \(.name) \(.link)"'
echo CI_DONE
