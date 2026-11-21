#!/bin/sh
# DeadRamp CI representative subset.
#
# The full suite spans roughly 1,900 test paths across 101 groups and
# stays a local gate. CI instead runs a documented representative
# subset with a fixed selection rule, so the gate is principled and
# reproducible rather than a hand picked list:
#
#   1. Group the 101 groups by category (the name prefix before the
#      tier suffix). There are 41 categories.
#   2. From each category take the alphabetically first group, the
#      lowest tier and earliest built representative of that category.
#   3. In that group run the two smoke gates every group is built to
#      carry: test_main_cli.py (the service starts and serves through
#      its own CLI) and test_negative_control.py (the mutation
#      negative control). Groups missing one of the two files run
#      whichever exists.
#
# Every category is therefore exercised on every push, through the
# same two gates, in a few minutes. Set CI_SUBSET_LIMIT=N to run only
# the first N categories while debugging the subset itself.
set -e
cd "$(dirname "$0")/.."
cats=$(ls groups | sed -E 's/-(l[0-9]+|untiered)$//' | sort -u)
n=0
for c in $cats; do
  g=$(ls -d groups/$c-* | sort | head -1)
  for f in test_main_cli.py test_negative_control.py; do
    if [ -f "$g/tests/$f" ]; then
      echo "== $g $f"
      python3 -m unittest discover -s "$g/tests" -p "$f"
    fi
  done
  n=$((n+1))
  if [ -n "$CI_SUBSET_LIMIT" ] && [ "$n" -ge "$CI_SUBSET_LIMIT" ]; then break; fi
done
echo "subset complete: $n categories"
