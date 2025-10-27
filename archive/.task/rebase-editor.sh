#!/bin/bash
# Script to automate the interactive rebase editor

# Read the rebase todo file
TODO_FILE="$1"

# Replace pick with reword for specific commits
sed -i '' '
s/^pick 7479bd8/reword 7479bd8/
s/^pick b7585c2/reword b7585c2/
s/^pick eb43de7/reword eb43de7/
s/^pick 882f26b/reword 882f26b/
s/^pick 1f3a021/reword 1f3a021/
s/^pick 89f2414/reword 89f2414/
s/^pick d042455/reword d042455/
s/^pick 90399f3/reword 90399f3/
s/^pick 7d38cf9/reword 7d38cf9/
s/^pick f037426/reword f037426/
s/^pick 8f16629/reword 8f16629/
s/^pick e1fd0ee/reword e1fd0ee/
s/^pick 77c0cce/reword 77c0cce/
s/^pick e327182/reword e327182/
s/^pick cc41de2/reword cc41de2/
s/^pick cd158ba/reword cd158ba/
s/^pick 1805031/reword 1805031/
s/^pick 28f61f8/reword 28f61f8/
s/^pick 8b05def/reword 8b05def/
s/^pick 827ff1f/reword 827ff1f/
' "$TODO_FILE"