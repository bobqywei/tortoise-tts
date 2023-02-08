import os
import argparse
from typing import List

parser = argparse.ArgumentParser()
parser.add_argument('--audio', type=str, help='Audio data dir.', default=None)


def get_leaf_files(directory: str) -> List[str]:
    paths = []
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            paths += get_leaf_files(item_path)
        else:
            paths.append(item_path)
    return paths


if __name__ == '__main__':
    args = parser.parse_args()
    paths = [p for p in get_leaf_files(args.audio) if p.endswith('combined.wav')]
    with open(os.path.join(args.audio, 'generated.txt'), 'w') as f:
        for p in paths:
            path = p.replace(args.audio, '')
            f.write(path + '\n')

