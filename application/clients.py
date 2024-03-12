from flask import current_app as app
from openai import OpenAI

assert app.config['OPENAI_API_KEY'], "ERROR: OpenAI Key is missing"

openai_client = OpenAI(api_key=app.config['OPENAI_API_KEY'])