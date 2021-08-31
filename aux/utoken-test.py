#!/usr/bin/env python

"""Script calls tokenizer(s), reformatters, visualizers for testing.
   Sample call: utoken-test.py -i amr-general-corpus.eng.txt
   Sample call: utoken-test.py -i set1 -cv
   Sample call: utoken-test.py -i set2 -cv
"""

import argparse
import os
import re
import subprocess
import sys


if __name__ == "__main__":
    src_dir = os.path.dirname(os.path.realpath(__file__))
    root_dir = os.path.dirname(src_dir)
    public_test_data_dir = os.path.join(root_dir, 'test', 'data')
    private_test_data_dir = os.path.join(public_test_data_dir, 'private')
    parser = argparse.ArgumentParser(description='Runs tokenization test(s)')
    parser.add_argument('-i', '--input', type=str, help='(comma-separated input filenames)')
    parser.add_argument('-c', '--compare', action='count', default=0, help='(compare results with other tokenizers)')
    parser.add_argument('-v', '--visualize', action='count', default=0, help='(visualize results)')
    args = parser.parse_args()
    filenames: list[str] = args.input.split(r'[;,]\s*')
    # filename expansion
    filenames2 = []
    for filename in filenames:
        if filename == 'set1':
            filenames2.extend(['amr-general-corpus.eng.txt',
                               'Bible-ULT-woid.eng.txt' if args.compare else 'Bible-ULT.eng.txt',
                               'pmindia_v1.eng.txt',
                               'pmindia_v1.hin.txt',
                               'test1.eng.txt',
                               'test.mal.txt'])
        elif filename == 'set2':
            filenames2.extend(['Bible-IRV-woid.hin.txt' if args.compare else 'Bible-IRV.hin.txt',
                               'saral-dev.kaz.txt',
                               'train99005.uig.txt'])
        else:
            filenames2.append(filename)
    filenames = filenames2
    for filename in filenames:
        if m := re.match(r'(.*)\.txt$', filename):
            core_filename: str = m.group(1)
            if os.path.isfile(os.path.join(public_test_data_dir, filename)):
                test_dir = public_test_data_dir
            elif os.path.isfile(os.path.join(private_test_data_dir, filename)):
                test_dir = private_test_data_dir
            else:
                sys.stderr.write(f"Can't find file {filename}\n")
                continue

            # utokenizer.py call
            utokenize_system_call_args = ['utokenize.py']
            if m := re.match(r'.*\.([a-z]{3})$', core_filename):
                lang_code = m.group(1)
            else:
                lang_code = None
            if lang_code:
                utokenize_system_call_args.extend(['--lc', lang_code])
            if args.compare:
                utokenize_system_call_args.append('--mt')
                mt_clause = 'mt.'
            else:
                mt_clause = ''
            if (core_filename.startswith('Bible') and '-woid.' not in core_filename)\
                    or filename in ('test.mal.txt', 'test1.eng.txt'):
                utokenize_system_call_args.append('-f')
            input_filename = os.path.join(test_dir, filename)
            output_filename = os.path.join(test_dir, 'utoken-out', f'{core_filename}.{mt_clause}tok')
            json_annotation_filename = os.path.join(test_dir, 'utoken-out', f'{core_filename}.{mt_clause}json')
            dcln_annotation_filename = os.path.join(test_dir, 'utoken-out', f'{core_filename}.{mt_clause}dcln')
            utokenize_system_call_args.extend(['-i', input_filename])
            utokenize_system_call_args.extend(['-o', output_filename])
            utokenize_system_call_args.extend(['-a', json_annotation_filename])
            sys.stderr.write(f"utokenize.py {filename} ...\n")
            # sys.stderr.write(f"{' '.join(utokenize_system_call_args)} ...\n")
            subprocess.run(utokenize_system_call_args)

            # reformat-annotation-json2dcln.py call
            reformat_system_call_args = \
                f'reformat-annotation-json2dcln.py < {json_annotation_filename} > {dcln_annotation_filename}'
            sys.stderr.write(f"reformat {json_annotation_filename} ...\n")
            # sys.stderr.write(f'{reformat_system_call_args} ...\n')
            subprocess.run(reformat_system_call_args, shell=True)

            if args.compare:
                # build sacremoses tokenization, if it does not already exist
                sacremoses_filename = os.path.join(public_test_data_dir, 'tok-comparison', 'sacremoses',
                                                   f'{core_filename}.tok')
                if not os.path.isfile(sacremoses_filename):
                    command = f"cat {input_filename}" \
                              f" | sacremoses -l en tokenize -a -x -p ':web:'" \
                              f" > {sacremoses_filename}"
                    sys.stderr.write(f"sacremoses {input_filename} ...\n")
                    sys.stderr.write(f"{command} ...\n")
                    subprocess.run(command, shell=True)

                # build old ulf-tokenizer tokenization, if it does not already exist
                old_ulf_tokenizer_filename = os.path.join(public_test_data_dir, 'tok-comparison', 'old-ulf-tokenizer',
                                                          f'{core_filename}.tok')
                if not os.path.isfile(old_ulf_tokenizer_filename):
                    command = f"cat {input_filename}" \
                              f" | tokenize-english.pl" \
                              f" > {old_ulf_tokenizer_filename}"
                    sys.stderr.write(f"old ulf-tokenizer {input_filename} ...\n")
                    sys.stderr.write(f"{command} ...\n")
                    subprocess.run(command, shell=True)

                ref_clause = None
                if lang_code and lang_code != 'eng':
                    english_filename = re.sub(r'\.[a-z]{3}\.txt$', '.eng.txt', input_filename)
                    sys.stderr.write(f"**** {input_filename} to {english_filename}\n")
                    if os.path.isfile(english_filename):
                        ref_clause = f' -ref {input_filename} -ref2 {english_filename}' \
                                     f' -ref-legends {lang_code}.txt eng.txt'
                if not ref_clause:
                    ref_clause = f' -ref {input_filename} -ref-legend {lang_code}.txt'
                sacremoses_viz_filename = os.path.join(public_test_data_dir, 'viz',
                                                       f'{core_filename}.sacrem-utoken-diff.html')
                command = f'color-mt-diffs.pl {sacremoses_filename} {output_filename}' \
                          f' -legends sacrem utoken{ref_clause}' \
                          f' -out {sacremoses_viz_filename}'
                sys.stderr.write(f"{command} ...\n")
                sys.stderr.write(f"color-mt-diffs.pl sacremoses {input_filename}"
                                 f" -out {sacremoses_viz_filename} ...\n")
                subprocess.run(command, shell=True)
                old_ulf_tokenizer_viz_filename = os.path.join(public_test_data_dir, 'viz',
                                                              f'{core_filename}.old-u-t-utoken-diff.html')
                command = f'color-mt-diffs.pl {old_ulf_tokenizer_filename} {output_filename}' \
                          f' -legends old-u-t utoken{ref_clause}' \
                          f' -out {old_ulf_tokenizer_viz_filename}'
                sys.stderr.write(f"{command} ...\n")
                sys.stderr.write(f"color-mt-diffs.pl old ulf-tokenizer {input_filename}"
                                 f" -out {old_ulf_tokenizer_viz_filename} ...\n")
                subprocess.run(command, shell=True)
        else:
            sys.stderr.write(f"Ignoring filename {filename}, because it does not end in '.txt'\n")
            continue
