from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

def calculate_pay(hours, hourly_income, tax_rate):
    gross_pay = hours * hourly_income
    tax = gross_pay * (tax_rate / 100)
    pay_aftertax = gross_pay - tax
    # Daily income/tax for 8 hour day
    daily_income = hourly_income * 8
    daily_tax = daily_income * (tax_rate / 100)
    return pay_aftertax, daily_income, daily_tax

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
    hourly_income = request.form.get('hourly_income', type=float)
    tax_rate = request.form.get('tax_rate', type=float)
    pay_result, daily_income, daily_tax = calculate_pay(hours, hourly_income, tax_rate)
    return render_template(
        'index.qmd', 
        pay_result=pay_result,
        daily_income=daily_income,
        daily_tax=daily_tax,
        hours=hours,
        hourly_income=hourly_income,
        tax_rate=tax_rate
    )

@app.route('/wordcount', methods=['POST'])
def wordcount():
    user_text = request.form.get('userText', '')
    word_count = count_words(user_text)
    return render_template('index.qmd', word_count=word_count, user_text=user_text)

if __name__ == '__main__':
    app.run(debug=True)
