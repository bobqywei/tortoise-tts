from collections import defaultdict
import os
import re
import argparse
from typing import Set

from file_utils import get_leaf_files

parser = argparse.ArgumentParser()
parser.add_argument('--dir', type=str, help='Directory to trace for text files.', default=None)

ENGLISH_WORDS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data/engmix.txt')


def get_english_words(path) -> Set[str]:
    with open(path, 'rb') as f:
        lines = f.readlines()
        words = set()
        for line in lines:
            word = line.decode('utf-8', 'ignore').strip()
            words.add(word)
        return words


if __name__ == '__main__':
    args = parser.parse_args()
    textfiles = [p for p in get_leaf_files(args.dir) if p.endswith('.txt')]
    english_words = get_english_words(ENGLISH_WORDS_PATH)
    abbrevs = defaultdict(list)
    for path in textfiles:
        filename = os.path.basename(path)
        with open(path, 'r') as f:
            text = f.read()
        matches = re.findall(r"\s+([A-Z]+\.*[A-Z]+)+(\.*[A-Z]\.*)*\b", text)
        for match in matches:
            potential_abbrev = ''.join(match)
            if potential_abbrev.lower() not in english_words:
                abbrevs[potential_abbrev].append(filename)
    with open('abbrevs.txt', 'w') as f:
        for k, v in sorted(abbrevs.items(), key=lambda x: x[0]):
            f.write(f"{k}: {','.join(v)}\n")
