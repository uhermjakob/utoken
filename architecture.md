# utoken architecture

## Overview
The tokenizer works through a hierarchy of tokenization steps. After a normalization step (that deletes all non-decodable characters (surrogates) and some control characters and normalizes whitespaces), the tokenizer identifies a number of special constructs such as XML tags, URLs, email addresses, hashtags, handles and numbers (e.g. -12,345,678.90 or १,२३,४५,६७८.९०) using a range of full Unicode regular expressions (e.g. \p{L} for any letter). Once identified, the texts in these special tokens are no longer subject to further tokenization steps, which prevents them from inadvertent fragmentation. Both pattern-based and lexically-based decontraction steps decompose texts such as John’s and can’t to John ’s and can n’t.

```
::contraction c'mon ::target come on ::lcode eng
::contraction dont ::target do n't ::lcode eng
::contraction won't ::target will n't ::lcode eng
::repair ca n't ::target can n't ::lcode eng
::repair U.S ::target U.S. ::lcode eng
::abbrev mSv/hr ::exp millisievert per hour ::lcode eng ::sem-class unit-of-measurement
::abbrev No. ::exp number ::lcode eng ::case-sensitive True ::right-context \s*\d
::abbrev int'l ::exp international ::lcode eng
::punct-split ( ::side both
::punct-split - ::side end ::group True ::left-context (?:\pL\pM*\pL\pM*|[.,;:!?])
```
A number of tokenization steps are supported by data files with entries such as those shown above to support decontraction, repair (e.g. due to previous mistokenization, or missing periods), abbreviation handling and punctuation splitting. Note that many entries contain additional slots such as language code, semantic class, case sensitivity, context restrictions, the token side to which punctation split-off is applicable, and group (which allows multiple punctuation of the same kind to be tokenized together, e.g. !!!!).

The tokenizer can provide charts for a richer additional output. These charts allow to mark up tokens with any type (e.g. URL, number), multi-word tokens (e.g. et al.), sub-word tokens, and alternative tokens. They also align chart tokens back to offsets in the original text.

After two weeks of development, we conducted a first test, comparing utoken to ulf-tokenizer, previously developed and optimized over several years, on the English-language general AMR Corpus with 39k sentences, incl. a variety of genres such as newswire and discussion forums.

The two tokenizers fully agreed for 96.6% of sentences, representing 99.8%-99.9% of tokens.

A first analysis of a sample of differences shows that the new utoken is better already. We plan to do more testing on other corpora, scripts and languages and plan to continue the development of utoken.

## Tokenization Steps
*utoken* has an ordered list of tokenization steps, each of which deals with a particular aspect of tokenization.
Starting with the first tokenization step, the tokenization steps try to find a token to be split off. If successful, the tokenization step calls itself on the string to the left of the token and to the string on the right of the token, and then combines the results with the token it found before. When a tokenization step does not find a token, it calls the next tokenization step on the same string.

#### Example
* Number heuristic is applied to sentence: *The 25,000 vaccine doses were stored at -20°C.*
* Number heuristic identifies *25,000* as a number and recursively calls itself for (1) *The* and (2) *vaccine doses were stored at -20°C.* 
* Number heuristic does now find any more numbers in *The* and therefore calls the next heuristic step on *The* .
* Number heuristic, when applied to *vaccine doses were stored at -20°C.*, identifies *-20* as a number and recursively calls itself on (1) *vaccine doses were stored at* and (2) *°C.*
* Number heuristic does not find any more numbers in (1) and (2) above, and therefore calls the next tokeniztion step on (1) and (2).

## Bit Vectors
In a *utoken* bit vector, every bit stands for a certain property of a sequence of characters, including in particular a single character.
Examples for such properties for a character potentially include 
* character is in Arabic script Unicode block
* character is a digit (in any script)
* character is a deletable control character
* character is @
* character is a vowel

The bit vector for a sequence of characters (in particular the whole line of text) is the combination of all character bit vectors with a bit-wise 'or'. In the code, the bit vector for a whole line of text is referred to as a line vector, or 'lv' for short.
If the "Arabic script" bit is set, it means that at least one character in the sentence/sequence is in Arabic script.
Bit vectors are used for two purposes:
1 New character classes. A bit in the bit vector can define a new class of characters such as 'vowel' that are not covered by Python or UnicodeData. In an initialization step, the appropriate bit in te bit vector is set for all characters of the class. Then later, class membership can quickly be checked by performing a simple bit-vector 'and'.
1 Speed. A tokenzation script that checks for certain Arabic tokens might do a quick check whether the line contains any Arabic characters using a simple bit-vector 'and'. The email tokenization step for example can just compare the line bit vector and the '@' bit vector to check if any '@' occur, and otherwise move on without wasting time when no ampersands and therefore no email addresses occur in a line.
