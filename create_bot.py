from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import os

token_bot = os.environ.get('TOKEN_BOT')
bot = Bot(token=token_bot)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

"""
import os
token_bot = os.environ.get('TOKEN_BOT')
bot = Bot(token=token_bot)


bot_token = "6743399707:AAEi4LsoMUad2eRpR4cGt1s4G8TGNINvk8o"
bot = Bot(token=bot_token)
"""