# utoken architecture

## Tokenization Steps
*utoken* has an ordered list of tokenization steps, each of which deals with a particular aspect of tokenization.
Starting with the first tokenization step, the tokenization steps try to find a token to be split off. If successful, the tokenization step calls itself on the string to the left of the token and to the string on the right of the token, and then combines the results with the token it found before. When a tokenization step does not find a token, it calls the next tokenization step on the same string.

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
