import os
import glob
import argparse
import shutil
from typing import List

parser = argparse.ArgumentParser()
parser.add_argument('--text', type=str, help='A dir containing the text', default=None)
parser.add_argument('--audio', type=str, help='A dir containing the audio', default=None)


def has_subdirectories(directory_path):
    for _, dirs, _ in os.walk(directory_path):
        if dirs:
            return True
    return False


def get_leaf_files(directory: str) -> List[str]:
    paths = []
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            paths += get_leaf_files(item_path)
        else:
            paths.append(item_path)
    return paths


def move_file(src_path, dest_path):
    dest_dir = os.path.dirname(dest_path)
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    shutil.move(src_path, dest_path)


def delete_if_empty(dir_path):
    if os.path.isdir(dir_path):
        if not os.listdir(dir_path):
            os.rmdir(dir_path)
            print(f"{dir_path} deleted.")
        else:
            print(f"{dir_path} is not empty.")
    else:
        print(f"{dir_path} is not a directory.")


if __name__ == '__main__':
    args = parser.parse_args()
    textfiles = glob.glob(os.path.join(args.text, '*.txt'))

    for path in textfiles:
        fn = os.path.basename(path).split('---')[0]
        suffix = os.path.basename(path).split('---')[-1].rstrip('.txt')
        leaf_paths = get_leaf_files(os.path.join(args.audio))
        for leaf_path in leaf_paths:
            if fn in leaf_path:
                leaf_tokens = leaf_path.split('/')
                if leaf_tokens[-2].startswith(fn):
                    leaf_tokens[-2] = f'{fn}---{suffix}'
                    move_file(leaf_path, os.path.join(*leaf_tokens))
                    delete_if_empty(os.path.dirname(leaf_path))
