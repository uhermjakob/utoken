#!/usr/bin/env python

"""Script calls tokenizer(s), reformatters, visualizers for testing.
   Sample call: tok-test.py -i amr-general-corpus.eng.txt
   Sample call: tok-test.py -i set1 -c
   Sample call: tok-test.py -i set2 -c
"""

import argparse
import logging as log
import os
from pathlib import Path
import re
import subprocess
import sys

log.basicConfig(level=log.INFO)


if __name__ == "__main__":
    src_dir = os.path.dirname(os.path.realpath(__file__))
    root_dir = os.path.dirname(src_dir)
    public_test_data_dir = os.path.join(root_dir, 'test', 'data')
    private_test_data_dir = os.path.join(public_test_data_dir, 'private')
    wiki_test_data_dir = os.path.join(public_test_data_dir, 'uroman-large-test-set')
    parser = argparse.ArgumentParser(description='Runs tokenization test(s)')
    parser.add_argument('-i', '--input', type=str, help='(comma-separated input filenames)')
    parser.add_argument('-c', '--compare', action='count', default=0, help='(compare results with other tokenizers)')
    parser.add_argument('-o', '--orig_compare', action='count', default=0, help='(compare original text w/ utoken)')
    parser.add_argument('-d', '--detokenize', action='count', default=0, help='(detokenize results)')
    parser.add_argument('-r', '--detokenize_only', action='count', default=0,
                        help='(detokenize without new tokenization; \'r\' as in reverse)')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    args = parser.parse_args()
    if args.detokenize_only:
        args.detokenize = True
        tokenize_p = False
    else:
        tokenize_p = True
    filenames: list[str] = args.input.split(r'[;,]\s*')
    # filename expansion
    filenames2 = []
    for filename in filenames:
        if filename == 'set1':
            filenames2.extend(['amr-general-corpus.eng.txt',
                               'Bible-ULT-woid.eng.txt',  # if args.compare else 'Bible-ULT.eng.txt'
                               'pmindia_v1.eng.txt',
                               'pmindia_v1.hin.txt',
                               '3S-tweetsdev.orig.eng.txt',
                               '3S-tweetsdev.orig.fas.txt',
                               'challenge.eng.txt',
                               'test1.eng.txt',
                               'test.mal.txt'])
        elif filename == 'set2':
            filenames2.extend(['NewTestament-430randVerses.ecg.txt',
                               'OldTestament-sel.hbo.txt',
                               'Odyssey-Republic-sel.grc.txt',
                               'amh.txt',
                               'ara.txt',
                               'asm.txt',
                               'ben.txt',
                               'bul.txt',
                               'cat.txt',
                               'ces.txt',
                               'cym.txt',
                               'deu.txt',
                               'ell.txt',
                               'eng.txt',
                               'est.txt',
                               'fin.txt',
                               'fra.txt',
                               'guj.txt',
                               'heb.txt',
                               'hun.txt',
                               'hye.txt',
                               'ind.txt',
                               'ita.txt',
                               'kan.txt',
                               'kat.txt',
                               'kor.txt',
                               'lao.txt',
                               'lit.txt',
                               'mal.txt',
                               'mar.txt',
                               'nld.txt',
                               'nor.txt',
                               'ori.txt',
                               'pol.txt',
                               'por.txt',
                               'pus.txt',
                               'que.txt',
                               'ron.txt',
                               'rus.txt',
                               'slk.txt',
                               'som.txt',
                               'spa.txt',
                               'swa.txt',
                               'swe.txt',
                               'tam.txt',
                               'tel.txt',
                               'tgl.txt',
                               'tur.txt',
                               'urd.txt',
                               'vie.txt',
                               'xho.txt',
                               'yor.txt',
                               'zul.txt'])
        elif filename == 'set3':
            filenames2.extend(['Bible-IRV-woid.hin.txt',  # if args.compare else 'Bible-IRV.hin.txt'
                               'saral-dev.kaz.txt',
                               'train46735.tgl.txt',
                               'train99005.uig.txt'])
        elif filename == 'set4':
            filenames2.extend(['ELRC_wikipedia_health.tgl.txt',
                               'OPUS_ParaCrawl_v7_1.tgl.txt'])
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
            elif os.path.isfile(os.path.join(wiki_test_data_dir, filename)):
                test_dir = wiki_test_data_dir
            else:
                sys.stderr.write(f"Can't find file {filename}\n")
                continue

            if m := re.match(r'(?:.*\.)?([a-z]{3})$', core_filename):
                lang_code = m.group(1)
            else:
                lang_code = None
            input_filename = os.path.join(test_dir, filename)
            output_filename = os.path.join(test_dir, 'utoken-out', f'{core_filename}.tok')
            ref_file_s = None
            ref_legend_s = None
            if lang_code and lang_code != 'eng' and re.match(r'.*\.[a-z]{3}\.txt$', input_filename):
                english_filename = re.sub(r'\.[a-z]{3}\.txt$', '.eng.txt', input_filename)
                if os.path.isfile(english_filename):
                    ref_file_s = f' {input_filename} {english_filename}'
                    ref_legend_s = f' {lang_code}.txt eng.txt'
            if ref_file_s is None:
                input_filename_path = Path(input_filename)
                google_dir = input_filename_path.parent / 'google-translations'
                english_filename = google_dir / f'{input_filename_path.stem}.eng.txt'
                if english_filename.is_file():
                    ref_file_s = f' {input_filename} {english_filename}'
                    ref_legend_s = f' {lang_code}.txt google'
            if not ref_file_s:
                ref_file_s = f' {input_filename}'
                ref_legend_s = f' {lang_code}.txt'
            # utokenizer call
            if tokenize_p:
                utokenize_system_call_args = ['python -m utoken.utokenize']
                if lang_code:
                    utokenize_system_call_args.extend(['--lc', lang_code])
                if (core_filename.startswith('Bible') and '-woid.' not in core_filename)\
                        or filename in ('test.mal.txt', 'test1.eng.txt'):
                    utokenize_system_call_args.append('-f')
                json_annotation_filename = os.path.join(test_dir, 'utoken-out', f'{core_filename}.json')
                dcln_annotation_filename = os.path.join(test_dir, 'utoken-out', f'{core_filename}.dcln')
                utokenize_system_call_args.extend(['-i', input_filename])
                utokenize_system_call_args.extend(['-o', output_filename])
                utokenize_system_call_args.extend(['-a', json_annotation_filename])
                utokenize_system_call = ' '.join(utokenize_system_call_args)
                if args.verbose:
                    sys.stderr.write(f"{utokenize_system_call} ...\n")
                else:
                    sys.stderr.write(f"\nutokenize.py {filename} ...\n")
                subprocess.run(utokenize_system_call, shell=True)

                # reformat-annotation-json2dcln.py call
                reformat_system_call_args = \
                    f'reformat-annotation-json2dcln.py < {json_annotation_filename} > {dcln_annotation_filename}'
                sys.stderr.write(f"reformat ...\n")
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
                    old_ulf_tokenizer_filename = os.path.join(public_test_data_dir, 'tok-comparison',
                                                              'old-ulf-tokenizer', f'{core_filename}.tok')
                    if not os.path.isfile(old_ulf_tokenizer_filename):
                        command = f"cat {input_filename}" \
                                  f" | tokenize-english.pl" \
                                  f" > {old_ulf_tokenizer_filename}"
                        sys.stderr.write(f"old ulf-tokenizer {input_filename} ...\n")
                        sys.stderr.write(f"{command} ...\n")
                        subprocess.run(command, shell=True)

                    sys.stderr.write(f"boost ...\n")
                    b1_command = f'boost-tok.py < {output_filename} > {output_filename}.boost'
                    b2_command = f'boost-tok.py < {old_ulf_tokenizer_filename} > {old_ulf_tokenizer_filename}.boost'
                    b3_command = f'boost-tok.py < {sacremoses_filename} > {sacremoses_filename}.boost'
                    subprocess.run(b1_command, shell=True)
                    subprocess.run(b2_command, shell=True)
                    subprocess.run(b3_command, shell=True)
                    if args.orig_compare:
                        b4_command = f'boost-tok.py < {input_filename} > {input_filename}.boost'
                        subprocess.run(b4_command, shell=True)
                    sys.stderr.write(f"color ...\n")
                    sacremoses_viz_filename = os.path.join(public_test_data_dir, 'viz',
                                                           f'{core_filename}.sacrem-utoken-diff.html')
                    command = f'color-mt-diffs.pl {sacremoses_filename} {output_filename}{ref_file_s}' \
                              f' -b {sacremoses_filename}.boost {output_filename}.boost' \
                              f' -l sacrem utoken{ref_legend_s}' \
                              f' -o {sacremoses_viz_filename}'
                    # sys.stderr.write(f"{command} ...\n")
                    if args.verbose:
                        print(command)
                    subprocess.run(command, shell=True)
                    old_ulf_tokenizer_viz_filename = os.path.join(public_test_data_dir, 'viz',
                                                                  f'{core_filename}.old-u-t-utoken-diff.html')
                    command = f'color-mt-diffs.pl {old_ulf_tokenizer_filename} {output_filename}{ref_file_s}' \
                              f' -b {old_ulf_tokenizer_filename}.boost {output_filename}.boost' \
                              f' -l old-u-t utoken{ref_legend_s}' \
                              f' -o {old_ulf_tokenizer_viz_filename}'
                    # sys.stderr.write(f"{command} ...\n")
                    if args.verbose:
                        print(command)
                    subprocess.run(command, shell=True)
                    if args.orig_compare:
                        orig_text_viz_filename = os.path.join(public_test_data_dir, 'viz',
                                                              f'{core_filename}.orig-text-utoken-diff.html')
                        ref_file_s2 = re.sub(f' {input_filename}', '', ref_file_s)
                        ref_legend_s2 = re.sub(f' {lang_code}.txt', '', ref_legend_s)
                        command = f'color-mt-diffs.pl {input_filename} {output_filename}{ref_file_s2}' \
                                  f' -b {input_filename}.boost {output_filename}.boost' \
                                  f' -l {lang_code}.txt utoken{ref_legend_s2}' \
                                  f' -o {orig_text_viz_filename}' \
                                  f' -a'
                        # sys.stderr.write(f"{command} ...\n")
                        if args.verbose:
                            print(command)
                        subprocess.run(command, shell=True)
            if args.detokenize:
                if Path(output_filename).is_file():
                    if tokenize_p:
                        sys.stderr.write(f"detok ...\n")
                    else:
                        sys.stderr.write(f"\ndetok {output_filename} ...\n")
                    detok_filename = re.sub(r'\.tok$', '.detok', output_filename)
                    command = f'python -m utoken.detokenize -i {output_filename} -o {detok_filename}'
                    if lang_code:
                        command += f' --lc {lang_code}'
                    # sys.stderr.write(f"{command} ...\n")
                    subprocess.run(command, shell=True)
                    if args.compare:
                        detok_viz_filename = os.path.join(public_test_data_dir, 'viz',
                                                          f'{core_filename}.orig-text-detok-diff.html')
                        b5_command = f'boost-detok.py < {input_filename} > {input_filename}.boost'
                        subprocess.run(b5_command, shell=True)
                        b6_command = f'boost-detok.py < {detok_filename} > {detok_filename}.boost'
                        subprocess.run(b6_command, shell=True)
                        command = f'color-mt-diffs.pl {input_filename} {detok_filename}{ref_file_s}' \
                                  f' -b {input_filename}.boost {detok_filename}.boost' \
                                  f' -l {lang_code}.txt detok{ref_legend_s}' \
                                  f' -o {detok_viz_filename}'
                        # sys.stderr.write(f"{command} ...\n")
                        if args.verbose:
                            print(command)
                        subprocess.run(command, shell=True)
                else:
                    sys.stderr.write(f"detok warning: {output_filename} missing\n")
        else:
            sys.stderr.write(f"WARNING: Ignoring filename {filename}, because it does not end in '.txt'\n")
            continue
