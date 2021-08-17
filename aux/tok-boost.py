#!/usr/bin/env python

"""This script re-tokenizes a few things, so that there is less clutter (fewer differences) in comparison
with utoken. Usage: tok-boost.py < STDIN > STDOUT. Suitable for --b1/b2 in colot-mt-diff.pl"""

import re
import sys

if __name__ == "__main__":
    for line in sys.stdin:
       for _ in range(2):
           line = re.sub('! !', '!!', line)
           line = re.sub('\? \?', '??', line)
           line = re.sub('‹ ‹', '‹‹', line)
           line = re.sub('› ›', '››', line)
       line = re.sub(r" (['’]) (['’]) ", r" \1\2 ", line)
       line = re.sub(r" (['’]) (['’])$", r" \1\2", line)
       line = re.sub(r" (['’]) (d|ll|m|re|s|ve)\b", r" \1\2", line, flags=re.IGNORECASE)
       line = re.sub(r"\b(are|could|did|do|does|had|has|have|is|shall|should|was|were|will|would)n (['’])t\b",
                     r"\1 n\2t", line, flags=re.IGNORECASE)
       line = re.sub(r"\bca n(['’])t\b", r"can n\1t", line, flags=re.IGNORECASE)
       line = re.sub(r"\bcan (['’])t\b", r"can n\1t", line, flags=re.IGNORECASE)
       line = re.sub(r"\bwo n(['’])t\b", r"will n\1t", line, flags=re.IGNORECASE)
       line = re.sub(r"\bwon (['’])t\b", r"will n\1t", line, flags=re.IGNORECASE)
       line = re.sub(r"\b(can)(not)\b", r"\1 \2", line, flags=re.IGNORECASE)
       line = re.sub(r" @-@ (in) @-@ (law)\b", r"-\1-\2", line, flags=re.IGNORECASE)
       print(line.rstrip())

