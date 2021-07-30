#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
"""
# -*- encoding: utf-8 -*-
import logging as log
import re
import sys
from typing import Dict, List, Optional

__version__ = '0.0.1'
last_mod_date = 'July 19, 2021'


class ResourceEntry:
    """Annotated entries for abbreviations, contractions, repairs etc."""
    def __init__(self, s: str,
                 sem_class: Optional[str] = None, lcode: Optional[str] = None,
                 country: Optional[str] = None, comment: Optional[str] = None):
        self.s = s                      # e.g. Gen.
        self.lcode = lcode              # language code, e.g. eng
        self.country = country          # country, e.g. Canada
        self.sem_class = sem_class      # e.g. pre-name-title
        self.comment = comment


class AbbreviationEntry(ResourceEntry):
    def __init__(self, abbrev: str, expansion: Optional[List[str]], sem_class: Optional[str] = None,
                 lcode: Optional[str] = None, country: Optional[str] = None, comment: Optional[str] = None):
        super().__init__(abbrev, sem_class=sem_class, lcode=lcode, country=country, comment=comment)
        self.expansion = expansion      # e.g. General


class ResourceDict:
    def __init__(self):
        self.resource_dict = {}
        self.reverse_resource_dict = {}
        self.max_s_length = 0

    def load_resource(self, filename: str) -> None:
        with open(filename) as f_in:
            line_number = 0
            n_warnings = 0
            n_entries = 0
            for line in f_in:
                line_number += 1
                if re.match(r'^\uFEFF?\s*(?:#.*)?$', line):  # ignore empty or comment line
                    continue
                # Check whether cost file line is well-formed. Following call will output specific warnings.
                valid = double_colon_del_list_validation(line, str(line_number), filename,
                                                         valid_slots=['abbrev', 'case-sensitive', 'comment',
                                                                      'contraction', 'country',
                                                                      'exp', 'lcode', 'preserve', 'repair',
                                                                      'sem-class', 'target'],
                                                         required_slot_dict={'abbrev': [],
                                                                             'contraction': ['target'],
                                                                             'preserve': [],
                                                                             'repair': ['target']})
                if not valid:
                    n_warnings += 1
                    continue
                if m1 := re.match(r"::(\S+)", line):
                    head_slot = m1.group(1)
                else:
                    continue
                if head_slot == 'abbrev':
                    abbreviation = slot_value_in_double_colon_del_list(line, 'abbrev')
                    expansion_s = slot_value_in_double_colon_del_list(line, 'exp')
                    if expansion_s:
                        expansions = re.split(r';\s*', expansion_s)
                    else:
                        expansions = None
                    sem_class = slot_value_in_double_colon_del_list(line, 'sem-class')
                    abbreviation_entry = AbbreviationEntry(abbreviation, expansion=expansions, sem_class=sem_class)
                    abbreviation_entry_list = self.resource_dict.get(abbreviation, [])
                    abbreviation_entry_list.append(abbreviation_entry)
                    self.resource_dict[abbreviation] = abbreviation_entry_list
                    if expansions:
                        for expansion in expansions:
                            rev_abbreviation_list: List[ResourceEntry] = self.reverse_resource_dict.get(expansion, [])
                            rev_abbreviation_list.append(abbreviation_entry)
                            self.reverse_resource_dict[expansion] = rev_abbreviation_list
                    if len(abbreviation) > self.max_s_length:
                        self.max_s_length = len(abbreviation)
                    n_entries += 1
            log.info(f'Loaded {n_entries} entries from {line_number} lines in {filename}')


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional[str] = None) -> str:
    """For a given slot, e.g. 'cost', get its value from a line such as '::s1 of course ::s2 ::cost 0.3' -> 0.3
    The value can be an empty string, as for ::s2 in the example above."""
    m = re.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', line)
    return m.group(1).strip() if m else default


def double_colon_del_list_validation(s: str, line_id: str, filename: str,
                                     valid_slots: List[str], required_slot_dict: Dict[str, List[str]]) -> bool:
    """Check whether a string (typically line in data file) is a well-formed double-colon expression"""
    valid = True
    prev_slots = []
    if slots := re.findall(r'::([a-z]\S*)', s, re.IGNORECASE):
        head_slot = slots[0]
        if (required_slots := required_slot_dict.get(head_slot, None)) is None:
            valid = False
            log.warning(f'found invalid head-slot ::{head_slot} in line {line_id} in {filename}')
            required_slots = []
    else:
        log.warning(f'found no slots in line {line_id} in {filename}')
        return False
    # Check for duplicates and unexpected slots
    for slot in slots:
        if slot in valid_slots:
            if slot in prev_slots:
                valid = False
                log.warning(f'found duplicate slot ::{slot} in line {line_id} in {filename}')
            else:
                prev_slots.append(slot)
        else:
            valid = False
            log.warning(f'found unexpected slot ::{slot} in line {line_id} in {filename}')
    # Check for missing required slots
    if required_slots:
        for slot in required_slots:
            if slot not in prev_slots:
                valid = False
                log.warning(f'missing required slot ::{slot} in line {line_id} in {filename}')
    # Check for ::slot syntax problems
    m = re.match(r'.*?(\S+::[a-z]\S*)', s)
    if m:
        valid = False
        value = m.group(1)
        if re.match(r'.*:::', value):
            log.warning(f"suspected spurious colon in '{value}' in line {line_id} in {filename}")
        else:
            log.warning(f"# Warning: suspected missing space in '{value}' in line {line_id} in {filename}")
    m = re.match(r'(?:.*\s)?(:[a-z]\S*)', s)
    if m:
        valid = False
        log.warning(f"suspected missing colon in '{m.group(1)}' in line {line_id} in {filename}")
    return valid


def increment_dict_count(ht: dict, key: str, increment=1) -> int:
    """For example ht['NUMBER-OF-LINES']"""
    ht[key] = ht.get(key, 0) + increment
    return ht[key]


def join_tokens(tokens: List[str]):
    """Join tokens with space, ignoring empty tokens"""
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
