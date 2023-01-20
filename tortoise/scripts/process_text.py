import os
import re
import argparse

from file_utils import get_leaf_files

parser = argparse.ArgumentParser()
parser.add_argument('--dir', type=str, help='Directory to trace for text files.', default=None)


REPLACE = {
    # Remove citations
    r'\[.*?\]': '',
    r'<.*?>': '',
    r'\(\d+\)': '',
    # Replace math symbols
    r'%': 'percent',
    r'(\d)\s*-\s*(\d)': r'\1 to \2',
    r'\+' : ' plus ',
    r'(\d)\s*/\s*(\d)': r'\1 divided by \2',
    r'(\d)\s*\*\s*(\d)': r'\1 times \2',
    r'(\d)\s*\^\s*(\d)': r'\1 to the power of \2',
    r'([a-zA-Z])\s*/\s*([a-zA-Z])': r'\1 or \2',
    # Replace short form numbers
    r'no\.\s*(\d+)': r'number \1',
    r'\=': ' equals ',
    # Replace quotations
    r"[“”]": "\"",
    r"[‘’]": "\'",
    # Replace abbreviations
    r"\bADD\b": " attention deficit disorder ",
    r"\bCB\b": " Chris Bosh ",
    r"\bACL\b": " anterior cruciate ligament ",
    r'\bOK\b': ' okay ',
    r'\bESP\b': ' especially ',
    r'\bIII\b': ' the third ',
    r'\bNBA\b': ' National Basketball Association ',
    r'\bOCD\b': ' obsessive compulsive disorder ',
    r'\bSUV\b': ' sport utility vehicle ',
    r'\bTV\b': ' television ',
    r'\bUS\b': ' United States ',
    r'\bYC\b': ' Y Combinator ',
    r'\bMCL\b': ' medial collateral ligament ',
    r'\bUD\b': ' Udonis Haslem ',
    r'\bNC\b': ' North Carolina ',
    r'\bMIT\b': ' the Massachusetts Institute of Technology ',
    r'\bJV\b': ' junior varsity ',
}


if __name__ == '__main__':
    args = parser.parse_args()
    textfiles = [p for p in get_leaf_files(args.dir) if p.endswith('.txt') and 'mark_cuban' not in p]
    for path in textfiles:
        with open(path, 'r') as f:
            text = f.read()
        for k, v in REPLACE.items():
            text = re.sub(k, v, text)
        with open(path, 'w') as f:
            f.write(text)
