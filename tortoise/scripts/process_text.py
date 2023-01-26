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
    # Prevent run-on sentences
    r':': '.',
    r';': '.',
}

ABBREVS = {
    'II': ' the second ',
    'III': ' the third ',
    'VII': ' the seventh ',
    'VIII': ' the eighth ',
    'ACL': ' anterior cruciate ligament ',
    'AAU': ' american athletic union ',
    'ADD': ' attention deficit disorder ',
    'ATM': ' automated teller machine ',
    'CB': ' Chris Bosh ',
    'ESP': ' especially ',
    'GM': ' general manager ',
    'JV': ' junior varsity ',
    'LA': ' Los Angeles ',
    'MCL': ' medial collateral ligament ',
    'MIT': ' the Massachusetts Institute of Technology ',
    'MLS': ' Major League Soccer ',
    'MRI': ' magnetic resonance imaging ',
    'NBA': ' National Basketball Association ',
    'NC': ' North Carolina ',
    'NHL': ' National Hockey League ',
    'NSA': ' National Security Agency ',
    'OA': ' O.A. ',
    'OB': ' O.B. ',
    'OC': ' O.C. ',
    'OCD': ' obsessive compulsive disorder ',
    'OT': ' overtime ',
    'PG': ' point guard ',
    'PR': ' public relations ',
    'PTSD': ' post traumatic stress disorder ',
    'PU': ' P.U. ',
    'RF': ' radio frequency ',
    'RIAA': ' Recording Industry Association of America ',
    'SF': ' S.F. ',
    'Shaq': ' Shaquille ',
    'shaq': ' shaquille ',
    'SMG': ' submachine gun ',
    'SS': ' S.S. ',
    'SUV': ' sport utility vehicle ',
    'TV': ' television ',
    'UCLA': ' University of California, Los Angeles ',
    'UD': ' Udonis Haslem ',
    'US': ' United States ',
    'USB': ' U.S.B. ',
    'USL': ' United Soccer League ',
    'weeknd': ' weekend ',
    'Weeknd': ' Weekend ',
    'WGBS': ' West Georgia Broadcasting System ',
    'WWI': ' World War One ',
    'WWII': ' World War Two ',
    'YC': ' Wye Combinator ',
}


if __name__ == '__main__':
    args = parser.parse_args()
    textfiles = [p for p in get_leaf_files(args.dir) if p.endswith('.txt')]
    for path in textfiles:
        with open(path, 'r') as f:
            text = f.read()
        old_text = text

        for k, v in REPLACE.items():
            text = re.sub(k, v, text)
        for k, v in ABBREVS.items():
            text = re.sub(r'\b' + k + r'\b', v, text)

        if text != old_text:
            print(path)
            with open(path, 'w') as f:
                f.write(text)
