from aiogram import types, Dispatcher
from create_bot import bot, dp
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Command
import asyncio
import ping3
import nmap
import aiohttp
import sys
import subprocess
import redis
import socket
from aiogram.types import ChatActions
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
from aiocron import crontab
import os
import requests

# env
redis_host = os.environ.get('REDIS_HOST')
redis_port = os.environ.get('REDIS_PORT')

class StartState(StatesGroup):
    STARTED = State()

class PingState(StatesGroup):
    EnterURL = State()
    EnterURLbd = State()
    ActionChoose = State()
    RepeatAction = State()

# cmd /start
async def cmd_start(message: types.Message, state: FSMContext):

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    bd_btn = types.KeyboardButton("Monitoring IPs")
    test_btn = types.KeyboardButton("Test the network")
    keyboard.add(test_btn, bd_btn)
    
    await message.answer( f"Shalom, *{message['from'].first_name}*!\nPlease press the button to Test the network or Monitoring IPs.", reply_markup=keyboard)
    
    chat_id = message.chat.id
    asyncio.create_task(ping_urls_periodically(state, chat_id))
    await state.finish()

    await StartState.STARTED.set()

# btn "to the begining"
@dp.message_handler(lambda message: message.text == "to the begining", state='*')
async def bnt_start(message: types.Message, state: FSMContext):

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    bd_btn = types.KeyboardButton("Monitoring IPs")
    test_btn = types.KeyboardButton("Test the network")
    keyboard.add(test_btn, bd_btn)
    
    await message.answer( f"*{message['from'].first_name}*!\nPlease press the button to Test the network or Monitoring IPs.", reply_markup=keyboard)
    
    chat_id = message.chat.id
    asyncio.create_task(ping_urls_periodically(state, chat_id))

    await state.finish()

    await StartState.STARTED.set()    

# monitoring
@dp.message_handler(lambda message: message.text == "Monitoring IPs", state='*')
async def db_handler(message: types.Message, state: FSMContext):

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True) 
    keyboard.row('View IPs', 'Add IP', 'Remove IP')
    keyboard.row('to the begining')

    await message.answer("Choose an action for", reply_markup=keyboard)

# address verification
@dp.message_handler(lambda message: message.text in ["Test the network", "Add IP", "Remove IP"], state='*')
async def cmd_handler(message: types.Message, state: FSMContext):
    await state.update_data(selected_button=message.text)  
    await message.answer("Enter URL website", reply_markup=types.ReplyKeyboardRemove())
    await PingState.EnterURL.set()

@dp.message_handler(state=PingState.EnterURL)
async def enter_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    url = url.replace(" ", "").replace(",", ".")
    url = url.lower()

    await state.update_data(url=url)

    try:
        socket.inet_aton(url)
    except socket.error:
        try:
            socket.gethostbyname(url)
        except socket.gaierror:
            await message.answer(f"The {url} does not exist.\nTry again")
            return

    data = await state.get_data()
    selected_button = data.get("selected_button")

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    if selected_button == "Test the network":
        keyboard.row('Ping', 'Nmap')
        keyboard.row('Traceroute', 'Curl')
        keyboard.row('to the begining')

    elif selected_button == "Add IP":
        keyboard.add(KeyboardButton(text="Add IP to DB"))

    elif selected_button == "Remove IP":
        keyboard.add(KeyboardButton(text="Remove IP from DB"))

    if selected_button == "Test the network":
        await message.answer(
            f"Choose for {url}",
            reply_markup=keyboard
        )

    elif selected_button == "Add IP":
        await message.answer(
            f"Confirm action for {url}",
            reply_markup=keyboard
        )
    elif selected_button == "Remove IP":
        await message.answer(
            f"Confirm action for {url}",
            reply_markup=keyboard
        )

    await PingState.ActionChoose.set()

# btns
@dp.message_handler(lambda message: message.text == "Add IP to DB" or message.text == "Remove IP from DB" or message.text == "Ping" or message.text == "Nmap" or message.text == "Traceroute" or message.text == "Curl", state=[PingState.ActionChoose, PingState.RepeatAction])
async def ping_chosen_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    url = data.get("url", None)

    if message.text == "Ping":
        result = await ping_website_function(url)
        await message.answer(result)
    elif message.text == "Nmap":
        await message.answer(f"Nmap started for {url}...")
        result = await nmap_function(url, message.chat.id, bot, message)
        await message.answer(result)
    elif message.text == "Traceroute":
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.row('Ping', 'Nmap')
        keyboard.row('Traceroute', 'Curl')
        keyboard.row('to the begining')
        await message.answer(f"Traceroute started for {url}...")
        await message.answer(f"To stop the trace route, click the 'Stop' button.")
        await trace_route_website_function(url, message.chat.id, bot)
        await message.answer("Trace route completed.", reply_markup=keyboard)
    elif message.text == "Curl":
        result = await curl_command(url, message)
        await message.answer(result)
    elif message.text == "Add IP to DB":
        await store_url(url, message)  
        await state.reset_state()  
    elif message.text == "Remove IP from DB":
        await remove_url(url, message)  

        await state.reset_state()  

# db
@dp.message_handler(lambda message: message.text == "View IPs", state='*')
async def db_list_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    redis_connection = redis.Redis(host=redis_host, port=redis_port)
    all_keys = redis_connection.keys()

    db_list = []

    for key in all_keys:
        value = redis_connection.get(key)
        if value is not None:
            db_list.append(value.decode())

    if db_list:
        response = "Addresses in the DB:\n"
        for ip in db_list:
            response += f"- {ip}\n"
        await message.answer(response)
    else:
        await message.answer("Your database is empty.")

# stop traceroute
@dp.message_handler(lambda message: message.text == "Stop", state=[PingState.ActionChoose, PingState.RepeatAction])
async def stop_traceroute_handler(message: types.Message, state: FSMContext):
    global stop_traceroute, process
    stop_traceroute = True
    if process and process.returncode is None:
        process.terminate()

@dp.callback_query_handler(lambda c: c.data == 'stop')
async def stop_trace_route_handler(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    await stop_trace_route(callback_query, chat_id, bot)

# ping
async def ping_website_function(url):    
    response_time = ping3.ping(url)
    return f"Время отклика {url}: {response_time} мс"

async def nmap_function(url, chat_id, bot, message):
    nm = nmap.PortScanner()
    try:
        for i in range(1, 500, 50):
            start_range = i
            end_range = i + 49
            nm.scan(hosts=url, arguments=f'-p {start_range}-{end_range}')
            result = ""
            for url in nm.all_hosts():
                try:
                    domain_name = socket.gethostbyaddr(url)[0]  # получаем доменное имя из IP-адреса
                except socket.herror:
                    domain_name = url  # Если нет доменного имени, используем IP-адрес
                result += f"Result scan host: {url}\n"
                result += f"State ports:\n"
                for proto in nm[url].all_protocols():
                    lport = nm[url][proto].keys()
                    try:
                        await bot.delete_message(chat_id=wait_message.chat.id, message_id=wait_message.message_id)
                    except:
                        pass  # Пропускаем ошибку при удалении сообщения
                    if lport:
                        for port in lport:
                            port_state = nm[url][proto][port]['state']
                            service_name = nm[url][proto][port]['name']
                            protocol = proto.lower()
                            port_info = f"Port: {port}/{protocol} State: {port_state} Service: {service_name}\n"
                            await bot.send_message(chat_id=chat_id, text=port_info)
                            result += port_info
                        wait_message = await bot.send_message(chat_id=chat_id, text=(f"⏰ Continuing with the scanning..."))
        await bot.delete_message(chat_id=wait_message.chat.id, message_id=wait_message.message_id)              
        await bot.send_message(chat_id=chat_id, text='nmap done')
    except Exception as e:
        print(f"Error: {str(e)}")
        await bot.send_message(chat_id=chat_id, text='An error occurred')

# traceroute
async def trace_route_website_function(url, chat_id, bot):
    global stop_traceroute, process
    try:
        stop_traceroute = False
        
        process = await asyncio.create_subprocess_shell(f"traceroute {url}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        while True:
            if stop_traceroute:
                process.send_signal(subprocess.signal.SIGINT)
                await bot.send_message(chat_id, "Traceroute stopped.")
                break

            line = await process.stdout.readline()
            if not line:
                break

            message = line.decode('utf-8')
            # Создание кнопки "Stop"
            stop_button = types.KeyboardButton("Stop")
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(stop_button)
            
            await bot.send_message(chat_id, message, reply_markup=keyboard)

        _, stderr = await process.communicate()
        if stderr:
            error_message = stderr.decode('utf-8')
            await bot.send_message(chat_id, f"Message: {error_message}")

    except Exception as e:
        await bot.send_message(chat_id, f"An error occurred while performing the traceroute: {str(e)}")

# curl
async def curl_command(url, message):
    try:
        ip = socket.gethostbyname(url)

        # Create subprocess and set timeout for 10 seconds
        cmd = ["curl", ip]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
        output, _ = await asyncio.wait_for(process.communicate(), timeout=10)
        decoded_output = output.decode("utf-8")

        await message.answer(f"For {url}\n\nThe result of the curl command:\n{decoded_output}")

    except asyncio.TimeoutError:
        await message.answer("The request did not receive a response within 10 seconds.")

    except Exception as e:
        await message.answer(f"The curl command encountered an error: {str(e)}")
                

# btn Add IP to DB
async def store_url(url, message):

    redis_connection = redis.Redis(host=redis_host, port=redis_port)

    key = f"{url}"
    stored_url = redis_connection.get(key)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True) 

    keyboard.row('View IPs', 'Add IP', 'Remove IP')
    keyboard.row('to the begining')

    if stored_url is not None:
        stored_url = stored_url.decode()  # Преобразуем байтовую строку в обычную строку
        await message.answer(f"URL {stored_url} already exists in the DB.", reply_markup=keyboard)
    else:
        redis_connection.set(key, url)
        await message.answer(f"URL {url} has been successfully added to the DB!", reply_markup=keyboard)

# btn Remove IP from DB
async def remove_url(url, message):
    redis_connection = redis.Redis(host=redis_host, port=redis_port)
    key = f"{url}"
    remove_url = redis_connection.get(key)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True) 
    keyboard.row('View IPs', 'Add IP', 'Remove IP')
    keyboard.row('to the begining')

    if remove_url is not None:
        remove_url = remove_url.decode()  # Преобразуем байтовую строку в обычную строку
        redis_connection.delete(key)
        await message.answer(f"URL {url} has been successfully removed from the DB.", reply_markup=keyboard)
    else:
        await message.answer(f"URL {url} is not found the DB.", reply_markup=keyboard)

# btn View your DB
@dp.message_handler(lambda message: message.text == "View your DB", state='*')
async def db_list_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    redis_connection = redis.Redis(host=redis_host, port=redis_port)
    all_keys = redis_connection.keys()

    db_list = []

    for key in all_keys:
        value = redis_connection.get(key)
        if value is not None:
            db_list.append(value.decode())

    if db_list:
        response = "Addresses in the DB:\n"
        for ip in db_list:
            response += f"- {ip}\n"
        await message.answer(response)
    else:
        await message.answer("Your database is empty.")

# ping 
async def ping_urls_periodically(state, chat_id):

    unavailable_ips = []  # Список для хранения недоступных IP-адресов
    available_ips = []  # Список для хранения доступных IP-адресов

    while True:
        data = await state.get_data()
        redis_connection = redis.Redis(host=redis_host, port=redis_port)
        all_keys = redis_connection.keys()

        for key in all_keys:
            value = redis_connection.get(key)
            if value is not None:
                ip = value.decode()
                response_time = ping3.ping(ip)

                if response_time is None:
                    if ip not in unavailable_ips:
                        if ip not in available_ips:
                            if len(unavailable_ips) < 3:
                                message = f"IP {ip} is not available."
                                await bot.send_message(chat_id=chat_id, text=message)
                            unavailable_ips.append(ip)
                else:
                    if ip in unavailable_ips:
                        unavailable_ips.remove(ip)
                        if ip not in available_ips:
                            available_ips.append(ip)
                            message = f"IP {ip} has become available."
                            await bot.send_message(chat_id=chat_id, text=message)


        await asyncio.sleep(5)  # Пауза 5 секунд перед следующим пингом

        if len(unavailable_ips) == 3:
            unavailable_ips.clear()
        if len(available_ips) == 3:
            available_ips.clear()

def register_handlers_fsm(dp: Dispatcher):
    dp.register_message_handler(cmd_start, Command("start"), state="*")
    dp.register_message_handler(cmd_handler, lambda message: message.text in ["Test the network", "Add IP", "Remove IP"], state='*')
    dp.register_message_handler(db_handler, lambda message: message.text == "Monitoring IPs", state='*')
    dp.register_message_handler(enter_url, state=PingState.EnterURL)
    dp.register_message_handler(ping_chosen_handler, lambda message: message.text == "Ping" or message.text == "Add IP to DB" or message.text == "Remove IP from DB" or message.text == "Nmap" or message.text == "Traceroute" or message.text == "Curl", state=[PingState.ActionChoose, PingState.RepeatAction])
    dp.register_message_handler(db_list_handler, lambda message: message.text == "View IPs", state='*')
    dp.register_message_handler(stop_traceroute_handler,  lambda message: message.text == "Stop", state=[PingState.ActionChoose, PingState.RepeatAction])
    dp.register_callback_query_handler(stop_trace_route_handler, lambda c: c.data == 'stop')
    dp.register_message_handler(bnt_start, lambda message: message.text == "to the begining", state='*')



    


