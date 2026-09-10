# app.py
import streamlit as st
import chromadb
from sentence_transformers import SentenceTransformer
from src.generation.llm_client import generate_answer
from src.retrieval.hybrid_search import build_bm25_index, hybrid_retrieve_with_resources

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "marches_publics"
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


@st.cache_resource
def load_embedding_model():
    """Loaded once and cached across reruns/users, not on every question."""
    return SentenceTransformer(EMBEDDING_MODEL)


@st.cache_resource
def load_collection():
    """ChromaDB connection, also cached to avoid reopening on every question."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(COLLECTION_NAME)


@st.cache_resource
def load_bm25_index():
    """BM25 index over the collection's chunks, built once and cached like the other resources."""
    return build_bm25_index(load_collection())


def retrieve(question, n_results=3):
    model = load_embedding_model()
    collection = load_collection()
    bm25_index = load_bm25_index()
    return hybrid_retrieve_with_resources(question, model, collection, bm25_index, n_results=n_results)


# --- Interface ---

st.set_page_config(page_title="RAG Marchés Publics", page_icon="⚖️", layout="centered")

st.title(" Assistant Marchés Publics")
st.caption(
    "Système de question-réponse sur les textes juridiques relatifs aux marchés "
    "publics au Maroc (Décret 2-22-431, CCAG-EMO)."
)

question = st.text_input(
    "Pose ta question",
    placeholder="Ex : Quel est le délai de publication d'un avis d'appel d'offres ?"
)

language = st.radio("Langue de la réponse", ["Français", "English"], horizontal=True)

if st.button("Rechercher", type="primary") and question:
    with st.spinner("Recherche dans les textes juridiques..."):
        chunks = retrieve(question)

    with st.spinner("Génération de la réponse..."):
        answer = generate_answer(question, chunks, language=language)

    st.markdown("### Réponse")
    st.write(answer)

    with st.expander("Voir les articles source utilisés"):
        for c in chunks:
            st.markdown(f"**{c['article']}** — *{c['document']} ({c['document_type']})*")
            st.caption(c["text"][:300] + "...")
            st.divider()

st.caption(
    "⚠️ Réponses générées automatiquement à partir des textes indexés. "
    "À vérifier auprès des textes officiels pour toute décision engageante."
)