#!/usr/bin/env python3

from utoken import detokenize

detok = detokenize.Detokenizer(lang_code='eng')  # Initialize detokenizer, load resources
print(detok.detokenize_string("Do n't worry !"))
print(detok.detokenize_string("Sold , for $ 9,999.99 on ebay.com ."))

