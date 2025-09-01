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
SOURCES_PATH = os.path.join(DATA_DIR, "sources.json")
os.makedirs(DATA_DIR, exist_ok=True)

TOP_K = 8
CHUNK_SIZE = 1200

# Limit sources for stability during testing
DEFAULT_SOURCES = [
    {"name": "Met Office — UK Warnings", "url": "https://www.metoffice.gov.uk/weather/warnings-and-advice/uk-warnings"},
    # {"name": "Met Office — UK Forecast", "url": "https://www.metoffice.gov.uk/weather/forecast/uk"},
    # {"name": "Met Office — Climate (UK)", "url": "https://www.metoffice.gov.uk/research/climate/maps-and-data"},
    # {"name": "MWIS — Mountain Weather (UK)", "url": "https://www.mwis.org.uk/forecasts"},
    # {"name": "Environment Agency — Flood Warnings", "url": "https://check-for-flooding.service.gov.uk/alerts-and-warnings"},
    # {"name": "BBC Weather — Weather News", "url": "https://www.bbc.co.uk/weather/features"},
]

def load_sources():
    if os.path.exists(SOURCES_PATH):
        with open(SOURCES_PATH) as f:
            return json.load(f)
    return DEFAULT_SOURCES

def save_sources(sources):
    with open(SOURCES_PATH, "w") as f:
        json.dump(sources, f, indent=2)

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
        try:
            page = fetch_page(src["url"])
            for i, chunk in enumerate(chunk_text(page["text"])):
                docs.append({
                    "source_name": src["name"],
                    "url": src["url"],
                    "title": page["title"],
                    "chunk_id": i,
                    "chunk_text": chunk
                })
        except Exception as e:
            docs.append({
                "source_name": src["name"],
                "url": src["url"],
                "title": src["name"],
                "chunk_id": 0,
                "chunk_text": f"Error fetching: {e}"
            })
    if not docs:
        raise RuntimeError("No documents indexed. Check your sources or network connection.")
    vectorizer = TfidfVectorizer().fit([doc["chunk_text"] for doc in docs])
    X = vectorizer.transform([doc["chunk_text"] for doc in docs])
    for i, doc in enumerate(docs):
        doc["embedding"] = X[i].toarray()[0].tolist()
    with open(INDEX_PATH, "w") as f:
        json.dump(docs, f)
    return docs, vectorizer

def load_index():
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH) as f:
            docs = json.load(f)
        vectorizer = TfidfVectorizer().fit([doc["chunk_text"] for doc in docs])
        return docs, vectorizer
    return None, None

def search_index(docs, vectorizer, query, k=TOP_K):
    q_vec = vectorizer.transform([query]).toarray()
    doc_vecs = [doc["embedding"] for doc in docs]
    sims = cosine_similarity(q_vec, doc_vecs)[0]
    top_idx = sims.argsort()[-k:][::-1]
    return [docs[i] for i in top_idx]

def answer_with_rag(query, hits):
    context = "\n\n".join([f"[Source {i+1}] {hit['title']} ({hit['url']})\n---\n{hit['chunk_text'][:300]}" for i, hit in enumerate(hits)])
    prompt = (
        "You are a UK weather assistant. Answer strictly based on the provided sources. "
        "When uncertain, say so. Cite sources inline as [Source N] with the given numbering. "
        "Keep answers concise and practical. Include dates and locations when mentioned.\n\n"
        f"Question: {query}\n\nSources:\n{context}"
    )
    return f"(Demo) Would answer: {query}\n\n{context[:500]}..."

app_ui = ui.page_fluid(
    ui.h2("UK Weather Q&A (RAG, Local Demo)"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_text("src_name", "Source name", "Custom Source"),
            ui.input_text("src_url", "Source URL", "https://"),
            ui.input_action_button("add_source", "Add Source"),
            ui.hr(),
            ui.input_action_button("rebuild", "Refresh / Rebuild Index"),
            ui.hr(),
            ui.output_table("sources_tbl"),
        ),
        ui.div(
            ui.output_ui("status"),
            ui.input_text_area("question", "Ask about UK weather:", rows=3, placeholder="e.g., What's the latest severe weather warning for Scotland today?"),
            ui.input_action_button("ask", "Ask"),
            ui.output_ui("answer"),
            ui.hr(),
            ui.h4("Top Sources Used"),
            ui.output_table("hits"),
        )
    )
)

def server(input: Inputs, output: Outputs, session: Session):
    sources = reactive.value(load_sources())
    docs = reactive.value([])
    vectorizer = reactive.value(None)
    status_msg = reactive.value("")

    @reactive.effect
    def _():
        output.sources_tbl = render.table(lambda: pd.DataFrame(sources()))

    @reactive.effect
    def _():
        if os.path.exists(INDEX_PATH):
            d, v = load_index()
            docs.set(d)
            vectorizer.set(v)

    @input.add_source.click
    def _():
        s = sources()
        s.append({"name": input.src_name(), "url": input.src_url()})
        save_sources(s)
        sources.set(s)
        status_msg.set("Source added. Click 'Refresh / Rebuild Index' to update.")

    @input.rebuild.click
    def _():
        output.status = render.ui(lambda: "Building index, please wait...")
        try:
            d, v = build_index(sources())
            docs.set(d)
            vectorizer.set(v)
            status_msg.set("Index built successfully.")
        except Exception as e:
            status_msg.set(f"Error building index: {e}")
        output.status = render.ui(lambda: status_msg())

    @input.ask.click
    def _():
        if not docs() or not vectorizer():
            output.status = render.ui(lambda: "Building index, please wait...")
            try:
                d, v = build_index(sources())
                docs.set(d)
                vectorizer.set(v)
                status_msg.set("Index built successfully.")
            except Exception as e:
                status_msg.set(f"Error building index: {e}")
                output.status = render.ui(lambda: status_msg())
                return
        hits = search_index(docs(), vectorizer(), input.question())
        output.hits = render.table(lambda: pd.DataFrame([{
            "rank": i+1,
            "title": hit["title"][:80],
            "url": hit["url"]
        } for i, hit in enumerate(hits)]))
        output.answer = render.ui(lambda: answer_with_rag(input.question(), hits))
        output.status = render.ui(lambda: status_msg())

app = App(app_ui, server)