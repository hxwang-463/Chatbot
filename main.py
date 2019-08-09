from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config
import re
import spacy
import requests
import sqlite3


TOKEN = "874251429:AAGbXIM9_cn6ArfilkiFtm0AUK4Hq_PoefM"

nlp = spacy.load("en")
trainer = Trainer(config.load("config_spacy.yml"))  # Create a trainer that uses this config
training_data = load_data('rasa-flight.json')  # Load the training data
interpreter = trainer.train(training_data)  # Create an interpreter by training the model

conn = sqlite3.connect('flight.db')
c = conn.cursor()

INIT = 0
DATE_REQ = 1
AIRPORT_CHOOSE = 2
FLIGHT_LIST = 3

state = INIT
Departure = ""
Arrival = ""
F_num = ""
Date = ""


def send_message(state, message):

    new_state, response = respond(state, message)

    return new_state, response


def main(message):
    global state
    state, response = send_message(state, message)
    return response


def respond(state, message):
    global Departure, Arrival, F_num, Date
    if state == INIT:
        intent, search_type, airport_list, date = interpret(message, state)
        if intent == "ask_detail" or intent == "greet":
            return INIT, "Hi, I can help you search any flight you want, " \
                         "by Flight number, Airport or Route with the date!"
        if intent == "search_flight":
            if date == "0":
                return DATE_REQ, "what date do you want to search?"
            else:
                Date = date
            if search_type == 2:
                F_num = airport_list
                Departure = ""
                Arrival = ""
                response = get_list(Departure, Arrival, F_num, Date)
                return FLIGHT_LIST, response+"\nwhich one do you want to check in detail?"
            else:
                F_num = ""
                arr_len = len(airport_list["arr"]["data"])
                dep_len = len(airport_list["dep"]["data"])
                if arr_len == 1:
                    Arrival = airport_list["arr"]["data"][0]["iata"]
                if dep_len == 1:
                    Departure = airport_list["dep"]["data"][0]["iata"]
                if dep_len == 1 and arr_len == 1:
                    response = get_list(Departure, Arrival, F_num, Date)
                    return FLIGHT_LIST, response + "\nwhich one do you want to check in detail?"
                if dep_len > 1:
                    if arr_len > 1:
                        Arrival = airport_list["arr"]["data"]
                    Departure = airport_list["dep"]["data"]
                    k = min(dep_len, 3)
                    port_list = ""
                    for i in range(k):
                        port_list = port_list + airport_list["dep"]["data"][i]["iata"] + " : " + \
                                  airport_list["dep"]["data"][i]["name"]+'\n'
                    response = "{} airports available for departure, choose one you want by its code:\n".format(k) + port_list
                    return AIRPORT_CHOOSE, response

                if dep_len == 1 and arr_len > 1:
                    Arrival = airport_list["arr"]["data"]
                    k = min(arr_len, 3)
                    port_list = ""
                    for i in range(k):
                        port_list = port_list + airport_list["arr"]["data"][i]["iata"] + " : " + \
                                    airport_list["arr"]["data"][i]["name"] + '\n'
                    response = "{} airports available for arrival, choose one you want by its code.".format(k) + port_list
                    return AIRPORT_CHOOSE, response

    if state == DATE_REQ:
        Date = date2code(message)
        response = get_list(Departure, Arrival, F_num, Date)
        return FLIGHT_LIST, response + "\nwhich one do you want to check in detail?"

    if state == AIRPORT_CHOOSE:
        message = message.upper()
        if isinstance(Departure,str) is None:
            Departure=











def get_list(Dep, Arr, f_num, date):
    return "111"






def interpret(message, state):

    global interpreter, nlp
    data = interpreter.parse(message)
    doc = nlp(message)
    intent = data["intent"]["name"]
    if intent == "greet":
        return intent, {}, {}, {}

    if intent == "search_flight":
        airportlist = {}
        date = "0"
        ents = doc.ents
        for ent in ents:  # 提取地点 & 时间
            if ent.label_ == "GPE" or ent.label_ == "ORG":
                datype, airportcode = city2code(message, doc, ent.text)
                airportlist[datype] = airportcode.json()
            if  ent.label_ == "DATE":
                date = date2code(ent.text)
        flight_num = re.search(r"\b[A-Za-z]{2}[0-9]{1,4}\b|\b[A-Za-z]{1}[0-9]{2,5}\b|\b[0-9]{1}[A-Za-z]{1}[0-9]{1,4}\b", message)
        if flight_num:
            flight_num = flight_num.group(0)
            return intent, 2, flight_num, date
        # !!!!!! unknown的机场未处理
        return intent, 1, airportlist, date


def date2code(text):
    year = "2019"
    text = text.lower()
    month = re.search(r"\b[a-zA-Z]{3,4}\b", text).group(0)
    month_code={"jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06","jul":"07","aug":"08","sep":"09","sept":"09","oct":"10","nov":"11","dec":"12"}
    month = month_code[month]
    day = re.search(r"\b[0-9]{1,2}\b", text).group(0)
    if len(day)==1:
        day = "0" + day
    return year+month+day


def city2code(message, doc, text): # return datype: dep or arr, airportcode in json
    first_word = re.search("([\w']+)",text).group(1)
    index = message.find(first_word,0)
    n = 0
    datype = 0
    for i in range(index):
        if message[i] == " ":
            n = n + 1
    ancestor_list = list(doc[n].ancestors)
    dep_word = {"from", "depart", "departure", "leave"}
    arr_word = {"to", "arrive", "reach", "get", "go"}
    for i in range(len(ancestor_list)):
        if str(ancestor_list[i]) in dep_word:
            datype = "dep"
        elif str(ancestor_list[i]) in arr_word:
            datype = "arr"
    if datype == 0:
        datype = "unknown"

    url = 'http://www.flightstats.com/v2/api-next/search/airline-airport?query={}&type=airport&rqid=wz0b9ty387c'.format(text)
    r = requests.get(url)
    return datype, r


def telegram(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text=main(update.message.text))


def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")


# telegram start
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)
echo_handler = MessageHandler(Filters.text, telegram)
dispatcher.add_handler(echo_handler)
updater.start_polling()
