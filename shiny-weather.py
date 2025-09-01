import os
import json
import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from shiny import App, ui, render, reactive, Inputs, Outputs, Session
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# --- Config ---
DATA_DIR = "data"
INDEX_PATH = os.path.join(DATA_DIR, "index.json")
SOURCES_PATH = os.path.join(DATA_DIR, "sources.json")
os.makedirs(DATA_DIR, exist_ok=True)

TOP_K = 8
CHUNK_SIZE = 1200

# Default sources
DEFAULT_SOURCES = [
    {"name": "Met Office — UK Warnings", "url": "https://www.metoffice.gov.uk/weather/warnings-and-advice/uk-warnings"},
]

# --- Data handling ---
def load_sources():
    if os.path.exists(SOURCES_PATH):
        with open(SOURCES_PATH) as f:
            return json.load(f)
    return DEFAULT_SOURCES

def save_sources(sources):
    with open(SOURCES_PATH, "w") as f:
        json.dump(sources, f, indent=2)

async def fetch_page_async(session, url):
    try:
        async with session.get(url, timeout=8) as resp:
            text = await resp.text()
            soup = BeautifulSoup(text, "html.parser")
            title = soup.title.string if soup.title else url
            main = soup.find("main") or soup.find("article") or soup.body
            text = main.get_text(separator="\n") if main else soup.get_text(separator="\n")
            return {"url": url, "title": title, "text": text}
    except Exception as e:
        return {"url": url, "title": url, "text": f"Error fetching: {e}"}

def chunk_text(text, chunk_size=CHUNK_SIZE):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def search_index(docs, embeddings, vectorizer, query, k=TOP_K):
    q_vec = vectorizer.transform([query]).toarray()
    sims = cosine_similarity(q_vec, embeddings)[0]
    top_idx = sims.argsort()[-k:][::-1]
    return [docs[i] for i in top_idx]

def answer_with_rag(query, hits):
    context = "\n\n".join([f"[Source {i+1}] {hit['title']} ({hit['url']})\n---\n{hit['chunk_text'][:300]}" for i, hit in enumerate(hits)])
    return f"(Demo) Would answer: {query}\n\n{context[:500]}..."

# --- Globals ---
docs_global = []
vectorizer_global = None
embeddings_global = None
sources_global = load_sources()

# --- UI ---
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
            ui.output_ui("progress"),   # progress log
            ui.input_text_area("question", "Ask about UK weather:", rows=3, placeholder="e.g., What's the latest severe weather warning for Scotland today?"),
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
    global docs_global, vectorizer_global, embeddings_global, sources_global

    status_msg = reactive.value("Index ready.")
    sources = reactive.value(sources_global)
    progress_log = reactive.value([])

    def log(msg):
        logs = progress_log()
        logs.append(msg)
        progress_log.set(logs)
        reactive.flush()  # force live update

    @reactive.effect
    def _():
        output.sources_tbl = render.table(lambda: pd.DataFrame(sources()))

    @reactive.effect
    def _():
        output.progress = render.ui(lambda: ui.tags.ul([ui.tags.li(m) for m in progress_log()]))

    @input.add_source.click
    def _():
        s = sources()
        s.append({"name": input.src_name(), "url": input.src_url()})
        save_sources(s)
        sources.set(s)
        status_msg.set("Source added. Click 'Refresh / Rebuild Index' to update.")

    @input.rebuild.click
    def _():
        async def rebuild_with_progress():
            progress_log.set([])
            log("🔄 Starting rebuild...")
            docs = []
            async with aiohttp.ClientSession() as session_http:
                for i, src in enumerate(sources(), start=1):
                    log(f"Fetching {i}/{len(sources())}: {src['url']}")
                    page = await fetch_page_async(session_http, src["url"])
                    for j, chunk in enumerate(chunk_text(page["text"])):
                        docs.append({
                            "source_name": src["name"],
                            "url": src["url"],
                            "title": page["title"],
                            "chunk_id": j,
                            "chunk_text": chunk
                        })
                    log(f"✅ Done {i}/{len(sources())}: {src['url']}")
            return docs

        try:
            docs = asyncio.run(rebuild_with_progress())
            vectorizer = TfidfVectorizer().fit([doc["chunk_text"] for doc in docs])
            X = vectorizer.transform([doc["chunk_text"] for doc in docs])
            embeddings = X.toarray()

            with open(INDEX_PATH, "w") as f:
                json.dump(docs, f)

            docs_global, vectorizer_global, embeddings_global = docs, vectorizer, embeddings
            status_msg.set("Index rebuilt successfully.")
            log("🎉 Rebuild complete.")
        except Exception as e:
            status_msg.set("Rebuild failed. Using last good index.")
            log(f"❌ Rebuild failed: {e}")

    @input.ask.click
    def _():
        if not docs_global or vectorizer_global is None:
            output.status = render.ui(lambda: "Index not ready. Please rebuild.")
            return
        hits = search_index(docs_global, embeddings_global, vectorizer_global, input.question())
        output.hits = render.table(lambda: pd.DataFrame([{
            "rank": i+1,
            "title": hit["title"][:80],
            "url": hit["url"]
        } for i, hit in enumerate(hits)]))
        output.answer = render.ui(lambda: answer_with_rag(input.question(), hits))
        output.status = render.ui(lambda: status_msg())

# --- App ---
app = App(app_ui, server)
