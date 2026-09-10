# evaluate_hybrid.py
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_THIS_DIR))          # sibling import: evaluate_retrieval
sys.path.insert(0, str(_THIS_DIR.parent))   # project root: src.*

from evaluate_retrieval import TEST_QUESTIONS
from src.retrieval.hybrid_search import hybrid_retrieve


def run_evaluation():
    top1_correct = 0
    top3_correct = 0
    total = len(TEST_QUESTIONS)

    print(f"Running hybrid evaluation on {total} questions...\n")

    for item in TEST_QUESTIONS:
        question = item["question"]
        expected = item["expected_article"]

        chunks = hybrid_retrieve(question, n_results=5)
        found_articles = [c["article"] for c in chunks]

        is_top1 = bool(found_articles) and found_articles[0] == expected
        is_top3 = expected in found_articles[:3]

        if is_top1:
            top1_correct += 1
        if is_top3:
            top3_correct += 1

        status = "OK (top1)" if is_top1 else ("OK (top3)" if is_top3 else "MISS")
        print(f"[{status}] {question}")
        print(f"   Attendu: {expected} | Trouvé: {found_articles[:3]}")
        print()

    print("=" * 60)
    print(f"Précision au rang 1 : {top1_correct}/{total} ({100 * top1_correct / total:.0f}%)")
    print(f"Précision au rang 3 : {top3_correct}/{total} ({100 * top3_correct / total:.0f}%)")


if __name__ == "__main__":
    run_evaluation()
