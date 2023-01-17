import argparse
import glob
import os
import re

import whisper

from .file_utils import has_subdirectories


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', type=str, help='A dir containing the result audio to qa test.', default=None)

    args = parser.parse_args()
    leaf_dirs = [d for d, _, _ in os.walk(args.dir) if os.path.isdir(d) and not has_subdirectories(d)]

    if leaf_dirs:
        model = whisper.load_model("large-v2")

        for leaf_dir in leaf_dirs:
            print(f"Testing {leaf_dir}")
            incorrect = {}

            wav_paths = glob.glob(os.path.join(leaf_dir, "*.wav"))
            for wav_path in wav_paths:
                txt_path = wav_path.rstrip(".wav") + ".txt"
                if not os.path.exists(txt_path):
                    continue
                print(wav_path)

                with open(txt_path, "r") as f:
                    gt_text = f.read().strip()
                stt_text = model.transcribe(wav_path)["text"].strip()
                gt_tokens = [t for t in gt_text.split() if bool(re.search(r'[a-zA-Z0-9]', t))]
                stt_tokens = [t for t in stt_text.split() if bool(re.search(r'[a-zA-Z0-9]', t))]
                if len(stt_tokens) - len(gt_tokens) > 1 and sum([len(t) for t in stt_tokens]) - sum([len(t) for t in gt_tokens]) > 6:
                    print('Mismatch')
                    incorrect[wav_path.split('/')[-1].rstrip('.wav')] = (gt_text, stt_text)

            if incorrect:
                with open(os.path.join(leaf_dir, "failed"), "w") as f:
                    f.write(','.join(incorrect.keys()) + '\n')
                    for k, (gt, stt) in incorrect.items():
                        f.write(f'{k}:\n{gt}\n{stt}\n')
