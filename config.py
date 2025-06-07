from dotenv import load_dotenv
load_dotenv()
from dataclasses import dataclass
import os

@dataclass
class Config:
    bot_token: str
    admin_id: int

bot_token = os.getenv("BOT_TOKEN")
admin_id = os.getenv("ADMIN_ID")

if bot_token is None:
    raise ValueError("BOT_TOKEN environment variable is not set")
if admin_id is None:
    raise ValueError("ADMIN_ID environment variable is not set")

config = Config(
    bot_token=bot_token,
    admin_id=int(admin_id)
)