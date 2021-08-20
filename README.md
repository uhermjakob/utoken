# utoken
_utoken_ is a tokenizer that divides text into words, punctuation and special tokens such as numbers, URLs, XML tags, email-addresses and hashtags.

### Example
#### Input
```
Capt. O'Connor's car can't've cost $100,000.
```

#### Output
```
Capt. O'Connor 's car can n't 've cost $ 100,000 .
```

#### Optional annotation output
```
::line L1 ::s Capt. O'Connor's car can't've cost $100,000.
::span 0-5 ::type ABBREV ::sem-class military-rank ::surf Capt.
::span 6-14 ::type WORD-B ::surf O'Connor
::span 14-16 ::type DECONTRACTION ::surf 's
::span 17-20 ::type WORD-B ::surf car
::span 21-23 ::type DECONTRACTION ::surf can
::span 23-26 ::type DECONTRACTION ::surf n't
::span 26-29 ::type LEXICAL ::surf 've
::span 30-34 ::type WORD-B ::surf cost
::span 35-36 ::type PUNCT ::surf $
::span 36-43 ::type NUMBER ::surf 100,000
::span 43-44 ::type PUNCT-E ::surf .
```

### Usage
```
utokenize.py [-h] [-i INPUT-FILENAME] [-o OUTPUT-FILENAME] [-a ANNOTATION-FILENAME] [-p PROFILE-FILENAME]
             [--profile_scope PROFILE_SCOPE] [-d DATA_DIRECTORY] [--lc LANGUAGE-CODE] [-f] [-v] [-c] [--mt] [--version]
optional arguments:
  -h, --help            show this help message and exit
  -i INPUT-FILENAME, --input INPUT-FILENAME
                        (default: STDIN)
  -o OUTPUT-FILENAME, --output OUTPUT-FILENAME
                        (default: STDOUT)
  -a ANNOTATION-FILENAME, --annotation ANNOTATION-FILENAME
                        (optional output)
  -p PROFILE-FILENAME, --profile PROFILE-FILENAME
                        (optional output for performance analysis)
  --profile_scope PROFILE_SCOPE
                        (optional scope for performance analysis)
  -d DATA_DIRECTORY, --data_directory DATA_DIRECTORY
                        (default: standard data directory)
  --lc LANGUAGE-CODE    ISO 639-3, e.g. 'fas' for Persian
  -f, --first_token_is_line_id
                        First token is line ID (and will be exempt from any tokenization)
  -v, --verbose         write change log etc. to STDERR
  -c, --chart           build annotation chart, even without annotation output
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
* Preliminary (implementation started in mid-July 2021, current version 0.0.4)

### Limitations
* Currently excluded: no-space scripts like Chinese
* Substantial set of resource entries (data file) currently for English only
* Substantial testing so far only for English, Hindi, and to a lesser degree Kazakh and Uyghur

### Requirements
* Python 3.8 or higher
* regex module (https://pypi.org/project/regex/)
