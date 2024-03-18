from aiogram import Bot, Dispatcher, executor
from handlers import fsm
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import logging
import os

token_bot = os.environ.get('TOKEN_BOT')
bot = Bot(token=token_bot)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
logging.basicConfig(level=logging.INFO) # Используем промежуточное ПО LoggingMiddleware


async def on_startup(_):
    print('СТАРТУЕМ')

fsm.register_handlers_fsm(dp)

executor.start_polling(dp, skip_updates=True, on_startup=on_startup)