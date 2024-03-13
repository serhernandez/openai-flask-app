from flask import current_app as app
from flask import render_template, request, session
import markdown
#import tiktoken

from .models import Context, Conversation, FormattedMessage, Settings, db
from .clients import openai_client
#encoding = tiktoken.encoding_for_model(model)

@app.route("/")
def home_page():
    if Conversation.query.count() == 0:
        newConvo = Conversation(id = 0, name = "default")
        sysMess = Context(content = {"role": "system", "content": "You are an expert on the Python and Javascript programming languages. Provide helpful responses that include code examples when relevant."}, conversation_id = 0)
        db.session.add(newConvo)
        db.session.add(sysMess)
        db.session.commit()
        session['current_conversation'] = 0
    if Settings.query.count() == 0:
        defaultSettings = Settings(model = app.config['OPENAI_MODELS'][0], current=0)
        db.session.add(defaultSettings)
        db.session.commit()
    if 'current_conversation' not in session:
        session['current_conversation'] = Settings.query.with_entities(Settings.current).first()[0]
    if 'current_model' not in session:
        session['current_model'] = Settings.query.with_entities(Settings.model).first()[0]
    return render_template('home.html', models = app.config['OPENAI_MODELS'], curmodel = session['current_model'], chat_history=FormattedMessage.query.filter_by(conversation_id = session['current_conversation']).all(), 
                           chat_name = Conversation.query.filter_by(id = session['current_conversation']).with_entities(Conversation.name).first()[0], conversations = Conversation.query.all(),
                           sysprompt = Context.query.with_entities(Context.content).filter_by(conversation_id = session['current_conversation']).first()[0]['content'])

@app.route("/", methods=['POST'])
def process_data():
    data = request.form.get('text')
    formatted_data = {"role": "user", "content": data}
    userContext = Context(content = formatted_data, conversation_id = session['current_conversation'])
    userFormatted = FormattedMessage(role = "user", content = markdown.markdown(data, extensions=['codehilite', 'fenced_code']), conversation_id = session['current_conversation'])
    db.session.add(userContext)
    db.session.add(userFormatted)
    currentContext = list(map(lambda x: x[0], Context.query.with_entities(Context.content).filter_by(conversation_id=session['current_conversation']).all()))
    if session['current_model'] in app.config['OPENAI_MODELS']:
        completion = openai_client.chat.completions.create(model=session['current_model'], messages=currentContext, max_tokens=1000)
        response = completion.choices[0].message.content
    else:
        response = f"I am a dummy model and can only repeat your input back to you.</br>Your input: `{data}`"
    formatted_resp = markdown.markdown(response, extensions=['codehilite', 'fenced_code'])
    resp_dict = {"role": "assistant", "content": response}
    respContext = Context(content = resp_dict, conversation_id = session['current_conversation'])
    respFormatted = FormattedMessage(role = "assistant", content = formatted_resp, conversation_id = session['current_conversation'])
    db.session.add(respContext)
    db.session.add(respFormatted)
    db.session.commit()
    #if app.debug: print(list(map(lambda x: x[0], Context.query.with_entities(Context.content).all())))
    if app.debug and session['current_model'] in app.config['OPENAI_MODELS']: 
        print(f"Sent {completion.usage.prompt_tokens} tokens and received {completion.usage.completion_tokens} tokens, costing roughly ${(completion.usage.prompt_tokens/1000) * app.config['OPENAI_COSTS'][session['current_model']]['input'] + (completion.usage.completion_tokens/1000) * app.config['OPENAI_COSTS'][session['current_model']]['output']}")
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
    newcon = Conversation(id = new_id, name = " ".join([currname, "(copy)"]))
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

@app.route("/changemodel", methods=['PUT'])
def change_model():
    new_model = request.form.get('model')
    if new_model in app.config['OPENAI_MODELS'] or new_model == "dummy":
        session['current_model'] = new_model
        settings = Settings.query.first()
        settings.model = new_model
        db.session.commit()
        if app.debug: print(f"Model changed to {new_model} successfully.")
        return '', 204
    else:
        if app.debug: print(f"{new_model} is not a valid model.")
        return 'Invalid model selected', 400

@app.route("/changeprompt", methods=['PUT'])
def change_prompt():
    current_prompt = Context.query.filter_by(conversation_id = session['current_conversation']).first()
    new_prompt = request.form.get("newprompt")
    assembled_prompt = {"role": "system", "content": new_prompt}
    current_prompt.content = assembled_prompt
    db.session.commit()
    return '', 204