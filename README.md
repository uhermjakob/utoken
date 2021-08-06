# utoken
_utoken_ is a tokenizer that divides text into words, punctuation and special tokens such as numbers, URLs, XML tags, email-addresses and hashtags.

### Example
#### Input
```
Mr. Miller (Mary's ex-brother-in-law) can't afford $15,000.00.
```
#### Output
```
Mr. Miller ( Mary 's ex - brother-in-law ) can n't afford $ 15,000.00 .
```
#### Optional annotation output
```
::span 0-3 ::type ABBREV ::sem-class pre-name-title ::surf Mr.
::span 4-10 ::type WORD-B ::surf Miller
::span 11-12 ::type PUNCT ::surf (
::span 12-16 ::type WORD-B ::surf Mary
::span 16-18 ::type DECONTRACTION ::surf 's
::span 19-21 ::type WORD-B ::surf ex
::span 21-22 ::type PUNCT-E ::surf -
::span 22-36 ::type LEXICAL ::surf brother-in-law
::span 36-37 ::type PUNCT ::surf )
::span 38-40 ::type DECONTRACTION ::surf can
::span 40-43 ::type DECONTRACTION ::surf n't
::span 44-50 ::type WORD-B ::surf afford
::span 51-52 ::type PUNCT ::surf $
::span 52-61 ::type NUMBER ::surf 15,000.00
::span 61-62 ::type PUNCT-E ::surf .
```

### Usage
```
utokenize.py [-h] [-i INPUT-FILENAME] [-o OUTPUT-FILENAME] [-a ANNOTATION-FILENAME] [-p cProfile-FILENAME]
             [--lc LANGUAGE-CODE] [-f] [-v] [-c] [--mt] [--version]
optional arguments:
  -h, --help            show this help message and exit
  -i INPUT-FILENAME, --input INPUT-FILENAME
                        (default: STDIN)
  -o OUTPUT-FILENAME, --output OUTPUT-FILENAME
                        (default: STDOUT)
  -a ANNOTATION-FILENAME, --annotation ANNOTATION-FILENAME
                        (optional output)
  -p cProfile-FILENAME, --profile cProfile-FILENAME
                        (optional output)
  --lc LANGUAGE-CODE    ISO 639-3, e.g. 'fas' for Persian
  -f, --first_token_is_line_id
                        First token is line ID
  -v, --verbose         write change log etc. to STDERR
  -c, --chart           build chart, even without annotation output
  --mt                  MT-style output with @ added to certain punctuation
  --version             show program's version number and exit
```

### Design
* Written by Ulf Hermjakob, USC Information Sciences Institute, 2021
* A universal tokenizer, i.e. designed to work with a wide variety of scripts and languages.
* Modular, expandable architecture.
* More information in data files rather than program code.
* Written in Python.
* Maintains a chart data structure with detailed additional information that can also serve as a basis for further processing.
* Very preliminary (implementation started in mid-July 2021, current version 0.0.2)

### Limitations
* Currently excluded: no-space scripts like Chinese
* Substantial set of resource entries (data file) currently for English only
* Substantial testing so far for English only

### Requirements
* Python 3.8 or higher
* regex module (https://pypi.org/project/regex/)
