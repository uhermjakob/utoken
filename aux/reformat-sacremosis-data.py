#!/usr/bin/env python

"""Script reformats Sacremoses nonbreaking_prefix file to utoken format"""

import logging as log
import regex
import sys


if __name__ == "__main__":
    log.basicConfig(level=log.INFO)
    lcode = sys.argv[1] if len(sys.argv) >= 2 else None
    line_number = 0
    section_name = None
    comment = None
    for line in sys.stdin:
        line_number += 1
        prev_comment = comment
        comment = None
        if regex.match(r'\s*$', line):
            section_name = None
        elif m := regex.match(r'#\s*(consonants|phonetics)', line):
            section_name = m.group(1)
        elif m := regex.match(r'#\s*(\S|\S.*\S)\s*$', line):
            comment = m.group(1)
        elif m2 := regex.match(r'((?:\pL|\d).*?)(\s+#.*|\s*)$', line):
            abbreviation = m2.group(1) + '.'
            out = f'::abbrev {abbreviation}'
            if lcode:
                out += f' ::lcode {lcode}'
            if section_name == 'consonants':
                out += f' ::token-category consonant'
            elif section_name == 'phonetics':
                out += f' ::token-category phonetics'
            if '#NUMERIC_ONLY#' in m2.group(2):
                out += r' ::right-context \s*\d'
            if prev_comment:
                out += f' ::eng {prev_comment}.'
            print(out)
