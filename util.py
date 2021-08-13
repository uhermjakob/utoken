#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
"""
# -*- encoding: utf-8 -*-
import logging as log
import re
import regex
import sys
from typing import Dict, List, Optional, Pattern

__version__ = '0.0.4'
last_mod_date = 'August 12, 2021'


class ResourceEntry:
    """Annotated entries for abbreviations, contractions, repairs etc."""
    def __init__(self, s: str, tag: Optional[str] = None,
                 sem_class: Optional[str] = None, country: Optional[str] = None,
                 lcode: Optional[str] = None, etym_lcode: Optional[str] = None,
                 left_context: Optional[Pattern[str]] = None, left_context_not: Optional[Pattern[str]] = None,
                 right_context: Optional[Pattern[str]] = None, right_context_not: Optional[Pattern[str]] = None,
                 case_sensitive: bool = False):
        self.s = s                      # e.g. Gen.
        self.lcode = lcode              # language code, e.g. eng
        self.etym_lcode = etym_lcode    # etymological language code, e.g. lat
        self.country = country          # country, e.g. Canada
        self.sem_class = sem_class      # e.g. pre-name-title
        self.case_sensitive = case_sensitive
        self.tag = tag
        self.left_context: Optional[Pattern[str]] = left_context
        self.left_context_not: Optional[Pattern[str]] = left_context_not
        self.right_context: Optional[Pattern[str]] = right_context
        self.right_context_not: Optional[Pattern[str]] = right_context_not


class AbbreviationEntry(ResourceEntry):
    def __init__(self, abbrev: str, expansions: Optional[List[str]], sem_class: Optional[str] = None,
                 lcode: Optional[str] = None, country: Optional[str] = None, tag: Optional[str] = None):
        super().__init__(abbrev, sem_class=sem_class, lcode=lcode, country=country, tag=tag)
        self.expansions = expansions      # e.g. [General]


class RepairEntry(ResourceEntry):
    def __init__(self, bad_s: str, good_s: str, sem_class: Optional[str] = None, problem: Optional[str] = None,
                 lcode: Optional[str] = None, country: Optional[str] = None, tag: Optional[str] = None):
        super().__init__(bad_s, sem_class=sem_class, lcode=lcode, country=country, tag=tag)
        self.target = good_s      # repaired, e.g. "ca n't" is repaired as "can n't"
        self.problem = problem


class ContractionEntry(ResourceEntry):
    def __init__(self, contraction: str, decontraction: str, sem_class: Optional[str] = None,
                 lcode: Optional[str] = None, country: Optional[str] = None, tag: Optional[str] = None,
                 char_splits: Optional[List[int]] = None):
        super().__init__(contraction, sem_class=sem_class, lcode=lcode, country=country, tag=tag)
        self.target = decontraction      # e.g. "won't" is decontracted to "will n't"
        self.char_splits = char_splits   # e.g. [2,3] for "won't"/"will n't" as latter elems map to 2+3 chars in won't


class PreserveEntry(ResourceEntry):
    def __init__(self, s: str, sem_class: Optional[str] = None, lcode: Optional[str] = None,
                 country: Optional[str] = None, tag: Optional[str] = None):
        super().__init__(s, sem_class=sem_class, lcode=lcode, country=country, tag=tag)


class PunctSplitEntry(ResourceEntry):
    def __init__(self, s: str, side: str, group: Optional[bool], sem_class: Optional[str] = None,
                 lcode: Optional[str] = None, country: Optional[str] = None, tag: Optional[str] = None):
        super().__init__(s, sem_class=sem_class, lcode=lcode, country=country, tag=tag)
        self.side = side
        self.group = group if group else False


class ResourceDict:
    def __init__(self):
        """Dictionary of ResourceEntries. All dictionary keys are lower case."""
        self.resource_dict: Dict[str, List[ResourceEntry]] = {}          # primary dict
        self.reverse_resource_dict: Dict[str, List[ResourceEntry]] = {}  # reverse index
        self.prefix_dict: Dict[str, bool] = {}              # prefixes of headwords to more efficiently stop search
        self.prefix_dict_preserve: Dict[str, bool] = {}
        self.prefix_dict_punct: Dict[str, bool] = {}
        self.max_s_length: int = 0

    def register_resource_entry_in_reverse_resource_dict(self, resource_entry: ResourceEntry, rev_anchors: List[str]):
        for rev_anchor in rev_anchors:
            rev_resource_list: List[ResourceEntry] = self.reverse_resource_dict.get(rev_anchor, [])
            rev_resource_list.append(resource_entry)
            self.reverse_resource_dict[rev_anchor] = rev_resource_list

    @staticmethod
    def expand_resource_lines(orig_line: str) -> List[str]:
        lines = [orig_line]
        # expand resource entry with apostophe to alternatives with closely related characters (e.g. single quotes)
        apostrophe = "'"
        n_lines = len(lines)
        for line in lines[0:n_lines]:
            if apostrophe in line:
                repl_chars = "’‘"
                if "::punct-split" in line:
                    continue
                elif m5 := regex.match(r'(::\S+\s+)(\S|\S.*?\S)(\s+::target\s+)(\S|\S.*?\S)(\s+::\S.*|\s*)$', line):
                    if apostrophe in m5.group(2):
                        for repl_char in repl_chars:
                            new_line = f'{m5.group(1)}{regex.sub(apostrophe, repl_char, m5.group(2))}{m5.group(3)}' \
                                       f'{regex.sub(apostrophe, repl_char, m5.group(4))}{m5.group(5)}'
                            # log.info(f'Expanded line {new_line}')
                            lines.append(new_line)
                elif m3 := regex.match(r'(::\S+\s+)(\S|\S.*?\S)(\s+::\S.*|\s*)$', line):
                    if apostrophe in m3.group(2):
                        for repl_char in repl_chars:
                            new_line = f'{m3.group(1)}{regex.sub(apostrophe, repl_char, m3.group(2))}{m3.group(3)}'
                            # log.info(f'Expanded line {new_line}')
                            lines.append(new_line)
        # expand resource entry with ::inflections
        n_lines = len(lines)
        for line in lines[0:n_lines]:
            inflection_s = slot_value_in_double_colon_del_list(line, 'inflections')
            inflections = re.split(r';\s*', inflection_s) if inflection_s else []
            for inflection in inflections:
                if m3 := regex.match(r'(::\S+\s+)(\S|\S.*?\S)(\s+::\S.*)$', line):
                    new_line = f'{m3.group(1)}{inflection}{m3.group(3)}'
                    # remove ::inflections ...
                    new_line = re.sub(r'::inflections\s+(?:\S|\S.*\S)\s*(::\S.*|)$', r'\1', new_line)
                    # log.info(f'Expanded line {new_line}')
                    lines.append(new_line)
        return lines

    re_comma_space = re.compile(r',\s*')

    def load_resource(self, filename: str) -> None:
        """Loads abbreviations, contractions etc. Example input file: data/tok-resource-eng.txt"""
        try:
            with open(filename) as f_in:
                line_number = 0
                n_warnings = 0
                n_entries = 0
                n_expanded_lines = 0
                for orig_line in f_in:
                    line_number += 1
                    line_without_comment = orig_line
                    if '#' in orig_line:
                        if orig_line.startswith('#'):
                            continue
                        if (m1 := re.match(r"(.*::\S+(?:\s+\S+)?)(.*)$", orig_line)) \
                                and (m2 := re.match(r"(.*?)\s+#.*", m1.group(2))):
                            line_without_comment = m1.group(1) + m2.group(1)
                    lines = self.expand_resource_lines(line_without_comment)
                    n_expanded_lines += len(lines) - 1
                    for line in lines:
                        if re.match(r'^\uFEFF?\s*(?:#.*)?$', line):  # ignore empty or comment line
                            continue
                        # Check whether cost file line is well-formed. Following call will output specific warnings.
                        valid = double_colon_del_list_validation(line, str(line_number), filename,
                                                                 valid_slots=['abbrev',
                                                                              'case-sensitive',
                                                                              'char-split',
                                                                              'comment',
                                                                              'contraction',
                                                                              'country',
                                                                              'etym-lc',
                                                                              'example',
                                                                              'exp',
                                                                              'group',
                                                                              'inflections',
                                                                              'lcode',
                                                                              'left-context',
                                                                              'left-context-not',
                                                                              'preserve',
                                                                              'problem',
                                                                              'punct-split',
                                                                              'repair',
                                                                              'right-context',
                                                                              'right-context-not',
                                                                              'sem-class',
                                                                              'side',
                                                                              'tag',
                                                                              'target'],
                                                                 required_slot_dict={'abbrev': [],
                                                                                     'contraction': ['target'],
                                                                                     'preserve': [],
                                                                                     'punct-split': ['side'],
                                                                                     'repair': ['target']})
                        if not valid:
                            n_warnings += 1
                            continue
                        if m1 := re.match(r"::(\S+)", line):
                            head_slot = m1.group(1)
                        else:
                            continue
                        s = slot_value_in_double_colon_del_list(line, head_slot)
                        resource_entry = None
                        if head_slot == 'abbrev':
                            expansion_s = slot_value_in_double_colon_del_list(line, 'exp')
                            expansions = re.split(r';\s*', expansion_s) if expansion_s else []
                            resource_entry = AbbreviationEntry(s, expansions=expansions)
                            self.register_resource_entry_in_reverse_resource_dict(resource_entry, expansions)
                        elif head_slot == 'contraction':
                            target = slot_value_in_double_colon_del_list(line, 'target')
                            char_split_s = slot_value_in_double_colon_del_list(line, 'char-split')
                            char_splits = None
                            if char_split_s:
                                target_tokens = re.split(r'\s+', target)
                                if re.match(r'\d+(?:,\s*\d+)*', char_split_s):
                                    char_splits = [int(i) for i in self.re_comma_space.split(char_split_s)]
                                    if (l1 := len(target_tokens)) != (l2 := len(char_splits)):
                                        log.warning(f"Number of target elements ({l1}) and "
                                                    f"number of char-split elements ({l2}) don't match "
                                                    f"in line {line_number} in {filename}")
                                        char_splits = None
                                    if (l1 := len(s)) != (l2 := sum(char_splits)):
                                        log.warning(f"Length of contraction ({l1}) and "
                                                    f"sum of char-split elements ({l2}) don't match "
                                                    f"in line {line_number} in {filename}")
                                        char_splits = None
                                else:
                                    log.warning(f'Ignoring ill-formed ::char-split {char_split_s} '
                                                f'in line {line_number} in {filename} '
                                                f'(Value should be list of comma-separated integers, e.g. 2,3')
                            resource_entry = ContractionEntry(s, target, char_splits=char_splits)
                            self.register_resource_entry_in_reverse_resource_dict(resource_entry, [target])
                        elif head_slot == 'preserve':
                            resource_entry = PreserveEntry(s)
                        elif head_slot == 'punct-split':
                            side = slot_value_in_double_colon_del_list(line, 'side')
                            group = slot_value_in_double_colon_del_list(line, 'group')
                            resource_entry = PunctSplitEntry(s, side, group=bool(group))
                        elif head_slot == 'repair':
                            target = slot_value_in_double_colon_del_list(line, 'target')
                            resource_entry = RepairEntry(s, target)
                            self.register_resource_entry_in_reverse_resource_dict(resource_entry, [target])
                        if resource_entry:  # register resource_entry with lowercase key
                            if len(s) > self.max_s_length:
                                self.max_s_length = len(s)
                            lc_s = s.lower()
                            for prefix_length in range(1, len(lc_s)+1):
                                if head_slot == 'punct-split':
                                    self.prefix_dict_punct[lc_s[:prefix_length]] = True
                                elif head_slot == 'preserve':
                                    self.prefix_dict_preserve[lc_s[:prefix_length]] = True
                                else:
                                    self.prefix_dict[lc_s[:prefix_length]] = True
                            if sem_class := slot_value_in_double_colon_del_list(line, 'sem-class'):
                                resource_entry.sem_class = sem_class
                            if slot_value_in_double_colon_del_list(line, 'case-sensitive'):
                                resource_entry.case_sensitive = True
                                # log.info(f'Case-sensitive({s}) is True')
                            if left_context_s := slot_value_in_double_colon_del_list(line, 'left-context'):
                                try:
                                    resource_entry.left_context = regex.compile(eval('r".*' + left_context_s + '$"'))
                                    # log.info(f'Left-context({s}) {left_context_s} {resource_entry.left_context}')
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::left-context '
                                                f'{left_context_s}')
                            if left_context_not_s := slot_value_in_double_colon_del_list(line, 'left-context-not'):
                                try:
                                    resource_entry.left_context_not = \
                                        regex.compile(eval('r".*(?<!' + left_context_not_s + ')$"'))
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::left-context-not '
                                                f'{left_context_not_s}')
                            if right_context_s := slot_value_in_double_colon_del_list(line, 'right-context'):
                                try:
                                    resource_entry.right_context = regex.compile(eval('r"' + right_context_s + '"'))
                                    # log.info(f'Right-context({s}) {right_context_s} {resource_entry.right_context}')
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::right-context '
                                                f'{right_context_s}')
                            if right_context_not_s := slot_value_in_double_colon_del_list(line, 'right-context-not'):
                                try:
                                    resource_entry.right_context_not = \
                                        regex.compile(eval('r"(?!' + right_context_not_s + ')"'))
                                    # log.info(f'Right-context-not({s}) {right_context_not_s}
                                    # {resource_entry.right_context_not}')
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::right-context-not '
                                                f'{right_context_not_s}')
                            abbreviation_entry_list = self.resource_dict.get(lc_s, [])
                            abbreviation_entry_list.append(resource_entry)
                            self.resource_dict[lc_s] = abbreviation_entry_list
                            n_entries += 1
                expanded_clause = f' (plus {n_expanded_lines} expanded lines)' if n_expanded_lines else ''
                log.info(f'Loaded {n_entries} entries from {line_number} lines{expanded_clause} in {filename}')
        except OSError:
            log.warning(f'Could not open resource file {filename}')


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
