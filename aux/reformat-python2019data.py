#!/usr/bin/env python

import logging as log
import re
import sys
from typing import Optional


def slot_value_in_double_colon_del_list(s: str, slot: str, default: Optional[str] = None) -> str:
    m = re.match(fr'(?:.*\s)?::{slot}(|\s+\S.*?)(?:\s+::\S.*|\s*)$', s)
    return m.group(1).strip() if m else default


if __name__ == "__main__":
    log.basicConfig(level=log.INFO)
    # print('START')
    line_number = 0
    for line in sys.stdin:
        line_number += 1
        slots = set(re.findall(r'::([a-z]\S*)', line, re.IGNORECASE))
        comment = slot_value_in_double_colon_del_list(line, 'comment')
        lc = slot_value_in_double_colon_del_list(line, 'lc')
        contraction = slot_value_in_double_colon_del_list(line, 'contraction')
        norm = slot_value_in_double_colon_del_list(line, 'norm')
        token = slot_value_in_double_colon_del_list(line, 'token')
        abbreviation_expansion = slot_value_in_double_colon_del_list(line, 'abbreviation-expansion')
        named_entity_type = slot_value_in_double_colon_del_list(line, 'named-entity-type')
        type_value = slot_value_in_double_colon_del_list(line, 'type')
        alt_spelling = slot_value_in_double_colon_del_list(line, 'alt-spelling')    # +hyphen
        plural = slot_value_in_double_colon_del_list(line, 'plural')
        misspelling = slot_value_in_double_colon_del_list(line, 'misspelling')
        case_invariant = slot_value_in_double_colon_del_list(line, 'case-invariant')
        left_context = slot_value_in_double_colon_del_list(line, 'left-context')
        left_typed_context = slot_value_in_double_colon_del_list(line, 'left-typed-context')
        right_context = slot_value_in_double_colon_del_list(line, 'right-context')
        right_typed_context = slot_value_in_double_colon_del_list(line, 'right-typed-context')
        etym_lc = slot_value_in_double_colon_del_list(line, 'etym-lc')
        add_period_if_missing = slot_value_in_double_colon_del_list(line, 'add-period-if-missing')
        suffix_variations = slot_value_in_double_colon_del_list(line, 'suffix-variations')
        sem_class = slot_value_in_double_colon_del_list(line, 'sem-class')
        token_category = slot_value_in_double_colon_del_list(line, 'token-category')
        taxon = slot_value_in_double_colon_del_list(line, 'taxon')
        currency_prefix = slot_value_in_double_colon_del_list(line, 'currency-prefix')

        if line.startswith('::token ') or line.startswith('::misspelling ') or line.startswith('::currency-prefix '):
            if line.startswith('::currency-prefix'):
                out = f'::abbrev {currency_prefix}'
                if abbreviation_expansion:
                    out += f' ::exp {abbreviation_expansion}'
                else:
                    log.info(f'L.{line_number} ::currency-prefix without ::abbreviation-expansion')
                out += " ::token-category prefix"
                if token_category or (type_value and type_value != 'unit'):
                    log.info(f'L.{line_number} ::currency-prefix includes explicit ::type or ::token-category')
            elif abbreviation_expansion:
                out = f'::abbrev {token} ::exp {abbreviation_expansion}'
            elif line.startswith('::misspelling'):
                out = f'::misspelling {misspelling}'
                if norm:
                    out += f' ::target {norm}'
                else:
                    log.info(f'L.{line_number} ::misspelling without ::norm')
            else:
                out = f'::lexical {token}'
            if lc:
                out += f' ::lcode {lc}'
            if etym_lc:
                out += f' ::etym-lcode {etym_lc}'
            if named_entity_type:
                if sem_class:
                    log.info(f"L.{line_number} Duplicate sem-class by named-entity-type '{named_entity_type}'")
                if named_entity_type in ['book', 'broadcast-program',
                                         'city', 'company', 'country', 'country-region', 'criminal-organization',
                                         'disease', 'event', 'festival', 'island', 'military', 'organization',
                                         'person-last-name', 'political-party',
                                         'product', 'protein', 'province', 'publication',
                                         'state', 'treaty', 'world-region']:
                    sem_class = named_entity_type
                else:
                    sem_class = named_entity_type
                    log.info(f"L.{line_number} Unknown named-entity-type '{named_entity_type}'")
                out += f' ::sem-class {sem_class}'
            if type_value:
                if sem_class:
                    log.info(f"L.{line_number} Duplicate sem-class by type '{type_value}'")
                if type_value == 'word':
                    sem_class = None
                elif type_value == 'unit':
                    if currency_prefix:
                        sem_class = 'currency-unit'
                    else:
                        sem_class = 'unit-of-measurement'
                elif type_value in ['symbol', 'URL-prefix']:
                    token_category = type_value
                else:
                    sem_class = type_value
                    log.info(f"L.{line_number} Unknown type '{type}'")
                if token_category:
                    out += f' ::token-category {token_category}'
                if sem_class:
                    out += f' ::sem-class {sem_class}'
            if taxon:
                out += f' ::taxon {taxon}'
            if case_invariant is not None:
                out += ' ::case-sensitive True'
            if left_context:
                out += f' ::left-context {left_context}'
            if left_typed_context:
                out += f' ::left-types-context {left_typed_context}'
            if right_context:
                out += f' ::right-context {right_context}'
            if right_typed_context:
                out += f' ::right-types-context {right_typed_context}'
            if add_period_if_missing:
                out += f' ::add-period-if-missing {add_period_if_missing}'
            if plural:
                out += f' ::plural {plural}'
            if alt_spelling:
                out += f' ::alt-spelling {alt_spelling}'
            if misspelling and not line.startswith('::misspelling'):
                out += f' ::misspelling {misspelling}'
            if suffix_variations:
                out += f' ::suffix-variations {suffix_variations}'
            if comment:
                out += f' ::comment {comment}'
            if extras := (slots - {'token', 'lc', 'case-invariant', 'abbreviation-expansion', 'comment',
                                   'add-period-if-missing', 'alt-spelling', 'misspelling', 'misspelling-type',
                                   'etym-lc', 'suffix-variations', 'norm',
                                   'named-entity-type', 'plural', 'taxon', 'type', 'currency-prefix',
                                   'left-context', 'left-typed-context', 'right-context', 'right-typed-context'}):
                log.warning(f'L.{line_number} abbreviation entry has unknown slots: {extras}')
            print(out)
