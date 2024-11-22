import telebot
import time
import requests
import json
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))

weather_token = os.getenv('WTHR_TOKEN')


def safe_me(func):
    def secure_me(message):
        if message.from_user.id not in [int(os.getenv('MY_TG_ID')), int(os.getenv('SCND_TG_ID'))]:
            return bot.send_message(message.chat.id, 'Я тебя не знаю')
        return func(message)
    return secure_me


def cur_time(dt, timezone, alls=True):  # Получаем время 24-часового формата
    unix_timestamp = float(dt + timezone)
    time_struct = time.gmtime(unix_timestamp)
    if alls:
        month = time.strftime('%b', time_struct)
        day = int(time.strftime('%d', time_struct))
        return time.strftime(f'%H:%M, {day} {months[month]}', time_struct)
    else:
        return time.strftime('%H:%M', time_struct)


def get_dir(deg, wnd_spd):  # Возвращает направление ветра
    if wnd_spd == 0:
        return ''
    elif 337.5 < deg <= 360 or 0 <= deg < 22.5:
        drn = 'С⬇️'
    elif 22.5 < deg < 67.5:
        drn = 'С-В↙️'
    elif 67.5 < deg < 112.5:
        drn = 'В⬅️'
    elif 112.5 < deg < 157.5:
        drn = 'Ю-В↖️'
    elif 157.5 < deg < 202.5:
        drn = "Ю⬆️"
    elif 202.5 < deg < 247.5:
        drn = "Ю-З↗️"
    elif 247.5 < deg < 292.5:
        drn = "З➡️"
    elif 292.5 < deg < 337.5:
        drn = "С-З↘️"
    return ', ' + drn


def get_pwr(wind):  # Определяет силу ветра
    if wind == 0:
        return "штиль"
    elif 0 < wind <= 0.2:
        pwr = "штиль"
    elif 0.3 <= wind <= 1.5:
        pwr = "тихий"
    elif 1.6 <= wind <= 3.3:
        pwr = "легкий"
    elif 3.4 <= wind <= 5.4:
        pwr = "слабый"
    elif 5.5 <= wind <= 7.9:
        pwr = "умеренный"
    elif 8 <= wind <= 10.7:
        pwr = "свежий"
    elif 10.8 <= wind <= 13.8:
        pwr = "сильный"
    elif 13.9 <= wind <= 17.1:
        pwr = "крепкий"
    elif 17.2 <= wind <= 20.7:
        pwr = "очень крепкий"
    elif 20.8 <= wind <= 24.4:
        pwr = "шторм"
    elif 24.5 <= wind <= 28.4:
        pwr = "сильный шторм"
    elif 28.5 <= wind <= 32.6:
        pwr = "жестокий шторм"
    else:
        pwr = "ураган"
    return pwr


def edit_temp_text(city_name, temp, feels_like):  # Делает текст более приятным для чтения и понимания о температуре
    if temp == feels_like:
        return f'Сейчас в {city_name} {temp}°C🌡\n'
    else:
        return f'Сейчас в {city_name} {temp}°C, ощущается как {feels_like}°C🌡\n'


months = {
    'Jan': 'янв',
    'Feb': 'фев',
    'Mar': 'марта',
    'Apr': 'апр',
    'May': 'мая',
    'Jun': 'июн',
    'Jul': 'июл',
    'Aug': 'авг',
    'Sep': 'сен',
    'Oct': 'окт',
    'Nov': 'нояб',
    'Dec': 'дек'
}

emoji = {
    'ясно': '🌞',
    'солнечно': '☀️',
    'переменная облачность': '🌦',
    'облачно с прояснениями': '🌥',
    'облачно': '☁️',
    'гроза': '🌩',
    'дожд': '🌧',
    'пасмурно': '⛅️',
    'туман': '🌫',
    'град': '🧊',
    'снег': '🌨',
    'ветер': '🌬',
    'зырк': '👀'
}


@bot.message_handler(commands=['start'])
@safe_me
def greet(message):  # Команда приветствия пользователя
    bot.send_message(message.chat.id, f'Привет, {message.from_user.first_name}!\nНапиши мне название места и я пришлю сводку погоды!😀')


@bot.message_handler(commands=['help'])
@safe_me
def help_user(message):
    bot.send_message(message.chat.id, f'{message.from_user.first_name}, напиши мне название места и я пришлю сводку погоды.\n'
                                      f'Если сообщение о погоде не поступает, повтори свой запрос через некоторое время или подожди пока я не отвечу🤓')


# А дальше всё ок
@bot.message_handler(content_types=['text'])
@safe_me
def get_weather(message):  # Основная функция, отправляет сводку погоды
    city = message.text
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city.capitalize()}&lang=ru&units=metric&APPID=" + weather_token
    flag_mes = False  # Костыль, который позволяет не спамить о переподключении и всё выводится одним сообщением
    while True:  # Повторный запрос серверу, если он не отвечает
        try:
            r = requests.get(url)
            break
        except requests.exceptions.ReadTimeout:
            if not flag_mes:
                msg = bot.send_message(message.chat.id, '⏳Подождите, идет переподключение...')
                time.sleep(5)
                flag_mes = True
            else:
                time.sleep(5)
    if flag_mes:
        bot.delete_message(message.chat.id, msg.message_id)
    if r.status_code == 200:
        data = json.loads(r.text)
        main = data['main']
        utc = data['timezone']
        at_pr = int(round(main['pressure'] * 0.75006375541921, 0))
        wind = (lambda spd: int(round(spd, 0)) if spd >= 1 else round(spd, 1))(data['wind']['speed'])
        weather = data['weather']
        w_emoji = emoji['зырк']
        try:  # Если в запросе не было направления ветра
            cur_drn = get_dir(data['wind']['deg'], wind)
        except KeyError:
            cur_drn = ''
        for em in emoji:
            if em in weather[0]["description"]:
                w_emoji = emoji[em]
                break
        temp_text = edit_temp_text(city.title(), int(round(main['temp'], 0)), int(round(main['feels_like'], 0))) + f'На улице {weather[0]["description"]}{w_emoji}'
        bot.send_message(message.chat.id, temp_text)
        bot.send_message(message.chat.id, f'Доп. информация:\n'
                         f'🎈Давление: {at_pr} мм рт. ст.\n'
                         f'💨Ветер: {wind} м/с ({get_pwr(wind)}{cur_drn})\n'
                         f'💦Влажность: {main['humidity']}%')
        bot.send_message(message.chat.id, f'🕰Местное время {cur_time(data['dt'], utc)}\n'
                         f'🌅Восход в {cur_time(data['sys']['sunrise'], utc, alls=False)}\n'
                         f'🌄Закат в {cur_time(data['sys']['sunset'], utc, alls=False)}')
    else:
        pr_msg = bot.send_message(message.chat.id, '❌Проблемы с API погоды или Ваш запрос неверный❌')
        time.sleep(5)
        bot.delete_message(message.chat.id, pr_msg.message_id)


bot.polling(none_stop=True)
