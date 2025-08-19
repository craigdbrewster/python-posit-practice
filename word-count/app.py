from shiny import App, ui, render
import requests
from bs4 import BeautifulSoup
from collections import Counter
import re

# GDS Header and Footer HTML with CDN links for styles
gds_header = """
<link rel="stylesheet" href="https://assets.publishing.service.gov.uk/government-frontend/govuk-frontend.min.css" />
<header class="govuk-header" role="banner" data-module="govuk-header">
  <div class="govuk-header__container govuk-width-container">
    <div class="govuk-header__logo">
      <a href="https://www.gov.uk" class="govuk-header__link govuk-header__link--homepage">
        <span class="govuk-header__logotype-text">
          GOV.UK
        </span>
      </a>
    </div>
    <div class="govuk-header__content">
      <a href="#" class="govuk-header__link govuk-header__service-name">
        Word Count Tool
      </a>
    </div>
  </div>
</header>
"""

gds_footer = """
<footer class="govuk-footer " role="contentinfo">
  <div class="govuk-width-container ">
    <div class="govuk-footer__meta">
      <div class="govuk-footer__meta-item govuk-footer__meta-item--grow">
        <span class="govuk-footer__license-description">
          &copy; Crown copyright
        </span>
      </div>
    </div>
  </div>
</footer>
"""

app_ui = ui.page_fluid(
    ui.HTML(gds_header),
    ui.HTML("""
    <nav class="govuk-breadcrumbs" aria-label="Breadcrumb">
      <ol class="govuk-breadcrumbs__list">
        <li class="govuk-breadcrumbs__list-item">
          <a class="govuk-breadcrumbs__link" href="#">Home</a>
        </li>
        <li class="govuk-breadcrumbs__list-item">
          <span aria-current="page">Word Count</span>
        </li>
      </ol>
    </nav>
    """),
    ui.h1("Word Count", class_="govuk-heading-xl govuk-!-margin-top-6 govuk-!-margin-bottom-6"),
    ui.input_text("url", "Enter a URL", placeholder="https://www.gov.uk"),
    ui.input_action_button("count", "Count words"),
    ui.output_ui("result"),
    ui.output_text_verbatim("error"),
    ui.HTML(gds_footer)  # Place footer at the end
)

def server(input, output, session):
    @output
    @render.ui
    def result():
        if input.count() == 0:
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
            table = ui.HTML("<table class='govuk-table'><thead><tr><th>Word</th><th>Count</th></tr></thead><tbody>")
            for word, count in common:
                table.add_child(ui.HTML(f"<tr><td>{word}</td><td>{count}</td></tr>"))
            table.add_child(ui.HTML("</tbody></table>"))
            return [
                ui.h3(f"Total words: {total}"),
                ui.h4("Top 20 most common words"),
                table
            ]
        except Exception as e:
            return ui.p(f"Error: {e}")

app = App(app_ui, server)
