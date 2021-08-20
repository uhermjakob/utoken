#!/usr/bin/env python

"""Script reformats tokenization annotation from json to double-colon format (for human consumption)"""

import json
import sys


if __name__ == "__main__":
    if True:
        annotations = json.load(sys.stdin)
        annotation_number = 0
        for annotation in annotations:
            annotation_number += 1
            id = annotation.get('ID', None)
            snt = annotation.get('snt', None)
            print(f'::line {id} ::s {snt}')
            chart_elements = annotation.get('chart', [])
            for chart_element in chart_elements:
                out_clauses = []
                # sys.stderr.write(f'annotation: {annotation}   (type: {type(annotation)})\n')
                for slot in ('span', 'type', 'sem-class', 'surf'):
                    value = chart_element.get(slot, None)
                    if value is not None:
                        out_clauses.append(f'::{slot} {value}')
                print(' '.join(out_clauses))
