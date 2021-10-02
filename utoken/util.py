#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
"""
# -*- encoding: utf-8 -*-
from collections import defaultdict
import logging as log
from pathlib import Path
import re
import regex
import sys
from typing import Dict, List, Optional, Pattern
from . import __version__, last_mod_date


class ResourceEntry:
    """Annotated entries for abbreviations, contractions, repairs etc."""
    def __init__(self, s: str, tag: Optional[str] = None,
                 sem_class: Optional[str] = None, country: Optional[str] = None,
                 lcode: Optional[str] = None, lang_codes_not: List[str] = None, etym_lcode: Optional[str] = None,
                 left_context: Optional[Pattern[str]] = None, left_context_not: Optional[Pattern[str]] = None,
                 right_context: Optional[Pattern[str]] = None, right_context_not: Optional[Pattern[str]] = None,
                 case_sensitive: bool = False):
        self.s = s                      # e.g. Gen.
        self.lcode = lcode              # language code, e.g. eng
        self.lang_codes_not = lang_codes_not
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


class LexicalPriorityEntry(ResourceEntry):
    """LexicalPriorityEntry are applied earlier (i.e. with higher priority) than regular LexicalEntry."""
    def __init__(self, s: str, sem_class: Optional[str] = None, lcode: Optional[str] = None):
        super().__init__(s, sem_class=sem_class, lcode=lcode)


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


class LexicalEntry(ResourceEntry):
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
        self.prefix_dict_lexical: Dict[str, bool] = {}
        self.prefix_dict_punct: Dict[str, bool] = {}
        self.max_s_length: int = 0
        self.pre_name_title_list = defaultdict(list)  # key: lang_code  value: ["Mr.", "Dr."]
        self.phonetics_list = defaultdict(list)       # key: lang_code  value: ["Ey.", "Bi.", "Si."]

    def register_resource_entry_in_reverse_resource_dict(self, resource_entry: ResourceEntry, rev_anchors: List[str]):
        for rev_anchor in rev_anchors:
            rev_resource_list: List[ResourceEntry] = self.reverse_resource_dict.get(rev_anchor, [])
            rev_resource_list.append(resource_entry)
            self.reverse_resource_dict[rev_anchor] = rev_resource_list

    @staticmethod
    def line_without_comment(line: str) -> str:
        if '#' in line:
            if line.startswith('#'):
                return '\n'
            if (m1 := re.match(r"(.*::\S+(?:\s+\S+)?)(.*)$", line)) and (m2 := re.match(r"(.*?)\s+#.*", m1.group(2))):
                return m1.group(1) + m2.group(1)
        return line

    def abbrev_space_expansions(self, abbrev: str) -> List[str]:
        """'e.g.' -> ['e.g.', 'e. g.']"""
        if m3 := regex.match(r'((?:\pL\pM*|\d|[-_])+) ?([.·]) ?((?:\pL|\d).*)$', abbrev):
            first_elem = m3.group(1)
            punct = m3.group(2)
            result_list = []
            for sub_expansion in self.abbrev_space_expansions(m3.group(3)):
                result_list.append(first_elem + punct + sub_expansion)
                if punct in '·':
                    result_list.append(first_elem + ' ' + punct + ' ' + sub_expansion)
                else:
                    result_list.append(first_elem + punct + ' ' + sub_expansion)
            return result_list
        else:
            return [abbrev]

    def expand_resource_lines(self, orig_line: str) -> List[str]:
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
                            lines.append(new_line)
                elif m3 := regex.match(r'(::\S+\s+)(\S|\S.*?\S)(\s+::\S.*|\s*)$', line):
                    if apostrophe in m3.group(2):
                        for repl_char in repl_chars:
                            new_line = f'{m3.group(1)}{regex.sub(apostrophe, repl_char, m3.group(2))}{m3.group(3)}'
                            lines.append(new_line)
        # expand resource entry with ::plural
        n_lines = len(lines)
        for line in lines[0:n_lines]:
            plural_s = slot_value_in_double_colon_del_list(line, 'plural')
            plurals = re.split(r';\s*', plural_s) if plural_s else []
            for plural in plurals:
                if m3 := regex.match(r'(::\S+\s+)(\S|\S.*?\S)(\s+::\S.*)$', line):
                    if plural == '+s':
                        plural2 = m3.group(2) + 's'
                    else:
                        plural2 = plural
                    new_line = f'{m3.group(1)}{plural2}{m3.group(3)}'
                    # remove ::plural ...
                    new_line = re.sub(r'::plural\s+(?:\S|\S.*\S)\s*(::\S.*|)$', r'\1', new_line)
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
                    lines.append(new_line)
        # expand resource entry with ::alt-spelling
        n_lines = len(lines)
        for line in lines[0:n_lines]:
            alt_spelling_s = slot_value_in_double_colon_del_list(line, 'alt-spelling')
            alt_spellings = re.split(r';\s*', alt_spelling_s) if alt_spelling_s else []
            for alt_spelling in alt_spellings:
                if m3 := regex.match(r'(::\S+\s+)(\S|\S.*?\S)(\s+::\S.*)$', line):
                    if alt_spelling == '+hyphen':
                        alt_spelling2 = re.sub(' ', '-', m3.group(2))
                    else:
                        alt_spelling2 = alt_spelling
                    new_line = f'{m3.group(1)}{alt_spelling2}{m3.group(3)}'
                    # remove ::alt-spelling ...
                    new_line = re.sub(r'::alt-spelling\s+(?:\S|\S.*\S)\s*(::\S.*|)$', r'\1', new_line)
                    lines.append(new_line)
        # expand resource entry with extra spaces in punctuation e.g. -> e. g.
        n_lines = len(lines)
        for line in lines[0:n_lines]:
            if m3 := regex.match(r'::(abbrev|lexical)\s+(\S|\S.*?\S)(\s+::\S.*)$', line):
                abbreviation = m3.group(2)  # Could also be lexical item such as "St. Petersburg"
                if regex.match(r'.*[.·] ?\S', abbreviation) \
                        and slot_value_in_double_colon_del_list(line, 'sem-class') != 'url'\
                        and (line.startswith('::abbrev ') or line.startswith('::lexical ')):
                    for expanded_abbreviation in self.abbrev_space_expansions(abbreviation):
                        if expanded_abbreviation != abbreviation:
                            new_line = f'::repair {expanded_abbreviation} ::target {abbreviation}{m3.group(3)}'
                            lines.append(new_line)
                            # log.info(f'Expanding {abbreviation} TO {expanded_abbreviation}')
        # expand resource entry with ::last-char-repeatable
        n_lines = len(lines)
        for line in lines[0:n_lines]:
            if slot_value_in_double_colon_del_list(line, 'last-char-repeatable'):
                if m3 := regex.match(r'(::\S+\s+)(\S|\S.*?\S)(\s+::\S.*)$', line):
                    token = m3.group(2)
                    last_char = token[-1]
                    for _ in range(127):
                        token += last_char
                        new_line = f'{m3.group(1)}{token}{m3.group(3)}'
                        # remove any ::last-char-repeatable ...
                        new_line = re.sub(r'::last-char-repeatable\s+(?:\S|\S.*\S)\s*(::\S.*|)$', r'\1', new_line)
                        lines.append(new_line)
        # expand resource entry with ::misspelling
        n_lines = len(lines)
        for line in lines[0:n_lines]:
            if line.startswith('::misspelling'):
                misspelling = slot_value_in_double_colon_del_list(line, 'misspelling')
                target = slot_value_in_double_colon_del_list(line, 'target')
                if misspelling and target:
                    rest_line = line.rstrip()
                    rest_line = re.sub(r'::misspelling\s+(?:\S|\S.*\S)\s*(::\S.*|)$', r'\1', rest_line)
                    rest_line = re.sub(r'::target\s+(?:\S|\S.*\S)\s*(::\S.*|)$', r'\1', rest_line)
                    rest_line = re.sub(r'::suffix-variations\s+(?:\S|\S.*\S)\s*(::\S.*|)$', r'\1', rest_line)
                    raw_suffix_variation_s = slot_value_in_double_colon_del_list(line, 'suffix-variations')
                    if raw_suffix_variation_s and (m2 := regex.match(r'((?:\pL\pM*)+)\/(.*)$', raw_suffix_variation_s)):
                        lemma_suffix = m2.group(1)
                        suffix_variations = re.split(r';\s*', m2.group(2))
                    else:
                        lemma_suffix = ''
                        suffix_variations = re.split(r';\s*', raw_suffix_variation_s) if raw_suffix_variation_s else []
                    misspellings = [misspelling]
                    targets = [target]
                    misspelling_without_suffix = misspelling[:-len(lemma_suffix)] \
                        if lemma_suffix and misspelling.endswith(lemma_suffix) \
                        else misspelling
                    target_without_suffix = target[:-len(lemma_suffix)] \
                        if lemma_suffix and target.endswith(lemma_suffix) \
                        else target
                    for suffix_variation in suffix_variations:
                        misspellings.append(misspelling_without_suffix + suffix_variation)
                        targets.append(target_without_suffix + suffix_variation)
                    for misspelling_variation, target_variation in zip(misspellings, targets):
                        new_line = f'::repair {misspelling_variation} ::target {target_variation} {rest_line}'
                        lines.append(new_line)
            else:
                misspelling_s = slot_value_in_double_colon_del_list(line, 'misspelling')
                misspellings = re.split(r';\s*', misspelling_s) if misspelling_s else []
                for misspelling in misspellings:
                    if m3 := regex.match(r'(::(?:abbrev|lexical)\s+)(\S|\S.*?\S)(\s+::\S.*)$', line):
                        new_line = f'::repair {misspelling} ::target {m3.group(2)}{m3.group(3)}'
                        # remove ::misspelling ...
                        new_line = re.sub(r'::misspelling\s+(?:\S|\S.*\S)\s*(::\S.*|)$', r'\1', new_line)
                        lines.append(new_line)
        return lines

    re_comma_space = re.compile(r',\s*')
    re_contains_digit = regex.compile(r'.*\d')

    def load_resource(self, filename: Path, lang_code: Optional[str] = None, verbose: bool = True) -> None:
        """Loads abbreviations, contractions etc. for tokenization.
        Example input file: data/tok-resource-eng.txt"""
        try:
            with open(filename) as f_in:
                line_number = 0
                n_warnings = 0
                n_entries = 0
                n_expanded_lines = 0
                for orig_line in f_in:
                    line_number += 1
                    line_without_comment = self.line_without_comment(orig_line)
                    if line_without_comment.strip() == '':
                        continue
                    lines = self.expand_resource_lines(line_without_comment)
                    n_expanded_lines += len(lines) - 1
                    for line in lines:
                        if re.match(r'^\uFEFF?\s*(?:#.*)?$', line):  # ignore empty or comment line
                            continue
                        # Check whether cost file line is well-formed. Following call will output specific warnings.
                        valid = double_colon_del_list_validation(line, str(line_number), str(filename),
                                                                 valid_slots=['abbrev',
                                                                              'alt-spelling',
                                                                              'case-sensitive',
                                                                              'char-split',
                                                                              'comment',
                                                                              'contraction',
                                                                              'country',
                                                                              'eng',
                                                                              'etym-lcode',
                                                                              'example',
                                                                              'exp',
                                                                              'group',
                                                                              'inflections',
                                                                              'last-char-repeatable',
                                                                              'lcode',
                                                                              'lcode-not',
                                                                              'left-context',
                                                                              'left-context-not',
                                                                              'lexical',
                                                                              'misspelling',
                                                                              'nonstandard',
                                                                              'plural',
                                                                              'problem',
                                                                              'priority',
                                                                              'punct-split',
                                                                              'repair',
                                                                              'right-context',
                                                                              'right-context-not',
                                                                              'sem-class',
                                                                              'side',
                                                                              'substandard',
                                                                              'suffix-variations',
                                                                              'syntax-checked',
                                                                              'tag',
                                                                              'target',
                                                                              'taxon',
                                                                              'token-category'],
                                                                 required_slot_dict={'abbrev': [],
                                                                                     'contraction': ['target'],
                                                                                     'lexical': [],
                                                                                     'misspelling': ['target'],
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
                        elif head_slot == 'lexical':
                            sem_class = slot_value_in_double_colon_del_list(line, 'sem-class')
                            priority = slot_value_in_double_colon_del_list(line, 'priority')
                            if priority or (sem_class in ('url',)) or self.re_contains_digit.match(s):
                                resource_entry = LexicalPriorityEntry(s)
                            else:
                                resource_entry = LexicalEntry(s)
                        elif head_slot == 'punct-split':
                            side = slot_value_in_double_colon_del_list(line, 'side')
                            if side not in ('start', 'end', 'both'):
                                log.warning(f'Invalid side {side} in line {line_number} in {filename} '
                                            f'(should be one of start/end/both)')
                            group = slot_value_in_double_colon_del_list(line, 'group', False)
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
                                elif head_slot == 'lexical' and not isinstance(resource_entry, LexicalPriorityEntry):
                                    self.prefix_dict_lexical[lc_s[:prefix_length]] = True
                                else:
                                    self.prefix_dict[lc_s[:prefix_length]] = True
                            if sem_class := slot_value_in_double_colon_del_list(line, 'sem-class'):
                                resource_entry.sem_class = sem_class
                                if (sem_class == "pre-name-title") \
                                        and (lcode := slot_value_in_double_colon_del_list(line, 'lcode')):
                                    self.pre_name_title_list[lcode].append(lc_s)
                            if (token_category := slot_value_in_double_colon_del_list(line, 'token-category')) \
                                    and (token_category == 'phonetics') \
                                    and (lcode := slot_value_in_double_colon_del_list(line, 'lcode')):
                                self.phonetics_list[lcode].append(lc_s)
                            if slot_value_in_double_colon_del_list(line, 'case-sensitive'):
                                resource_entry.case_sensitive = True
                            if tag := slot_value_in_double_colon_del_list(line, 'tag'):
                                resource_entry.tag = tag
                            if left_context_s := slot_value_in_double_colon_del_list(line, 'left-context'):
                                try:
                                    resource_entry.left_context = regex.compile(eval('r".*' + left_context_s + '$"'),
                                                                                flags=regex.VERSION1)
                                    # log.info(f'Left-context({s}) {left_context_s} {resource_entry.left_context}')
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::left-context '
                                                f'{left_context_s}')
                            if left_context_not_s := slot_value_in_double_colon_del_list(line, 'left-context-not'):
                                try:
                                    resource_entry.left_context_not = \
                                        regex.compile(eval('r".*(?<!' + left_context_not_s + ')$"'),
                                                      flags=regex.VERSION1)
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::left-context-not '
                                                f'{left_context_not_s}')
                            if right_context_s := slot_value_in_double_colon_del_list(line, 'right-context'):
                                try:
                                    resource_entry.right_context = regex.compile(eval('r"' + right_context_s + '"'),
                                                                                 flags=regex.VERSION1)
                                    # log.info(f'Right-context({s}) {right_context_s} {resource_entry.right_context}')
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::right-context '
                                                f'{right_context_s}')
                            if right_context_not_s := slot_value_in_double_colon_del_list(line, 'right-context-not'):
                                try:
                                    resource_entry.right_context_not = \
                                        regex.compile(eval('r"(?!' + right_context_not_s + ')"'),
                                                      flags=regex.VERSION1)
                                    # log.info(f'Right-context-not({s}) {right_context_not_s}
                                    # {resource_entry.right_context_not}')
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::right-context-not '
                                                f'{right_context_not_s}')
                            if lang_code_not_s := slot_value_in_double_colon_del_list(line, 'lcode-not'):
                                resource_entry.lang_codes_not = re.split(r'[;,\s*]', lang_code_not_s)
                            abbreviation_entry_list = self.resource_dict.get(lc_s, [])
                            abbreviation_entry_list.append(resource_entry)
                            self.resource_dict[lc_s] = abbreviation_entry_list
                            n_entries += 1
                expanded_clause = f' (plus {n_expanded_lines} expanded lines)' if n_expanded_lines else ''
                if verbose:
                    log.info(f'Loaded {n_entries} entries from {line_number} lines{expanded_clause} in {filename}')
        except OSError:
            if lang_code:
                log.warning(f"No resource file available for language '{lang_code}' ({filename})")
            else:
                log.warning(f'Could not open general resource file {filename}')


class DetokenizationEntry:
    def __init__(self, s: str, group: Optional[bool] = False, lang_codes: List[str] = None,
                 left_context: Optional[Pattern[str]] = None, left_context_not: Optional[Pattern[str]] = None,
                 right_context: Optional[Pattern[str]] = None, right_context_not: Optional[Pattern[str]] = None,
                 case_sensitive: bool = False):
        self.s = s
        self.group = group
        self.lang_codes = lang_codes
        self.left_context: Optional[Pattern[str]] = left_context
        self.left_context_not: Optional[Pattern[str]] = left_context_not
        self.right_context: Optional[Pattern[str]] = right_context
        self.right_context_not: Optional[Pattern[str]] = right_context_not
        self.case_sensitive = case_sensitive

    def detokenization_entry_fulfills_conditions(self, token: str, left_context: str, right_context: str,
                                                 lang_code: Optional[str], group: Optional[bool] = False) -> bool:
        """This methods checks whether a detokenization-entry satisfies any context conditions."""
        lang_codes = self.lang_codes
        return ((not lang_code or not lang_codes or (lang_code in lang_codes))
                and (not self.case_sensitive or (token == self.s))
                and (not group or self.group)
                and (not (re_l := self.left_context) or re_l.match(left_context))
                and (not (re_l_n := self.left_context_not) or not re_l_n.match(left_context))
                and (not (re_r := self.right_context) or re_r.match(right_context))
                and (not (re_r_n := self.right_context_not) or not re_r_n.match(right_context)))


class DetokenizationMarkupEntry(DetokenizationEntry):
    def __init__(self, s: str, group: Optional[bool] = False, paired_delimiter: Optional[bool] = False,
                 left_context: Optional[Pattern[str]] = None, left_context_not: Optional[Pattern[str]] = None,
                 right_context: Optional[Pattern[str]] = None, right_context_not: Optional[Pattern[str]] = None,
                 case_sensitive: Optional[bool] = False):
        super().__init__(s, group=group, left_context=left_context, left_context_not=left_context_not,
                         right_context=right_context, right_context_not=right_context_not,
                         case_sensitive=case_sensitive)
        self.paired_delimiter = paired_delimiter
        self.exception_list = []


class DetokenizationContractionEntry(DetokenizationEntry):
    def __init__(self, target: str, contraction: str,
                 left_context: Optional[Pattern[str]] = None, left_context_not: Optional[Pattern[str]] = None,
                 right_context: Optional[Pattern[str]] = None, right_context_not: Optional[Pattern[str]] = None,
                 case_sensitive: Optional[bool] = False):
        super().__init__(target, left_context=left_context, left_context_not=left_context_not,
                         right_context=right_context, right_context_not=right_context_not,
                         case_sensitive=case_sensitive)
        self.contraction_s = contraction


class DetokenizationResource:
    def __init__(self):
        self.attach_tag = '@'  # default
        self.auto_attach_left = defaultdict(list)
        self.auto_attach_right = defaultdict(list)
        self.auto_attach_left_w_lc = {}
        self.auto_attach_right_w_lc = {}
        self.markup_attach = defaultdict(list)
        self.markup_attach_re_elements = set()
        self.markup_attach_re_string = None
        self.markup_attach_re = None   # compiled regular expression
        self.contraction_dict = defaultdict(list)

    def load_resource(self, filename: Path, doc_lang_codes: List[str], verbose: bool = True) -> None:
        """Loads detokenization resources such as auto-attach, markup-attach etc.
        Example input file: data/detok-resource.txt
        This file is also loaded by the tokenizer to produce appropriate mt-style @...@ tokens."""
        try:
            with open(filename) as f_in:
                line_number = 0
                n_warnings = 0
                n_entries = 0
                resource_dict = ResourceDict()
                for orig_line in f_in:
                    line_number += 1
                    line_without_comment = resource_dict.line_without_comment(orig_line)
                    if line_without_comment.strip() == '':
                        continue
                    lines = resource_dict.expand_resource_lines(line_without_comment)
                    for line in lines:
                        if re.match(r'^\uFEFF?\s*(?:#.*)?$', line):  # ignore empty or comment line
                            continue
                        if re.match(r'::(repair|punct-split|abbrev|misspelling)\b', line):
                            continue  # In tok-resources, only ::contraction entries are relevant.
                        # Check whether cost file line is well-formed. Following call will output specific warnings.
                        valid = double_colon_del_list_validation(line, str(line_number), str(filename),
                                                                 valid_slots=['alt-spelling',
                                                                              'attach-tag',
                                                                              'auto-attach',
                                                                              'char-split',
                                                                              'case-sensitive',
                                                                              'comment',
                                                                              'contraction',
                                                                              'country',
                                                                              'eng',
                                                                              'etym-lcode',
                                                                              'example',
                                                                              'except',
                                                                              'group',
                                                                              'last-char-repeatable',
                                                                              'lcode',
                                                                              'lcode-not',
                                                                              'left-context',
                                                                              'left-context-not',
                                                                              'lexical',
                                                                              'markup-attach',
                                                                              'misspelling',
                                                                              'nonstandard',
                                                                              'paired-delimiter',
                                                                              'plural',
                                                                              'priority',
                                                                              'right-context',
                                                                              'right-context-not',
                                                                              'sem-class',
                                                                              'side',
                                                                              'substandard',
                                                                              'syntax-checked',
                                                                              'tag',
                                                                              'target',
                                                                              'taxon',
                                                                              'token-category'],
                                                                 required_slot_dict={'attach-tag': [],
                                                                                     'auto-attach': ['side'],
                                                                                     'contraction': ['target'],
                                                                                     'lexical': [],
                                                                                     'markup-attach': []})
                        if not valid:
                            n_warnings += 1
                            continue
                        if m1 := re.match(r"::(\S+)", line):
                            head_slot = m1.group(1)
                        else:
                            continue
                        line_lang_code_s = slot_value_in_double_colon_del_list(line, 'lcode')
                        line_lang_codes = re.split(r'[;,\s*]', line_lang_code_s) if line_lang_code_s else []
                        if doc_lang_codes and line_lang_codes:
                            if not lists_share_element(doc_lang_codes, line_lang_codes):
                                continue
                        s = slot_value_in_double_colon_del_list(line, head_slot)
                        lc_s = s.lower()
                        detokenization_entry = None
                        if head_slot == 'auto-attach':
                            side = slot_value_in_double_colon_del_list(line, 'side')
                            group = bool(slot_value_in_double_colon_del_list(line, 'group', False))
                            detokenization_entry = DetokenizationEntry(s, group, line_lang_codes)
                            if side == 'left' or side == 'both':
                                for line_lang_code in (line_lang_codes if line_lang_codes else [None]):
                                    key = f'{line_lang_code} {lc_s}'
                                    if self.auto_attach_left_w_lc.get(key, False):
                                        lcode_clause = f' ::lcode {line_lang_code}' if line_lang_code else ''
                                        log.warning(f'Duplicate ::auto-attach {lc_s} ::side left{lcode_clause}')
                                    else:
                                        self.auto_attach_left_w_lc[key] = True
                                self.auto_attach_left[lc_s].append(detokenization_entry)
                            if side == 'right' or side == 'both':
                                for line_lang_code in (line_lang_codes if line_lang_codes else [None]):
                                    key = f'{line_lang_code} {lc_s}'
                                    if self.auto_attach_right_w_lc.get(key, False):
                                        lcode_clause = f' ::lcode {line_lang_code}' if line_lang_code else ''
                                        log.warning(f'Duplicate ::auto-attach {lc_s} ::side right{lcode_clause}')
                                    else:
                                        self.auto_attach_right_w_lc[key] = True
                                self.auto_attach_right[lc_s].append(detokenization_entry)
                        elif head_slot == 'markup-attach':
                            paired_delimiter = bool(slot_value_in_double_colon_del_list(line, 'paired-delimiter',
                                                                                        False))
                            group = bool(slot_value_in_double_colon_del_list(line, 'group', False))
                            detokenization_entry = DetokenizationMarkupEntry(s, group=group,
                                                                             paired_delimiter=paired_delimiter)
                            if except_s := slot_value_in_double_colon_del_list(line, 'except'):
                                detokenization_entry.exception_list = re.split(r'\s+', except_s)
                            self.markup_attach[lc_s].append(detokenization_entry)
                            self.markup_attach_re_elements.add(re.escape(lc_s) + ('+' if group else ''))
                        elif head_slot == 'attach_tag':
                            self.attach_tag = s
                        elif head_slot == 'contraction':
                            if ((not slot_value_in_double_colon_del_list(line, 'nonstandard'))
                                    and (not slot_value_in_double_colon_del_list(line, 'substandard'))):
                                target = slot_value_in_double_colon_del_list(line, 'target')
                                lc_target = target.lower()
                                detokenization_entry = DetokenizationContractionEntry(target, s)
                                self.contraction_dict[lc_target].append(detokenization_entry)
                        elif head_slot == 'lexical':
                            tag = slot_value_in_double_colon_del_list(line, 'tag')
                            if tag in ('DECONTRACTION-L', 'DECONTRACTION-R', 'DECONTRACTION-B'):
                                detokenization_entry = DetokenizationEntry(s)
                                if tag in ('DECONTRACTION-L', 'DECONTRACTION-B'):  # e.g. s', 'n'
                                    self.auto_attach_right[lc_s].append(detokenization_entry)
                                if tag in ('DECONTRACTION-R', 'DECONTRACTION-B'):  # e.g. 's, 'n'
                                    self.auto_attach_left[lc_s].append(detokenization_entry)
                        if detokenization_entry:
                            detokenization_entry.case_sensitive = \
                                bool(slot_value_in_double_colon_del_list(line, 'case-sensitive'))
                            if left_context_s := slot_value_in_double_colon_del_list(line, 'left-context'):
                                try:
                                    detokenization_entry.left_context = \
                                        regex.compile(eval('r".*' + left_context_s + '$"'), flags=regex.VERSION1)
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::left-context '
                                                f'{left_context_s}')
                            if left_context_not_s := slot_value_in_double_colon_del_list(line, 'left-context-not'):
                                try:
                                    detokenization_entry.left_context_not = \
                                        regex.compile(eval('r".*(?<!' + left_context_not_s + ')$"'),
                                                      flags=regex.VERSION1)
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::left-context-not '
                                                f'{left_context_not_s}')
                            if right_context_s := slot_value_in_double_colon_del_list(line, 'right-context'):
                                try:
                                    detokenization_entry.right_context = \
                                        regex.compile(eval('r"' + right_context_s + '"'), flags=regex.VERSION1)
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::right-context '
                                                f'{right_context_s}')
                            if right_context_not_s := slot_value_in_double_colon_del_list(line, 'right-context-not'):
                                try:
                                    detokenization_entry.right_context_not = \
                                        regex.compile(eval('r"(?!' + right_context_not_s + ')"'),
                                                      flags=regex.VERSION1)
                                except regex.error:
                                    log.warning(f'Regex compile error in l.{line_number} for {s} ::right-context-not '
                                                f'{right_context_not_s}')
                            n_entries += 1
                if verbose:
                    log.info(f'Loaded {n_entries} entries from {line_number} lines in {filename}')
        except OSError:
            log.warning(f'Could not open general resource file {filename}')

    def build_markup_attach_re(self, tok: Optional = None) -> None:
        """After all detok resources are loaded, compile markup_attach_re from markup_attach_re_elements."""
        attach_tag = self.attach_tag
        if tok:
            tok.char_type_vector_dict[attach_tag] = tok.char_type_vector_dict.get(attach_tag, 0) \
                                                    | tok.char_is_attach_tag
        self.markup_attach_re_elements.update('/')  # for robustness
        regex_string_core = attach_tag + '?(?:' + '|'.join(self.markup_attach_re_elements) + ')' + attach_tag + '?'
        self.markup_attach_re_string = '(?:' + regex_string_core + '|' + attach_tag + attach_tag + ')'
        # log.info(f"markup_attach_re: {self.markup_attach_re_string}")
        self.markup_attach_re = re.compile('^' + self.markup_attach_re_string + '$', flags=re.IGNORECASE)
        # log.info(f"markup_attach_re: {self.markup_attach_re}")


def slot_value_in_double_colon_del_list(line: str, slot: str, default: Optional = None) -> str:
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
    if m := re.match(r'.*?(\S+::[a-z]\S*)', s):
        valid = False
        value = m.group(1)
        if re.match(r'.*:::', value):
            log.warning(f"suspected spurious colon in '{value}' in line {line_id} in {filename}")
        else:
            log.warning(f"# Warning: suspected missing space in '{value}' in line {line_id} in {filename}")
    # Element starts with single colon (:). Might be slot with a missing colon.
    if m := re.match(r'(?:.*\s)?(:[a-z]\S*)', s):
        # Exception :emoji-shortcut:
        if re.match(r':[a-z][-_a-z]*[a-z]:$', m.group(1), flags=re.IGNORECASE) \
                and re.match(r'.*\b(?:symbol|emoji)\b', s, flags=re.IGNORECASE):
            pass
        elif re.match(r'.*::syntax-checked True\b', s):
            pass
        else:
            valid = False
            log.warning(f"suspected missing colon in '{m.group(1)}' in line {line_id} in {filename}")
    return valid


def load_top_level_domains(filename: Path) -> (List[str], List[str], List[str]):
    """Loads top level domain resource for URLs etc.
    Example input file: data/top-level-domain-codes.txt"""
    top_level_domain_names_with_low_reliability = []
    top_level_domain_names_with_normal_reliability = []
    top_level_domain_names_with_high_reliability = []
    try:
        with open(filename) as f_in:
            line_number = 0
            n_warnings = 0
            n_entries = 0
            for orig_line in f_in:
                line_number += 1
                line = ResourceDict.line_without_comment(orig_line)
                if line.strip() == '':
                    continue
                if re.match(r'^\uFEFF?\s*(?:#.*)?$', line):  # ignore empty or comment line
                    continue
                # Check whether cost file line is well-formed. Following call will output specific warnings.
                valid = double_colon_del_list_validation(line, str(line_number), str(filename),
                                                         valid_slots=['code',
                                                                      'comment',
                                                                      'country-name',
                                                                      'example',
                                                                      'reliability'],
                                                         required_slot_dict={'code': []})
                if not valid:
                    n_warnings += 1
                    continue
                if code := slot_value_in_double_colon_del_list(line, 'code'):
                    # country_code = slot_value_in_double_colon_del_list(line, 'country-code')
                    reliability = slot_value_in_double_colon_del_list(line, 'reliability')
                    if reliability == 'low':
                        top_level_domain_names_with_low_reliability.append(code.lower())
                    elif reliability == 'high':
                        top_level_domain_names_with_high_reliability.append(code.lower())
                    else:
                        top_level_domain_names_with_normal_reliability.append(code.lower())
                    n_entries += 1
                else:
                    log.warning(f'Could not process line {line_number} in {filename}')
            # log.info(f'Loaded {n_entries} entries from {line_number} lines in {filename}')
            top_level_domain_names_with_low_reliability.sort()
            top_level_domain_names_with_normal_reliability.sort()
            top_level_domain_names_with_high_reliability.sort()
    except OSError:
        log.warning(f'Could not open top-level-domain file {filename}')
    return (top_level_domain_names_with_low_reliability,
            top_level_domain_names_with_normal_reliability,
            top_level_domain_names_with_high_reliability)


def lists_share_element(list1: list, list2: list) -> bool:
    for elem1 in list1:
        for elem2 in list2:
            if elem1 == elem2:
                return True
    return False


re_non_letter = regex.compile(r'\P{L}')
re_split_on_first_letter = regex.compile(r'(\P{L}+)(\p{L}.*)')


def adjust_capitalization(s: str, orig_s) -> str:
    """Adjust capitalization of s according to orig_s. Example: if s=will orig_s=Wo then return Will"""
    if s == orig_s:
        return s
    else:
        if re_non_letter.sub('', s) == (orig_s_letters := re_non_letter.sub('', orig_s)):
            return s
        elif (len(orig_s_letters) >= 1) and orig_s_letters[0].isupper():
            if (len(orig_s_letters) >= 2) and orig_s_letters[1].isupper():
                return s.upper()
            elif m2 := re_split_on_first_letter.match(s):
                return m2.group(1) + m2.group(2).capitalize()
            else:
                return s.capitalize()
        else:
            return s


def increment_dict_count(ht: dict, key: str, increment=1) -> int:
    """For example ht['NUMBER-OF-LINES']"""
    ht[key] = ht.get(key, 0) + increment
    return ht[key]


def join_tokens(tokens: List[str]) -> str:
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
