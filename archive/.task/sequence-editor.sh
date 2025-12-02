#!/bin/bash
# This script modifies the rebase todo list

# Mark specific commits for rewording
sed -i '' -e 's/^pick \(7479bd8\)/reword \1/' \
          -e 's/^pick \(b7585c2\)/reword \1/' \
          -e 's/^pick \(eb43de7\)/reword \1/' \
          -e 's/^pick \(882f26b\)/reword \1/' \
          -e 's/^pick \(1f3a021\)/reword \1/' \
          -e 's/^pick \(89f2414\)/reword \1/' \
          -e 's/^pick \(d042455\)/reword \1/' \
          -e 's/^pick \(90399f3\)/reword \1/' \
          -e 's/^pick \(7d38cf9\)/reword \1/' \
          -e 's/^pick \(f037426\)/reword \1/' \
          -e 's/^pick \(8f16629\)/reword \1/' \
          -e 's/^pick \(e1fd0ee\)/reword \1/' \
          -e 's/^pick \(77c0cce\)/reword \1/' \
          -e 's/^pick \(e327182\)/reword \1/' \
          -e 's/^pick \(cc41de2\)/reword \1/' \
          -e 's/^pick \(cd158ba\)/reword \1/' \
          -e 's/^pick \(1805031\)/reword \1/' \
          -e 's/^pick \(28f61f8\)/reword \1/' \
          -e 's/^pick \(8b05def\)/reword \1/' \
          -e 's/^pick \(827ff1f\)/reword \1/' "$1"
