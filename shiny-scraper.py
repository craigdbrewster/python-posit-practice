from shiny import App, ui, render, reactive
import requests
from bs4 import BeautifulSoup
from keybert import KeyBERT
import re

kw_model = KeyBERT()

app_ui = ui.page_fluid(
    ui.h2("Webpage Word Scraper"),
    ui.input_text("url", "Enter URL to scrape:", placeholder="https://www.gov.uk/"),
    ui.input_action_button("scrape", "Scrape page"),
    ui.input_text_area("words", "Scraped Words", value="", rows=10, width="100%"),
    ui.input_text_area("themes", "Common Themes / Keywords (KeyBERT)", value="", rows=4, width="100%"),
    ui.input_text("wordcount", "Total Word Count", value="", width="30%")
)

def get_page_words(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        texts = soup.stripped_strings
        words = " ".join(texts)
        return words
    except Exception as e:
        return f"Error: {e}"

def extract_themes(text, top_n=5):
    keywords = kw_model.extract_keywords(text, top_n=top_n, stop_words="english")
    return ", ".join([kw for kw, _ in keywords])

def count_words(text):
    return len(re.findall(r'\b\w+\b', text))

def server(input, output, session):
    @reactive.effect
    @reactive.event(input.scrape)
    def _():
        url = input.url()
        if url:
            words = get_page_words(url)
            if words.startswith("Error:"):
                ui.update_text_area("words", value=words)
                ui.update_text_area("themes", value="")
                ui.update_text("wordcount", value="")
            else:
                ui.update_text_area("words", value=words)
                themes = extract_themes(words)
                ui.update_text_area("themes", value=themes)
                wc = count_words(words)
                ui.update_text("wordcount", value=str(wc))
        else:
            ui.update_text_area("words", value="Please enter a URL.")
            ui.update_text_area("themes", value="")
            ui.update_text("wordcount", value="")

app = App(app_ui, server)
