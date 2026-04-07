#!/bin/bash
# Wrapper: Claude Code only renders multi-line from separate echo calls.
OUTPUT=$(python "$(dirname "$0")/statusline.py")
LINE1=$(echo "$OUTPUT" | sed -n '1p')
LINE2=$(echo "$OUTPUT" | sed -n '2p')
echo "$LINE1"
[ -n "$LINE2" ] && echo "$LINE2"
