from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

def get_pay(num_hours):
    pay_pretax = num_hours * 15
    pay_aftertax = pay_pretax * (1 - 0.12)
    return pay_aftertax

def count_words(text):
    # Remove leading/trailing whitespace and check for empty
    text = text.strip()
    if not text:
        return 0
    # Split on any sequence of whitespace
    return len(text.split())

@app.route('/', methods=['GET'])
def index():
    return render_template('index.qmd')

@app.route('/pay', methods=['POST'])
def pay():
    hours = request.form.get('hours', type=float)
    pay_result = get_pay(hours)
    return render_template('index.qmd', pay_result=pay_result)

@app.route('/wordcount', methods=['POST'])
def wordcount():
    user_text = request.form.get('userText', '')
    word_count = count_words(user_text)
    return render_template('index.qmd', word_count=word_count, user_text=user_text)

if __name__ == '__main__':
    app.run(debug=True)
