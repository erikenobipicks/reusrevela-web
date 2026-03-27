from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os, secrets, smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

CALC_URL = os.environ.get('CALC_URL', 'https://calculadora.reusrevela.cat')

@app.route('/')
def index():
    lang = session.get('lang', 'ca')
    return render_template('index.html', lang=lang, CALC_URL=CALC_URL)

@app.route('/serveis')
def serveis():
    lang = session.get('lang', 'ca')
    return render_template('serveis.html', lang=lang, CALC_URL=CALC_URL)

@app.route('/sobre')
def sobre():
    lang = session.get('lang', 'ca')
    return render_template('sobre.html', lang=lang, CALC_URL=CALC_URL)

@app.route('/contacte')
def contacte():
    lang = session.get('lang', 'ca')
    return render_template('contacte.html', lang=lang, CALC_URL=CALC_URL)

@app.route('/professionals')
def professionals():
    lang = session.get('lang', 'ca')
    return render_template('professionals.html', lang=lang, CALC_URL=CALC_URL)

@app.route('/lang/<code>')
def set_lang(code):
    if code in ('ca', 'es'):
        session['lang'] = code
    return redirect(request.referrer or url_for('index'))

@app.route('/api/contacte', methods=['POST'])
def api_contacte():
    d = request.json
    nom   = d.get('nom','')
    email = d.get('email','')
    msg   = d.get('missatge','')
    print(f"Contacte: {nom} <{email}> — {msg[:80]}")
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
