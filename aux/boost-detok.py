#!/usr/bin/env python

"""This script de-tokenizes a few things, so that there is less clutter (fewer differences) in comparison
with detokenize. Usage: boost-detok.py < STDIN > STDOUT. Suitable for --b1/b2 in colot-mt-diff.pl"""

import re
import regex
import sys

if __name__ == "__main__":
    for line in sys.stdin:
        line = ' ' + line.strip() + ' '
        line = re.sub('', '™', line)
        line = re.sub('', '‘', line)
        line = re.sub('', '’', line)
        line = re.sub('', '”', line)
        line = re.sub('', '“', line)
        line = re.sub('', '–', line)
        line = re.sub('', '—', line)
        for _ in range(2):
            line = re.sub(r" (['’])(d|em|m|re|s|ve) ", r'\1\2 ', line)
            line = re.sub(r'(\d) ([%]) ', r'\1\2 ', line)
            line = re.sub(r' ([$]|US$|RMB) (\d)', r' \1\2', line)
            line = regex.sub(r'(\pL) ([:]) ', r'\1\2 ', line)
            line = re.sub(r' ([(“‘\[]) ', r' \1', line)
            line = re.sub(r' ([)!?”])', r'\1', line)
            line = re.sub(r' ([.,;।’!?]’?”?’?\'?"?\)?]?”?|!+|\?+) ', r'\1 ', line)
            line = re.sub(r' (can) (not) ', r' \1\2 ', line, flags=re.IGNORECASE)
            line = re.sub(r" ([i’]) s ", "\1s ", line)
            line = re.sub(r'(, ") ([a-z])', r'\1\2', line, flags=re.IGNORECASE)
            line = re.sub(r"\b(are|ca|could|did|do|does|had|has|have|is|sha|should|was|were|wo|would) ?n['’]?t\b",
                          r"\1n't", line, flags=re.IGNORECASE)
        print(line.strip())

