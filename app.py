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

class Context(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    conversation_id = db.Column(db.Integer, db.ForeignKey(Conversation.id))
    conversation = db.relationship('Conversation', backref='context')

class FormattedMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(100))
    content = db.Column(db.String(10000))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    conversation_id = db.Column(db.Integer, db.ForeignKey(Conversation.id))
    conversation = db.relationship('Conversation', backref='formatted_messages')

@app.route("/")
def home_page():
    if Conversation.query.count() == 0:
        newConvo = Conversation(id = 0, name = "default")
        sysMess = Context(content = {"role": "system", "content": "You're an expert on the Python and Javascript programming languages. Provide helpful responses that include code examples when relevant."})
        db.session.add(newConvo)
        db.session.add(sysMess)
        db.session.commit()
    return render_template('home.html', chat_history=FormattedMessage.query.filter_by(conversation_id = 0).all())

@app.route("/", methods=['POST'])
def process_data():
    data = request.form.get('text')
    formatted_data = {"role": "user", "content": data}
    userContext = Context(content = formatted_data, conversation_id = 0)
    userFormatted = FormattedMessage(role = "user", content = markdown.markdown(data, extensions=['codehilite', 'fenced_code']), conversation_id = 0)
    db.session.add(userContext)
    db.session.add(userFormatted)
    completion = client.chat.completions.create(model=model, messages=list(map(lambda x: x[0], Context.query.with_entities(Context.content).all())), max_tokens=1000)
    response = completion.choices[0].message.content
    formatted_resp = markdown.markdown(response, extensions=['codehilite', 'fenced_code'])
    resp_dict = {"role": "assistant", "content": response}
    respContext = Context(content = resp_dict, conversation_id = 0)
    respFormatted = FormattedMessage(role = "assistant", content = formatted_resp, conversation_id = 0)
    db.session.add(respContext)
    db.session.add(respFormatted)
    db.session.commit()
    if app.debug: print(list(map(lambda x: x[0], Context.query.with_entities(Context.content).all())))
    return formatted_resp

with app.app_context():
    db.create_all()