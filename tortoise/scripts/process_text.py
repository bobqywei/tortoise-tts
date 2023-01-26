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
    "ACL": " anterior cruciate ligament ",
    "AAU": " american athletic union ",
    "ADD": " attention deficit disorder ",
    "CB": " Chris Bosh ",
    'ESP': ' especially ',
    'II': ' the second ',
    'III': ' the third ',
    'VII': ' the seventh ',
    'VIII': ' the eighth ',
    'NBA': ' National Basketball Association ',
    'OCD': ' obsessive compulsive disorder ',
    'SUV': ' sport utility vehicle ',
    'TV': ' television ',
    'US': ' United States ',
    'YC': ' Wye Combinator ',
    'MCL': ' medial collateral ligament ',
    'UD': ' Udonis Haslem ',
    'NC': ' North Carolina ',
    'MIT': ' the Massachusetts Institute of Technology ',
    'JV': ' junior varsity ',
    'weeknd': ' weekend ',
    'Weeknd': ' Weekend ',
    'USL': ' United Soccer League ',
    'RIAA': ' Recording Industry Association of America ',
    'PR': ' public relations ',
    'PG': ' point guard ',
    'Shaq': ' Shaquille ',
    'shaq': ' shaquille ',
    'OT': ' overtime ',
    'NHL': ' National Hockey League ',
    'MLS': ' Major League Soccer ',
    'GM': ' general manager ',
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
