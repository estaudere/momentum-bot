from deta import Deta
from dotenv import load_dotenv
import os

load_dotenv()

deta = Deta(os.getenv('DETA_PROJECT_KEY'))
users = deta.Base("users")
events = deta.Base("events")
records = deta.Base("records")
committees = deta.Base("temp-committees")