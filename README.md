# utoken
_utoken_ is a tokenizer that divides text into words, punctuation and special tokens such as numbers, URLs, XML tags, email-addresses and hashtags.
The tokenizer comes with a companion detokenizer.
Initial public release of beta version 0.1.0 on Oct. 1, 2021.

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
::line 1 ::s Capt. O'Connor's car can't've cost$100,000.
::span 0-5 ::type ABBREV ::sem-class military-rank ::surf Capt.
::span 6-14 ::type LEXICAL ::sem-class person-last-name ::surf O'Connor
::span 14-16 ::type DECONTRACTION ::surf 's
::span 17-20 ::type WORD-B ::surf car
::span 21-23 ::type DECONTRACTION ::surf can
::span 23-26 ::type DECONTRACTION ::surf n't
::span 26-29 ::type DECONTRACTION-R ::surf 've
::span 30-34 ::type WORD-B ::surf cost
::span 34-35 ::type PUNCT ::sem-class currency-unit ::surf $
::span 35-42 ::type NUMBER ::surf 100,000
::span 42-43 ::type PUNCT-E ::surf .
```

### Usage &nbsp; (click below for details)
<details>
<summary>utokenize (command line interface to tokenize a file)</summary>

```bash
python -m utoken.utokenize [-h] [-i INPUT-FILENAME] [-o OUTPUT-FILENAME] [-a ANNOTATION-FILENAME] 
                           [--annotation_format ANNOTATION_FORMAT] [-p PROFILE-FILENAME] 
                           [--profile_scope PROFILE_SCOPE] [-d DATA_DIRECTORY] [--lc LANGUAGE-CODE] 
                           [-f] [-v] [-c] [--simple] [--version]
  
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
  -c, --chart           build annotation chart, even without annotation output
  --simple              prevent MT-style output (e.g. @-@). Note: can degrade any detokinzation
  --version             show program's version number and exit
```
Note: Please make sure that your $PYTHONPATH includes the directory in which this README file resides.
</details>

<details>
<summary>detokenize (command line interface to detokenize a file)</summary>

```bash
python -m utoken.detokenize [-h] [-i INPUT-FILENAME] [-o OUTPUT-FILENAME] [-d DATA_DIRECTORY] 
                            [--lc LANGUAGE-CODE] [-f] [-v] [--version]
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
Note: Please make sure that your $PYTHONPATH includes the directory in which this README file resides.
</details>

<details>
<summary>utokenize_string (Python function call to tokenize a string)</summary>
  
```python
from utoken import utokenize
  
tok = utokenize.Tokenizer(lang_code='eng')  # Initialize tokenizer, load resources
print(tok.utokenize_string("Dont worry!"))
print(tok.utokenize_string("Sold,for $9,999.99 on ebay.com."))
```
Output:
```
Do n't worry !
Sold , for $ 9,999.99 on ebay.com .
```
Note: Please make sure that your $PYTHONPATH includes the directory in which this README file resides.
</details>

<details>
<summary>detokenize_string (Python function call to detokenize a string)</summary>
 
```python
from utoken import detokenize

detok = detokenize.Detokenizer(lang_code='eng')  # Initialize detokenizer, load resources
print(detok.detokenize_string("Do n't worry !"))
print(detok.detokenize_string("Sold , for $ 9,999.99 on ebay.com ."))
```
Output:
```
Don't worry!
Sold, for $9,999.99 on ebay.com.
```
Note: Please make sure that your $PYTHONPATH includes the directory in which this README file resides.
</details>

### Design
* Written by Ulf Hermjakob, USC Information Sciences Institute, 2021
* A universal tokenizer, i.e. designed to work with a wide variety of scripts and languages.
* Modular, expandable architecture.
* More information in data files rather than program code.
* Written in Python.
* Maintains a chart data structure with detailed additional information that can also serve as a basis for further processing.
* First public release on Oct. 1, 2021: beta version 0.1.0

### Limitations
* Currently excluded: no-space scripts like Chinese and Japanese
* Large set of resource entries (data file) currently for English only; limited resource entries for 50+ other languages
* Languages tested so far: Amharic, Arabic, Assamese, Bengali, Bulgarian, Dutch, __English__, __Farsi__, French, Georgian, German, Greek (Ancient/Koine/Modern), Hebrew (Ancient/Modern), __Hindi__, Indonesian, Kannada, __Kazakh__, Korean, Lao, Lithuanian, Malayalam, Pashto, Portuguese, Russian, Somali, Spanish, Swahili, Swedish, __Tagalog__, Tamil, Turkish, __Uyghur__, Zulu
  * For languages in __bold__: large-scale testing of thousands to hundreds of thousands of sentences per language.
  * For other modern languages: a few hundred sentences from 100 Wikipedia articles per language.
  * For Ancient Hebrew and Koine Greek: a few hundred verses each from the Bible's Old and New Testament respectively.  
  * For Ancient Greek: a few hundred sentences from Homer's _Odyssey_ and Plato's _Republic_.

### Requirements
* Python 3.8 or higher
* regex module (https://pypi.org/project/regex/) &nbsp; ```import regex```

### More topics &nbsp; (click below for details)
<details>
<summary>What gets split and what not</summary>

### What gets split
* Contractions: ```John's``` → ```John``` ```'s```; ```we've``` → ```we``` ```'ve```; ```can't``` → ```can``` ```n't```; ```won't``` → ```will``` ```n't```
* Quantities into number and unit: ```5,000km²``` → ```5,000``` ```km²```
* Ordinal numbers into number and ordinal particle: ```350th``` → ```350``` ```th```
* Non-lexical hyphenated expressions: ```peace-loving``` → ```peace``` ```@-@``` ```loving```
* Name initials: ```J.S.Bach``` → ```J.``` ```S.``` ```Bach```
 
### What stays together
* XML tags: ```<a href="http://www.hollywoodbowl.com">```
* URLs: ```https://www.youtube.com/watch?v=AaZ_RSt0KP8```
* Email addresses: ```а.almukhanov@energo.gov.kz```
* Filenames: ```Оперплан_каз2015.doc```
* Numbers: ```-12,345,678.90``` &nbsp; ```१,२३,४५,६७८.९०```
* Abbreviations: ```Mr.``` &nbsp; ```e.g.``` &nbsp; ```w/o```
* Lexicon entries with dashes: ```T-shirt``` &nbsp; ```father-in-law``` &nbsp; ```so-called``` &nbsp; ```Port-au-Prince```
* Lexicon entries with apostrophe: ```Xi’an``` &nbsp; <nobr>```'s-Gravenhage```</nobr>
* Hashtags, handles: ```#global_warming``` &nbsp; ```#2``` &nbsp; ```@GermanBeer```
* Groups of related punctuation: ```???```
* Groups of emojis and other symbols: ```⚽👍🎉```
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
  
<details>
<summary>Why is tokenization hard?</summary>

### Why is tokenization hard?
Tokenization is more then just splitting a sentence along spaces, as a lot of punctuation such as commas and periods are attached to adjacent words.
But we can't just blindly split off commas and periods, as this would break numbers such as `12,345.60`, abbreviations such as `Mr.` or URLs such as `www.usc.edu`.

* There are many special types of entities that need to be preserved in tokenization, e.g. 
  * XML tags: ```<a href="http://www.hollywoodbowl.com">```
  * URLs: ```https://www.youtube.com/watch?v=AaZ_RSt0KP8```
  * Email addresses: ```а.almukhanov@energo.gov.kz```
  * Filenames: ```Оперплан_каз2015.doc```
  * Numbers: ```-12,345,678.90``` &nbsp; ```१,२३,४५,६७८.९०```
  * Hashtags, handles: ```#global_warming``` &nbsp; ```#2``` &nbsp; ```@GermanBeer```
* __Abbreviations__ can be hard to determine in many languages, as a period might indicate an abbreviation or the end of a sentence.
  * Abbreviations: ```Mr.``` &nbsp; ```e.g.``` &nbsp; ```w/o```
* __Apostrophes__ are normal letters in some languages, e.g. Somali ```su'aal``` (_question_). Apostrophes can appear in foreign names (e.g. ```Xi'an``` and ```'s-Gravenhage```). In some languages, an apostrophe is used for contractions, such as ```John's``` and ```we'll``` in English. Additionally, an apostrophe can be used as a quote around a word or phrase such as `'Good job!'`. All these cases have to be treated differently.
* __Hyphens__ can join independent words such as in `peace-loving` (which should be split). But they also occur inside lexical phrases such as `T-shirt` that should __not__ be split.
* Many applications need to map a tokenized sentence back to 'normal' untokenized text. To support such a __detokenizer__, the tokenizer's output must facilitate future detokenization. For example, by default, the tokenizer adds attachment tags such as '@' to punctuation to indicate to which side(s) they should attach after detokenization. For more on this topic, please see topic _Mark-up of certain punctuation_ above.
* Other challenges: symbols, variation selectors, non-standard whitespaces, special characters such as `zero width non-joiner`.
* In general, it is hard to make a tokenizer work __universally__, for a wide range of languages, scripts and conventions.
* _utoken_ uses a combination of general patterns and lists of specific tokens to solve many of the challenges above. (See more under topic _Tokenization data files_.)
* Example for a language-specific challenge: In Modern Hebrew, acronyms are marked by placing a _gershayim_ between the last two characters, e.g. ארה״ב (USA). In practice, the _gershayim_ is often replaced by the more readily available quotation mark ("). However, quotation marks are also used for quotations, e.g. <span dir="rtl">ה"סתום"</span> (the "valve"), so care has to be taken to do justice to both acronymns (preserve as a single token) and quotes (separate into multiple tokens).
</details>

<details>
<summary>Tokenization data files</summary>

### Tokenization data files
_utokenize_ includes a number of data files to supports its operation:
* `tok-resource.txt` includes language-independent tokenization resource entries, especially for punctuation, abbreviations (e.g. ```km²```) and names (especially those with hyphens, spaces and other non-alpha characters)
* `tok-resource-eng-global.txt` contains tokenization resource entries for English that are also loaded for other languages. This is helpful as foreign texts often code-switch to English.
* `tok-resource-eng.txt` contains tokenization resource entries for English that are not shared, including those that would not work in other languages. For example, in English, _dont_ in a non-standard version of _don't_ and is tokenized into ```do``` ```n't```, but in French, _dont_ (_of which_) is a regular word that should be left alone.
* `detok-resource.txt` includes resources for detokenization. The file is also used by the tokenizer to mark up certain punctuation with attachment tags such as @-@.
* There are numerous other `tok-resource-xxx.txt` files for other languages, some larger than others. Some languages such as Farsi just don't use contractions and abbreviations with periods that much, so there are few entries. Others files might benefit from additional contributions. 
* `top-level-domain-codes.txt` contains a list of suffixes such as .com, .org, .uk, .tv to support tokenization of URLs and email address.

Exmaples of resource entries:
```
::punct-split ! ::side end ::group True ::comment multiple !!! remain grouped as a single token
::contraction can't ::target can n't ::lcode eng
::repair wo n't ::target will n't ::lcode eng ::problem previous tokenizer
::abbrev No. ::exp number ::lcode eng ::sem-class corpus-component ::case-sensitive True ::right-context \s*\d
::lexical T-shirt ::lcode eng ::plural +s
::misspelling accomodate ::target accommodate ::lcode eng ::suffix-variations e/ed;es;ing;ion;ions

::markup-attach - ::group True ::comment hyphen-minus ::example the hyphen in _peace-loving_ will be marked up as ```@-@```
::auto-attach th ::side left ::left-context \d ::lcode eng ::example 20th
```
</details>

<details>
<summary>Speed</summary>

### Speed
210,000 characters per second (real time) on a 39k sentence English AMR corpus on a 2021 MacBook Pro using a single CPU.
Parallelization is trivial as sentences are tokenized independent of each other.
</details>

<details>
<summary>Testing</summary>

### Testing
_utoken_ has been tested on 45 corpora in 34 languages and 13 scripts (as of version 0.1.0).
Tests include 
* Manual review of lots of tokenization
* Comparison to other tokenizers: [Sacremoses](https://github.com/alvations/sacremoses) and [ulf-tokenizer](https://github.com/isi-nlp/ulf-tokenizer)
* Tokenization analysis scripts: 
  * wildebeest (text normalization and cleaning; analysis of types of characters used, encoding issues) 
  * aux/tok-analysis.py (looks for a number of potential problems such as tokens with mixed letters/digits, mixed letters/punctuation, potential abbreviations separated from period)
* Comparisons to previous versions of all test corpora before release.
</details>

<details>
<summary>Related software</summary>

### Related software
* [Universal romanizer _uroman_](https://github.com/isi-nlp/uroman), written by Ulf Hermjakob (same author)
</details>

<details>
<summary>Future work — Feedback and contributions welcome</summary>

### Future work — Feedback and contributions welcome
Plans include 
* Building resources, testing and fine-tuning of additional languages such as Hausa, Italian, Telugu, Vietnamese.
* Adding new special entity types such as IPA pronunciations, geographic coordinates, complex IDs such as 403(k).
* Semi-supervised learning of lexical and abbreviation resources from large corpora.
</details>

