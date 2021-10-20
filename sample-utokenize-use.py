#!/usr/bin/env python3
# Sample utoken utokenization call.

from utoken import utokenize

tok = utokenize.Tokenizer(lang_code='eng')  # Initialize tokenizer, load resources
print(tok.utokenize_string("Dont worry!"))
print(tok.utokenize_string("Sold,for $9,999.99 on ebay.com."))
