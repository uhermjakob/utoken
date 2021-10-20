#!/usr/bin/env python

"""Script checks tokenization for changes.
   Sample call: tok-diff.py <filename.tok> ... <dir> ...
   Sample call: tok-diff.py      # will check default directories
   Sample call: tok-diff.py -u   # will update reference tokenizations (detokenizations with -d)
   Sample call: tok-diff.py -d   # detokenization instead of tokenization
   Sample call: tok-diff.py -v0.1.1  # will save as ...v0.1.1 (unless it already exists)
"""

from shutil import copyfile
import difflib
import logging as log
from pathlib import Path
import os
import re
import subprocess
import sys
from typing import List

log.basicConfig(level=log.INFO)


class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def read_sentence_block_from_dcln_file(file: Path) -> List[str]:
    sentence_block_list = []
    block = ''
    with open(file) as f:
        for line in f:
            if line.startswith('::line'):
                if block != '':
                    sentence_block_list.append(block)
                block = line
            else:
                block += line
        if block != '':
            sentence_block_list.append(block)
    return sentence_block_list


if __name__ == "__main__":
    root_test_data_dir = Path(__file__).parent.parent / "test" / "data"
    public_test_data_dir = root_test_data_dir
    private_test_data_dir = public_test_data_dir / 'private'
    wiki_test_data_dir = public_test_data_dir / 'uroman-large-test-set'
    # log.info(f'root_test_data_dir {root_test_data_dir}')
    cwd = Path.cwd()
    tok_filenames = []
    dcln_filenames = []
    detok_filenames = []
    directories = []
    update_p = False
    detok_p = False
    new_version = None
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.is_file():
            if re.match(r'.*\.tok$', arg):
                tok_filenames.append(path)
            elif re.match(r'.*\.detok$', arg):
                detok_filenames.append(path)
            elif re.match(r'.*\.dcln$', arg):
                dcln_filenames.append(path)
            else:
                log.warning(f'Invalid arg {arg} Filename should be *.tok or *.dcln')
        elif path.is_dir():
            directories.append(path)
        elif re.match(r'-+u', arg):
            update_p = True
        elif re.match(r'-+[dr]', arg):  # d as in detokenize, r as in reverse
            detok_p = True
        elif re.match(r'-*v\d+(\.\d+)(\.\d+)$', arg):
            new_version = arg.lstrip('-')
        else:
            log.warning(f'Invalid arg {arg}')
    if not tok_filenames and not dcln_filenames and not detok_filenames and not directories:
        directories = [public_test_data_dir / 'utoken-out',
                       private_test_data_dir / 'utoken-out',
                       wiki_test_data_dir / 'utoken-out']
    # if tok_filenames:
    #     log.info(f'filenames: {tok_filenames}')
    # if dcln_filenames:
    #     log.info(f'filenames: {dcln_filenames}')
    n_updates = 0
    for directory in directories:
        if detok_p:
            filenames = list(directory.glob('*.detok'))
        else:
            filenames = list(directory.glob('*.tok')) + list(directory.glob('*.dcln'))
        filenames.sort()
        for filename in filenames:
            save_filename = Path(str(filename) + '~save')
            if save_filename.is_file():
                save_filename2 = Path(str(filename) + '~save2')
                rel_filename = Path(os.path.relpath(filename, cwd))
                n_lines = 0
                n_diff_lines = 0
                if str(filename).endswith('tok'):  # .tok or .detok
                    with open(save_filename) as f1, open(filename) as f2:
                        for line1, line2 in zip(f1, f2):
                            n_lines += 1
                            if line1 != line2:
                                n_diff_lines += 1
                elif str(filename).endswith('.dcln'):
                    sentence_block_list1 = read_sentence_block_from_dcln_file(save_filename)
                    sentence_block_list2 = read_sentence_block_from_dcln_file(filename)
                    for sentence_block1, sentence_block2 in zip(sentence_block_list1, sentence_block_list2):
                        n_lines += 1
                        if sentence_block1 != sentence_block2:
                            n_diff_lines += 1
                if n_diff_lines:
                    if update_p:
                        print(f"{Bcolors.WARNING}{rel_filename} {n_diff_lines}/{n_lines} lines differ{Bcolors.ENDC}")
                        copyfile(save_filename, save_filename2)
                        copyfile(filename, save_filename)
                        n_updates += 1
                    else:
                        print(f'{Bcolors.FAIL}{rel_filename} {n_diff_lines}/{n_lines} lines differ{Bcolors.ENDC}')
                elif new_version:
                    pass
                else:
                    print(f'{Bcolors.OKGREEN}{rel_filename} {n_diff_lines}/{n_lines} lines differ{Bcolors.ENDC}')
                if new_version:
                    version_filename = Path(str(filename) + f'.{new_version}')
                    if version_filename.is_file():
                        print(f'{Bcolors.FAIL}Warning: {version_filename} already exists. Not saved.{Bcolors.ENDC}')
                    else:
                        copyfile(filename, version_filename)
                        print(f'{Bcolors.OKGREEN}Saved as {version_filename}{Bcolors.ENDC}')
    if n_updates:
        log.info(f"Updated {n_updates} file{'' if n_updates == 1 else 's'}")
    for filename in dcln_filenames:
        save_filename = Path(str(filename) + '~save')
        if filename.is_file() and save_filename.is_file():
            n_lines = 0
            n_diff_lines = 0
            sentence_block_list1 = read_sentence_block_from_dcln_file(save_filename)
            sentence_block_list2 = read_sentence_block_from_dcln_file(filename)
            for sentence_block1, sentence_block2 in zip(sentence_block_list1, sentence_block_list2):
                n_lines += 1
                if sentence_block1 != sentence_block2:
                    n_diff_lines += 1
                    diff = difflib.ndiff(sentence_block1.splitlines(), sentence_block2.splitlines())
                    buffer_lines = []
                    n_lines_in_block = 0
                    n_lines_to_last_diff = None
                    for d in diff:
                        n_lines_in_block += 1
                        if d.startswith('-') or d.startswith('+'):
                            # print last 3 of any previous buffer lines (unprinted matching lines)
                            for buffer_line in buffer_lines[-3:]:
                                print(buffer_line.rstrip())
                            buffer_lines = []
                            if d.startswith('-'):
                                print(f'{Bcolors.FAIL}{d.rstrip()}{Bcolors.ENDC}')
                            else:
                                print(f'{Bcolors.OKGREEN}{d.rstrip()}{Bcolors.ENDC}')
                            n_lines_to_last_diff = 0
                        elif d.startswith('?'):
                            continue
                        # always print ::line info for differing blocks
                        elif n_lines_in_block == 1:
                            print(d.rstrip())
                        # print up to 3 lines after diff
                        elif n_lines_to_last_diff is not None:
                            print(d.rstrip())
                            n_lines_to_last_diff += 1
                            if n_lines_to_last_diff >= 3:
                                n_lines_to_last_diff = None
                        else:
                            buffer_lines.append(d.rstrip())
            log.info(f'{n_diff_lines}/{n_lines} lines differed.')
    if len(tok_filenames) == 1:
        filename = tok_filenames[0]
    elif len(detok_filenames) == 1:
        filename = detok_filenames[0]
    else:
        filename = None
    if filename:
        save_filename = Path(str(filename) + '~save')
        if filename.is_file() and save_filename.is_file():
            command = f'color-mt-diffs.pl {save_filename} {filename}'
            legend = ' -l old new'
            file_stem = filename.stem
            txt_filename = filename.parent.parent / (file_stem + '.txt')
            if txt_filename.is_file():
                command += f' {txt_filename}'
                legend += ' txt'
            eng_filename = None
            eng_legend = 'eng'
            if re.match(r'.*\.[a-z]{3}$', file_stem):
                eng_filename_name = re.sub(r'\.[a-z]{3}$', '.eng.txt', file_stem)
                if eng_filename_name != filename.name:
                    eng_filename_cand = filename.parent.parent / eng_filename_name
                    if eng_filename_cand.is_file():
                        eng_filename = eng_filename_cand
            if not eng_filename:
                google_dir = filename.parent.parent / 'google-translations'
                eng_filename_cand = google_dir / f'{file_stem}.eng.txt'
                if eng_filename_cand.is_file():
                    eng_filename = eng_filename_cand
                    eng_legend = 'google'
            if eng_filename:
                command += f' {eng_filename}'
                legend += ' ' + eng_legend
            command += legend
            command += ' -o /Users/ulf/utoken/test/data/viz/out.html'
            # log.info(f'command: {command}')
            subprocess.run(command, shell=True)
