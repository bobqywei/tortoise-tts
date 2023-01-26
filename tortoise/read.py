import argparse
from collections import defaultdict
import os
from time import time

import torch
import torchaudio
import whisper

from api import TextToSpeech, MODELS_DIR
from utils.audio import load_audio, load_voices
from utils.text import split_and_recombine_text
from scripts.stt import check_texts_approx_match
from scripts.file_utils import get_leaf_files

parser = argparse.ArgumentParser()
parser.add_argument('--textdir', type=str, help='A dir containing the texts to read.', default=None)
parser.add_argument('--voice', type=str, help='Selects the voice to use for generation. See options in voices/ directory (and add your own!) '
                                                'Use the & character to join two voices together. Use a comma to perform inference on multiple voices.', default='pat')
parser.add_argument('--outdir', type=str, help='Where to store outputs.', default='results/')
parser.add_argument('--candidates', type=int, help='How many output candidates to produce per-voice. Only the first candidate is actually used in the final product, the others can be used manually.', default=1)
parser.add_argument('--fix', help='Enable failure fixing mode.', default=False, action='store_true')
parser.add_argument('--qa', help='Enable QA with stt.', default=False, action='store_true')

# Optional
parser.add_argument('--textfile', type=str, help='A file containing the text to read.', default="tortoise/data/riding_hood.txt")
parser.add_argument('--batch_size', type=int, help='Batch size to use.', default=16)
parser.add_argument('--preset', type=str, help='Which voice preset to use.', default='standard')
parser.add_argument('--regenerate', type=str, help='Comma-separated list of clip numbers to re-generate, or nothing.', default=None)
parser.add_argument('--model_dir', type=str, help='Where to find pretrained model checkpoints. Tortoise automatically downloads these to .models, so this'
                                                    'should only be specified if you have custom checkpoints.', default=MODELS_DIR)
parser.add_argument('--seed', type=int, help='Random seed which can be used to reproduce results.', default=None)
parser.add_argument('--produce_debug_state', type=bool, help='Whether or not to produce debug_state.pth, which can aid in reproducing problems. Defaults to true.', default=True)


if __name__ == '__main__':
    args = parser.parse_args()
    regenerate = args.regenerate
    tts = TextToSpeech(models_dir=args.model_dir, autoregressive_batch_size=args.batch_size)
    seed = int(time()) if args.seed is None else args.seed
    selected_voices = args.voice.split(',')

    use_stt = args.qa or args.fix
    if use_stt:
        stt = whisper.load_model("large-v2")

    if args.textdir is not None:
        text_paths = [p for p in get_leaf_files(args.textdir) if p.endswith('.txt')]
        textdirs_to_files_map = defaultdict(list)
        for text_path in text_paths:
            textdirs_to_files_map[os.path.dirname(text_path)].append(text_path)
    else:
        textdirs_to_files_map = {os.path.dirname(args.textfile): [args.textfile]}
        if regenerate is not None:
            regenerate = [int(e) for e in regenerate.split(',')]
    total_num_files = sum([len(v) for v in textdirs_to_files_map.values()])

    text_index = 0
    for textdir, textfiles in textdirs_to_files_map.items():
        outdir = os.path.join(args.outdir, os.path.basename(textdir))

        for textfile in textfiles:
            text_index += 1
            filename = textfile.split('/')[-1].split('.')[0]

            # Process text
            with open(textfile, 'r', encoding='utf-8') as f:
                text = ' '.join([l for l in f.readlines()])
            if '|' in text:
                print("Found the '|' character in your text, which I will use as a cue for where to split it up. If this was not"
                    "your intent, please remove all '|' characters from the input.")
                texts = text.split('|')
            else:
                texts = split_and_recombine_text(text)

            for selected_voice in selected_voices:
                audio_dir = os.path.join(outdir, selected_voice, filename)

                # If we're in fix mode, check which clips failed and regenerate only those
                if args.fix and os.path.isdir(audio_dir):
                    fail_path = os.path.join(audio_dir, 'fails')
                    if os.path.exists(fail_path):
                        with open(fail_path, 'r') as f:
                            line = f.readline().strip()
                            if line:
                                regenerate = [int(e) for e in line.split(',')]
                elif not os.path.isdir(audio_dir):
                    os.makedirs(audio_dir, exist_ok=True)

                # Skip if we are not regenerating and combined audio exists
                if not regenerate and os.path.exists(os.path.join(audio_dir, 'combined.wav')):
                    continue

                # Get voice samples and voice conditioning latents
                if '&' in selected_voice:
                    voice_sel = selected_voice.split('&')
                else:
                    voice_sel = [selected_voice]
                voice_samples, conditioning_latents = load_voices(voice_sel)

                failed = {}
                all_parts = []
                for segment_index, text in enumerate(texts):
                    print(f'\n{text_index}/{total_num_files}: {filename}\n{segment_index + 1}/{len(texts)}: {text}\n{selected_voice}')

                    wav_path = os.path.join(audio_dir, f'{segment_index}.wav')
                    # Skip if we are not regenerating this clip and audio exists
                    if (not regenerate or segment_index not in regenerate) and os.path.exists(wav_path):
                        all_parts.append(load_audio(wav_path, 24000))
                        continue

                    # Write text clip to file to match audio clips
                    with open(os.path.join(audio_dir, f'{segment_index}.txt'), 'w') as f:
                        f.write(text)

                    generated = tts.tts_with_preset(text, voice_samples=voice_samples, conditioning_latents=conditioning_latents,
                                                    preset=args.preset, k=args.candidates, use_deterministic_seed=seed)
                    if args.candidates == 1:
                        generated = [generated]

                    passed = False
                    for g in generated:
                        gen = g.squeeze(0).cpu()
                        torchaudio.save(wav_path, gen, 24000)
                        if use_stt:
                            result = stt.transcribe(wav_path)
                            # Save the sentence timestamps
                            with open(os.path.join(audio_dir, f'{segment_index}.timestamps'), "w") as f:
                                for segment in result['segments']:
                                    f.write(f"{segment['start']}-{segment['end']}: {segment['text']}\n")
                            # QA with stt results
                            if check_texts_approx_match(text, result['text'].strip()):
                                passed = True
                                break

                    all_parts.append(gen)
                    if use_stt and not passed:
                        failed[str(segment_index)] = (text, result['text'].strip())

                # Save the clip ids that failed speech-to-text test
                if use_stt:
                    fail_path = os.path.join(audio_dir, 'fails')
                    if len(failed) > 0:
                        with open(fail_path, 'w') as f:
                            f.write(','.join(failed.keys()) + '\n')
                            for i, (gt_text, stt_text) in failed.items():
                                f.write(f'{i}:\n{gt_text}\n{stt_text}\n')
                    elif os.path.exists(fail_path):
                        os.remove(fail_path)

                full_audio = torch.cat(all_parts, dim=-1)
                torchaudio.save(os.path.join(audio_dir, 'combined.wav'), full_audio, 24000)

                if args.produce_debug_state:
                    os.makedirs('debug_states', exist_ok=True)
                    dbg_state = (seed, texts, voice_samples, conditioning_latents)
                    torch.save(dbg_state, f'debug_states/read_debug_{selected_voice}.pth')
