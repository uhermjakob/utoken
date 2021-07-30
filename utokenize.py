#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
This script is a draft of a tokenizer.
When using STDIN and/or STDOUT, if might be necessary, particularly for older versions of Python, to do
'export PYTHONIOENCODING=UTF-8' before calling this Python script to ensure UTF-8 encoding.
"""
# -*- encoding: utf-8 -*-
import argparse
from itertools import chain
import datetime
import functools
import logging as log
# import os
# from pathlib import Path
import re
import regex
import sys
from typing import Callable, Match, Optional, TextIO
# import unicodedata as ud
from utoken import util

log.basicConfig(level=log.INFO)

__version__ = '0.0.2'
last_mod_date = 'July 29, 2021'


class VertexMap:
    """Maps character positions from current (after insertions/deletions) to original offsets.
    Typical deletions are for many control characters."""
    def __init__(self, s: str):
        self.size = len(s)
        self.char_map_to_orig_start_char = {}
        self.char_map_to_orig_end_char = {}
        for i in range(0, len(s)):
            self.char_map_to_orig_start_char[i] = i
            self.char_map_to_orig_end_char[i+1] = i+1

    def delete_char(self, position, n_characters) -> None:
        """Update VertexMap for deletion of n_characters starting at position."""
        old_len = self.size
        new_len = old_len - n_characters
        for i in range(position, new_len):
            self.char_map_to_orig_start_char[i] = self.char_map_to_orig_start_char[i+n_characters]
            self.char_map_to_orig_end_char[i+1] = self.char_map_to_orig_end_char[i+1+n_characters]
        for i in range(new_len, old_len):
            self.char_map_to_orig_start_char.pop(i, None)
            self.char_map_to_orig_end_char.pop(i+1, None)
        self.size = new_len

    def print(self) -> str:
        result = 'S'
        for i in range(0, self.size):
            result += f' {i}->{self.char_map_to_orig_start_char[i]}'
        result += ' E'
        for i in range(0, self.size):
            result += f' {i+1}->{self.char_map_to_orig_end_char[i+1]}'
        return result


class SimpleSpan:
    """Span from start vertex to end vertex, e.g. 0-1 for first characters.
    Soft version of span can include additional spaces etc. around a token."""
    def __init__(self, hard_from: int, hard_to: int,
                 soft_from: Optional[int] = None, soft_to: Optional[int] = None,
                 vm: Optional[VertexMap] = None):
        if vm:
            self.hard_from = vm.char_map_to_orig_start_char[hard_from]
            self.hard_to = vm.char_map_to_orig_end_char[hard_to]
            self.soft_from = self.hard_from if soft_from is None else vm.char_map_to_orig_start_char[soft_from]
            self.soft_to = self.hard_to if soft_to is None else vm.char_map_to_orig_end_char[soft_to]
        else:
            self.hard_from = hard_from
            self.hard_to = hard_to
            self.soft_from = hard_from if soft_from is None else soft_from
            self.soft_to = hard_to if soft_to is None else soft_to

    def print_hard_span(self) -> str:
        return f'{self.hard_from}-{self.hard_to}'


class ComplexSpan:
    """A complex span is a list of (non-contiguous) spans, e.g. (3-6, 10-13) for the 'cut off' in 'He cut it off.'"""
    def __init__(self, spans: [SimpleSpan]):
        self.spans = spans

    @staticmethod
    def compare_complex_spans(span1, span2) -> bool:
        return span1.spans[0].hard_from - span2.spans[0].hard_from \
            or span1.spans[0].hard_to - span2.spans[0].hard_to

    def print_hard_span(self) -> str:
        self.spans.sort(key=functools.cmp_to_key(ComplexSpan.compare_complex_spans))
        return ','.join(map(SimpleSpan.print_hard_span, self.spans))


class Token:
    """A token is most typically a word, number, or punctuation, but can be a multi-word phrase or part of a word."""
    def __init__(self, surf: str, snt_id: str, creator: str, span: ComplexSpan, orig_surf: Optional[str] = None):
        self.surf = surf
        self.orig_surf = surf if orig_surf is None else orig_surf
        self.snt_id = snt_id
        self.span = span
        self.creator = creator or "TOKEN"
        self.sem_class = None

    def print_short(self) -> str:
        return f'{self.span.print_hard_span()}:{self.creator} {self.surf}'


class Chart:
    def __init__(self, s: str, snt_id: str):
        """A chart is set of spanned tokens."""
        self.orig_s = s     # original sentence
        self.s0 = s         # original sentence without undecodable bytes (only UTF-8 conform characters)
        self.s = s          # current sentence, typically without deletable control characters
        self.snt_id = snt_id
        self.tokens = []
        self.vertex_map = VertexMap(s)

    def delete_char(self, position, n_characters) -> int:
        # function returns number of characters actually deleted
        old_len = len(self.s)
        # sanity check, just in case, but should not happen
        if n_characters + position > old_len:
            n_characters = old_len - position
        if n_characters <= 0:
            return 0
        # update s and vertex_map
        self.s = self.s[:position] + self.s[position+n_characters:]
        self.vertex_map.delete_char(position, n_characters)
        return n_characters

    def register_token(self, token: Token) -> None:
        self.tokens.append(token)

    @staticmethod
    def compare_tokens(token1, token2) -> bool:
        return token1.span.spans[0].hard_from - token2.span.spans[0].hard_from \
            or token1.span.spans[0].hard_to - token2.span.spans[0].hard_to

    def sort_tokens(self) -> None:
        self.tokens.sort(key=functools.cmp_to_key(Chart.compare_tokens))

    def print_short(self) -> str:
        self.sort_tokens()
        return f'Chart {self.snt_id}: ' + ' '.join(map(Token.print_short, self.tokens))

    def print_to_file(self, annotation_file: TextIO) -> None:
        self.sort_tokens()
        annotation_file.write(f'::line {self.snt_id} ::s {self.s0}\n')
        for token in self.tokens:
            annotation_file.write(f'::span {token.span.print_hard_span()} ::type {token.creator} ')
            if token.sem_class and token.sem_class != 'general':
                annotation_file.write(f'::sem-class {token.sem_class} ')
            annotation_file.write(f'::surf {token.surf}\n')


class Tokenizer:
    def __init__(self, lang_code: Optional[str] = None):
        # Ordered list of tokenization steps
        self.tok_step_functions = [self.normalize_characters,
                                   self.tokenize_urls,
                                   self.tokenize_emails,
                                   self.tokenize_mt_punctuation,
                                   self.tokenize_english_contractions,
                                   self.tokenize_numbers,
                                   self.tokenize_abbreviations,
                                   self.tokenize_punctuation,
                                   self.tokenize_main]
        self.next_tok_step_dict = {}
        for i in range(0, len(self.tok_step_functions) - 1):
            self.next_tok_step_dict[self.tok_step_functions[i]] = self.tok_step_functions[i + 1]
        self.next_tok_step_dict[self.tok_step_functions[-1]] = None
        self.char_type_vector_dict = {}
        # Initialize elementary bit vectors (integers each with a different bit set) will be used in bitwise operations.
        # To be expanded.
        self.lv = 0
        bit_vector = 1
        self.char_is_deletable_control_character = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_non_standard_space = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_surrogate = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_ampersand = bit_vector
        self.range_init_char_type_vector_dict()
        self.chart_p = False
        self.first_token_is_line_id_p = False
        self.verbose = False
        self.lang_code = lang_code
        self.n_lines_tokenized = 0
        self.tok_dict = util.ResourceDict()
        if lang_code:
            self.tok_dict.load_resource(f'data/tok-resource-{lang_code}.txt')
        self.tok_dict.load_resource('data/tok-resource.txt')  # language-independent tok-resource
        for lcode in ('eng', 'deu', 'mal'):
            if lcode is not lang_code:
                self.tok_dict.load_resource(f'data/tok-resource-{lcode}.txt')

    def range_init_char_type_vector_dict(self) -> None:
        # Deletable control characters,
        # keeping zero-width joiner/non-joiner (U+200E/U+200F) for now.
        for code_point in chain(range(0x0000, 0x0009), range(0x000B, 0x000D), range(0x000E, 0x0020), [0x007F],  # C0
                                range(0x0080, 0x00A0),     # C1 block of control characters
                                [0x00AD],                  # soft hyphen
                                [0x0640],                  # Arabic tatweel
                                range(0x200E, 0x2010),     # direction marks
                                range(0xFE00, 0xFE10),     # variation selectors 1-16
                                [0xFEFF],                  # byte order mark, zero width no-break space
                                range(0xE0100, 0xE01F0)):  # variation selectors 17-256
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_deletable_control_character
        # Surrogate
        for code_point in range(0xDC80, 0xDD00):
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_surrogate
        # Non-standard space
        for code_point in chain(range(0x2000, 0x200C), [0x00A0, 0x202F, 0x205F, 0x3000]):
            # A0: NO-BREAK SPACE; 202F: NARROW NO-BREAK SPACE; 205F: MEDIUM MATHEMATICAL SPACE; 3000: IDEOGRAPHIC SPACE
            char = chr(code_point)
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_non_standard_space
        # Ampersand
        self.char_type_vector_dict['@'] \
            = self.char_type_vector_dict.get('@', 0) | self.char_is_ampersand

    @staticmethod
    def rec_tok(token_surf: str, s: str, start_position: int, offset: int,
                token_type: str, line_id: str, chart: Optional[Chart],
                lang_code: str, ht: dict, calling_function, **token_kwargs) -> [str, Token]:
        """Recursive tokenization step (same method, applied to remaining string) using token-surf and start-position.
        Once a heuristic has identified a particular token span and type,
        this method computes all offsets, creates a new token, and recursively
        calls the calling function on the string preceding and following the new token."""
        end_position = start_position + len(token_surf)
        offset2 = offset + start_position
        offset3 = offset + end_position
        pre = s[:start_position]
        post = s[end_position:]
        if chart:
            new_token = Token(token_surf, line_id, token_type,
                              ComplexSpan([SimpleSpan(offset2, offset3, vm=chart.vertex_map)]))
            for key, value in token_kwargs.items():
                setattr(new_token, key, value)
            chart.register_token(new_token)
        pre_tokenization = calling_function(pre, chart, ht, lang_code, line_id, offset)
        post_tokenization = calling_function(post, chart, ht, lang_code, line_id, offset3)
        return util.join_tokens([pre_tokenization, token_surf, post_tokenization])

    def rec_tok_m3(self, m3: Match[str], s: str, offset: int,
                   token_type: str, line_id: str, chart: Optional[Chart],
                   lang_code: str, ht: dict, calling_function, **token_kwargs) -> [str, Token]:
        """Recursive tokenization step (same method, applied to remaining string) using Match object.
        The name 'm3' refers to the three groups it expects in the match object:
        (1) pre-token (2) token and (3) post-token.
        Method computes token-surf and start-position, then calls rec_tok."""
        pre_token = m3.group(1)
        token = m3.group(2)
        # post_token = m3.group(3)
        start_position = len(pre_token)
        end_position = start_position + len(token)
        token_surf = s[start_position:end_position]  # in case that the regex match operates on a mapped string
        return self.rec_tok(token_surf, s, start_position, offset, token_type, line_id, chart,
                            lang_code, ht, calling_function, **token_kwargs)

    def next_tok(self, current_tok_function:
                 Optional[Callable[[str, Chart, dict, str, Optional[str], int], str]],
                 s: str, chart: Chart, ht: dict, lang_code: str = '',
                 line_id: Optional[str] = None, offset: int = 0) -> str:
        """Method identifies and calls the next tokenization step (same string, different method)."""
        next_tokenization_function: Callable[[str, Chart, dict, str, Optional[str], int], str] \
            = self.next_tok_step_dict[current_tok_function] if current_tok_function \
            else self.tok_step_functions[0]  # first tokenization step
        if next_tokenization_function:
            s = next_tokenization_function(s, chart, ht, lang_code, line_id, offset)
        return s

    def normalize_characters(self, s: str, chart: Chart, ht: dict, lang_code: str = '',
                             line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenizer step deletes non-decodable bytes and most control characters."""
        this_function = self.normalize_characters
        # delete non-decodable bytes (surrogates)
        if self.lv & self.char_is_surrogate:
            deleted_chars = ''
            deleted_positions = []
            s_orig = s
            for i in range(0, len(s_orig)):
                char = s_orig[i]
                if self.char_type_vector_dict.get(char, 0) & self.char_is_surrogate:
                    s = s.replace(char, '')
                    deleted_chars += char
                    deleted_positions.append(str(i))
            n = len(deleted_positions)
            log.warning(f'Warning: In line {line_id}, '
                        f'deleted non-decodable {util.reg_plural("byte", n)} '
                        f'{deleted_chars.encode("ascii", errors="surrogateescape")} '
                        f'from {util.reg_plural("position", n)} {", ".join(deleted_positions)}')
            if chart:
                chart.s0 = s
                chart.s = s

        # delete some control characters, replace non-standard spaces with ASCII space
        if self.lv & self.char_is_deletable_control_character:
            for i in range(len(s)-1, -1, -1):
                if chart:
                    char = chart.s[i]
                    if self.char_type_vector_dict.get(char, 0) & self.char_is_deletable_control_character:
                        chart.delete_char(i, 1)
                    elif self.char_type_vector_dict.get(char, 0) & self.char_is_non_standard_space:
                        chart.s = chart.s.replace(char, ' ')
                else:
                    char = s[i]
                    if self.char_type_vector_dict.get(char, 0) & self.char_is_deletable_control_character:
                        s = s.replace(char, '')
                    elif self.char_type_vector_dict.get(char, 0) & self.char_is_non_standard_space:
                        s = s.replace(char, ' ')
            if chart:
                s = chart.s
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_url_anchor = re.compile(r'(.*)(?<![a-z])((?:https?|ftp)://)(.*)$', flags=re.IGNORECASE)

    def tokenize_urls(self, s: str, chart: Chart, ht: dict, lang_code: str = '',
                      line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off URL tokens such as https://www.amazon.com"""
        this_function = self.tokenize_urls
        if ('http' in s) or ('ftp' in s):
            if m := self.re_url_anchor.match(s):
                pre = m.group(1)
                anchor = m.group(2)
                post = m.group(3)
                index = 0
                len_post = len(post)
                internal_url_punctuation = "#%&'()*+,-./:;=?@_`~"
                final_url_punctuation = "/"
                # include alphanumeric and certain punctuation characters
                while index < len_post:
                    char = post[index]
                    if char.isalnum():
                        # log.info(f'URL char[{index}]: {char} is alphanumeric')
                        index += 1
                    elif char in internal_url_punctuation:
                        # log.info(f'URL char[{index}]: {char} is internal URL punct')
                        index += 1
                    else:
                        break
                # exclude certain punctuation characters at the end
                while index > 0:
                    char = post[index-1]
                    if char == ')':
                        if '(' in post[0:index-1]:
                            break
                        else:
                            index -= 1
                    elif (char in internal_url_punctuation) and (char not in final_url_punctuation):
                        index -= 1
                    else:
                        break
                # build result
                token_surf = anchor + post[0:index]
                start_position = len(pre)
                return self.rec_tok(token_surf, s, start_position, offset, 'URL',
                                    line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_email = regex.compile(r'(.*?)'
                             r'(?<!\pL\pM*|\d|[.])'
                             r'(\pL\pM*(?:\pL\pM*|\d|[-_.])*(?:\pL\pM*|\d)'
                             r'@'
                             r'\pL\pM*(?:\pL\pM*|\d|[-_.])*(?:\pL\pM*|\d)\.[a-z]{2,})'
                             r'(?!\pL|\pM|\d|[.])'
                             r'(.*)$', flags=regex.IGNORECASE)

    def tokenize_emails(self, s: str, chart: Chart, ht: dict, lang_code: str = '',
                        line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off email-address tokens such as ChunkyLover53@aol.com"""
        this_function = self.tokenize_emails
        if self.lv & self.char_is_ampersand:
            if m3 := self.re_email.match(s):
                return self.rec_tok_m3(m3, s, offset, 'EMAIL-ADDRESS', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_number = regex.compile(r'(.*?)'
                              r'(?<![-−–+.]|\d)'                      # negative lookbehind
                              r'([-−–+]?'                             # plus/minus sign
                              r'(?:\d{1,3}(?:,\d\d\d)+(?:\.\d+)?|'    # Western style, e.g. 12,345,678.90
                              r'\d{1,2}(?:,\d\d)*,\d\d\d(?:\.\d+)?|'  # Indian style, e.g. 1,23,45,678.90
                              r'\d+(?:\.\d+)?))'                      # plain, e.g. 12345678.90
                              r'(?![.,]\d)'                           # negative lookahead
                              r'(.*)')

    def tokenize_numbers(self, s: str, chart: Chart, ht: dict, lang_code: str = '',
                         line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off numbers such as 12,345,678.90"""
        this_function = self.tokenize_numbers
        if m3 := self.re_number.match(s):
            return self.rec_tok_m3(m3, s, offset, 'NUMBER', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_eng_neg_contraction = \
        re.compile(r'(.*?)\b(ai|are|ca|can|could|did|do|does|had|has|have|is|sha|should|was|were|wo|would)'
                   r'(n[o\'’]t)\b(.*)', flags=re.IGNORECASE)
    re_eng_suf_1_contraction = re.compile(r'(.*?[a-z])([\'’](?:ll|re|s|ve))\b(.*)', flags=re.IGNORECASE)
    re_eng_suf_d_contraction = re.compile(r'(.*?[aeiouy])([\'’]d)\b(.*)', flags=re.IGNORECASE)
    re_eng_suf_m_contraction = re.compile(r'(.*?\bI)([\'’]m)\b(.*)', flags=re.IGNORECASE)
    re_eng_preserve_token = regex.compile(r'(.*?)(?<!\pL\pM*|\d)([\'’](?:ll|re|s|ve|d|m))(?!\pL|\pM|\d)(.*)',
                                          flags=regex.IGNORECASE)

    def tokenize_english_contractions(self, s: str, chart: Chart, ht: dict, lang_code: str = '',
                                      line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step handles English contractions, e.g. (don't -> do not; won't -> will not;
        John's -> John 's; he'd -> he 'd"""
        this_function = self.tokenize_english_contractions
        # Tokenize contracted negation, e.g. "can't", "cannot", "couldn't"
        if m := self.re_eng_neg_contraction.match(s):
            pre, orig_token_surf1, token_surf2, post = m.group(1), m.group(2), m.group(3), m.group(4)
            # Expand contracted first part, e.g. "wo" (as in "won't") to "will"
            t1 = orig_token_surf1.lower()
            token_surf1 = 'is' if t1 == 'ai' else 'can' if t1 == 'ca' else 'shall' if t1 == 'sha' \
                else 'will' if t1 == 'wo' else orig_token_surf1
            # adjust capitalization
            if token_surf1 is not orig_token_surf1:
                if (len(orig_token_surf1) >= 1) and orig_token_surf1[0].isupper():
                    if (len(orig_token_surf1) >= 2) and orig_token_surf1[1].isupper():
                        token_surf1 = token_surf1.upper()
                    else:
                        token_surf1 = token_surf1.capitalize()
            start_position = len(pre)
            middle_position = start_position + len(orig_token_surf1)
            end_position = middle_position + len(token_surf2)
            offset2, offset3, offset4 = offset + start_position, offset + middle_position, offset + end_position
            if chart:
                new_token1 = Token(token_surf1, line_id, 'DECONTRACTION1',
                                   ComplexSpan([SimpleSpan(offset2, offset3, vm=chart.vertex_map)]),
                                   orig_surf=orig_token_surf1)
                new_token2 = Token(token_surf2, line_id, 'DECONTRACTION2',
                                   ComplexSpan([SimpleSpan(offset3, offset4, vm=chart.vertex_map)]))
                chart.register_token(new_token1)
                chart.register_token(new_token2)
            pre_tokenization = this_function(pre, chart, ht, lang_code, line_id, offset)
            post_tokenization = this_function(post, chart, ht, lang_code, line_id, offset4)
            return util.join_tokens([pre_tokenization, token_surf1, token_surf2, post_tokenization])
        # Tokenize other contractions such as:
        #   (1) "John's mother", "He's hungry.", "He'll come.", "We're here.", "You've got to be kidding."
        #   (2) "He'd rather die.", "They'd been informed." but not "cont'd"
        #   (3) "I'm done." but not "Ma'm"
        if m3 := self.re_eng_suf_1_contraction.match(s) \
                or self.re_eng_suf_d_contraction.match(s) \
                or self.re_eng_suf_m_contraction.match(s):
            return self.rec_tok_m3(m3, s, offset, 'DECONTRACTION', line_id, chart, lang_code, ht, this_function)
        if m3 := self.re_eng_preserve_token.match(s):
            return self.rec_tok_m3(m3, s, offset, 'PRESERVE', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_right_context_of_initial_letter = regex.compile(r'\s?(?:\p{Lu}\.\s?)*\p{Lu}\p{Ll}{2}')

    def tokenize_abbreviations(self, s: str, chart: Chart, ht: dict, lang_code: str = '',
                               line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off abbreviations ending in a period, searching right to left."""
        this_function = self.tokenize_abbreviations
        for i in range(len(s)-1, -1, -1):
            char = s[i]
            if char == '.':
                start_position = max(0, i - self.tok_dict.max_s_length) - 1
                while start_position+1 < i:
                    start_position += 1
                    if not s[start_position].isalpha():
                        continue  # first character must be a letter
                    if start_position > 0:
                        prev_char = s[start_position-1]
                        if prev_char.isalpha() or (prev_char in "'’"):
                            continue
                    abbrev_cand = s[start_position:i+1]
                    if (resource_entries := self.tok_dict.resource_dict.get(abbrev_cand, None)) \
                        and (abbrev_entries := (resource_entry for resource_entry in resource_entries
                                                if isinstance(resource_entry, util.AbbreviationEntry))):
                        return self.rec_tok(abbrev_cand, s, start_position, offset, 'ABBREV',
                                            line_id, chart, lang_code, ht, this_function,
                                            sem_class=next(abbrev_entries).sem_class)
        for start_position in range(0, len(s)-1):
            char = s[start_position]
            if char.isalpha() and char.isupper() and (s[start_position+1] == '.') \
               and ((start_position == 0) or not s[start_position - 1].isalpha()):
                if self.re_right_context_of_initial_letter.match(s[start_position+2:]):
                    token_surf = s[start_position:start_position+2]
                    return self.rec_tok(token_surf, s, start_position, offset, 'ABBREV-I',
                                        line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_mt_punct = regex.compile(r'(.*?(?:\pL\pM*\pL\pM*|\d|[!?’]))([-−–]+)(\pL\pM*\pL\pM*|\d)')

    def tokenize_mt_punctuation(self, s: str, chart: Chart, ht: dict, lang_code: str = '',
                                line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step currently splits of dashes in certain contexts."""
        this_function = self.tokenize_mt_punctuation
        if m3 := self.re_mt_punct.match(s):
            return self.rec_tok_m3(m3, s, offset, 'DASH', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_punct = re.compile(r'(.*?)'  # break off punctuation anywhere
                          r'(["“”„‟(){}«»\[\]〈〉（）［］【】「」《》。，、։።፣፤፥፦፧፨፠\u3008-\u3011\u3014-\u301B।॥%‰‱٪¢£€¥₹฿©®]|'
                          r'—+|…+|\.{2,}|\$+)'
                          r'(.*)$')
    re_punct_s = re.compile(r'(|.*?\s)(\'+|‘+|[¡¿])(.*)$')  # break off punctuation at the beginning of a token
    re_punct_e = re.compile(r'(.*?)(\'+|’+|[.?!‼⁇⁈⁉‽؟،,;؛！;？；:：])(\s.*|)$')  # break off punct. at the end of a token

    def tokenize_punctuation(self, s: str, chart: Chart, ht: dict, lang_code: str = '',
                             line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off regular punctuation."""
        this_function = self.tokenize_punctuation
        # Some punctuation should always be split off by itself regardless of context:
        # parentheses, brackets, dandas, currency signs.
        if m3 := self.re_punct.match(s):
            return self.rec_tok_m3(m3, s, offset, 'PUNCT', line_id, chart, lang_code, ht, this_function)
        # Some punctuation should be split off from the beginning of a token
        # (with a space or sentence-start to the left of the punctuation).
        if m3 := self.re_punct_s.match(s):
            return self.rec_tok_m3(m3, s, offset, 'PUNCT-S', line_id, chart, lang_code, ht, this_function)
        # Some punctuation should be split off from the end of a token
        # (with a space or sentence-end to the right of the punctuation.
        if m3 := self.re_punct_e.match(s):
            return self.rec_tok_m3(m3, s, offset, 'PUNCT-E', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    @staticmethod
    def tokenize_main(s: str, chart: Chart, _ht: dict, _lang_code: str = '',
                      line_id: Optional[str] = None, offset: int = 0) -> str:
        """This is the final tokenization step that tokenizes the remaining string by spaces."""
        tokens = []
        index = 0
        start_index = None
        len_s = len(s)
        while index <= len_s:
            char = s[index] if index < len_s else ' '
            if char.isspace():
                if start_index is not None:
                    token_surf = s[start_index:index]
                    tokens.append(token_surf)
                    if chart:
                        new_token = Token(token_surf, str(line_id), 'MAIN',
                                          ComplexSpan([SimpleSpan(offset+start_index, offset+index,
                                                                  vm=chart.vertex_map)]))
                        chart.register_token(new_token)
                    start_index = None
            elif start_index is None:
                start_index = index
            index += 1
        return util.join_tokens(tokens)

    def tokenize_string(self, s: str, ht: dict, lang_code: str = '', line_id: Optional[str] = None,
                        annotation_file: Optional[TextIO] = None) -> str:
        regex.DEFAULT_VERSION = regex.VERSION1
        self.lv = 0  # line_char_type_vector
        # Each bit in this vector is to capture character type info, e.g. char_is_arabic
        # Build a bit-vector for the whole line, as the bitwise 'or' of all character bit-vectors.
        for char in s:
            if char_type_vector := self.char_type_vector_dict.get(char, 0):
                # A set bit in the lv means that the bit has been set by at least one char.
                # So we will easily know whether e.g. a line contains a digit.
                # If not, some digit-specific tokenization steps can be skipped to improve run-time.
                self.lv = self.lv | char_type_vector
        # Initialize chart.
        chart = Chart(s, line_id) if self.chart_p else None
        # Call the first tokenization step function, which then recursively call all other tokenization step functions.
        s = self.next_tok(None, s, chart, ht, lang_code, line_id)
        self.n_lines_tokenized += 1
        if chart:
            if self.verbose:
                log.info(chart.print_short())  # Will print short version of chart to STDERR.
            elif (log.INFO >= log.root.level) and (self.n_lines_tokenized % 1000 == 0):
                sys.stderr.write('+' if self.n_lines_tokenized % 10000 == 0 else '.')
            if annotation_file:
                chart.print_to_file(annotation_file)
        return s.strip()

    re_id_snt = re.compile(r'(\S+)(\s+)(\S|\S.*\S)\s*$')

    def tokenize_lines(self, ht: dict, input_file: TextIO, output_file: TextIO, annotation_file: Optional[TextIO],
                       lang_code=''):
        """Apply normalization/cleaning to a file (or STDIN/STDOUT)."""
        line_number = 0
        for line in input_file:
            line_number += 1
            ht['NUMBER-OF-LINES'] = line_number
            if self.first_token_is_line_id_p:
                if m := self.re_id_snt.match(line):
                    line_id = m.group(1)
                    line_id_sep = m.group(2)
                    core_line = m.group(3)
                    output_file.write(line_id + line_id_sep
                                      + self.tokenize_string(core_line, ht, lang_code=lang_code,
                                                             line_id=line_id, annotation_file=annotation_file)
                                      + "\n")
            else:
                output_file.write(self.tokenize_string(line.rstrip("\n"), ht, lang_code=lang_code,
                                                       line_id=str(line_number), annotation_file=annotation_file)
                                  + "\n")


def main(argv):
    """Wrapper around tokenization that takes care of argument parsing and prints change stats to STDERR."""
    # parse arguments
    parser = argparse.ArgumentParser(description='Tokenizes a given text')
    parser.add_argument('-i', '--input', type=argparse.FileType('r', encoding='utf-8', errors='surrogateescape'),
                        default=sys.stdin, metavar='INPUT-FILENAME', help='(default: STDIN)')
    parser.add_argument('-o', '--output', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=sys.stdout, metavar='OUTPUT-FILENAME', help='(default: STDOUT)')
    parser.add_argument('-a', '--annotation', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, metavar='ANNOTATION-FILENAME', help='(optional output)')
    parser.add_argument('--lc', type=str, default='', metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('-f', '--first_token_is_line_id', action='count', default=0, help='First token is line ID')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='write change log etc. to STDERR')
    parser.add_argument('-c', '--chart', action='count', default=0, help='build chart, even without annotation output')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__} last modified: {last_mod_date}')
    args = parser.parse_args(argv)
    lang_code = args.lc
    tok = Tokenizer(lang_code=lang_code)
    tok.chart_p = bool(args.annotation) or bool(args.chart)
    tok.first_token_is_line_id_p = bool(args.first_token_is_line_id)
    tok.verbose = args.verbose

    # Open any input or output files. Make sure utf-8 encoding is properly set (in older Python3 versions).
    if args.input is sys.stdin and not re.search('utf-8', sys.stdin.encoding, re.IGNORECASE):
        log.error(f"Bad STDIN encoding '{sys.stdin.encoding}' as opposed to 'utf-8'. \
                    Suggestion: 'export PYTHONIOENCODING=UTF-8' or use '--input FILENAME' option")
    if args.output is sys.stdout and not re.search('utf-8', sys.stdout.encoding, re.IGNORECASE):
        log.error(f"Error: Bad STDIN/STDOUT encoding '{sys.stdout.encoding}' as opposed to 'utf-8'. \
                    Suggestion: 'export PYTHONIOENCODING=UTF-8' or use use '--output FILENAME' option")

    ht = {}
    start_time = datetime.datetime.now()
    if args.verbose:
        log_info = f'Start: {start_time}  Script: tokenize.py'
        if args.input is not sys.stdin:
            log_info += f'  Input: {args.input.name}'
        if args.output is not sys.stdout:
            log_info += f'  Output: {args.output.name}'
        if args.annotation:
            log_info += f'  Annotation: {args.annotation.name}'
        if tok.chart_p:
            log_info += f'  Chart to be built: {tok.chart_p}'
        if lang_code:
            log_info += f'  ISO 639-3 language code: {lang_code}'
        log.info(log_info)
    tok.tokenize_lines(ht, input_file=args.input, output_file=args.output, annotation_file=args.annotation,
                       lang_code=lang_code)
    if (log.INFO >= log.root.level) and (tok.n_lines_tokenized >= 1000):
        sys.stderr.write('\n')
    # Log some change stats.
    end_time = datetime.datetime.now()
    elapsed_time = end_time - start_time
    number_of_lines = ht.get('NUMBER-OF-LINES', 0)
    lines = 'line' if number_of_lines == 1 else 'lines'
    if args.verbose:
        log.info(f'End: {end_time}  Elapsed time: {elapsed_time}  Processed {str(number_of_lines)} {lines}')
    elif elapsed_time.seconds >= 10:
        log.info(f'Elapsed time: {elapsed_time.seconds} seconds for {number_of_lines:,} {lines}')


if __name__ == "__main__":
    main(sys.argv[1:])
