# src/generation/llm_client.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SYSTEM_PROMPT = """Tu es un assistant juridique spécialisé dans les marchés publics au Maroc.
Réponds UNIQUEMENT à partir des extraits de texte juridique fournis ci-dessous.
Si les extraits ne permettent pas de répondre, dis-le clairement plutôt que d'inventer.
Cite systématiquement l'article et le document source de chaque affirmation,
au format : (Article X, [nom du document])."""


def build_prompt(question, retrieved_chunks, language="Français"):
    """
    Builds the final prompt sent to the LLM, combining the user's question
    with the retrieved legal excerpts and their sources.
    """
    context_parts = []
    for chunk in retrieved_chunks:
        source = f"{chunk['document']} ({chunk['document_type']})"
        article = chunk['article']
        text = chunk['text']
        context_parts.append(f"[{article} - {source}]\n{text}")

    context = "\n\n---\n\n".join(context_parts)

    closing_instruction = (
        "Réponds en citant précisément l'article et le document source pour chaque affirmation."
        if language == "Français"
        else "Answer in English, citing the precise article and source document for each statement."
    )

    return f"""Extraits juridiques disponibles :

{context}

---

Question de l'utilisateur : {question}

{closing_instruction}"""

def generate_answer(question, retrieved_chunks, model="gpt-4o-mini", language="Français"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = build_prompt(question, retrieved_chunks, language)

    language_instruction = (
        "Réponds en français." if language == "Français"
        else "Answer in English, even though the source texts are in French."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + language_instruction},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content