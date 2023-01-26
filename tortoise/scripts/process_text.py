import re
import argparse

from file_utils import get_leaf_files

parser = argparse.ArgumentParser()
parser.add_argument('--dir', type=str, help='Directory to trace for text files.', default=None)


REPLACE = {
    # Remove citations
    # r'\[.*?\]': '',
    r'\[\d+\]': '',
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
    'AAU': ' american athletic union ',
    'ACL': ' anterior cruciate ligament ',
    'ADD': ' attention deficit disorder ',
    'AIVA': ' artificial intelligence virtual artist ',
    'AKA': ' also known as ',
    'ATM': ' automated teller machine ',
    'AV': ' audio video ',
    'BMI': ' B.M.I. ',
    'CB': ' Chris Bosh ',
    'CBS': ' Columbia Broadcasting System ',
    'CFO': ' chief financial officer ',
    'CGI': ' computer generated imagery ',
    'DIY': ' do it yourself ',
    'DJ': 'D.J.',
    'DP': 'D.P.',
    'DVD': ' digital video disc ',
    'DMT': ' dimethyltryptamine ',
    'EQ': ' equalizer ',
    'ESP': ' especially ',
    'FM': ' F.M. ',
    'GM': ' general manager ',
    'HQ': ' headquarters ',
    'IBM': ' International Business Machines ',
    'JFK': ' John F. Kennedy ',
    'JJ': ' J.J. ',
    'JV': ' junior varsity ',
    'JVC': ' J.V.C. ',
    'LA': ' Los Angeles ',
    'MC': ' M.C. ',
    'MCL': ' medial collateral ligament ',
    'MDMA': ' methylene dioxy methamphetamine ',
    'MIT': ' the Massachusetts Institute of Technology ',
    'MLS': ' Major League Soccer ',
    'MPC': ' marksman performance choice ',
    'MRI': ' magnetic resonance imaging ',
    'MTV': ' music television ',
    'NBA': ' National Basketball Association ',
    'NC': ' North Carolina ',
    'NCAA': ' National Collegiate Athletic Association ',
    'NHL': ' National Hockey League ',
    'NSA': ' National Security Agency ',
    'OA': ' O.A. ',
    'OB': ' O.B. ',
    'OC': ' O.C. ',
    'OCD': ' obsessive compulsive disorder ',
    'OT': ' overtime ',
    'PG': ' point guard ',
    'PJ': ' P.J. ',
    'PR': ' public relations ',
    'PRBLMS': ' problems ',
    'PTSD': ' post traumatic stress disorder ',
    'PU': ' P.U. ',
    'RCA': ' Radio Corporation of America ',
    'REM': ' R.E.M. ',
    'RF': ' radio frequency ',
    'RIAA': ' Recording Industry Association of America ',
    'SF': ' S.F. ',
    'Shaq': ' Shaquille ',
    'shaq': ' shaquille ',
    'SMG': ' submachine gun ',
    'SS': ' S.S. ',
    'SUV': ' sport utility vehicle ',
    'TGIF': ' thank god it\'s friday ',
    'TR': ' T.R. ',
    'TRO': ' T.R.O. ',
    'TV': ' television ',
    'UCLA': ' University of California, Los Angeles ',
    'UD': ' Udonis Haslem ',
    'UK': ' United Kingdom ',
    'US': ' United States ',
    'USB': ' U.S.B. ',
    'USL': ' United Soccer League ',
    'VCR': ' video cassette recorder ',
    'VOL': ' volume ',
    'weeknd': ' weekend ',
    'Weeknd': ' Weekend ',
    'WGBS': ' West Georgia Broadcasting System ',
    'WWI': ' World War One ',
    'WWII': ' World War Two ',
    'XXL': ' extra extra large ',
    'YC': ' Wye Combinator ',
    'YG': ' Young Gangsta ',
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
