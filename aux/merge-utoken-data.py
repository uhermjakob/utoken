#!/usr/bin/env python
# merge-utoken-data.py <anchor_filename> <new_filename> > STDOUT!!

import logging as log
import re
import regex
import sys
from typing import Optional
import unicodedata as ud


def strip_diacritics(s):
    return ''.join(c for c in ud.normalize('NFD', s)
                   if ud.category(c) != 'Mn')


def slot_value_in_double_colon_del_list(s: str, slot: str, default: Optional[str] = None) -> str:
    m = re.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', s)
    return m.group(1).strip() if m else default


re_non_letters = regex.compile(r'\PL')


def token_sort_function(s: str) -> str:
    """ removes non-letters, removes diacritics, lowers case; e.g. Capt. -> capt"""
    key1 = strip_diacritics(re_non_letters.sub('', s)).lower()
    return f'{key1} \U000FFFFF {s}'


if __name__ == "__main__":
    log.basicConfig(level=log.INFO)
    # log.info(f'ARGV: {sys.argv}')
    token_sort_function('Capt.')
    group_key_to_token_dict = {}
    anchor_token_to_group_key_dict = {}
    group_key_token_to_anchor_line_dict = {}
    group_key_token_to_new_line_dict = {}
    dict_anchor_reverse = {}
    dict_new = {}
    head_slot_order = ['contraction', 'repair', 'punct-split', 'abbrev', 'lexical', 'misspelling']
    for file in ['anchor', 'new']:
        if file == 'anchor':
            filename = sys.argv[1]
        elif len(sys.argv) >= 3:
            filename = sys.argv[2]
        else:
            continue  # no merge, just re-sort anchor file
        with open(filename) as f:
            line_number = 0
            for line in f:
                line = line.strip('\uFEFF\u000A\u000D')
                line_number += 1
                if m2 := re.match(r"::(\S+)\s+(\S|\S.*?\S)\s*(?::.*|)$", line):
                    head_slot = m2.group(1)
                    token = m2.group(2)
                    head_slot_priority = head_slot_order.index(head_slot) if head_slot in head_slot_order \
                        else len(head_slot_order)
                    group_key = f'{head_slot_priority:03d}'
                    sub_group_p = False
                    if sem_class := slot_value_in_double_colon_del_list(line, 'sem-class'):
                        group_key += f' ::sem-class {sem_class}'
                        sub_group_p = True
                    else:
                        group_key += ' ::sem-class-none'
                    if taxon := slot_value_in_double_colon_del_list(line, 'taxon'):
                        group_key += f' ::taxon {taxon}'
                        sub_group_p = True
                    else:
                        group_key += ' ::taxon-none'
                    if token_category := slot_value_in_double_colon_del_list(line, 'token-category'):
                        group_key += f' ::token-category {token_category}'
                        sub_group_p = True
                    else:
                        group_key += ' ::token-category-none'
                    if tag := slot_value_in_double_colon_del_list(line, 'tag'):
                        group_key += f' ::tag {tag}'
                        sub_group_p = True
                    else:
                        group_key += ' ::tag-none'
                    if etym_lcode := slot_value_in_double_colon_del_list(line, 'etym-lcode'):
                        group_key += f' ::etym-lcode {etym_lcode}'
                        sub_group_p = True
                    else:
                        group_key += ' ::etym-lcode-none'
                    if problem := slot_value_in_double_colon_del_list(line, 'problem'):
                        group_key += f' ::problem {problem}'
                        sub_group_p = True
                    else:
                        group_key += ' ::problem-none'
                    token_list = group_key_to_token_dict.get(group_key, [])
                    if file == 'anchor':
                        anchor_token_to_group_key_dict.setdefault(token, []).append(group_key)
                        group_key_token_to_anchor_line_dict.setdefault(f'{group_key} {token}', []).append(line)
                    elif file == 'new':
                        if ((not sub_group_p)
                                and (group_key_list := anchor_token_to_group_key_dict.get(token, None))):
                            group_key = group_key_list[0]
                        group_key_token_to_new_line_dict.setdefault(f'{group_key} {token}', []).append(line)
                    group_key_to_token_dict.setdefault(group_key, []).append(token)
                elif line.strip() != '' and not line.startswith('#'):
                    log.info(f'L.{line_number}.{file} Missing :: at the beginning')
    for group_key in sorted(group_key_to_token_dict.keys()):
        # print(group_key)
        for token in sorted(set(group_key_to_token_dict.get(group_key, None)), key=token_sort_function):
            # print(f'    {token}')
            last_anchor_line = ''
            for anchor_line in group_key_token_to_anchor_line_dict.get(f'{group_key} {token}', []):
                print(anchor_line)
                last_anchor_line = anchor_line + ' '
            for new_line in group_key_token_to_new_line_dict.get(f'{group_key} {token}', []):
                if not last_anchor_line.startswith(new_line):
                    if new_line.startswith('::misspelling'):
                        print(new_line)
                    else:
                        print('#' + new_line)
        print()
