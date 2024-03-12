from . import db
from datetime import datetime

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