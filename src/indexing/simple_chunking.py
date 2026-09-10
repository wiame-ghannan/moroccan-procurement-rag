# src/indexing/simple_chunking.py
import json
import glob
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

# Safety net: if a single article's text exceeds this many characters,
# it gets split further. Most articles are well under this limit.
MAX_CHUNK_CHARS = 2000


def load_articles_from_json(json_path):
    """Loads a single *_structure.json file produced by the parser."""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def load_all_articles(processed_folder="data/processed"):
    """Loads every *_structure.json file found in the processed folder."""
    all_articles = []
    for json_path in glob.glob(f"{processed_folder}/**/*_structure.json", recursive=True):
        articles = load_articles_from_json(json_path)
        all_articles.extend(articles)
    return all_articles


def article_to_nodes(article, splitter):
    """
    Converts a single parsed article into one or more TextNodes.
    Most articles become exactly one node; very long articles are
    split further while keeping the same metadata on every piece.
    """
    metadata = {k: v for k, v in article.items() if k != "text"}
    text = article["text"]

    if len(text) <= MAX_CHUNK_CHARS:
        return [TextNode(text=text, metadata=metadata)]

    # Long article: split into multiple sub-chunks, tagging each part
    sub_texts = splitter.split_text(text)
    nodes = []
    for i, sub_text in enumerate(sub_texts):
        sub_metadata = dict(metadata)
        sub_metadata["chunk_part"] = f"{i + 1}/{len(sub_texts)}"
        nodes.append(TextNode(text=sub_text, metadata=sub_metadata))
    return nodes


def build_nodes(processed_folder="data/processed"):
    """
    Main entry point: loads all parsed articles across every document
    and returns a flat list of TextNodes ready for embedding.
    """
    splitter = SentenceSplitter(chunk_size=MAX_CHUNK_CHARS, chunk_overlap=200)
    articles = load_all_articles(processed_folder)

    all_nodes = []
    for article in articles:
        nodes = article_to_nodes(article, splitter)
        all_nodes.extend(nodes)

    return all_nodes


if __name__ == "__main__":
    nodes = build_nodes()

    print(f"Total articles loaded: {len(load_all_articles())}")
    print(f"Total chunks (nodes) created: {len(nodes)}")

    # Show a breakdown by document to sanity-check
    by_document = {}
    for node in nodes:
        doc_name = node.metadata.get("document", "unknown")
        by_document[doc_name] = by_document.get(doc_name, 0) + 1

    print("\nChunks per document:")
    for doc_name, count in by_document.items():
        print(f"  - {doc_name}: {count} chunks")

    # Preview the first node to sanity-check content and metadata
    print("\n--- Preview of first node ---")
    print("Metadata:", nodes[0].metadata)
    print("Text (first 200 chars):", nodes[0].text[:200])