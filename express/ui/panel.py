# to run: python -m express.ui.panel

from flask import Flask, render_template, request, redirect, abort

from .. import database


app = Flask(__name__)

running = True

# Testing data
@app.route('/')
def index():
    #data = {
    #    'running': running,
    #    'last_price_update': 456123146,
    #    'items': len(database.get_items())
    #}
    #return render_template('index.html', data=data)
    return redirect('/prices')


@app.route('/prices')
def prices():
    return render_template('prices.html', items=database._get_pricelist())


@app.route('/delete/<name>')
def delete(name):
    database.remove_price(name)
    return redirect('/prices')


@app.route('/add', methods=['POST'])
def add():
    data = dict(request.form.items())
    names = data['names'].split(', ')
    for name in names:
        database.add_price(name)
    return redirect('/prices')


if __name__ == '__main__':
    app.run(debug=True)
