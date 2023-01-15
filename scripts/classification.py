from typing import Iterable, Sequence, Tuple

import argparse
import glob
import os

import numpy as np
import torch
import transformers

PAUL_GRAHAM_CATEGORIES = {
    "business": ["economics", "finance", "startups", "businesses"],
    "politics": ["politics"],
    "philosophy": ["philosophy", "life advice"],
    "technology": ["computer programming", "coding", "software", "information technology"],
    "religion": ["religion"],
    "communication": ["communication skills"],
}


def has_subdirectories(directory_path):
    for _, dirs, _ in os.walk(directory_path):
        if dirs:
            return True
    return False


class TextClassifier:
    def __init__(
        self,
        labels: Iterable[str],
        model_name: str = "facebook/bart-large-mnli",
        device: torch.device = torch.device("cpu"),
    ):
        self._device = device
        self._labels = labels
        self._model = transformers.pipeline(
            task='zero-shot-classification', model=model_name, device=device)

    @property
    def labels(self):
        return self._labels

    def classify(self, text: str) -> Sequence[Tuple[str, float]]:
        return self._model(text, candidate_labels=self._labels)


class TextSummarizer:
    def __init__(self, model_name: str = "facebook/bart-large-cnn", device: torch.device = torch.device("cpu")):
        self._device = device
        self._model = transformers.pipeline(task='summarization', model=model_name, device=device, framework='pt')

    def summarize(self, text: str) -> str:
        return self._model(text, min_length=30, max_length=130)[0]['summary_text']


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', type=str, help='A dir containing the result audio to qa test.', default=None)
    args = parser.parse_args()

    flat_labels = [value for values in PAUL_GRAHAM_CATEGORIES.values() for value in values]

    leaf_dirs = [d for d, _, _ in os.walk(args.dir) if os.path.isdir(d) and not has_subdirectories(d)]

    if leaf_dirs:
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        classifier = TextClassifier(flat_labels, device=device)
        summarizer = TextSummarizer(device=device)

        for leaf_dir in leaf_dirs:
            text_paths = glob.glob(os.path.join(leaf_dir, "*.txt"))
            for text_path in text_paths:
                print("classifying", text_path)
                with open(text_path, "r") as f:
                    text = ' '.join(f.read().strip().split()[-500:])
                text = summarizer.summarize(text)
                result = classifier.classify(text)

                labels = (result['labels'])
                scores = (result['scores'])
                top_label = labels[0]
                top_category = None
                for k, v in PAUL_GRAHAM_CATEGORIES.items():
                    if top_label in v:
                        top_category = k
                        break

                filename = os.path.basename(text_path).rstrip(".txt").split('---')[0]
                os.rename(text_path, os.path.join(leaf_dir, f"{filename}---{top_category}.txt"))
