import argparse
import glob
import os
import re

import whisper

from scripts.file_utils import has_subdirectories

parser = argparse.ArgumentParser()
parser.add_argument('--audio', type=str, help='A dir containing the result audio to qa test.', default=None)

def check_texts_approx_match(gt_text, stt_text):
    gt_tokens = [t for t in gt_text.split() if bool(re.search(r'[a-zA-Z0-9]', t))]
    stt_tokens = [t for t in stt_text.split() if bool(re.search(r'[a-zA-Z0-9]', t))]
    if len(stt_tokens) - len(gt_tokens) > 1 and sum([len(t) for t in stt_tokens]) - sum([len(t) for t in gt_tokens]) > 6:
        return False
    return True


if __name__ == '__main__':
    args = parser.parse_args()
    leaf_dirs = [d for d, _, _ in os.walk(args.audio) if os.path.isdir(d) and not has_subdirectories(d)]

    if leaf_dirs:
        model = whisper.load_model("large-v2")

        for leaf_dir in leaf_dirs:
            if os.path.exists(os.path.join(leaf_dir, 'fails')):
                print(f"Skipping {leaf_dir}")
                continue

            print(f"Testing {leaf_dir}")
            incorrect = {}

            wav_paths = glob.glob(os.path.join(leaf_dir, "*.wav"))
            for wav_path in wav_paths:
                section_num = wav_path.split('/')[-1].rstrip('.wav')
                txt_path = os.path.join(leaf_dir, f"{section_num}.txt")
                if not os.path.exists(txt_path):
                    continue
                print(wav_path)

                with open(txt_path, "r") as f:
                    gt_text = f.read().strip()
                result = model.transcribe(wav_path)
                stt_text = result['text'].strip()
                if not check_texts_approx_match(gt_text, stt_text):
                    print('Mismatch')
                    incorrect[section_num] = (gt_text, stt_text)

                with open(os.path.join(leaf_dir, f'{section_num}.timestamps'), "w") as f:
                    for segment in result['segments']:
                        f.write(f"{segment['start']}-{segment['end']}: {segment['text']}\n")

            if incorrect:
                with open(os.path.join(leaf_dir, "fails"), "w") as f:
                    f.write(','.join(incorrect.keys()) + '\n')
                    for k, (gt, stt) in incorrect.items():
                        f.write(f'{k}:\n{gt}\n{stt}\n')
