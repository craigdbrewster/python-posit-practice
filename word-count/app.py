from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
import os

# Tell Flask to look for templates in the current folder
app = Flask(__name__, template_folder=".")

def get_word_count(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching the URL: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(separator=" ")

    words = re.findall(r"\b\w+\b", text.lower())
    word_count = Counter(words)

    return {"total_words": len(words), "common": word_count.most_common(20)}, None

@app.route("/", methods=["GET", "POST"])
def index():
    results, error = None, None
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        if not url:
            error = "You must enter a URL"
        else:
            results, error = get_word_count(url)
    return render_template("index.html", results=results, error=error)

if __name__ == "__main__":
    app.run(debug=True)  # Posit Connect overrides host/port automatically
