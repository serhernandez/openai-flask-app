from flask import Flask, render_template, request, session
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.route("/")
def home_page():
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('home.html', chat_history=session['chat_history'])

@app.route("/", methods=['POST'])
def process_data():
    data = request.form.get('text')
    response = f"I have processed {data}"
    session['chat_history'].append(data)
    session['chat_history'].append(response)
    session.modified=True
    print(session['chat_history'])
    return response