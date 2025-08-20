from flask import Flask, render_template, request

app = Flask(__name__)

def get_pay(num_hours):
    pay_pretax = num_hours * 15
    pay_aftertax = pay_pretax * (1 - .12)
    return pay_aftertax

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        hours = float(request.form['hours'])
        result = get_pay(hours)
    return render_template('form.html', result=result)

if __name__ == '__main__':
    app.run(debug=True)
