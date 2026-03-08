#!/usr/bin/env python3
# ============================================================
#   OPEN METEO TELEGRAM BOT — BY HACKKNEKKI
#   v2.0 — Исправлено экранирование | 2026
# ============================================================

import urllib.request
import urllib.parse
import json
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

# ─────────────────────────────────────────────
#  НАСТРОЙКИ
# ─────────────────────────────────────────────
BOT_TOKEN = "8779391250:AAFp_IVnB8uh-5xzaha-OXuzLFumLW9q3Hs"  # ← замени на токен от @BotFather

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("weather_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  КОДЫ ПОГОДЫ WMO
# ─────────────────────────────────────────────
WMO = {
    0:  ("☀️",  "Ясно"),
    1:  ("🌤",  "Почти ясно"),
    2:  ("⛅",  "Переменная облачность"),
    3:  ("☁️",  "Пасмурно"),
    45: ("🌫",  "Туман"),
    48: ("🌫",  "Туман с изморозью"),
    51: ("🌦",  "Слабая морось"),
    53: ("🌦",  "Умеренная морось"),
    55: ("🌧",  "Сильная морось"),
    61: ("🌧",  "Слабый дождь"),
    63: ("🌧",  "Умеренный дождь"),
    65: ("🌧",  "Сильный дождь"),
    71: ("🌨",  "Слабый снег"),
    73: ("❄️",  "Умеренный снег"),
    75: ("❄️",  "Сильный снег"),
    77: ("🌨",  "Снежная крупа"),
    80: ("🌦",  "Лёгкий ливень"),
    81: ("🌧",  "Умеренный ливень"),
    82: ("⛈",  "Сильный ливень"),
    85: ("🌨",  "Снежные ливни"),
    86: ("❄️",  "Сильные снежные ливни"),
    95: ("⛈",  "Гроза"),
    96: ("⛈",  "Гроза с градом"),
    99: ("⛈",  "Сильная гроза с градом"),
}

FAVORITES = {
    "🏔 Хорог":    (37.4897, 71.5601),
    "🌿 Душанбе":  (38.5598, 68.7870),
    "🏔 Рушан":    (37.9333, 71.5500),
    "🏔 Баджа":    (37.65,   71.55),
    "🌆 Москва":   (55.7558, 37.6173),
    "🌍 Лондон":   (51.5074, -0.1278),
}

# ─────────────────────────────────────────────
#  УТИЛИТЫ
# ─────────────────────────────────────────────
def wmo_desc(code):
    if code is None: return "❓", "Нет данных"
    return WMO.get(int(code), ("❓", f"Код {code}"))

def wind_dir(deg):
    if deg is None: return "-"
    dirs = ["С","СВ","В","ЮВ","Ю","ЮЗ","З","СЗ"]
    return dirs[round(deg / 45) % 8]

def f(val, dec=1):
    if val is None: return "н/д"
    return str(round(val, dec))

def sunrise_time(s):
    if not s: return "-"
    return s.split("T")[-1][:5]

def temp_emoji(t):
    if t is None: return "🌡"
    if t <= -20: return "🥶"
    if t <= 0:   return "❄️"
    if t <= 10:  return "🧊"
    if t <= 20:  return "😊"
    if t <= 30:  return "☀️"
    return "🔥"

def uv_info(uv):
    if uv is None: return "⚪", "н/д"
    if uv <= 2:   return "🟢", "Низкий"
    if uv <= 5:   return "🟡", "Умеренный"
    if uv <= 7:   return "🟠", "Высокий"
    if uv <= 10:  return "🔴", "Очень высокий"
    return "🟣", "Экстремальный"

def wind_dot(ws):
    if ws is None: return "⚪"
    if ws < 10:  return "🟢"
    if ws < 30:  return "🟡"
    if ws < 50:  return "🟠"
    return "🔴"

def vis_dot(vis):
    if vis is None: return "⚪"
    if vis >= 10000: return "🟢"
    if vis >= 5000:  return "🟡"
    if vis >= 1000:  return "🟠"
    return "🔴"

# ─────────────────────────────────────────────
#  ВАЖНО: используем HTML вместо MarkdownV2
#  HTML намного надёжнее — нет проблем с экранированием
# ─────────────────────────────────────────────
def h(text):
    """Экранирование для HTML"""
    return str(text).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

# ─────────────────────────────────────────────
#  API
# ─────────────────────────────────────────────
def fetch_weather(lat, lon):
    params = {
        "latitude":  lat,
        "longitude": lon,
        "current": ",".join([
            "temperature_2m","relative_humidity_2m","apparent_temperature",
            "precipitation","rain","snowfall","weather_code","cloud_cover",
            "surface_pressure","wind_speed_10m","wind_direction_10m",
            "wind_gusts_10m","visibility","is_day",
        ]),
        "daily": ",".join([
            "temperature_2m_max","temperature_2m_min","precipitation_sum",
            "rain_sum","snowfall_sum","precipitation_hours","wind_speed_10m_max",
            "sunrise","sunset","uv_index_max","sunshine_duration",
        ]),
        "timezone":      "auto",
        "forecast_days": "1",
    }
    url = f"https://api.open-meteo.com/v1/forecast?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.error(f"Weather API: {e}")
        return None

def geocode(name):
    url = (f"https://geocoding-api.open-meteo.com/v1/search"
           f"?name={urllib.parse.quote(name)}&count=5&language=ru&format=json")
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read()).get("results", [])
    except Exception as e:
        logger.error(f"Geocode: {e}")
        return []

# ─────────────────────────────────────────────
#  ФОРМАТИРОВАНИЕ — HTML (надёжно!)
# ─────────────────────────────────────────────
def format_weather(data, place_name, lat, lon):
    cur   = data.get("current", {})
    daily = data.get("daily", {})
    tz    = data.get("timezone_abbreviation", "")
    elev  = data.get("elevation", "?")
    dtime = cur.get("time", "-")

    wcode  = cur.get("weather_code")
    icon, desc = wmo_desc(wcode)
    t      = cur.get("temperature_2m")
    t_feel = cur.get("apparent_temperature")
    is_day = cur.get("is_day", 1)
    rh     = cur.get("relative_humidity_2m")
    cc     = cur.get("cloud_cover")
    prec   = cur.get("precipitation")
    rain   = cur.get("rain")
    snow   = cur.get("snowfall")
    ws     = cur.get("wind_speed_10m")
    wg     = cur.get("wind_gusts_10m")
    wd     = cur.get("wind_direction_10m")
    pres   = cur.get("surface_pressure")
    vis    = cur.get("visibility")

    t_max  = daily.get("temperature_2m_max",  [None])[0]
    t_min  = daily.get("temperature_2m_min",  [None])[0]
    p_sum  = daily.get("precipitation_sum",   [None])[0]
    r_sum  = daily.get("rain_sum",            [None])[0]
    s_sum  = daily.get("snowfall_sum",        [None])[0]
    p_hrs  = daily.get("precipitation_hours", [None])[0]
    wmax   = daily.get("wind_speed_10m_max",  [None])[0]
    sunrise= daily.get("sunrise",             [None])[0]
    sunset = daily.get("sunset",              [None])[0]
    uv     = daily.get("uv_index_max",        [None])[0]
    sun_s  = daily.get("sunshine_duration",   [None])[0]
    sun_h  = round(sun_s / 3600, 1) if sun_s else None

    day_night  = "☀️ День" if is_day else "🌙 Ночь"
    te         = temp_emoji(t)
    uv_dot, uv_text = uv_info(uv)
    vis_km     = f"{round(vis/1000,1)} км" if vis else "н/д"

    msg = (
        f"╔══════════════════════════╗\n"
        f"║ {icon}  <b>{h(desc)}</b>\n"
        f"║ {h(day_night)}  │  {h(dtime)} {h(tz)}\n"
        f"╚══════════════════════════╝\n"
        f"\n"
        f"📍 <b>{h(place_name)}</b>\n"
        f"🌐 <code>{h(lat)}, {h(lon)}</code>  ⛰ <code>{h(elev)} м</code>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌡 <b>ТЕМПЕРАТУРА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{te} Сейчас:        <code>{h(f(t))} °C</code>\n"
        f"🤔 Ощущается:    <code>{h(f(t_feel))} °C</code>\n"
        f"🔺 Макс сегодня: <code>{h(f(t_max))} °C</code>\n"
        f"🔻 Мин сегодня:  <code>{h(f(t_min))} °C</code>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💧 <b>ВЛАЖНОСТЬ И ОБЛАЧНОСТЬ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💧 Влажность:    <code>{h(f(rh,0))} %</code>\n"
        f"☁️ Облачность:   <code>{h(f(cc,0))} %</code>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌧 <b>ОСАДКИ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌧 Осадки сейчас:  <code>{h(f(prec,2))} мм</code>\n"
        f"🌦 Дождь сейчас:   <code>{h(f(rain,2))} мм</code>\n"
        f"❄️ Снег сейчас:    <code>{h(f(snow,2))} см</code>\n"
        f"📊 Осадки за день: <code>{h(f(p_sum,2))} мм</code>\n"
        f"🌦 Дождь за день:  <code>{h(f(r_sum,2))} мм</code>\n"
        f"❄️ Снег за день:   <code>{h(f(s_sum,2))} см</code>\n"
        f"⏱ Часов с осадк.: <code>{h(f(p_hrs,0))} ч</code>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💨 <b>ВЕТЕР</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{wind_dot(ws)} Скорость:     <code>{h(f(ws))} км/ч</code>\n"
        f"🌬 Порывы:       <code>{h(f(wg))} км/ч</code>\n"
        f"🧭 Направление:  <code>{h(f(wd,0))}° {h(wind_dir(wd))}</code>\n"
        f"⚡ Макс за день: <code>{h(f(wmax))} км/ч</code>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔭 <b>АТМОСФЕРА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔵 Давление:     <code>{h(f(pres))} гПа</code>\n"
        f"{vis_dot(vis)} Видимость:    <code>{h(vis_km)}</code>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"☀️ <b>СОЛНЦЕ И УФ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{uv_dot} УФ-индекс:    <code>{h(f(uv))} — {h(uv_text)}</code>\n"
        f"🌞 Солн. сияние: <code>{h(f(sun_h))} ч</code>\n"
        f"🌅 Восход:       <code>{h(sunrise_time(sunrise))}</code>\n"
        f"🌇 Закат:        <code>{h(sunrise_time(sunset))}</code>\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>OPEN METEO BY HACKKNEKKI © 2026</b>\n"
        f"📡 <i>Источник: open-meteo.com</i>"
    )
    return msg

# ─────────────────────────────────────────────
#  КЛАВИАТУРЫ
# ─────────────────────────────────────────────
def main_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🔍 Поиск города"),  KeyboardButton("📍 Геолокация")],
        [KeyboardButton("⭐ Избранное"),      KeyboardButton("ℹ️ Помощь")],
    ], resize_keyboard=True)

def favorites_kb():
    rows = []
    row  = []
    for name in FAVORITES:
        row.append(InlineKeyboardButton(name, callback_data=f"fav:{name}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    return InlineKeyboardMarkup(rows)

def action_kb(lat, lon, place):
    # Ограничиваем длину place для callback_data (макс 64 байта)
    short = place[:20].replace(":", "-")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Обновить",     callback_data=f"ref|{lat}|{lon}|{short}"),
        InlineKeyboardButton("🔍 Другой город", callback_data="newsearch"),
    ]])

def geo_results_kb(results):
    rows = []
    for i, res in enumerate(results[:5]):
        name    = res.get("name","")
        country = res.get("country","")
        admin   = res.get("admin1","")
        elev    = res.get("elevation","?")
        lat     = res.get("latitude")
        lon     = res.get("longitude")
        label   = f"{i+1}. {name}, {admin} ({country}) ⛰{elev}м"
        # Используем | как разделитель — он не встречается в названиях
        safe_place = f"{name}, {country}"[:25].replace("|","-")
        rows.append([InlineKeyboardButton(
            label, callback_data=f"pick|{lat}|{lon}|{safe_place}"
        )])
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

# ─────────────────────────────────────────────
#  ОТПРАВКА ПОГОДЫ
# ─────────────────────────────────────────────
async def send_weather(message, lat, lon, place_name):
    msg_obj = await message.reply_text("🌍 Загружаю погоду...")
    data = fetch_weather(lat, lon)
    if not data:
        await msg_obj.edit_text("❌ Ошибка получения данных. Проверьте интернет.")
        return
    text = format_weather(data, place_name, lat, lon)
    kb   = action_kb(lat, lon, place_name)
    try:
        await msg_obj.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception as e:
        logger.error(f"Format error: {e}")
        # Запасной вариант — без форматирования
        try:
            await msg_obj.edit_text(
                f"❌ Ошибка отображения.\n"
                f"Данные получены но не отображаются.\n"
                f"Попробуйте: /weather {place_name}",
                reply_markup=kb
            )
        except:
            pass

# ─────────────────────────────────────────────
#  ХЭНДЛЕРЫ
# ─────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"╔═══════════════════════════╗\n"
        f"║  🌍 <b>OPEN METEO BOT</b>\n"
        f"║  <b>BY HACKKNEKKI © 2026</b>\n"
        f"╚═══════════════════════════╝\n"
        f"\n"
        f"👋 Привет, <b>{h(user.first_name)}</b>!\n"
        f"\n"
        f"Я профессиональный погодный бот.\n"
        f"<b>20 параметров</b> для любой точки мира.\n"
        f"\n"
        f"<b>Что умею:</b>\n"
        f"🔍 Поиск по названию города\n"
        f"📍 Погода по GPS\n"
        f"🌡 Температура, осадки, ветер\n"
        f"☀️ УФ-индекс, восход/закат\n"
        f"⭐ Избранные города (Хорог, Рушан...)\n"
        f"\n"
        f"👇 <b>Выберите действие:</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=main_kb())

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"ℹ️ <b>ПОМОЩЬ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"<b>Команды:</b>\n"
        f"<code>/start</code> — Запустить бота\n"
        f"<code>/help</code> — Эта справка\n"
        f"<code>/weather Город</code> — Быстрая погода\n"
        f"\n"
        f"<b>Примеры:</b>\n"
        f"<code>/weather Душанбе</code>\n"
        f"<code>/weather Хорог</code>\n"
        f"<code>/weather Barchuv</code>\n"
        f"<code>/weather 37.49 71.56</code>\n"
        f"\n"
        f"<b>20 параметров:</b>\n"
        f"🌡 Температура (текущая, ощущаемая, макс/мин)\n"
        f"💧 Влажность и облачность\n"
        f"🌧 Осадки (дождь, снег, суммы)\n"
        f"💨 Ветер (скорость, порывы, направление)\n"
        f"🔭 Давление и видимость\n"
        f"☀️ УФ-индекс, солнечное сияние, восход/закат\n"
        f"\n"
        f"⚡ <b>HACKKNEKKI © 2026</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=main_kb())

async def cmd_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Укажите город:\n<code>/weather Душанбе</code>\n<code>/weather 37.49 71.56</code>",
            parse_mode=ParseMode.HTML
        )
        return
    query = " ".join(args)
    parts = query.replace(",", " ").split()
    if len(parts) == 2:
        try:
            lat, lon = float(parts[0]), float(parts[1])
            await send_weather(update.message, lat, lon, f"📍 {lat}, {lon}")
            return
        except ValueError:
            pass
    results = geocode(query)
    if not results:
        await update.message.reply_text("❌ Место не найдено.")
        return
    r = results[0]
    await send_weather(update.message, r["latitude"], r["longitude"],
                       f"{r.get('name','')}, {r.get('country','')}")

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "🔍 Поиск города":
        context.user_data["search"] = True
        await update.message.reply_text(
            "🔍 <b>Введите название города или координаты:</b>\n\n"
            "Примеры:\n"
            "<code>Душанбе</code>\n"
            "<code>Хорог</code>\n"
            "<code>Barchuv</code>\n"
            "<code>37.49, 71.56</code>",
            parse_mode=ParseMode.HTML
        )

    elif text == "📍 Геолокация":
        kb = ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Отправить геолокацию", request_location=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
        await update.message.reply_text("📍 Нажмите кнопку:", reply_markup=kb)

    elif text == "⭐ Избранное":
        await update.message.reply_text(
            "⭐ <b>ИЗБРАННЫЕ ГОРОДА:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=favorites_kb()
        )

    elif text == "ℹ️ Помощь":
        await cmd_help(update, context)

    elif context.user_data.get("search"):
        context.user_data["search"] = False
        parts = text.replace(",", " ").split()
        if len(parts) == 2:
            try:
                lat, lon = float(parts[0]), float(parts[1])
                await send_weather(update.message, lat, lon, f"📍 {lat}, {lon}")
                return
            except ValueError:
                pass
        msg = await update.message.reply_text("🔍 Ищу...")
        results = geocode(text)
        if not results:
            await msg.edit_text("❌ Место не найдено. Попробуйте другое название.")
            return
        if len(results) == 1:
            r = results[0]
            await msg.delete()
            await send_weather(update.message, r["latitude"], r["longitude"],
                               f"{r.get('name','')}, {r.get('country','')}")
        else:
            await msg.edit_text(
                f"🔍 <b>Найдено {len(results)} мест. Выберите:</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=geo_results_kb(results)
            )
    else:
        await update.message.reply_text(
            "💡 Используйте кнопки меню или <code>/weather Город</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_kb()
        )

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.location
    await send_weather(update.message, loc.latitude, loc.longitude, "📍 Ваше местоположение")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("fav:"):
        name = data[4:]
        if name in FAVORITES:
            lat, lon = FAVORITES[name]
            await send_weather(q.message, lat, lon, name)

    elif data.startswith("pick|"):
        # Разделитель | вместо : чтобы не ломать координаты
        parts = data.split("|", 3)
        lat, lon, place = float(parts[1]), float(parts[2]), parts[3]
        await send_weather(q.message, lat, lon, place)

    elif data.startswith("ref|"):
        parts = data.split("|", 3)
        lat, lon, place = float(parts[1]), float(parts[2]), parts[3]
        weather_data = fetch_weather(lat, lon)
        if weather_data:
            text = format_weather(weather_data, place, lat, lon)
            kb   = action_kb(lat, lon, place)
            try:
                await q.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
            except Exception as e:
                logger.error(f"Refresh error: {e}")

    elif data == "newsearch":
        context.user_data["search"] = True
        await q.message.reply_text(
            "🔍 <b>Введите название города:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_kb()
        )

    elif data == "cancel":
        await q.edit_message_text("❌ Отменено.")

# ─────────────────────────────────────────────
#  ЗАПУСК
# ─────────────────────────────────────────────
def main():
    print("╔══════════════════════════════════╗")
    print("║  🌍 OPEN METEO BOT BY HACKKNEKKI ║")
    print("║  v2.0 — Запуск...                ║")
    print("╚══════════════════════════════════╝")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler
