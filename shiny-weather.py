import os
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup
from shiny import App, ui, render, reactive, Inputs, Outputs, Session
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "index.json")
os.makedirs(DATA_DIR, exist_ok=True)

TOP_K = 5
CHUNK_SIZE = 1200

DEFAULT_SOURCES = [
    {
        "name": "Wikipedia - Climate of the United Kingdom",
        "url": "https://en.wikipedia.org/wiki/Climate_of_the_United_Kingdom"
    }
]

def fetch_page(url):
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string if soup.title else url
        main = soup.find("main") or soup.find("article") or soup.body
        text = main.get_text(separator="\n") if main else soup.get_text(separator="\n")
        return {"url": url, "title": title, "text": text}
    except Exception as e:
        return {"url": url, "title": url, "text": f"Error fetching: {e}"}

def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def build_index(sources):
    docs = []
    for src in sources:
        page = fetch_page(src["url"])
        for i, chunk in enumerate(chunk_text(page["text"])):
            docs.append({
                "source_name": src["name"],
                "url": src["url"],
                "title": page["title"],
                "chunk_id": i,
                "chunk_text": chunk
            })
    vectorizer = TfidfVectorizer().fit([doc["chunk_text"] for doc in docs])
    X = vectorizer.transform([doc["chunk_text"] for doc in docs])
    embeddings = X.toarray()
    with open(INDEX_PATH, "w") as f:
        json.dump(docs, f)
    return docs, vectorizer, embeddings

def search_index(docs, embeddings, vectorizer, query, k=TOP_K):
    q_vec = vectorizer.transform([query]).toarray()
    sims = cosine_similarity(q_vec, embeddings)[0]
    top_idx = sims.argsort()[-k:][::-1]
    return [docs[i] for i in top_idx]

def answer_with_rag(query, hits):
    context = "\n\n".join([f"[Source {i+1}] {hit['title']} ({hit['url']})\n---\n{hit['chunk_text'][:300]}" for i, hit in enumerate(hits)])
    return f"(Demo) Would answer: {query}\n\n{context[:500]}..."

# --- UI ---
app_ui = ui.page_fluid(
    ui.h2("UK Weather Q&A (RAG, Local Demo)"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_action_button("rebuild", "Rebuild Index"),
            ui.hr(),
            ui.output_table("sources_tbl"),
        ),
        ui.div(
            ui.output_ui("status"),
            ui.input_text_area("question", "Ask about UK weather:", rows=3, placeholder="e.g., What is the climate like in Scotland?"),
            ui.input_action_button("ask", "Ask"),
            ui.output_ui("answer"),
            ui.hr(),
            ui.h4("Top Sources Used"),
            ui.output_table("hits"),
        )
    )
)

# --- Server ---
def server(input: Inputs, output: Outputs, session: Session):
    sources = reactive.value(DEFAULT_SOURCES)
    docs = reactive.value([])
    vectorizer = reactive.value(None)
    embeddings = reactive.value(None)
    status_msg = reactive.value("Index ready.")

    @reactive.effect
    def _():
        output.sources_tbl = render.table(lambda: pd.DataFrame(sources()))

    @input.rebuild.click
    def _():
        output.status = render.ui(lambda: "Building index, please wait...")
        try:
            d, v, e = build_index(sources())
            docs.set(d)
            vectorizer.set(v)
            embeddings.set(e)
            status_msg.set("Index rebuilt successfully.")
        except Exception as ex:
            status_msg.set(f"Error building index: {ex}")
        output.status = render.ui(lambda: status_msg())

    @input.ask.click
    def _():
        if not docs() or vectorizer() is None or embeddings() is None:
            output.status = render.ui(lambda: "Index not ready. Please rebuild.")
            return
        hits = search_index(docs(), embeddings(), vectorizer(), input.question())
        output.hits = render.table(lambda: pd.DataFrame([{
            "rank": i+1,
            "title": hit["title"][:80],
            "url": hit["url"]
        } for i, hit in enumerate(hits)]))
        output.answer = render.ui(lambda: answer_with_rag(input.question(), hits))
        output.status = render.ui(lambda: status_msg())

app = App(app_ui, server)