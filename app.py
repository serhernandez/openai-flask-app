from flask import Flask, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import markdown, os, secrets, tiktoken

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
load_dotenv()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
db = SQLAlchemy(app)

API_KEY = os.getenv("OPENAI_API_KEY", "")
assert API_KEY, "ERROR: OpenAI Key is missing"

client = OpenAI(api_key=API_KEY)
openai_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"]
#encoding = tiktoken.encoding_for_model(model)

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

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(30))
    current = db.Column(db.Integer)

@app.route("/")
def home_page():
    if Conversation.query.count() == 0:
        newConvo = Conversation(id = 0, name = "default")
        sysMess = Context(content = {"role": "system", "content": "You're an expert on the Python and Javascript programming languages. Provide helpful responses that include code examples when relevant."}, conversation_id = 0)
        db.session.add(newConvo)
        db.session.add(sysMess)
        db.session.commit()
        session['current_conversation'] = 0
    if Settings.query.count() == 0:
        defaultSettings = Settings(model = openai_models[0], current=0)
        db.session.add(defaultSettings)
        db.session.commit()
    if 'current_conversation' not in session:
        session['current_conversation'] = Settings.query.with_entities(Settings.current).first()[0]
    if 'current_model' not in session:
        session['current_model'] = Settings.query.with_entities(Settings.model).first()[0]
    return render_template('home.html', chat_history=FormattedMessage.query.filter_by(conversation_id = session['current_conversation']).all(), chat_name = Conversation.query.filter_by(id = session['current_conversation']).with_entities(Conversation.name).first()[0], conversations = Conversation.query.all())

@app.route("/", methods=['POST'])
def process_data():
    data = request.form.get('text')
    formatted_data = {"role": "user", "content": data}
    userContext = Context(content = formatted_data, conversation_id = session['current_conversation'])
    userFormatted = FormattedMessage(role = "user", content = markdown.markdown(data, extensions=['codehilite', 'fenced_code']), conversation_id = session['current_conversation'])
    db.session.add(userContext)
    db.session.add(userFormatted)
    currentContext = list(map(lambda x: x[0], Context.query.with_entities(Context.content).filter_by(conversation_id=session['current_conversation']).all()))
    completion = client.chat.completions.create(model=session['current_model'], messages=currentContext, max_tokens=1000)
    response = completion.choices[0].message.content
    formatted_resp = markdown.markdown(response, extensions=['codehilite', 'fenced_code'])
    resp_dict = {"role": "assistant", "content": response}
    respContext = Context(content = resp_dict, conversation_id = session['current_conversation'])
    respFormatted = FormattedMessage(role = "assistant", content = formatted_resp, conversation_id = session['current_conversation'])
    db.session.add(respContext)
    db.session.add(respFormatted)
    db.session.commit()
    #if app.debug: print(list(map(lambda x: x[0], Context.query.with_entities(Context.content).all())))
    if app.debug: print(f"Sent {completion.usage.prompt_tokens} tokens and received {completion.usage.completion_tokens} tokens, costing roughly ${(completion.usage.prompt_tokens/1000) * 0.0005 + (completion.usage.completion_tokens/1000) * 0.0015}")
    return formatted_resp

@app.route("/rename", methods=['PUT'])
def rename_chat():
    newName = request.form.get('title')
    conversation = Conversation.query.filter_by(id=session['current_conversation']).first()
    conversation.name = newName
    db.session.commit()
    if app.debug: print(f"Conversation renamed to {newName} successfully")
    return '', 204

@app.route("/select", methods=['POST'])
def select_chat():
    new_id = request.form.get('id')
    session['current_conversation'] = new_id
    settings = Settings.query.first()
    settings.current = new_id
    db.session.commit()
    return '', 204

@app.route("/newchat", methods=['POST'])
def create_chat():
    new_id = int(Conversation.query.order_by(Conversation.id.desc()).with_entities(Conversation.id).first()[0]) + 1
    new_conversation = Conversation(id = new_id, name = "New Chat")
    sysMess = Context(content = {"role": "system", "content": "You're an expert on the Python and Javascript programming languages. Provide helpful responses that include code examples when relevant."}, conversation_id = new_id)
    db.session.add(new_conversation)
    db.session.add(sysMess)
    db.session.commit()
    session['current_conversation'] = new_id
    return '', 204

@app.route("/delete", methods=['DELETE'])
def delete_chat():
    selconvo = Conversation.query.filter_by(id = session['current_conversation']).first()
    selmess = FormattedMessage.query.filter_by(conversation_id = session['current_conversation']).all()
    selcontext = Context.query.filter_by(conversation_id = session['current_conversation']).all()
    for mess in selmess:
        db.session.delete(mess)
    for cont in selcontext:
        db.session.delete(cont)
    db.session.delete(selconvo)
    for i in range(int(session['current_conversation']) + 1, len(Conversation.query.all())+1):
        selconvo = Conversation.query.filter_by(id = i).first()
        selmess = FormattedMessage.query.filter_by(conversation_id = i).all()
        selcontext = Context.query.filter_by(conversation_id = i).all()
        selconvo.id = i - 1
        for j in range(len(selmess)):
            selmess[j].conversation_id = i - 1
        for j in range(len(selcontext)):
            selcontext[j].conversation_id = i - 1
    db.session.commit()
    session['current_conversation'] = 0    
    return '', 204

@app.route("/duplicate", methods=['POST'])
def duplicate_chat():
    currname = Conversation.query.filter_by(id = session['current_conversation']).with_entities(Conversation.name).first()[0]
    new_id = int(Conversation.query.order_by(Conversation.id.desc()).with_entities(Conversation.id).first()[0]) + 1
    newcon = Conversation(id = new_id, name = currname)
    db.session.add(newcon)
    currcon = Context.query.filter_by(conversation_id = session['current_conversation']).all()
    curmess = FormattedMessage.query.filter_by(conversation_id = session['current_conversation']).all()
    for con in currcon:
        newcon = Context(content=con.content, timestamp=con.timestamp, conversation_id = new_id)
        db.session.add(newcon)
    for mess in curmess:
        newmess = FormattedMessage(role = mess.role, content=mess.content, timestamp=mess.timestamp, conversation_id=new_id)
        db.session.add(newmess)
    db.session.commit()
    session['current_conversation'] = new_id
    return '', 204

with app.app_context():
    db.create_all()