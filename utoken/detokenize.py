#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Written by Ulf Hermjakob, USC/ISI
This script is a draft of a detokenizer.
When using STDIN and/or STDOUT, if might be necessary, particularly for older versions of Python, to do
'export PYTHONIOENCODING=UTF-8' before calling this Python script to ensure UTF-8 encoding.
"""
# -*- encoding: utf-8 -*-
import argparse
import datetime
import logging as log
import os
import re
import sys
from typing import Optional, TextIO
import util
from __init__ import __version__, last_mod_date

log.basicConfig(level=log.INFO)


class Detokenizer:
    def __init__(self, lang_code: Optional[str] = None, data_dir: Optional[str] = None):
        self.number_of_lines = 0
        self.lang_code: Optional[str] = lang_code
        self.first_token_is_line_id_p = False
        if data_dir is None:
            data_dir = self.default_data_dir()
        self.detok_dict = util.DetokenizationDict()
        self.detok_dict.load_resource(os.path.join(data_dir, f'detok-resource.txt'))
        attach_tag = self.detok_dict.attach_tag
        xml_tag_re_s = r'\s*(' + attach_tag + r'?</?[a-zA-Z][^<>]*>' + attach_tag + r'?)(\s.*|)$'
        # log.info(f'xml_tag_re_s {xml_tag_re_s}')
        self.xml_tag_re = re.compile(xml_tag_re_s)
        self.non_whitespace_re = re.compile(r'\s*(\S+)(.*)$')

    @staticmethod
    def default_data_dir() -> str:
        src_dir = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(src_dir, "../data")

    def tokens_in_tokenized_string(self, s: str):
        tokens = []
        while m2 := self.xml_tag_re.match(s) or self.non_whitespace_re.match(s):
            tokens.append(m2.group(1))
            s = m2.group(2)
        return tokens

    @staticmethod
    def detokenization_entry_fulfills_conditions(detokenization_entry: util.DetokenizationEntry,
                                                 _token: str, left_context: str, right_context: str,
                                                 lang_code: Optional[str], group: Optional[bool] = False) -> bool:
        """This methods checks whether a detokenization-entry satisfies any context conditions."""
        lang_codes = detokenization_entry.lang_codes
        return ((not lang_code or not lang_codes or (lang_code in lang_codes))
                and (not group or detokenization_entry.group)
                and (not (re_l := detokenization_entry.left_context) or re_l.match(left_context))
                and (not (re_l_n := detokenization_entry.left_context_not) or not re_l_n.match(left_context))
                and (not (re_r := detokenization_entry.right_context) or re_r.match(right_context))
                and (not (re_r_n := detokenization_entry.right_context_not) or not re_r_n.match(right_context)))

    def token_auto_attaches_to_left(self, s: str, left_context: str, right_context: str,
                                    lang_code: Optional[str]) -> bool:
        for detokenization_entry in self.detok_dict.auto_attach_left.get(s, []):
            if self.detokenization_entry_fulfills_conditions(detokenization_entry, s, left_context, right_context,
                                                             lang_code):
                return True
        s0 = s[0]
        if all(c == s0 for c in s):
            for detokenization_entry in self.detok_dict.auto_attach_left.get(s0, []):
                if self.detokenization_entry_fulfills_conditions(detokenization_entry, s, left_context, right_context,
                                                                 lang_code, True):
                    return True
        return False

    def token_auto_attaches_to_right(self, s: str, left_context: str, right_context: str,
                                     lang_code: Optional[str]) -> bool:
        for detokenization_entry in self.detok_dict.auto_attach_right.get(s, []):
            if self.detokenization_entry_fulfills_conditions(detokenization_entry, s, left_context, right_context,
                                                             lang_code):
                return True
        s0 = s[0]
        if all(c == s0 for c in s):
            for detokenization_entry in self.detok_dict.auto_attach_right.get(s0, []):
                if self.detokenization_entry_fulfills_conditions(detokenization_entry, s, left_context, right_context,
                                                                 lang_code, True):
                    return True
        return False

    def detokenize_string(self, s: str, lang_code: Optional[str], _line_id: Optional[str]) -> str:
        markup_attach_re = self.detok_dict.markup_attach_re
        attach_tag = self.detok_dict.attach_tag
        s = s.strip()
        # log.info(f's: {s}')
        if s == '':
            return ''
        if '<' in s:
            tokens = self.tokens_in_tokenized_string(s)
        else:
            tokens = re.split(r'\s+', s)
        # log.info(f"tokens: {' :: '.join(tokens)} ({len(tokens)})")
        eliminate_space_based_on_previous_token = True  # no space before first token
        result = ''
        prev_token = ''
        token = tokens[0]
        next_tokens = tokens[1:]
        next_tokens.append('')
        for next_token in next_tokens:
            token_is_marked_up = markup_attach_re.match(token)
            # Add space between tokens with certain exceptions.
            if ((not eliminate_space_based_on_previous_token)
                    and (not (token_is_marked_up and token.startswith(attach_tag)))
                    and (not self.token_auto_attaches_to_left(token, prev_token, next_token, lang_code))):
                result += ' '
            # Add the token, stripped of any attach_tag
            result += token.strip(attach_tag) if token_is_marked_up else token
            # For the next round, see if space can be eliminated based on this round.
            eliminate_space_based_on_previous_token = \
                ((token_is_marked_up and token.endswith(attach_tag))
                    or self.token_auto_attaches_to_right(token, prev_token, next_token, lang_code))
            # log.info(f'Token-{i}: {token} is markup-punct')
            prev_token, token = token, next_token
        return result

    re_id_snt = re.compile(r'(\S+)(\s+)(\S|\S.*\S)\s*$')

    def detokenize_lines(self, input_file: TextIO, output_file: TextIO, lang_code: Optional[str] = None):
        """Apply normalization/cleaning to a file (or STDIN/STDOUT)."""
        line_number = 0
        for line in input_file:
            line_number += 1
            if self.first_token_is_line_id_p:
                if m := self.re_id_snt.match(line):
                    line_id, line_id_sep, core_line = m.group(1, 2, 3)
                    output_file.write(line_id + line_id_sep
                                      + self.detokenize_string(core_line, lang_code, line_id)
                                      + "\n")
            else:
                line_id = str(line_number)
                output_file.write(self.detokenize_string(line.rstrip("\n"), lang_code, line_id)
                                  + "\n")
        self.number_of_lines = line_number


def main():
    """Wrapper around detokenization that takes care of argument parsing and prints change stats to STDERR."""
    # parse arguments
    parser = argparse.ArgumentParser(description='Detokenizes a given text')
    parser.add_argument('-i', '--input', type=argparse.FileType('r', encoding='utf-8', errors='surrogateescape'),
                        default=sys.stdin, metavar='INPUT-FILENAME', help='(default: STDIN)')
    parser.add_argument('-o', '--output', type=argparse.FileType('w', encoding='utf-8', errors='ignore'),
                        default=sys.stdout, metavar='OUTPUT-FILENAME', help='(default: STDOUT)')
    parser.add_argument('-d', '--data_directory', type=str, default=None, help='(default: standard data directory)')
    parser.add_argument('--lc', type=str, default=None,
                        metavar='LANGUAGE-CODE', help="ISO 639-3, e.g. 'fas' for Persian")
    parser.add_argument('-f', '--first_token_is_line_id', action='count', default=0,
                        help='First token is line ID (and will be exempt from any tokenization)')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='write change log etc. to STDERR')
    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {__version__} last modified: {last_mod_date}')
    args = parser.parse_args()
    lang_code = args.lc
    data_dir = args.data_directory
    detok = Detokenizer(lang_code=lang_code, data_dir=data_dir)
    detok.first_token_is_line_id_p = bool(args.first_token_is_line_id)

    # Open any input or output files. Make sure utf-8 encoding is properly set (in older Python3 versions).
    if args.input is sys.stdin and not re.search('utf-8', sys.stdin.encoding, re.IGNORECASE):
        log.error(f"Bad STDIN encoding '{sys.stdin.encoding}' as opposed to 'utf-8'. \
                    Suggestion: 'export PYTHONIOENCODING=UTF-8' or use '--input FILENAME' option")
    if args.output is sys.stdout and not re.search('utf-8', sys.stdout.encoding, re.IGNORECASE):
        log.error(f"Error: Bad STDIN/STDOUT encoding '{sys.stdout.encoding}' as opposed to 'utf-8'. \
                    Suggestion: 'export PYTHONIOENCODING=UTF-8' or use use '--output FILENAME' option")

    start_time = datetime.datetime.now()
    if args.verbose:
        log_info = f'Start: {start_time}  Script: tokenize.py'
        if args.input is not sys.stdin:
            log_info += f'  Input: {args.input.name}'
        if args.output is not sys.stdout:
            log_info += f'  Output: {args.output.name}'
        if lang_code:
            log_info += f'  ISO 639-3 language code: {lang_code}'
        log.info(log_info)
    detok.detokenize_lines(input_file=args.input, output_file=args.output, lang_code=lang_code)
    end_time = datetime.datetime.now()
    elapsed_time = end_time - start_time
    number_of_lines = detok.number_of_lines
    lines = 'line' if number_of_lines == 1 else 'lines'
    if args.verbose:
        log.info(f'End: {end_time}  Elapsed time: {elapsed_time}  Processed {str(number_of_lines)} {lines}')
    elif elapsed_time.seconds >= 10:
        log.info(f'Elapsed time: {elapsed_time.seconds} seconds for {number_of_lines:,} {lines}')


if __name__ == "__main__":
    main()
