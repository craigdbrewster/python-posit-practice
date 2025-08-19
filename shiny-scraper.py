from shiny import App, ui, render, reactive
import requests
from bs4 import BeautifulSoup

app_ui = ui.page_fluid(
    ui.h2("Webpage Word Scraper"),
    ui.input_text("url", "Enter URL to scrape:", placeholder="https://www.gov.uk/"),
    ui.input_action_button("scrape", "Scrape page"),
    ui.input_text_area("words", "Scraped Words", value="", rows=15, width="100%")
)

def get_page_words(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts, styles, etc.
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        texts = soup.stripped_strings
        words = " ".join(texts)
        return words
    except Exception as e:
        return f"Error: {e}"

def server(input, output, session):
    @reactive.effect
    @reactive.event(input.scrape)
    def _():
        url = input.url()
        if url:
            words = get_page_words(url)
            ui.update_text_area("words", value=words)
        else:
            ui.update_text_area("words", value="Please enter a URL.")

app = App(app_ui, server)
