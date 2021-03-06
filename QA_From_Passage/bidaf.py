import os
import sys
import requests
import shutil
from typing import Dict, List, Tuple
import nltk
import numpy as np
from nltk import word_tokenize
from onnxruntime import InferenceSession
# nltk.download('punkt')

# pylint:disable=line-too-long
class BidafModelRuntime:
    def __init__(self, targets: List[str], queries: Dict[str, str], model_dir: str):
        self.queries = queries
        self.targets = targets
        bidaf_model = (model_dir+"bidaf-9.onnx")

        self.session = InferenceSession(bidaf_model)

        self.processed_queries = self._process_queries()


    @staticmethod
    def init_bidaf(bidaf_model_dir: str, download_ntlk_punkt: bool = False) -> bool:

        if not os.path.isdir(bidaf_model_dir):
            os.makedirs(bidaf_model_dir, exist_ok=True)



        # Download Punkt Sentence Tokenizer
        if download_ntlk_punkt:
            nltk.download("punkt", download_dir=bidaf_model_dir)
            nltk.download("punkt")

        # Download bidaf onnx model
        onnx_model_file = os.path.abspath(os.path.join(bidaf_model_dir, "bidaf.onnx"))


        if not os.path.isfile(onnx_model_file):
            response = requests.get(
                "https://onnxzoo.blob.core.windows.net/models/opset_9/bidaf/bidaf.onnx",
                stream=True,
            )
            with open(onnx_model_file, "wb") as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
        return True

    def serve(self, context: str) -> Dict[str, str]:

        BidafModelRuntime.init_bidaf('model/',False)
        result = {}
        cw, cc = BidafModelRuntime._preprocess(context)
        for target in self.targets:
            qw, qc = self.processed_queries[target]
            answer = self.session.run(
                ["start_pos", "end_pos"],
                {
                    "context_word": cw,
                    "context_char": cc,
                    "query_word": qw,
                    "query_char": qc,
                },
            )
            start = answer[0].item()
            end = answer[1].item()
            result_item = cw[start : end + 1]
            result[target] = BidafModelRuntime._convert_result(result_item)

        return result

    def _process_queries(self) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:

        result = {}
        for target in self.targets:
            question = self.queries[target]
            result[target] = BidafModelRuntime._preprocess(question)

        return result

    @staticmethod
    def _convert_result(result_item: np.ndarray) -> str:

        result = []
        for item in result_item:
            result.append(item[0])

        return " ".join(result)

    @staticmethod
    def _preprocess(text: str) -> Tuple[np.ndarray, np.ndarray]:

        tokens = word_tokenize(text)
        # split into lower-case word tokens, in numpy array with shape of (seq, 1)
        words = np.asarray([w.lower() for w in tokens]).reshape(-1, 1)
        # split words into chars, in numpy array with shape of (seq, 1, 1, 16)
        chars = [[c for c in t][:16] for t in tokens]
        chars = [cs + [""] * (16 - len(cs)) for cs in chars]
        chars = np.asarray(chars).reshape(-1, 1, 1, 16)
        return words, chars


