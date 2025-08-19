from shiny import App, ui, render
import requests
from bs4 import BeautifulSoup
from collections import Counter
import re

app_ui = ui.page_fluid(
    ui.h2("Word Count from URL"),
    ui.input_text("url", "Enter a URL", placeholder="https://www.gov.uk"),
    ui.input_action_button("go", "Count Words"),
    ui.output_ui("result")
)

def server(input, output, session):
    @output
    @render.ui
    def result():
        if input.go() == 0:
            return None
        url = input.url()
        if not url:
            return ui.p("Please enter a URL.")
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=" ")
            words = re.findall(r"\b\w+\b", text.lower())
            total = len(words)
            counter = Counter(words)
            common = counter.most_common(20)
            table = ui.HTML("<table><tr><th>Word</th><th>Count</th></tr>")
            for word, count in common:
                table.add_child(ui.HTML(f"<tr><td>{word}</td><td>{count}</td></tr>"))
            table.add_child(ui.HTML("</table>"))
            return [
                ui.h3(f"Total words: {total}"),
                ui.h4("Top 20 most common words"),
                table
            ]
        except Exception as e:
            return ui.p(f"Error: {e}")

app = App(app_ui, server)
