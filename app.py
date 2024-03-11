from flask import Flask, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import markdown, os, secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
load_dotenv()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
db = SQLAlchemy(app)

API_KEY = os.getenv("OPENAI_API_KEY", "")
assert API_KEY, "ERROR: OpenAI Key is missing"

client = OpenAI(api_key=API_KEY)
model = "gpt-3.5-turbo"

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200))
    sender = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    conversation_id = db.Column(db.Integer, db.ForeignKey(Conversation.id))
    conversation = db.relationship('Conversation', backref='messages')

@app.route("/")
def home_page():
    if 'chat_history' not in session:
        session['chat_history'] = [{"role": "system", "content": "You're an expert on the Python and Javascript programming languages. Provide helpful responses that include code examples when relevant."}]
    return render_template('home.html', chat_history=session['chat_history'][1:])

@app.route("/", methods=['POST'])
def process_data():
    if app.debug: print("post request received")
    data = request.form.get('text')
    session['chat_history'].append({"role": "user", "content":data})
    completion = client.chat.completions.create(model=model, messages=session['chat_history'], max_tokens=1000)
    response = {"role": "assistant", "content":markdown.markdown(completion.choices[0].message.content, extensions=['codehilite', 'fenced_code'])}
    if app.debug: print(response['content'])
    session['chat_history'].append(response)
    session.modified=True
    if app.debug: print(session['chat_history'])
    return response['content']

with app.app_context():
    db.create_all()