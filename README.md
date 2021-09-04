# utoken
_utoken_ is a tokenizer that divides text into words, punctuation and special tokens such as numbers, URLs, XML tags, email-addresses and hashtags.
The tokenizer comes with a companion detokenizer.

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
_The ouput below is in the more human-friendly annotation format. Default format is the more computer-friendly JSON._
```
::line 1 ::s Capt. O'Connor's car can't've cost $100,000.
::span 0-5 ::type ABBREV ::sem-class military-rank ::surf Capt.
::span 6-14 ::type LEXICAL ::sem-class person-last-name ::surf O'Connor
::span 14-16 ::type DECONTRACTION ::surf 's
::span 17-20 ::type WORD-B ::surf car
::span 21-23 ::type DECONTRACTION ::surf can
::span 23-26 ::type DECONTRACTION ::surf n't
::span 26-29 ::type DECONTRACTION-R ::surf 've
::span 30-34 ::type WORD-B ::surf cost
::span 35-36 ::type PUNCT ::sem-class currency-unit ::surf $
::span 36-43 ::type NUMBER ::surf 100,000
::span 43-44 ::type PUNCT-E ::surf .
```

### Usage
```
utokenize.py [-h] [-i INPUT-FILENAME] [-o OUTPUT-FILENAME] [-a ANNOTATION-FILENAME] [--annotation_format ANNOTATION_FORMAT]
             [-p PROFILE-FILENAME] [--profile_scope PROFILE_SCOPE] [-d DATA_DIRECTORY] [--lc LANGUAGE-CODE] [-f] [-v] [--simple]
             [--version]
optional arguments:
  -h, --help            show this help message and exit
  -i INPUT-FILENAME, --input INPUT-FILENAME
                        (default: STDIN)
  -o OUTPUT-FILENAME, --output OUTPUT-FILENAME
                        (default: STDOUT)
  -a ANNOTATION-FILENAME, --annotation_file ANNOTATION-FILENAME
                        (optional output)
  --annotation_format ANNOTATION_FORMAT
                        (default: 'json'; alternative: 'double-colon')
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
  --simple              prevent MT-style output (e.g. @-@). Note: can degrade any detokinzation
  --version             show program's version number and exit
```

```
detokenize.py [-h] [-i INPUT-FILENAME] [-o OUTPUT-FILENAME] [-d DATA_DIRECTORY] [--lc LANGUAGE-CODE] [-f] [-v] [--version]
optional arguments:
  -h, --help            show this help message and exit
  -i INPUT-FILENAME, --input INPUT-FILENAME
                        (default: STDIN)
  -o OUTPUT-FILENAME, --output OUTPUT-FILENAME
                        (default: STDOUT)
  -d DATA_DIRECTORY, --data_directory DATA_DIRECTORY
                        (default: standard data directory)
  --lc LANGUAGE-CODE    ISO 639-3, e.g. 'fas' for Persian
  -f, --first_token_is_line_id
                        First token is line ID (and will be exempt from any tokenization)
  -v, --verbose         write change log etc. to STDERR
  --version             show program's version number and exit
```

### Design
* Written by Ulf Hermjakob, USC Information Sciences Institute, 2021
* A universal tokenizer, i.e. designed to work with a wide variety of scripts and languages.
* Modular, expandable architecture.
* More information in data files rather than program code.
* Written in Python.
* Maintains a chart data structure with detailed additional information that can also serve as a basis for further processing.
* Preliminary (implementation started in mid-July 2021, current version 0.0.5)

### Limitations
* Currently excluded: no-space scripts like Chinese
* Substantial set of resource entries (data file) currently for English only
* Substantial testing so far only for English, Hindi, Farsi and to a lesser degree Kazakh and Uyghur

### Requirements
* Python 3.8 or higher
* regex module (https://pypi.org/project/regex/) &nbsp; ```import regex```

### More topics (click to open)
<details>
<summary>What gets split and what not</summary>

### What gets split
* Contractions: John's → John 's; we've → we 've; can't → can n't; won't → will n't
* Quantities into number and unit: 5,000km² → 5,000 km²
* Ordinal numbers into number and ordinal particle: 350th → 350 th
* Non-lexical hyphenated expressions: peace-loving → peace @-@ loving
* Name initials: J.S.Bach → J. S. Bach
 
### What stays together
* XML tags: ```<a href="http://www.hollywoodbowl.com">```
* URLs: ```http://www.youtube.com/watch?v=IAaDVOd2sRQ```
* Email addresses: ```а.almukhanov@energo.gov.kz```
* Filenames: ```Оперплан_каз2015.doc```
* Numbers: ```-12,345,678.90``` &nbsp; ```१,२३,४५,६७८.९०```
* Abbreviations: ```Mr.``` &nbsp; ```e.g.``` &nbsp; ```w/o```
* Lexicon entries with dashes etc.: ```T-shirt``` &nbsp; ```father-in-law``` &nbsp; ```so-called``` &nbsp; ```Port-au-Prince``` &nbsp; &nbsp; ```Xi’an``` &nbsp; ```'s-Gravenhage```
* Hashtags, handles: ```#global_warming``` &nbsp; ```#2``` &nbsp; ```@GermanBeer```
* Groups of related punctuation: ```???```
* Groups of emojis and other symbols: ```👍👍🎉```
* Words with an internal _zero width non-joiner_: e.g. Farsi ```می‌خواهم```
</details>

<details>
<summary>Mark-up of certain punctuation (e.g. @-@) and option --simple</summary>

### Mark-up of certain punctuation (e.g. @-@)
For many application such as machine translation, tokenization is important, but should be reversed when producing the final output.
In some cases, this is relatively straight forward, so ```.``` and ```,``` typically attach to the word on the left and ```(``` attaches to the word on the right.
In other cases, it can generally be very hard to decide how to detokenize, so we add a special tag such as ```@``` during tokenization in order to guide later dekonization.
A ```@``` on one or both sides of punctuation indicates that in the original text, the punctuation and neighboring word were together. 
To look at it in another way, the tokenizer basically upgrades the non-directional ```"``` to an open ```"@``` or close ```@"``` delimiter. 

Example: ```("Hello,world!")``` &nbsp; Tokenized: ```( "@ Hello , world ! @" )``` &nbsp; Detokenized: ```("Hello, world!")```
  
If later detokenization is not import and you want to suppress any markup with ```@```, call _utokenizer.py_ with the option _--simple_
  
Example: ```("Hello,world!")``` &nbsp; Tokenized (simple): ```( " Hello , world ! " )``` &nbsp; Detokenized: ```(" Hello, world! ")```
</details>

<details>
<summary>Option --first_token_is_line_id</summary>

### Option --first_token_is_line_id
In some applications, the text to be tokenized is preceded by a sentence ID at the beginning of each line and tokenization should *not* be applied to those sentence IDs.  
Option ```--first_token_is_line_id```, or ```-f``` for short, suppresses tokenization of those sentence IDs.

* Example input: ```GEN:1:1	In the beginning, God created the heavens and the earth.```
* ```utokenize.pl``` tokenization: ```GEN @:@ 1 @:@ 1 In the beginning , God created the heavens and the earth .```
* ```utokenize.pl -f``` tokenization: ```GEN:1:1 In the beginning , God created the heavens and the earth .```
</details>
  
