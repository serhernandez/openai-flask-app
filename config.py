from dotenv import load_dotenv
from os import getenv
from secrets import token_hex

load_dotenv()

class Config:
    OPENAI_API_KEY = getenv("OPENAI_API_KEY", "")
    OPENAI_COSTS = {
        'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-4-turbo-preview': {'input': 0.01, 'output': 0.03}
    }
    OPENAI_MODELS = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"]
    SECRET_KEY = token_hex(16)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///chat.db'