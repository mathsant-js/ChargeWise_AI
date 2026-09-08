import os
import json
import time
import sys, os; sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from chatbot import GoodWeChatbot
from tiktoken import get_encoding

# Helper to count tokens (approximate, using tiktoken's cl100k_base)
encoding = get_encoding("cl100k_base")

def count_tokens(text: str) -> int:
    return len(encoding.encode(text))


def load_cases(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_case(case):
    bot = GoodWeChatbot()
    start = time.time()
    response = bot.responder(case["input"])
    elapsed = time.time() - start
    # simple intent detection via keyword search (lowercase)
    intent = case.get("expected_intent", "")
    found = intent.lower() in response.lower()
    # token count for the whole exchange (input + response)
    tokens = count_tokens(case["input"] + response)
    return {
        "session_id": case["session_id"],
        "input": case["input"],
        "expected_intent": intent,
        "response": response,
        "intent_found": found,
        "time_s": round(elapsed, 3),
        "tokens": tokens,
    }


def main():
    dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    results_path = os.path.join(os.path.dirname(__file__), "legacy_results.json")
    cases = load_cases(dataset_path)
    results = [evaluate_case(c) for c in cases]
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Evaluation completed – {len(results)} cases written to legacy_results.json")

if __name__ == "__main__":
    main()
