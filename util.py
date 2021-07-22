#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
"""
# -*- encoding: utf-8 -*-
import logging as log
import re
import sys
from typing import List, Optional

__version__ = '0.0.1'
last_mod_date = 'July 19, 2021'


class AbbreviationEntry:
    """Annotated abbreviation"""
    def __init__(self, abbrev: str, exp: Optional[List[str]], abbrev_type: Optional[str] = None,
                 lcode: Optional[str] = None, country: Optional[str] = None, comment: Optional[str] = None):
        self.abbreviation = abbrev      # e.g. Gen.
        self.expansion = exp            # e.g. General
        self.type = abbrev_type         # e.g. pre-name-title
        self.lcode = lcode              # language code, e.g. eng
        self.country = country
        self.comment = comment


class AbbreviationDict:
    def __init__(self):
        self.abbrev_dict = {}
        self.reverse_abbrev_dict = {}
        self.max_abbrev_length = 0

    def load_abbreviations(self, filename: str) -> None:
        with open(filename) as f_in:
            line_number = 0
            n_warnings = 0
            n_entries = 0
            for line in f_in:
                line_number += 1
                if re.match(r'^\uFEFF?\s*(?:#.*)?$', line):  # ignore empty or comment line
                    continue
                # Check whether cost file line is well-formed. Following call will output specific warnings.
                valid = double_colon_del_list_validation(line, line_number, filename,
                                                         valid_slots=['abbrev', 'exp', 'type', 'lcode', 'country',
                                                                      'comment'],
                                                         required_slots=['abbrev'])
                if not valid:
                    n_warnings += 1
                    continue
                abbreviation = slot_value_in_double_colon_del_list(line, 'abbrev')
                expansion_s = slot_value_in_double_colon_del_list(line, 'exp')
                if expansion_s:
                    expansions = re.split(r';\s*', expansion_s)
                else:
                    expansions = None
                abbrev_type = slot_value_in_double_colon_del_list(line, 'type')
                abbreviation_entry = AbbreviationEntry(abbreviation, exp=expansions, abbrev_type=abbrev_type)
                abbreviation_entry_list = self.abbrev_dict.get(abbreviation, [])
                abbreviation_entry_list.append(abbreviation_entry)
                self.abbrev_dict[abbreviation] = abbreviation_entry_list
                if expansions:
                    for expansion in expansions:
                        rev_abbreviation_list: List[AbbreviationEntry] = self.reverse_abbrev_dict.get(expansion, [])
                        rev_abbreviation_list.append(abbreviation_entry)
                        self.reverse_abbrev_dict[expansion] = rev_abbreviation_list
                if len(abbreviation) > self.max_abbrev_length:
                    self.max_abbrev_length = len(abbreviation)
                n_entries += 1
            log.info(f'Loaded {n_entries} entries from {line_number} lines in {filename}')


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional[str] = None) -> str:
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = re.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else default


def double_colon_del_list_validation(s: str, line_number: int, filename: str,
                                     valid_slots: List[str], required_slots: List[str] = None) -> bool:
    """Check whether a string (typically line in data file) is a well-formed double-colon expression"""
    valid = True
    prev_slots = []
    slots = re.findall(r'::([a-z]\S*)', s, re.IGNORECASE)
    # Check for duplicates and unexpected slots
    for slot in slots:
        if slot in valid_slots:
            if slot in prev_slots:
                valid = False
                log.warning(f'found duplicate slot ::{slot} in line {line_number} in {filename}')
            else:
                prev_slots.append(slot)
        else:
            valid = False
            log.warning(f'found unexpected slot ::{slot} in line {line_number} in {filename}')
    # Check for missing required slots
    if required_slots:
        for slot in required_slots:
            if slot not in prev_slots:
                valid = False
                log.warning(f'missing required slot ::{slot} in line {line_number} in {filename}')
    # Check for ::slot syntax problems
    m = re.match(r'.*?(\S+::[a-z]\S*)', s)
    if m:
        valid = False
        value = m.group(1)
        if re.match(r'.*:::', value):
            log.warning(f"suspected spurious colon in '{value}' in line {line_number} in {filename}")
        else:
            log.warning(f"# Warning: suspected missing space in '{value}' in line {line_number} in {filename}")
    m = re.match(r'(?:.*\s)?(:[a-z]\S*)', s)
    if m:
        valid = False
        log.warning(f"suspected missing colon in '{m.group(1)}' in line {line_number} in {filename}")
    return valid


def increment_dict_count(ht: dict, key: str, increment=1) -> int:
    """For example ht['NUMBER-OF-LINES']"""
    ht[key] = ht.get(key, 0) + increment
    return ht[key]


def join_tokens(tokens: List[str]):
    '''Join tokens with space, ignoring empty tokens'''
    return ' '.join([token for token in tokens if token != ''])


def reg_plural(s: str, n: int) -> str:
    """Form regular English plural form, e.g. 'position' -> 'positions' 'bush' -> 'bushes'"""
    if n == 1:
        return s
    elif re.match('(?:[sx]|[sc]h)$', s):
        return s + 'es'
    else:
        return s + 's'


if __name__ == "__main__":
    sys.stderr.write(f'%(prog)s {__version__} last modified: {last_mod_date}')
