#!/usr/bin/env python

"""Script analyzes a tokenization annotation for a range of suspicious tokens."""

from collections import defaultdict
import functools
import json
import logging as log
import regex
import sys
from typing import TextIO


log.basicConfig(level=log.INFO)


class TokenizationAnomaly:
    def __init__(self, s: str):
        self.s = s
        self.count = 0
        self.locations = []

    @staticmethod
    def register_anomaly(surf: str, loc: str, anomaly_dict: dict) -> None:
        anomaly_entry: TokenizationAnomaly = anomaly_dict.get(surf, None)
        if not anomaly_entry:
            anomaly_entry = TokenizationAnomaly(surf)
            anomaly_dict[surf] = anomaly_entry
        anomaly_entry.count += 1
        anomaly_entry.locations.append(loc)


class TokenizationAnalysis:
    def __init__(self):
        self.token_count = defaultdict(int)
        self.case_anomalies = {}
        self.letter_punct_anomalies = {}
        self.letters_wo_period_anomalies = {}
        self.pre_number_anomalies = {}
        self.post_number_anomalies = {}

    re_lower_upper = regex.compile(r'.*\p{Ll}\pM*\p{Lu}', flags=regex.V1)
    re_contains_letter = regex.compile(r'.*\pL', flags=regex.V1)
    re_ends_w_letter = regex.compile(r'.*\pL\pM*$', flags=regex.V1)
    re_contains_punct = regex.compile(r'.*\pP', flags=regex.V1)
    re_span_components = regex.compile(r'(\d+)-(\d+)$')

    def analyze_tokenization(self, input_file: TextIO) -> None:
        annotations = json.load(input_file)
        n_annotations = 0
        snt_id = None
        snt = None
        for annotation in annotations:
            n_annotations += 1
            if id_cand := annotation.get('ID', None):
                snt_id = id_cand
            if snt_cand := annotation.get('snt', None):
                snt = snt_cand
            if chart_elements := annotation.get('chart', []):
                left_surf1, left_surf2 = '', ''
                for chart_element in chart_elements:
                    span = chart_element.get('span', None)
                    if m2 := self.re_span_components.match(span):
                        left_context = ' ' + snt[0:int(m2.group(1))]
                        right_context = snt[int(m2.group(2)):] + ' '
                    else:
                        left_context, right_context = ' ', ' '
                    surf = chart_element.get('surf', None)
                    self.token_count[surf] += 1
                    tokenization_type = chart_element.get('type', None)
                    # sem_class = chart_element.get('sem-class', None)
                    if tokenization_type not in ('BBCode', 'EMAIL-ADDRESS', 'HANDLE', 'URL', 'XML') \
                            and tokenization_type not in ('ABBREV', 'ABBREV-P', 'ABBREV-PP',
                                                          'DECONTRACTION', 'DECONTRACTION-L', 'DECONTRACTION-R',
                                                          'HASHTAG', 'LEXICAL', 'REPAIR'):
                        if self.re_lower_upper.match(surf) \
                                and not regex.match(r'Ma?c\p{Lu}\p{Ll}+$', surf):
                            TokenizationAnomaly.register_anomaly(surf, snt_id, self.case_anomalies)
                        if self.re_contains_letter.match(surf) and self.re_contains_punct.match(surf) \
                                and not regex.match(r"(?:\p{Lu}\.|'n'|@?&quot;@?)$", surf):
                            TokenizationAnomaly.register_anomaly(surf, snt_id, self.letter_punct_anomalies)
                        if len(surf) <= 4 and self.re_ends_w_letter.match(surf) and right_context.startswith('.'):
                            right_context_token = regex.sub(r'\s.*$', '', right_context)
                            TokenizationAnomaly.register_anomaly(surf + ' ' + right_context_token,
                                                                 snt_id, self.letters_wo_period_anomalies)
                        if tokenization_type in ('NUMBER', 'NUMBER-2', 'NUMBER-B'):
                            if not regex.match(r'.*(?:[ (\[$£]| ["”]|\bRMB|\bRs\.|<.*">|No\.)$', left_context) \
                                    and not (regex.match(r'\d+$', left_surf2)
                                             and regex.match(r'@?[-:/]@?$', left_surf1)):
                                left_context_token = regex.sub(r'.*\s', '', left_context)
                                token_pattern = regex.sub(r'[0-9]', 'd', surf)
                                TokenizationAnomaly.register_anomaly(left_context_token + ' ' + token_pattern,
                                                                     snt_id, self.pre_number_anomalies)
                            if not regex.match(r"(?:(?:%|\+|st|nd|rd|th|[kKM])?[\"”]?[_.,;!?:\)\]]?[\"”]? |[-:/]\d|'s|[)\]]|<\/)",
                                               right_context):
                                right_context_token = regex.sub(r'\s.*$', '', right_context)
                                token_pattern = regex.sub(r'[0-9]', 'd', surf)
                                TokenizationAnomaly.register_anomaly(token_pattern + ' ' + right_context_token,
                                                                     snt_id, self.post_number_anomalies)
                    left_surf2, left_surf1 = left_surf1, surf
        log.info(f'Processed {n_annotations} annotations.')

    @staticmethod
    def reg_plural(s: str, n: int) -> str:
        """Form regular English plural form, e.g. 'position' -> 'positions' 'bush' -> 'bushes'"""
        if n == 1:
            return s
        elif regex.match('(?:[sx]|[sc]h)$', s):
            return s + 'es'
        else:
            return s + 's'

    @staticmethod
    def compare_anomalies(a1: TokenizationAnomaly, a2: TokenizationAnomaly):
        if diff := a2.count - a1.count:
            return diff
        lc_s1 = a1.s.lower()
        lc_s2 = a2.s.lower()
        if lc_s1 > lc_s2:
            return 1
        elif lc_s2 > lc_s1:
            return -1
        else:
            return 0

    def print_tokenization_analysis(self) -> None:
        dicts = (self.case_anomalies, self.letter_punct_anomalies, self.letters_wo_period_anomalies,
                 self.pre_number_anomalies, self.post_number_anomalies)
        legends = ('lower/upper case', 'letter+punct', 'letter w/o period', 'pre-number', 'post-number')
        for i in range(len(dicts)):
            print(legends[i])
            anomalies = list(dicts[i].values())
            anomalies.sort(key=functools.cmp_to_key(self.compare_anomalies))
            for anomaly in anomalies:
                count = anomaly.count
                s = anomaly.s
                token_count_clause = ''
                if dicts[i] == self.letters_wo_period_anomalies:
                    token = regex.sub(r'\s.*$', '', s)
                    token_count = self.token_count.get(token, 0)
                    if count < 0.4 * token_count:
                        # log.info(f'  skipping letters_wo_period_anomalies for {s} ({count}/{token_count})')
                        continue
                    else:
                        token_count_clause = f' #{token_count}'
                instance_s = self.reg_plural('instance', count)
                locations = anomaly.locations
                location_s = ', '.join(locations)
                n_locations = len(locations)
                line_s = self.reg_plural('line', n_locations)
                print(f'   {s} ({count} {instance_s}; {line_s} {location_s}) {token_count_clause}')


def main():
    ta = TokenizationAnalysis()
    ta.analyze_tokenization(sys.stdin)
    ta.print_tokenization_analysis()


if __name__ == "__main__":
    main()
