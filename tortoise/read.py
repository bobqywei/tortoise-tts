import argparse
import glob
import os
import re
from time import time

import torch
import torchaudio
import whisper

from api import TextToSpeech, MODELS_DIR
from utils.audio import load_audio, load_voices
from utils.text import split_and_recombine_text


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--textfile', type=str, help='A file containing the text to read.', default="tortoise/data/riding_hood.txt")
    parser.add_argument('--textdir', type=str, help='A dir containing the texts to read.', default=None)
    parser.add_argument('--voice', type=str, help='Selects the voice to use for generation. See options in voices/ directory (and add your own!) '
                                                 'Use the & character to join two voices together. Use a comma to perform inference on multiple voices.', default='pat')
    parser.add_argument('--outdir', type=str, help='Where to store outputs.', default='results/')
    parser.add_argument('--preset', type=str, help='Which voice preset to use.', default='standard')
    parser.add_argument('--regenerate', type=str, help='Comma-separated list of clip numbers to re-generate, or nothing.', default=None)
    parser.add_argument('--candidates', type=int, help='How many output candidates to produce per-voice. Only the first candidate is actually used in the final product, the others can be used manually.', default=1)
    parser.add_argument('--batch_size', type=int, help='Batch size to use.', default=16)
    parser.add_argument('--model_dir', type=str, help='Where to find pretrained model checkpoints. Tortoise automatically downloads these to .models, so this'
                                                      'should only be specified if you have custom checkpoints.', default=MODELS_DIR)
    parser.add_argument('--seed', type=int, help='Random seed which can be used to reproduce results.', default=None)
    parser.add_argument('--produce_debug_state', type=bool, help='Whether or not to produce debug_state.pth, which can aid in reproducing problems. Defaults to true.', default=True)
    parser.add_argument('--fix', type=bool, help='Enable failure fixing mode.', default=False)

    args = parser.parse_args()
    regenerate = args.regenerate
    tts = TextToSpeech(models_dir=args.model_dir, autoregressive_batch_size=args.batch_size)
    stt = whisper.load_model("large-v2")
    seed = int(time()) if args.seed is None else args.seed

    if args.textdir is not None:
        textfiles = glob.glob(os.path.join(args.textdir, '*.txt'))
    else:
        textfiles = [args.textfile]
        if regenerate is not None:
            regenerate = [int(e) for e in regenerate.split(',')]
    selected_voices = args.voice.split(',')

    for textfile in textfiles:
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
            outdir = os.path.join(args.outdir, selected_voice, filename)

            if args.fix and os.path.isdir(outdir):
                fail_path = os.path.join(outdir, 'fails')
                if os.path.exists(fail_path):
                    with open(fail_path, 'r') as f:
                        line = f.readline().strip()
                        if line != '':
                            regenerate = [int(e) for e in line.split(',')]
                
            # Skip if already generated and not regenerating
            if regenerate is None and os.path.isdir(outdir):
                continue
            os.makedirs(outdir, exist_ok=True)

            # Track if clips failed speech-to-text test
            failed = {}

            if '&' in selected_voice:
                voice_sel = selected_voice.split('&')
            else:
                voice_sel = [selected_voice]

            voice_samples, conditioning_latents = load_voices(voice_sel)

            all_parts = []
            for j, text in enumerate(texts):

                # Write text clip to file to match audio clips
                with open(os.path.join(outdir, f'{j}.txt'), 'w') as f:
                    f.write(text)

                print(f'\nGenerating clip for {filename} {j}/{len(texts)}: {text}')
                # Directly load audio if already generated and we are not regenerating this clip
                if regenerate is not None and j not in regenerate:
                    audio_path = os.path.join(outdir, f'{j}.wav')
                    if os.path.exists(audio_path):
                        all_parts.append(load_audio(audio_path, 24000))
                        continue

                wav_path = os.path.join(outdir, f'{j}.wav')
                if args.candidates == 1:
                    gen = tts.tts_with_preset(text, voice_samples=voice_samples, conditioning_latents=conditioning_latents,
                                            preset=args.preset, k=args.candidates, use_deterministic_seed=seed)
                    gen = gen.squeeze(0).cpu()
                    torchaudio.save(wav_path, gen, 24000)

                else:
                    gen = tts.tts_with_preset(text, voice_samples=voice_samples, conditioning_latents=conditioning_latents,
                                            preset=args.preset, k=args.candidates, use_deterministic_seed=seed)
                    passed = False
                    for k, g in enumerate(gen):
                        gen = g.squeeze(0).cpu()
                        torchaudio.save(wav_path, gen, 24000)

                        # Transcribe speech to text and compare to ground truth
                        stt_text = stt.transcribe(wav_path)['text'].strip()
                        gt_tokens = [t for t in text.split() if bool(re.search(r'[a-zA-Z0-9]', t))]
                        stt_tokens = [t for t in stt_text.split() if bool(re.search(r'[a-zA-Z0-9]', t))]
                        if len(stt_tokens) - len(gt_tokens) <= 1 or sum([len(t) for t in stt_tokens]) - sum([len(t) for t in gt_tokens]) <= 6:
                            passed = True
                            break
                    if not passed:
                        failed[str(j)] = (text, stt_text)

                all_parts.append(gen)

            # Save the clip ids that failed speech-to-text test
            with open(os.path.join(outdir, 'fails'), 'w') as f:
                if len(failed) > 0:
                    f.write(','.join(failed.keys()) + '\n')
                    for i, (gt_text, stt_text) in failed.items():
                        f.write(f'{i}:\n{gt_text}\n{stt_text}\n')

            full_audio = torch.cat(all_parts, dim=-1)
            torchaudio.save(os.path.join(outdir, 'combined.wav'), full_audio, 24000)

            if args.produce_debug_state:
                os.makedirs('debug_states', exist_ok=True)
                dbg_state = (seed, texts, voice_samples, conditioning_latents)
                torch.save(dbg_state, f'debug_states/read_debug_{selected_voice}.pth')
