"""Deterministyczne reguły wspólne dla promptu, walidacji i statystyk."""
import re
import unicodedata

def words(text):
    text=unicodedata.normalize('NFC',text).casefold().replace('’', "'")
    return re.findall(r"[^\W\d_]+(?:['-][^\W\d_]+)*",text,re.UNICODE)

def sentences(text):
    return [part.strip() for part in re.findall(r'[^.!?\n]+(?:[.!?]+|(?=\n|$))',text) if words(part)]
