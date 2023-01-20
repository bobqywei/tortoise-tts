from collections import defaultdict
import os
import re
import argparse

from file_utils import get_leaf_files

parser = argparse.ArgumentParser()
parser.add_argument('--dir', type=str, help='Directory to trace for text files.', default=None)


if __name__ == '__main__':
    args = parser.parse_args()
    textfiles = [p for p in get_leaf_files(args.dir) if p.endswith('.txt')]
    abbrevs = defaultdict(list)
    for path in textfiles:
        filename = os.path.basename(path)
        with open(path, 'r') as f:
            text = f.read()
        matches = re.findall(r"\s+([A-Z]+\.*[A-Z]+)+(\.*[A-Z]\.*)*\b", text)
        for match in matches:
            abbrevs[''.join(match)].append(filename)
    with open('abbrevs.txt', 'w') as f:
        for k, v in sorted(abbrevs.items(), key=lambda x: x[0]):
            f.write(f"{k}: {','.join(v)}\n")
