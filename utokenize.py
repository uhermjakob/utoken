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
import cProfile
import datetime
import functools
import logging as log
# import os
# from pathlib import Path
import pstats
import re
import regex
import sys
from typing import Callable, List, Match, Optional, TextIO, Tuple, Type
import unicodedata as ud
import util

log.basicConfig(level=log.INFO)

__version__ = '0.0.4'
last_mod_date = 'August 14, 2021'


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
            if token.sem_class:
                annotation_file.write(f'::sem-class {token.sem_class} ')
            annotation_file.write(f'::surf {token.surf}\n')


class Tokenizer:
    def __init__(self, lang_code: Optional[str] = None):
        # Ordered list of tokenization steps
        self.tok_step_functions = [self.normalize_characters,
                                   self.tokenize_xmls,
                                   self.tokenize_urls,
                                   self.tokenize_emails,
                                   self.tokenize_filenames,
                                   self.tokenize_hashtags_and_handles,
                                   self.tokenize_abbreviation_patterns,
                                   self.tokenize_according_to_resource_entries,
                                   self.tokenize_abbreviation_initials,
                                   self.tokenize_abbreviation_periods,
                                   self.tokenize_english_contractions,
                                   self.tokenize_numbers,
                                   self.tokenize_lexical_according_to_resource_entries,
                                   self.tokenize_mt_punctuation,
                                   self.tokenize_punctuation_according_to_resource_entries,
                                   self.tokenize_post_punct,
                                   self.tokenize_main]
        self.next_tok_step_dict = {}
        for i in range(0, len(self.tok_step_functions) - 1):
            self.next_tok_step_dict[self.tok_step_functions[i]] = self.tok_step_functions[i + 1]
        self.next_tok_step_dict[self.tok_step_functions[-1]] = None
        self.char_type_vector_dict = {}
        # The following dictionary captures the irregular mappings from Windows1252 to UTF8.
        # noinspection SpellCheckingInspection
        self.spec_windows1252_to_utf8_dict = {
            '\x80': '\u20AC',  # Euro Sign
            #  81 is unassigned in Windows-1252
            '\x82': '\u201A',  # Single Low-9 Quotation Mark
            '\x83': '\u0192',  # Latin Small Letter F With Hook
            '\x84': '\u201E',  # Double Low-9 Quotation Mark
            '\x85': '\u2026',  # Horizontal Ellipsis
            '\x86': '\u2020',  # Dagger
            '\x87': '\u2021',  # Double Dagger
            '\x88': '\u02C6',  # Modifier Letter Circumflex Accent
            '\x89': '\u2030',  # Per Mille Sign
            '\x8A': '\u0160',  # Latin Capital Letter S With Caron
            '\x8B': '\u2039',  # Single Left-Pointing Angle Quotation Mark
            '\x8C': '\u0152',  # Latin Capital Ligature OE
            #  8D is unassigned in Windows-1252
            '\x8E': '\u017D',  # Latin Capital Letter Z With Caron
            #  8F is unassigned in Windows-1252
            #  90 is unassigned in Windows-1252
            '\x91': '\u2018',  # Left Single Quotation Mark
            '\x92': '\u2019',  # Right Single Quotation Mark
            '\x93': '\u201C',  # Left Double Quotation Mark
            '\x94': '\u201D',  # Right Double Quotation Mark
            '\x95': '\u2022',  # Bullet
            '\x96': '\u2013',  # En Dash
            '\x97': '\u2014',  # Em Dash
            '\x98': '\u02DC',  # Small Tilde
            '\x99': '\u2122',  # Trade Mark Sign
            '\x9A': '\u0161',  # Latin Small Letter S With Caron
            '\x9B': '\u203A',  # Single Right-Pointing Angle Quotation Mark
            '\x9C': '\u0153',  # Latin Small Ligature OE
            #  9D is unassigned in Windows-1252
            '\x9E': '\u017E',  # Latin Small Letter Z With Caron
            '\x9F': '\u0178'  # Latin Capital Letter Y With Diaeresis
        }
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
        bit_vector = bit_vector << 1
        self.char_is_number_sign = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_at_sign = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_apostrophe = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_dash = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_less_than_sign = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_left_square_bracket = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_micro_sign = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_alpha = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_modifier = bit_vector
        bit_vector = bit_vector << 1
        self.char_is_digit = bit_vector
        self.char_is_dash_or_digit = self.char_is_dash | self.char_is_digit
        self.range_init_char_type_vector_dict()
        self.chart_p: bool = False
        self.mt_tok_p: bool = False
        self.first_token_is_line_id_p: bool = False
        self.verbose: bool = False
        self.lang_code: Optional[str] = lang_code
        self.n_lines_tokenized = 0
        self.tok_dict = util.ResourceDict()
        self.current_orig_s: Optional[str] = None
        self.current_s: Optional[str] = None
        self.profile = None
        self.profile_active: bool = False
        self.profile_scope: Optional[str] = None
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
        self.char_type_vector_dict['&'] \
            = self.char_type_vector_dict.get('&', 0) | self.char_is_ampersand
        # Number sign
        self.char_type_vector_dict['#'] \
            = self.char_type_vector_dict.get('#', 0) | self.char_is_number_sign
        # At sign
        self.char_type_vector_dict['@'] \
            = self.char_type_vector_dict.get('@', 0) | self.char_is_at_sign
        # Less-than sign
        self.char_type_vector_dict['<'] \
            = self.char_type_vector_dict.get('<', 0) | self.char_is_less_than_sign
        # Micro sign; often normalized to Greek letter mu
        self.char_type_vector_dict['µ'] \
            = self.char_type_vector_dict.get('µ', 0) | self.char_is_micro_sign
        # At sign
        self.char_type_vector_dict['['] \
            = self.char_type_vector_dict.get('[', 0) | self.char_is_left_square_bracket
        # Apostrophe (incl. right single quotation mark)
        for char in "'’":
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_apostrophe
        # Dash (incl. hyphen)
        for char in "-−–":
            self.char_type_vector_dict[char] \
                = self.char_type_vector_dict.get(char, 0) | self.char_is_dash
        # alpha, digit
        for code_point in range(0x0000, 0xE0200):  # All Unicode points
            char = chr(code_point)
            if char.isalpha():
                self.char_type_vector_dict[char] \
                    = self.char_type_vector_dict.get(char, 0) | self.char_is_alpha
            elif char.isdigit():
                self.char_type_vector_dict[char] \
                    = self.char_type_vector_dict.get(char, 0) | self.char_is_digit
            elif ud.category(char).startswith("M"):
                self.char_type_vector_dict[char] \
                    = self.char_type_vector_dict.get(char, 0) | self.char_is_modifier

    def add_any_mt_tok_delimiter(self, token: str, start_offset: int, end_offset: int) -> str:
        """In MT-tokenization mode, adds @ before and after certain punctuation so facilitate later detokenization."""
        if token in ['-']:
            if current_s := self.current_s:
                # left_context = current_s[:start_offset]
                # right_context = current_s[end_offset:]
                # token0 = token
                if not (start_offset and current_s[start_offset-1].isspace()):
                    token = "@" + token
                if not ((end_offset < len(current_s)) and current_s[end_offset].isspace()):
                    token = token + "@"
                # log.info(f'add@: {left_context} :: {token0} :: {right_context} => {token}')
        return token

    def rec_tok(self, token_surfs: List[str], start_positions: List[int], s: str, offset: int,
                token_type: str, line_id: str, chart: Optional[Chart], lang_code: Optional[str],
                ht: dict, calling_function, orig_token_surfs: Optional[List[str]] = None,
                **kwargs) -> [str, Token]:
        """Recursive tokenization step (same method, applied to remaining string) using token-surf and start-position.
        Once a heuristic has identified a particular token span and type,
        this method computes all offsets, creates a new token, and recursively
        calls the calling function on the string preceding and following the new token.
        token_surfs/start_positions must not overlap and be in order"""
        # log.info(f'rec_tok token_surfs: {token_surfs} orig_token_surfs: {orig_token_surfs} '
        #          f'start_positions: {start_positions} s: {s} offset: {offset}')
        tokenizations = []
        position = 0
        for i in range(len(token_surfs)):
            token_surf = token_surfs[i]
            orig_token_surf = orig_token_surfs[i] if orig_token_surfs else token_surf
            start_position = start_positions[i]
            end_position = start_position + len(orig_token_surf)
            offset1 = offset + position
            offset2 = offset + start_position
            offset3 = offset + end_position
            if self.mt_tok_p:
                token_surf = self.add_any_mt_tok_delimiter(token_surf, offset2, offset3)
            if pre := s[position:start_position]:
                if i == 0 and kwargs.get('left_done', False):
                    tokenizations.append(self.next_tok(calling_function, pre, chart, ht, lang_code, line_id, offset1))
                else:
                    tokenizations.append(calling_function(pre, chart, ht, lang_code, line_id, offset1))
            tokenizations.append(token_surf)
            if chart:
                new_token = Token(token_surf, line_id, token_type,
                                  ComplexSpan([SimpleSpan(offset2, offset3, vm=chart.vertex_map)]),
                                  orig_surf=orig_token_surf)
                for key, value in kwargs.items():
                    if hasattr(new_token, key):
                        setattr(new_token, key, value)
                chart.register_token(new_token)
            position = end_position
        if post := s[position:]:
            tokenizations.append(calling_function(post, chart, ht, lang_code, line_id, offset+position))
        return util.join_tokens(tokenizations)

    def rec_tok_m3(self, m3: Match[str], s: str, offset: int,
                   token_type: str, line_id: str, chart: Optional[Chart],
                   lang_code: str, ht: dict, calling_function, **token_kwargs) -> [str, Token]:
        """Recursive tokenization step (same method, applied to remaining string) using Match object.
        The name 'm3' refers to the three groups it expects in the match object:
        (1) pre-token (2) token and (3) post-token.
        Method computes token-surf and start-position, then calls rec_tok."""
        pre_token, token, post_token = m3.group(1, 2, 3)
        start_position = len(pre_token)
        end_position = start_position + len(token)
        token_surf = s[start_position:end_position]  # in case that the regex match operates on a mapped string
        return self.rec_tok([token_surf], [start_position], s, offset, token_type, line_id, chart,
                            lang_code, ht, calling_function, [token_surf], **token_kwargs)

    def rec_tok_m5(self, m5: Match[str], s: str, offset: int,
                   token_type: str, line_id: str, chart: Optional[Chart],
                   lang_code: str, ht: dict, calling_function, **token_kwargs) -> [str, Token]:
        """Two-token version of rec_tok_m3.
        Recursive double tokenization step (same method, applied to remaining string) using Match object.
        The name 'm5' refers to the three groups it expects in the match object:
        (1) pre-token (2) token1 and (3) inter-token (4) token2 (5) post-token.
        Method computes token-surf and start-position, then calls rec_tok."""
        pre_token, token1, inter_token, token2, post_token = m5.group(1, 2, 3, 4, 5)
        start_position1 = len(pre_token)
        end_position1 = start_position1 + len(token1)
        start_position2 = end_position1 + len(inter_token)
        end_position2 = start_position2 + len(token2)
        token_surfs = [s[start_position1:end_position1], s[start_position2:end_position2]]
        start_positions = [start_position1, start_position2]
        return self.rec_tok(token_surfs, start_positions, s, offset, token_type, line_id, chart,
                            lang_code, ht, calling_function, token_surfs, **token_kwargs)

    def next_tok(self, current_tok_function:
                 Optional[Callable[[str, Chart, dict, str, Optional[str], int], str]],
                 s: str, chart: Chart, ht: dict, lang_code: str = '',
                 line_id: Optional[str] = None, offset: int = 0) -> str:
        """Method identifies and calls the next tokenization step (same string, different method)."""
        next_tokenization_function: Callable[[str, Chart, dict, str, Optional[str], int], str] \
            = self.next_tok_step_dict[current_tok_function] if current_tok_function \
            else self.tok_step_functions[0]  # first tokenization step
        if self.profile_scope:
            next_tokenization_function_name = next_tokenization_function.__name__
            if self.profile_scope == next_tokenization_function_name:
                # log.info(f'enable for {next_tokenization_function_name}')
                self.profile.enable()
                self.profile_active = True
            elif self.profile_active:
                # log.info(f'disable for {next_tokenization_function_name}')
                self.profile_active = False
                self.profile.disable()
        if next_tokenization_function:
            s = next_tokenization_function(s, chart, ht, lang_code, line_id, offset)
        return s

    def apply_spec_windows1252_to_utf8_mapping_dict(self, match: Match[str]) -> str:
        """Maps substring resulting from misencoding to repaired UTF8."""
        s = match.group()
        if s in self.spec_windows1252_to_utf8_dict:
            return self.spec_windows1252_to_utf8_dict[s]
        else:
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

        # Replace &#160; &#xA0; &nbsp; with U+00A0 (non-breakable space)
        if self.lv & self.char_is_ampersand:
            s = re.sub(r'&#160;|&#xA0;|&nbsp;', u'\u00A0', s, flags=re.IGNORECASE)
            if chart:
                chart.s0 = s
                chart.s = s

        # replace micro sign (µ) by Greek letter mu (μ)
        if self.lv & self.char_is_micro_sign:
            s = re.sub('µ', 'μ', s)  # Yes, they look alike!
            if chart:
                chart.s = s

        # repair some control characters in the C1 Control black (assuming they are still unconverted Windows1252),
        # delete some control characters, replace non-standard spaces with ASCII space
        if self.lv & self.char_is_deletable_control_character:
            s = re.sub(r'[\u0080-\u009F]', self.apply_spec_windows1252_to_utf8_mapping_dict, s)
            # update line vector
            for char in s:
                if char_type_vector := self.char_type_vector_dict.get(char, 0):
                    self.lv = self.lv | char_type_vector
            if chart:
                chart.s = s
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
        self.current_s = s
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_xml = re.compile(r'(.*?)'
                        r'(@?</?[a-z][-_:a-z0-9]*(?:\s+[a-z][-_:a-z0-9]*="[^"]*")*\s*/?>@?|'  # open tag
                        r'<\$[-_a-z0-9]+\$>|'                                                 # close tag
                        r'<!--.*?-->)'                                                        # comment tag
                        r'(.*)$',
                        flags=re.IGNORECASE)
    re_BBCode = re.compile(r'(.*?)'
                           r'(\[(?:QUOTE|URL)=[^\t\n\[\]]+]|\[/?(?:QUOTE|IMG|INDENT|URL)])'
                           r'(.*)$',
                           flags=re.IGNORECASE)

    def tokenize_xmls(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                      line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off XML tokens such as <a href="URL">...</a>"""
        this_function = self.tokenize_xmls
        if self.lv & self.char_is_less_than_sign:
            if m3 := self.re_xml.match(s):
                return self.rec_tok_m3(m3, s, offset, 'XML', line_id, chart, lang_code, ht, this_function)
        if self.lv & self.char_is_left_square_bracket:
            if m3 := self.re_BBCode.match(s):
                return self.rec_tok_m3(m3, s, offset, 'BBCode', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_dot_ab = regex.compile(r'.*\.[a-z][a-z]', flags=regex.IGNORECASE)  # expected in URLs and filenames
    re_url1 = regex.compile(r'(.*?)'
                            r"((?:https?|ftps?)://"
                            r"(\p{L}\p{M}*|\d|[-_,./:;=?@'`~#%&*+]|\((?:\p{L}\p{M}*|\d|[-_,./:;=?@'`~#%&*+])\))+"
                            r"(?:\p{L}\p{M}*|\d|[/]))"
                            r'(.*)$',
                            flags=regex.IGNORECASE)
    # Consider out-sourcing the following top-level domain names to data file.
    # Challenge: top-domain names (e.g. at|be|in|is|it|my|no|so|US) that can also be regular words, e.g. G-20.In car.so
    common_top_domain_suffixes = "museum|info|cat|com|edu|gov|int|mil|net|org|ar|at|au|be|bg|bi|br|ca|ch|cn|co|cz|" \
                                 "de|dk|es|eu|fi|fr|gr|hk|hu|id|ie|il|in|ir|is|it|jp|ke|kr|lu|mg|mx|my|nl|no|nz|" \
                                 "ph|pl|pt|ro|rs|ru|rw|se|sg|sk|so|tr|tv|tw|tz|ua|ug|uk|us|za"
    re_url2 = regex.compile(r'(.*?)'
                            r'(?<![\p{Latin}&&\p{Letter}]|\@)'  # negative lookbehind: no Latin+ letters, no @ please
                            r"((?:www(?:\.(?:\p{L}\p{M}*|\d|[-_]))+\.(?:[a-z]{2,4}]))|"
                            r"(?:(?:(?:\p{L}\p{M}*|\d|[-_])+\.)+(?:" + common_top_domain_suffixes + ")))"
                            r'(?![\p{Latin}&&\p{Letter}])'      # negative lookahead: no Latin+ letters please
                            r'(.*)$',
                            flags=regex.IGNORECASE)

    def tokenize_urls(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                      line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off URL tokens such as https://www.amazon.com"""
        this_function = self.tokenize_urls
        if self.re_dot_ab.match(s):
            if m3 := self.re_url1.match(s) or self.re_url2.match(s):
                return self.rec_tok_m3(m3, s, offset, 'URL', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    common_file_suffixes = "aspx?|bmp|cgi|csv|docx?|eps|gif|html?|jpeg|jpg|mov|mp3|mp4|" \
                           "pdf|php|png|pptx?|ps|rtf|tiff|tsv|tok|txt|xlsx?|xml"
    re_filename = regex.compile(r'(.*?)'
                                r'(?<!\pL\pM*|\d|[-_.@])'  # negative lookbehind: no letters, digits, @ please
                                r"((?:\pL\pM*)(?:\pL\pM*|\d|[-_.])*(?:\pL\pM*|\d)\.(?:" + common_file_suffixes + "))"
                                r'(?!\pL|\d)'      # negative lookahead: no letters or digits please
                                r'(.*)$',
                                flags=regex.IGNORECASE)

    def tokenize_filenames(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                           line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off filename tokens such as presentation.pptx"""
        this_function = self.tokenize_filenames
        if self.re_dot_ab.match(s):
            if m3 := self.re_filename.match(s):
                return self.rec_tok_m3(m3, s, offset, 'FILENAME', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_email = regex.compile(r'(.*?)'
                             r'(?<!\pL\pM*|\d|[.])'
                             r'(\pL\pM*(?:\pL\pM*|\d|[-_.])*(?:\pL\pM*|\d)'
                             r'@'
                             r'\pL\pM*(?:\pL\pM*|\d|[-_.])*(?:\pL\pM*|\d)\.[a-z]{2,})'
                             r'(?!\pL|\pM|\d|[.])'
                             r'(.*)$', flags=regex.IGNORECASE)

    def tokenize_emails(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                        line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off email-address tokens such as ChunkyLover53@aol.com"""
        this_function = self.tokenize_emails
        if self.lv & self.char_is_at_sign:
            if m3 := self.re_email.match(s):
                return self.rec_tok_m3(m3, s, offset, 'EMAIL-ADDRESS', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_hashtags_and_handles = regex.compile(r'(|.*?[ .,;()\[\]{}\'])'
                                            r'([#@]\pL\pM*(?:\pL\pM*|\d|[_])*(?:\pL\pM*|\d))'
                                            r'(?![.]?(?:\pL|\d))'
                                            r'(.*)$', flags=regex.IGNORECASE)

    def tokenize_hashtags_and_handles(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                                      line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off email-address tokens such as ChunkyLover53@aol.com"""
        this_function = self.tokenize_hashtags_and_handles
        if self.lv & (self.char_is_number_sign | self.char_is_at_sign):
            if m3 := self.re_hashtags_and_handles.match(s):
                token_type = "HASHTAG" if m3.group(2)[0] == '#' else 'HANDLE'
                return self.rec_tok_m3(m3, s, offset, token_type, line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_number = regex.compile(r'(.*?)'                                # excludes integers
                              r'(?<![-−–+.]|\d)'                      # negative lookbehind
                              r'([-−–+]?'                             # plus/minus sign
                              r'(?:\d{1,3}(?:,\d\d\d)+(?:\.\d+)?|'    # Western style, e.g. 12,345,678.90
                              r'\d{1,2}(?:,\d\d)*,\d\d\d(?:\.\d+)?|'  # Indian style, e.g. 1,23,45,678.90
                              r'\d+\.\d+))'                           # floating point, e.g. 12345678.90
                              r'(?![.,]\d)'                           # negative lookahead
                              r'(.*)')
    re_integer = regex.compile(r'(.*?)'
                               r'(?<![-−–+.]|\d|\pL\pM*)'             # negative lookbehind (stricter: no letters)
                               r'([-−–+]?'                            # plus/minus sign
                               r'\d+)'                                # plain integer, e.g. 12345678
                               r'(?![-−–.,]?\d)'                      # negative lookahead
                               r'(.*)')

    def tokenize_numbers(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                         line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off numbers such as 12,345,678.90"""
        this_function = self.tokenize_numbers
        if self.lv & self.char_is_digit:
            if m3 := self.re_number.match(s) or self.re_integer.match(s):
                return self.rec_tok_m3(m3, s, offset, 'NUMBER', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_eng_suf_contraction = re.compile(r'(.*?[a-z])([\'’](?:d|em|ll|m|re|s|ve))\b(.*)', flags=re.IGNORECASE)

    def tokenize_english_contractions(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                                      line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step handles English contractions such as John's -> John 's; he'd -> he 'd
        Others such as don't -> do not; won't -> will not are handled as resource_entries"""
        this_function = self.tokenize_english_contractions
        if self.lv & self.char_is_apostrophe:
            # Tokenize contractions such as:
            # (1) "John's mother", "He's hungry.", "He'll come.", "We're here.", "You've got to be kidding."
            # (2) "He'd rather die.", "They'd been informed.", "It'd be like war.",  but not "cont'd", "EFF'd up people"
            # (3) "I'm done.", "I don't like'm.", "Get'em."
            if m3 := self.re_eng_suf_contraction.match(s):
                return self.rec_tok_m3(m3, s, offset, 'DECONTRACTION', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    def resource_entry_fulfills_conditions(self, resource_entry: util.ResourceEntry,
                                           required_resource_entry_type: Type[util.ResourceEntry],
                                           token_surf: str, _s: str, start_position: int, end_position: int,
                                           offset: int) -> bool:
        """This method checks whether a resource-entry is of the proper type fulfills any conditions associated with it,
        including case-sensitive and positive and/or negative contexts to the left and/or right."""
        if not isinstance(resource_entry, required_resource_entry_type):
            # log.info(f'resource-entry({token_surf}) is not {required_resource_entry_type}')
            return False
        if resource_entry.case_sensitive:
            if resource_entry.s != token_surf:
                # log.info(f'resource-entry({token_surf}) no match case of {resource_entry.s}')
                return False
        if re_l := resource_entry.left_context:
            if not re_l.match(_left_context_s := self.current_s[:offset+start_position]):
                # log.info(f'resource-entry({token_surf}) no match left-context {re_l} with "{left_context_s}"')
                return False
        if re_l_n := resource_entry.left_context_not:
            if not re_l_n.match(_left_context_s := self.current_s[:offset+start_position]):
                # log.info(f'resource-entry({token_surf}) no match left-context-neg {re_l_n} with "{left_context_s}"')
                return False
        if re_r := resource_entry.right_context:
            if not re_r.match(_right_context_s := self.current_s[offset+end_position:]):
                # log.info(f'resource-entry({token_surf}) no match right-context {re_r} with "{right_context_s}"')
                return False
        if re_r_n := resource_entry.right_context_not:
            if not re_r_n.match(_right_context_s := self.current_s[offset+end_position:]):
                # log.info(f'resource-entry({token_surf}) no match right-context-not {re_r_n} with "{right_context_s}"')
                return False
        return True

    re_letters_only = regex.compile(r'\P{L}')

    def adjust_capitalization(self, s: str, orig_s) -> str:
        """Adjust capitalization of s according to orig_s. Example: if s=will orig_s=Wo then return Will"""
        if s == orig_s:
            return s
        else:
            if self.re_letters_only.sub('', s) == (orig_s_letters := self.re_letters_only.sub('', orig_s)):
                return s
            elif (len(orig_s_letters) >= 1) and orig_s_letters[0].isupper():
                if (len(orig_s_letters) >= 2) and orig_s_letters[1].isupper():
                    return s.upper()
                else:
                    return s.capitalize()
            else:
                return s

    re_space = re.compile(r'\s+')

    def map_contraction(self, orig_token: str, contraction_source: str, contraction_target: str,
                        orig_start_position: int, char_splits: Optional[List[int]] = None) \
            -> Tuple[List[str], List[str], List[int]]:
        """Example: orig_token='Can't' contraction_source='can't' contraction_target='can n't'"""

        if char_splits:
            start_position = orig_start_position
            remaining_orig_token = orig_token
            target_tokens = self.re_space.split(contraction_target)
            start_positions, tokens, orig_tokens = [], [], []
            for i in range(0, len(char_splits)):
                orig_token_len = char_splits[i]
                orig_token_elem = remaining_orig_token[:orig_token_len]
                orig_tokens.append(orig_token_elem)
                remaining_orig_token = remaining_orig_token[orig_token_len:]
                start_positions.append(start_position)
                start_position += orig_token_len
                target_token = target_tokens[i]
                adjusted_target_token = self.adjust_capitalization(target_token, orig_token_elem)
                tokens.append(adjusted_target_token)
            return tokens, orig_tokens, start_positions
        elif (' ' not in contraction_source) and (' ' not in contraction_target):
            return [self.adjust_capitalization(contraction_target, orig_token)], [orig_token], [orig_start_position]
        else:
            tokens1 = []
            tokens2 = []
            orig_tokens1 = []
            orig_tokens2 = []
            start_positions1 = []
            start_positions2 = []
            token = orig_token
            start_position = orig_start_position
            end_position = start_position+len(token)
            source = contraction_source
            target = contraction_target

            while token != '':
                # log.info(f'token: {token} source: {source} target: {target} start_position: {start_position} '
                #          f'end_position: {end_position}')
                target_elements = target.split()
                if target_elements and source.endswith(target_elements[-1]):
                    token_elem_len = len(target_elements[-1])
                    token_elem_start_position = end_position-token_elem_len
                    token_elem = target_elements.pop()
                    orig_token_elem = token[len(token)-token_elem_len:]
                    # log.info(f'insert token-e: {token_elem} orig_tokens: {orig_token_elem} '
                    #          f'start_positions: {token_elem_start_position}')
                    tokens2.insert(0, self.adjust_capitalization(token_elem, orig_token_elem))
                    orig_tokens2.insert(0, orig_token_elem)
                    start_positions2.insert(0, token_elem_start_position)
                    end_position -= token_elem_len
                    token = token[:-token_elem_len]
                    source = source[:-token_elem_len]
                    target = target[:-token_elem_len].rstrip()
                    while token.endswith(' '):
                        end_position -= 1
                        token = token[:-1]
                        if target.endswith(' '):
                            target = target[:-1]
                elif target_elements and source.startswith(target_elements[0]):
                    token_elem_len = len(target_elements[0])
                    token_elem_start_position = start_position
                    token_elem = target_elements.pop(0)
                    orig_token_elem = token[:token_elem_len]
                    # log.info(f'insert token-s: {token_elem} orig_tokens: {orig_token_elem} '
                    #          f'start_positions: {token_elem_start_position}')
                    tokens1.append(self.adjust_capitalization(token_elem, orig_token_elem))
                    orig_tokens1.append(orig_token_elem)
                    start_positions1.append(token_elem_start_position)
                    start_position += token_elem_len
                    token = token[token_elem_len:]
                    source = source[token_elem_len:]
                    target = target[token_elem_len:].lstrip()
                    while token.startswith(' '):
                        start_position += 1
                        token = token[1:]
                        if target.startswith(' '):
                            target = target[1:]
                elif len(target_elements) >= 1:  # Primarily for single target_elements.
                    # For multiple remaining mismatching target_elements, consider a separate case below.
                    # log.info(f'insert token-w: {target} orig_tokens: {token} '
                    #          f'start_positions: {start_position}')
                    tokens1.append(self.adjust_capitalization(target, token))
                    orig_tokens1.append(token)
                    start_positions1.append(start_position)
                    token = ""
                else:
                    break
            # log.info(f'return tokens: {tokens1 + tokens2} orig_tokens: {orig_tokens1 + orig_tokens2} '
            #          f'start_positions: {start_positions1+start_positions2}')
            return tokens1 + tokens2, orig_tokens1 + orig_tokens2, start_positions1 + start_positions2

    re_starts_w_modifier = regex.compile(r'\pM')
    re_starts_w_letter = regex.compile(r'\pL')
    re_starts_w_letter_or_digit = regex.compile(r'(\pL|\d)')
    re_starts_w_dashed_digit = regex.compile(r'[-−–]?\d')
    re_starts_w_single_s = regex.compile(r's(?!\pL|\d)', flags=regex.IGNORECASE)
    re_ends_w_letter = regex.compile(r'.*\pL\pM*$')          # including any modifiers
    re_ends_w_apostrophe = regex.compile(r".*['‘’]$")
    re_ends_w_letter_or_digit = regex.compile(r'.*(\pL\pM*|\d)$')

    def tokenize_according_to_resource_entries(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                                               line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step handles abbreviations, contractions and repairs according to data files
        such as data/tok-resource-eng.txt."""
        this_function = self.tokenize_according_to_resource_entries

        last_primary_char_type_vector = 0  # 'primary': not counting modifying letters
        len_s = len(s)
        s_lc = s.lower()
        for start_position in range(0, len_s):
            c = s[start_position]
            current_char_type_vector = self.char_type_vector_dict.get(c, 0)
            if current_char_type_vector & self.char_is_modifier:
                continue
            # general restriction: if token starts with a letter, it can't be preceded by a letter
            if last_primary_char_type_vector & self.char_is_alpha \
                    and current_char_type_vector & self.char_is_alpha:
                continue
            max_end_position = start_position
            position = start_position+1
            while position <= len_s and self.tok_dict.prefix_dict.get(s_lc[start_position:position], False):
                max_end_position = position
                position += 1
            end_position = max_end_position
            while end_position > start_position:
                token_candidate = s[start_position:end_position]
                token_candidate_lc = s_lc[start_position:end_position]
                right_context = s[end_position:]
                rc0 = right_context[0] if right_context != '' else ' '  # first character of right context
                rc0_type_vector = self.char_type_vector_dict.get(rc0, 0)
                # general restriction: if token ends in a letter, it can't be followed by a letter
                token_candidate_ends_in_letter = bool(self.re_ends_w_letter.match(token_candidate))
                if (not(token_candidate_ends_in_letter and (rc0_type_vector & self.char_is_alpha))
                        and not(rc0_type_vector & self.char_is_modifier)):  # not followed by orphan modifier
                    for resource_entry in self.tok_dict.resource_dict.get(token_candidate_lc, []):
                        if self.resource_entry_fulfills_conditions(resource_entry, util.ResourceEntry, token_candidate,
                                                                   s, start_position, end_position, offset):
                            sem_class = resource_entry.sem_class
                            resource_surf = resource_entry.s
                            clause = ''
                            if sem_class:
                                clause += f'; sem: {sem_class}'
                            if (isinstance(resource_entry, util.AbbreviationEntry)
                                    and ((sem_class == 'currency-unit')
                                         or (not(token_candidate_ends_in_letter
                                                 and (rc0_type_vector & self.char_is_dash_or_digit)  # quick pre-check
                                                 and self.re_starts_w_dashed_digit.match(right_context))))):
                                return self.rec_tok([token_candidate], [start_position], s, offset, 'ABBREV',
                                                    line_id, chart, lang_code, ht, this_function, [token_candidate],
                                                    sem_class=resource_entry.sem_class, left_done=True)
                            if isinstance(resource_entry, util.ContractionEntry):
                                tokens, orig_tokens, start_positions = \
                                    self.map_contraction(token_candidate, resource_surf, resource_entry.target,
                                                         start_position, char_splits=resource_entry.char_splits)
                                return self.rec_tok(tokens, start_positions, s, offset, 'DECONTRACTION',
                                                    line_id, chart, lang_code, ht, this_function, orig_tokens,
                                                    sem_class=resource_entry.sem_class, left_done=True)
                            if isinstance(resource_entry, util.RepairEntry):
                                tokens, orig_tokens, start_positions = \
                                    self.map_contraction(token_candidate, resource_surf, resource_entry.target,
                                                         start_position)
                                return self.rec_tok(tokens, start_positions, s, offset, 'REPAIR',
                                                    line_id, chart, lang_code, ht, this_function, orig_tokens,
                                                    sem_class=resource_entry.sem_class, left_done=True)
                end_position -= 1
            last_primary_char_type_vector = current_char_type_vector
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    def tokenize_lexical_according_to_resource_entries(self, s: str, chart: Chart, ht: dict,
                                                       lang_code: Optional[str] = None, line_id: Optional[str] = None,
                                                       offset: int = 0) -> str:
        """This tokenization step handles lexical entries according to data files such as data/tok-resource-eng.txt.
        This method mirrors the structure of tokenize_according_to_resource_entries. It is separate,
        because it needs to be mch further down the tokenization step sequence."""
        this_function = self.tokenize_lexical_according_to_resource_entries

        last_primary_char_type_vector = 0  # 'primary': not counting modifying letters
        len_s = len(s)
        s_lc = s.lower()
        for start_position in range(0, len_s):
            c = s[start_position]
            current_char_type_vector = self.char_type_vector_dict.get(c, 0)
            if current_char_type_vector & self.char_is_modifier:
                continue
            # general restriction: if token starts with a letter, it can't be preceded by a letter
            if last_primary_char_type_vector & self.char_is_alpha \
                    and current_char_type_vector & self.char_is_alpha:
                continue
            max_end_position = start_position
            position = start_position+1
            while position <= len_s \
                    and self.tok_dict.prefix_dict_lexical.get(s_lc[start_position:position], False):
                max_end_position = position
                position += 1
            end_position = max_end_position
            while end_position > start_position:
                token_candidate = s[start_position:end_position]
                token_candidate_lc = s_lc[start_position:end_position]
                right_context = s[end_position:]
                rc0 = right_context[0] if right_context != '' else ' '  # first character of right context
                rc0_type_vector = self.char_type_vector_dict.get(rc0, 0)
                # general restriction: if token ends in a letter, it can't be followed by a letter
                if (not((rc0_type_vector & self.char_is_alpha) and self.re_ends_w_letter.match(token_candidate))
                        and not(rc0_type_vector & self.char_is_modifier)):  # not followed by orphan modifier
                    for resource_entry in self.tok_dict.resource_dict.get(token_candidate_lc, []):
                        if self.resource_entry_fulfills_conditions(resource_entry, util.LexicalEntry, token_candidate,
                                                                   s, start_position, end_position, offset):
                            sem_class = resource_entry.sem_class
                            clause = ''
                            if sem_class:
                                clause += f'; sem: {sem_class}'
                            left_context = s[:start_position]
                            if (not(self.re_ends_w_letter_or_digit.match(token_candidate)
                                    and self.re_starts_w_letter_or_digit.match(right_context))
                                    and (not(self.re_ends_w_letter_or_digit.match(left_context)
                                             and self.re_starts_w_letter_or_digit.match(token_candidate)))
                                    # don't split off d' from d's etc.
                                    and (not(self.re_ends_w_apostrophe.match(token_candidate)
                                             and self.re_starts_w_single_s.match(right_context)))):
                                return self.rec_tok([token_candidate], [start_position], s, offset,
                                                    resource_entry.tag or 'LEXICAL',
                                                    line_id, chart, lang_code, ht, this_function, [token_candidate],
                                                    sem_class=resource_entry.sem_class, left_done=True)
                end_position -= 1
            last_primary_char_type_vector = current_char_type_vector
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    def tokenize_punctuation_according_to_resource_entries(self, s: str, chart: Chart, ht: dict,
                                                           lang_code: Optional[str] = None,
                                                           line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step handles punctuation according to data files such as data/tok-resource-eng.txt.
        This method mirrors the structure of tokenize_according_to_resource_entries. It is separate,
        because it needs to be mch further down the tokenization step sequence."""
        this_function = self.tokenize_punctuation_according_to_resource_entries

        len_s = len(s)
        s_lc = s.lower()
        for start_position in range(0, len_s):
            max_end_position = start_position
            position = start_position+1
            while position <= len_s and self.tok_dict.prefix_dict_punct.get(s_lc[start_position:position], False):
                max_end_position = position
                position += 1
            end_position = max_end_position
            while end_position > start_position:
                token_candidate = s[start_position:end_position]
                token_candidate_lc = s[start_position:end_position]
                for resource_entry in self.tok_dict.resource_dict.get(token_candidate_lc, []):
                    if self.resource_entry_fulfills_conditions(resource_entry, util.PunctSplitEntry, token_candidate,
                                                               s, start_position, end_position, offset):
                        side = resource_entry.side
                        end_position2 = end_position
                        if resource_entry.group:
                            while end_position2 < len_s and s[end_position2-1] == s[end_position2]:
                                end_position2 += 1
                        token = s[start_position:end_position2]  # includes any group reduplication
                        if side == 'both':
                            return self.rec_tok([token], [start_position], s, offset, 'PUNCT',
                                                line_id, chart, lang_code, ht, this_function, [token],
                                                sem_class=resource_entry.sem_class)
                        elif side == 'start' and ((start_position == 0) or s[start_position-1].isspace()):
                            return self.rec_tok([token], [start_position], s, offset, 'PUNCT-S',
                                                line_id, chart, lang_code, ht, this_function, [token],
                                                sem_class=resource_entry.sem_class)
                        elif side == 'end' and ((end_position2 == len_s) or s[end_position2].isspace()):
                            return self.rec_tok([token], [start_position], s, offset, 'PUNCT-E',
                                                line_id, chart, lang_code, ht, this_function, [token],
                                                sem_class=resource_entry.sem_class)
                end_position -= 1
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_cap_initial_letter = regex.compile(r".*\p{Lu}\.")
    re_right_context_of_initial_letter = regex.compile(r"\s?(?:\s?\p{Lu}\.)*\s?(?:\p{Lu}\p{Ll}{2}|(?:Mc|O'|O’)\p{Lu})")

    def tokenize_abbreviation_initials(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                                       line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off initials, e.g. J.F.Kennedy -> J. F. Kennedy"""
        this_function = self.tokenize_abbreviation_initials
        # Explore possibility of m3-style regex
        if self.re_cap_initial_letter.match(s):
            for start_position in range(0, len(s)-1):
                char = s[start_position]
                if char.isalpha() and char.isupper() and (s[start_position+1] == '.') \
                   and ((start_position == 0) or not s[start_position - 1].isalpha()):
                    if self.re_right_context_of_initial_letter.match(s[start_position+2:]):
                        token_surf = s[start_position:start_position+2]
                        return self.rec_tok([token_surf], [start_position], s, offset, 'ABBREV-I',
                                            line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_abbrev_acronym_product = regex.compile(r'(.*?)'
                                              r'(?<!\pL\pM*|\d|[-−–]+)'
                                              r'(\p{Lu}+[-−–](?:\d|\p{Lu}\pM*){1,3}(?:s)?)'
                                              r'(?!\pL|\d|[-−–])'
                                              r'(.*)')

    def tokenize_abbreviation_patterns(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                                       line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off pattern-based abbreviations such as F-15B"""
        this_function = self.tokenize_abbreviation_patterns
        if self.lv & self.char_is_dash:
            if m3 := self.re_abbrev_acronym_product.match(s):
                return self.rec_tok_m3(m3, s, offset, 'ABBREV-P', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_dot_pl = regex.compile(r'.*\pL')  # used to filter the following below
    re_abbrev_acronym_periods = regex.compile(r'(.*?)'
                                              r'(?<!\pL\pM*|\d|[-−–.]+)'
                                              r'((?:\pL\pM*\.){2,})'
                                              r'(?!\pL|\d|[.])'
                                              r'(.*)')

    def tokenize_abbreviation_periods(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                                      line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits off pattern-based abbreviations such as B.A.T."""
        this_function = self.tokenize_abbreviation_periods
        if self.re_dot_pl.match(s):
            if m3 := self.re_abbrev_acronym_periods.match(s):
                return self.rec_tok_m3(m3, s, offset, 'ABBREV-PP', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_mt_punct = regex.compile(r'(.*?(?:\pL\pM*\pL\pM*|\d|[!?’]))([-−–]+)(\pL\pM*\pL\pM*|\d)')

    def tokenize_mt_punctuation(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                                line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step currently splits of dashes in certain contexts."""
        this_function = self.tokenize_mt_punctuation
        if m3 := self.re_mt_punct.match(s):
            return self.rec_tok_m3(m3, s, offset, 'DASH', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_integer2 = regex.compile(r'(.*?)(?<!\pL\pM*|\d|[-−–+.])(\d+)((?:\pL|[/]).*)')

    def tokenize_post_punct(self, s: str, chart: Chart, ht: dict, lang_code: Optional[str] = None,
                            line_id: Optional[str] = None, offset: int = 0) -> str:
        """This tokenization step splits leading integers from letters, e.g. 5weeks -> 5 weeks."""
        this_function = self.tokenize_post_punct
        if m3 := self.re_integer2.match(s):
            return self.rec_tok_m3(m3, s, offset, 'NUMBER-2', line_id, chart, lang_code, ht, this_function)
        return self.next_tok(this_function, s, chart, ht, lang_code, line_id, offset)

    re_contains_letter = regex.compile(r'.*\pL')
    re_contains_number = regex.compile(r'.*\pN')
    re_contains_symbol = regex.compile(r'(?V1).*[\p{S}--[-=*+<>^|`]]')
    re_contains_punct = regex.compile(r'(?V1).*[\p{P}||[-=*+<>^|`]]')

    def basic_token_type(self, s: str) -> str:
        """For annotation output"""
        if self.re_contains_letter.match(s):
            return 'WORD-B'
        if self.re_contains_number.match(s):
            return 'NUMBER-B'
        if self.re_contains_symbol.match(s):
            return 'SYMBOL-B'
        if self.re_contains_punct.match(s):
            return 'PUNCT-B'
        else:
            return 'MISC-B'

    def tokenize_main(self, s: str, chart: Chart, _ht: dict, _lang_code: Optional[str] = None,
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
                        new_token = Token(token_surf, str(line_id), self.basic_token_type(token_surf),
                                          ComplexSpan([SimpleSpan(offset+start_index, offset+index,
                                                                  vm=chart.vertex_map)]))
                        chart.register_token(new_token)
                    start_index = None
            elif start_index is None:
                start_index = index
            index += 1
        return util.join_tokens(tokens)

    def tokenize_string(self, s: str, ht: dict, lang_code: Optional[str], line_id: Optional[str],
                        annotation_file: Optional[TextIO]) -> str:
        regex.DEFAULT_VERSION = regex.VERSION1
        self.current_orig_s = s
        self.current_s = s
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
                       lang_code: Optional[str] = None):
        """Apply normalization/cleaning to a file (or STDIN/STDOUT)."""
        line_number = 0
        for line in input_file:
            line_number += 1
            ht['NUMBER-OF-LINES'] = line_number
            if self.first_token_is_line_id_p:
                if m := self.re_id_snt.match(line):
                    line_id, line_id_sep, core_line = m.group(1, 2, 3)
                    output_file.write(line_id + line_id_sep
                                      + self.tokenize_string(core_line, ht, lang_code, line_id, annotation_file)
                                      + "\n")
            else:
                line_id = str(line_number)
                output_file.write(self.tokenize_string(line.rstrip("\n"), ht, lang_code, line_id, annotation_file)
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
    parser.add_argument('-p', '--profile', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=None, metavar='PROFILE-FILENAME', help='(optional output for performance analysis)')
    parser.add_argument('--profile_scope', type=Optional[str], default=None,
                        help='(optional scope for performance analysis)')
    parser.add_argument('--lc', type=Optional[str], default=None,
                        metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('-f', '--first_token_is_line_id', action='count', default=0,
                        help='First token is line ID (and will be exempt from any tokenization)')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='write change log etc. to STDERR')
    parser.add_argument('-c', '--chart', action='count', default=0,
                        help='build annotation chart, even without annotation output')
    parser.add_argument('--mt', action='count', default=0, help='MT-style output with @ added to certain punctuation')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__} last modified: {last_mod_date}')
    args = parser.parse_args(argv)
    lang_code = args.lc
    tok = Tokenizer(lang_code=lang_code)
    tok.chart_p = bool(args.annotation) or bool(args.chart)
    tok.mt_tok_p = bool(args.mt)
    tok.first_token_is_line_id_p = bool(args.first_token_is_line_id)
    tok.profile_scope = args.profile_scope  # e.g. None or 'tokenize_according_to_resource_entries'
    if args.profile or tok.profile_scope:
        tok.profile = cProfile.Profile()
        if tok.profile_scope is None:
            tok.profile.enable()
            tok.profile_active = True

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
        if tok.mt_tok_p:
            log_info += f'  MT tokenization (e.g. @-@): {tok.mt_tok_p}'
        if lang_code:
            log_info += f'  ISO 639-3 language code: {lang_code}'
        log.info(log_info)
    tok.tokenize_lines(ht, input_file=args.input, output_file=args.output, annotation_file=args.annotation,
                       lang_code=lang_code)
    if (log.INFO >= log.root.level) and (tok.n_lines_tokenized >= 1000):
        sys.stderr.write('\n')
    # Log some change stats.
    if args.profile or tok.profile_scope:
        if tok.profile_scope is None:
            tok.profile.disable()
            tok.profile_active = False
        ps = pstats.Stats(tok.profile, stream=args.profile).sort_stats(pstats.SortKey.TIME)
        ps.print_stats()
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
