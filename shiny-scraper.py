from shiny import App, ui, render, reactive
import requests
from bs4 import BeautifulSoup
from keybert import KeyBERT
import re

def read_html_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<!-- Error loading {filename}: {e} -->"

HEADER_HTML_FILE = "includes/gds-header.html"
WRAPPER_START_HTML_FILE = "includes/gds-wrapper-start.html"
WRAPPER_END_HTML_FILE = "includes/gds-wrapper-end.html"

header_html = read_html_file(HEADER_HTML_FILE)
wrapper_start_html = read_html_file(WRAPPER_START_HTML_FILE)
wrapper_end_html = read_html_file(WRAPPER_END_HTML_FILE)

kw_model = KeyBERT()

def clean_sentence(sentence):
    s = sentence.strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) < 30: return None
    if re.search(r"(Attribution|Live|Watch:|Comments \d{3,}|BBC Verify|click here|More on)", s, re.IGNORECASE):
        return None
    return s

def find_representative_sentence(text, keyword):
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
    candidates = []
    for s in sentences:
        if re.search(r'\b' + re.escape(keyword) + r'\b', s, re.IGNORECASE):
            cleaned = clean_sentence(s)
            if cleaned:
                candidates.append(cleaned)
    if candidates:
        return min(candidates, key=len)
    return f"This page covers the theme '{keyword}'."

def extract_themes(text, top_n=5):
    keywords = kw_model.extract_keywords(text, top_n=top_n, stop_words="english")
    if not keywords:
        return "No major themes detected."
    conversational = []
    for kw, _ in keywords:
        sent = find_representative_sentence(text, kw)
        conversational.append(f"**Theme: {kw}**\n{sent}")
    return "\n\n".join(conversational)

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

def count_words(text):
    return len(re.findall(r'\b\w+\b', text))

app_ui = ui.page_fluid(
    ui.HTML(header_html),
    ui.HTML(wrapper_start_html),
    ui.h1("Content Scraper", class_="govuk-heading-xl govuk-!-margin-top-6 govuk-!-margin-bottom-6"),
    ui.tags.form(
        ui.tags.div(
            ui.input_text("url", "Enter URL to scrape:", placeholder="https://www.gov.uk/", width="100%"),
            class_="govuk-form-group"
        ),
        ui.tags.div(
            ui.input_action_button("scrape", "Scrape page"),
            class_="govuk-form-group"
        ),
        ui.tags.div(
            ui.input_text_area("words", "Scraped Words", value="", rows=10, width="100%"),
            class_="govuk-form-group"
        ),
        ui.tags.div(
            ui.input_text_area("themes", "Content Themes (Conversational)", value="", rows=8, width="100%"),
            class_="govuk-form-group"
        ),
        ui.tags.div(
            ui.input_text("wordcount", "Total Word Count", value="", width="100%"),
            class_="govuk-form-group"
        ),
    ),
    ui.HTML(wrapper_end_html)
)

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
