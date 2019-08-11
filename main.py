from telegram.ext import Updater, CommandHandler, Filters, MessageHandler
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config
from lxml import etree
from PIL import Image
import re
import spacy
import sqlite3
import requests
import pytesseract
import os
import logging


TOKEN = "874251429:AAGbXIM9_cn6ArfilkiFtm0AUK4Hq_PoefM"

nlp = spacy.load("en")
trainer = Trainer(config.load("config_spacy.yml"))  # Create a trainer that uses this config
training_data = load_data('rasa-flight.json')  # Load the training data
interpreter = trainer.train(training_data)  # Create an interpreter by training the model

conn = sqlite3.connect('flight.db', check_same_thread = False)
c = conn.cursor()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

INIT = 0
DATE_REQ = 1
AIRPORT_CHOOSE = 2
FLIGHT_LIST = 3
GET_DETAIL = 4

state = INIT
Departure = ""
Arrival = ""
F_num = ""
Date = ""
Cache = ""
params = {"dep1": "", "dep2": "", "arr1": "", "arr2": "", "airlines": "", "rate": ""}
neg_params = {"dep1": "", "dep2": "", "arr1": "", "arr2": "", "airlines": ""}
specific_flight = {}


def send_message(state, message):

    new_state, response = respond(state, message)

    return new_state, response


def main(message):
    global state
    state, response = send_message(state, message)
    return response


def respond(state, message):
    global Departure, Arrival, F_num, Date, Cache, params, neg_params, c
    if state == INIT:
        intent, search_type, airport_list, date = interpret(message, state)
        if intent == "ask_detail" or intent == "greet":
            return INIT, "Hi, I can help you search any flight you want, " \
                         "by Flight number, Airport or Route with the date!"
        elif intent == "search_flight":
            if date == "0" and Date == "":
                Cache = message
                return DATE_REQ, "what date do you want to search?"
            else:
                Date = date
            if search_type == 2:
                F_num = airport_list
                Departure = ""
                Arrival = ""
                response = get_list(Departure, Arrival, F_num, Date)
                return FLIGHT_LIST, response+"\nwhich one or what kind of flight do you want?"
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
                    if response == "NO FOUND":
                        return INIT, "sorry, no found!"
                    return FLIGHT_LIST, response + "\nwhich one or what kind of flight do you want to check in detail?"
                if dep_len > 1:
                    if arr_len > 1:
                        Arrival = airport_list["arr"]["data"]
                    Departure = airport_list["dep"]["data"]
                    k = min(dep_len, 3)
                    port_list = ""
                    for i in range(k):
                        port_list = port_list + airport_list["dep"]["data"][i]["iata"] + " : " + \
                                  airport_list["dep"]["data"][i]["name"]+'\n'
                    response = "{} airports available for departure, " \
                               "choose one you want by its code:\n".format(k) + port_list
                    return AIRPORT_CHOOSE, response

                if dep_len == 1 and arr_len > 1:
                    Arrival = airport_list["arr"]["data"]
                    k = min(arr_len, 3)
                    port_list = ""
                    for i in range(k):
                        port_list = port_list + airport_list["arr"]["data"][i]["iata"] + " : " + \
                                    airport_list["arr"]["data"][i]["name"] + '\n'
                    response = "{} airports available for arrival," \
                               " choose one you want by its code.\n".format(k) + port_list
                    return AIRPORT_CHOOSE, response
        else:
            return INIT, "sorry I don't understand.\nI can help you search any flight you want, " \
                         "by Flight number, Airport or Route with the date!"

    if state == DATE_REQ:
        Date = date2code(message)
        new_state, response = respond(INIT, Cache)
        return new_state, response

    if state == AIRPORT_CHOOSE:
        message = message.lower()
        print(Departure)
        if isinstance(Departure, str) is False:
            Departure = re.search(r"\b[a-z]{3}\b", message).group(0)
            if isinstance(Arrival, str) is False:
                k = min(len(Arrival), 3)
                port_list = ""
                for i in range(k):
                    port_list = port_list + Arrival[i]["iata"] + " : " + \
                                Arrival[i]["name"] + '\n'
                response = "{} airports available for arrival," \
                           " choose one you want by its code.".format(k) + "\n" + port_list
                return AIRPORT_CHOOSE, response
            else:
                response = get_list(Departure, Arrival, F_num, Date)
                if response == "NO FOUND":
                    return INIT, "sorry, no found!"
                return FLIGHT_LIST, response + "\nwhich one or what kind of flight do you want to check in detail?"
        else:
            Arrival = re.search(r"\b[a-z]{3}\b", message).group(0)
            response = get_list(Departure, Arrival, F_num, Date)
            if response == "NO FOUND":
                return INIT, "sorry, no found!"
            return FLIGHT_LIST, response + "\nwhich one or what kind of flight do you want to check in detail?"

    if state == FLIGHT_LIST:
        if re.search(r"^[0-9]{1,2}$", message) is not None:
            fill_specific(message)
            return GET_DETAIL, "Greet!\nNow you can ask more information about this flight!"
        intent, airlines, time, rate = interpret(message, state)
        if intent == "ask_detail":
            return FLIGHT_LIST, "you can choose one by its code or number, " \
                                "also you can add filters about the airlines, departure time or on-time rate."
        if intent == "add_filter":
            make_params(message, airlines, time, rate)
            response = print_flight(c, params, neg_params)
            if response:
                return FLIGHT_LIST, "I can find these flights:\n" + response + \
                       "choose one by its code or add more filters!"
            else:
                params = {"dep1": "", "dep2": "", "arr1": "", "arr2": "", "airlines": "", "rate": ""}
                neg_params = {"dep1": "", "dep2": "", "arr1": "", "arr2": "", "airlines": ""}
                return FLIGHT_LIST, "sorry, no found~\nyou can choose again!"


def fill_specific(num):
    global c, specific_flight, Departure, Arrival, F_num
    query = "SELECT * FROM flight WHERE f0={}".flomat(num)
    c.execute("{}".format(query))
    results = c.fetchall()
    F_num = results[0][3]
    specific_flight["dep"] = results[0][4]
    specific_flight["dep_real"] = results[0][5]
    specific_flight["arr"] = results[0][7]
    specific_flight["arr_real"] = results[0][8]
    specific_flight["rate"] = results[0][10]
    specific_flight["status"] = results[0][11]

    url = "http://www.variflight.com/schedule/{}-{}-{}.html?AE71649A58c77=&fdate=20190810".\
        format(Departure, Arrival, F_num)






def make_params(message, airlines, time, rate):
    global params, neg_params
    if time["dep1"]:
        if time["deptorf"]:
            params["dep1"] = time["dep1"]
        else:
            neg_params["dep1"] = time["dep1"]
    if time["dep2"]:
        if time["deptorf"]:
            params["dep2"] = time["dep2"]
        else:
            neg_params["dep2"] = time["dep2"]
    if time["arr1"]:
        if time["arrtorf"]:
            params["arr1"] = time["arr1"]
        else:
            neg_params["arr1"] = time["arr1"]
    if time["arr2"]:
        if time["arrtorf"]:
            params["arr2"] = time["arr2"]
        else:
            neg_params["arr2"] = time["arr2"]
    if rate:
        params["rate"] = rate
    if airlines["name"]:
        if airlines["torf"]:
            params["airlines"] = airlines["name"]
        else:
            neg_params["airlines"] = airlines["name"]


def get_list(dep, arr, f_num, date):  # html ; sql
    global c, params, neg_params
    if f_num:
        put_flights_sql('http://www.variflight.com/flight/fnum/{}.html?AE71649A58c77&fdate={}'.format(f_num, date))
    else:
        put_flights_sql("http://www.variflight.com/flight/{}-{}.html?AE71649A58c77&fdate={}".format(dep, arr, date))
    c.execute("SELECT count(*) FROM flight")
    length = c.fetchall()[0][0]
    params = {"dep1": "", "dep2": "", "arr1": "", "arr2": "", "airlines": "", "rate": ""}
    neg_params = {"dep1": "", "dep2": "", "arr1": "", "arr2": "", "airlines": ""}
    if length == 0:
        response = "NO FOUND"
        return response
    elif length == 1:
        response = "Only ONE flight has been found!\n"
    else:
        response = "{} flights has been found!\n\n".format(length)
    results = print_flight(c, params, neg_params)

    return response + results


def put_flights_sql(url):
    global c
    c.execute("CREATE TABLE IF NOT EXISTS flight(f0 int,f1 text,f2 text,f3 text,f4 text,f5 text,"
              "f6 text,f7 text,f8 text,f9 text,f10 text,f11 text,f12 int,f13 int)")
    c.execute("DELETE from flight")

    base_url = 'http://www.variflight.com'
    r = requests.get(url)
    selector = etree.HTML(r.text)
    b = selector.xpath('//*[@class="searchlist_innerli"]')

    if b:
        name = selector.xpath('//*[@class="tit"]/h1/@title')[0]
        log = "{0}航班存在信息：".format(name)
        r = requests.Session()
        resp = r.get(url)
        selector = etree.HTML(resp.text)
        mylist = selector.xpath('//*[@id="list"]/li')
        num = 0

        for selector in mylist:
            is_share = selector.xpath('a[@class="list_share"]//text()')  # 共享航班
            if (len(is_share) == 1):
                continue
            a = selector.xpath('div[@class="li_com"]/span[1]/b/a//text()')  # 航班信息
            f1 = a[0]
            f2 = a[1][:2]
            f3 = a[1]
            f4 = selector.xpath('div[@class="li_com"]/span[2]/@dplan')  # 计划起飞
            f5 = selector.xpath('div[@class="li_com"]/span[3]/img/@src')  # 实际起飞
            if f5:
                url = base_url + f5[0]
                resp = r.get(url)
                filename = './pictures' + '.png'
                with open(filename, 'wb') as f:
                    f.write(resp.content)
                f5 = pytesseract.image_to_string(Image.open(filename))
                os.remove(filename)
                if len(f5) < 5:  # 若识别不出‘:’或者‘.’ 进行拼接
                    f5 = f5[:2] + ':' + f5[2:]
            else:
                f5 = '--:--'

            f6 = selector.xpath('div[@class="li_com"]/span[4]/text()')  # 出发地
            f7 = selector.xpath('div[@class="li_com"]/span[5]/@aplan')  # 计划到达
            f8 = selector.xpath('div[@class="li_com"]/span[6]/text()')  # 实际到达
            f8 = re.sub(r"[\s+\.\!\/_,$%^*(+\"\')]+|[+?【】？~@#￥%……&*]+|\\n+|\\r+|(\\xa0)+|(\\u3000)+|\\t", "",
                        str(f8[0]))
            if f8:
                f8 = '--:--'
            else:
                f8 = selector.xpath('div[@class="li_com"]/span[6]/img/@src')  # 实际到达
                url = base_url + f8[0]
                resp = r.get(url)
                filename = './pictures' + '.png'
                with open(filename, 'wb') as f8:
                    f8.write(resp.content)
                f8 = pytesseract.image_to_string(Image.open(filename))
                os.remove(filename)
                if len(f8) < 5:
                    f8 = f8[:2] + ':' + f8[2:]

            f9 = selector.xpath('div[@class="li_com"]/span[7]/text()')  # 到达地
            h = selector.xpath('div[@class="li_com"]/span[8]/img/@src')  # 准点率
            f11 = selector.xpath('div[@class="li_com"]/span[9]/text()')  # 状态
            h = base_url + h[0]  # 准点率
            filename = './pictures' + '.png'

            q = r.get(h)
            with open(filename, 'wb') as t:
                t.write(q.content)
            q = pytesseract.image_to_string(Image.open(filename))
            os.remove(filename)
            if q == "100%":
                q = "99.99%"
            if len(q) < 6:
                q = q[:2] + '.' + q[2:]
            f10 = q[:5]
            f12=int(f4[0][:2])
            f13=int(f7[0][:2])

            value = "VALUES({},'{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}', {}, {})" \
                .format(num, f1, f2, f3, f4[0], f5, f6[0], f7[0], f8, f9[0], f10, f11[0], f12, f13)
            c.execute("INSERT INTO flight(f0,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13) {}".format(value))
            num = num + 1

    else:
        name = selector.xpath('//*[@id="byNumInput"]/@value')[0]
        log = "{0}航班不存在信息".format(name)

    c.execute("commit")


def print_flight(c, params, neg_params):
    query = 'SELECT * FROM flight'
    text = []
    if params["dep1"]:
        text = text + ["f12>{}".format(params["dep1"])]
    if params["dep2"]:
        text = text + ["f12<{}".format(params["dep2"])]
    if params["arr1"]:
        text = text + ["f13>{}".format(params["arr1"])]
    if params["arr2"]:
        text = text + ["f13<{}".format(params["arr2"])]

    if neg_params["dep1"]:
        text = text + ["f12<{}".format(neg_params["dep1"])]
    if neg_params["dep2"]:
        text = text + ["f12>{}".format(neg_params["dep2"])]
    if neg_params["arr1"]:
        text = text + ["f13<{}".format(neg_params["arr1"])]
    if neg_params["arr2"]:
        text = text + ["f13>{}".format(neg_params["arr2"])]

    if params["airlines"]:
        airline_code = airline2code(params["airlines"])
        text = text + ["f2='{}'".format(airline_code)]
    if neg_params["airlines"]:
        airline_code = airline2code(neg_params["airlines"])
        text = text + ["f2!='{}'".format(airline_code)]

    if params["rate"]:
        text = text + ["f10>{}".format(params["rate"])]

    t = ' AND '.join(text)
    if t:
        p = query + ' WHERE ' + t
    else:
        p = query
    c.execute("{}".format(p))
    results = c.fetchall()
    response = ""
    for r in results:
        response = response+"NO.{} {} : {}-{}  {}\n".format(r[0], r[3].ljust(6, " "), r[4], r[7], r[11])

    return response


def airline2code(airline):
    url = 'http://www.flightstats.com/v2/api-next/search/airline-airport?query={}&type=airline&rqid=wz0b8ty387c'.format(airline)
    r = requests.get(url)
    return r.json()["data"][0]["fs"]


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
            if ent.label_ == "DATE":
                date = date2code(ent.text)
        flight_num = re.search(r"\b[A-Za-z]{2}[0-9]{1,4}\b|\b[A-Za-z]{1}[0-9]{2,5}\b|\b[0-9]{1}[A-Za-z]{1}[0-9]{1,4}\b",
                               message)
        if flight_num:
            flight_num = flight_num.group(0)
            return intent, 2, flight_num, date
        # !!!!!! unknown的机场未处理
        return intent, 1, airportlist, date
    elif intent == "add_filter":
        airlines = {}
        airlines["name"] = ""
        airlines["torf"] = ""
        time = {}
        time["dep1"] = ""
        time["dep2"] = ""
        time["arr1"] = ""
        time["arr2"] = ""
        time["arrtorf"] = ""
        time["deptorf"] = ""
        rate = ""
        ents = doc.ents
        e = []
        for i in ents:
            e.append(str(i))
        torf = negated_ents(message, e)
        for ent in ents:
            if ent.label_ == "TIME" or ent.label_ == "CARDINAL":
                time_torf = torf[ent.text]
                t_dict = {"before dawn": ["00", "06"], "morning": ["03", "11"],
                          "noon": ["10", "14"], "afternoon": ["12", "18"], "evening": ["18", "21"],
                          "night": ["19", "22"], "midnight": ["21", "24"]}
                index = message.find(ent.text, 0)
                n = 0
                for i in range(index):
                    if message[i] == " " or message[i] == ",":
                        n = n + 1
                ancestor_list = ",".join(str(i) for i in list(doc[n].ancestors))
                if "arrive" in ancestor_list:
                    time["arrtorf"] = time_torf
                    if ent.text in t_dict:
                        time["arr1"] = t_dict[ent.text][0]
                        time["arr2"] = t_dict[ent.text][1]
                    else:
                        hour = re.search(r"[0-9]{1,2}", ent.text).group(0)
                        if "before" in ancestor_list:
                            time["arr2"] = hour
                        else:
                            time["arr1"] = hour
                else:
                    time["deptorf"] = time_torf
                    if ent.text in t_dict:
                        time["dep1"] = t_dict[ent.text][0]
                        time["dep2"] = t_dict[ent.text][1]
                    else:
                        hour = re.search(r"[0-9]{1,2}", ent.text).group(0)
                        if "before" in ancestor_list:
                            time["dep2"] = hour
                        else:
                            time["dep1"] = hour

            elif ent.label_ == "PERCENT":
                rate = re.search(r"[0-9]{2}", ent.text).group(0)
            else:
                airlines["torf"] = torf[ent.text]
                airlines["name"] = ent.text
        return intent, airlines, time, rate


def negated_ents(phrase, ent_vals):
    ents = [e for e in ent_vals if e in phrase]
    ends = sorted([phrase.index(e) + len(e) for e in ents])
    start = 0
    chunks = []
    for end in ends:
        chunks.append(phrase[start:end])
        start = end
    result = {}
    for chunk in chunks:
        for ent in ents:
            if ent in chunk:
                if "not" in chunk or "n't" in chunk:
                    result[ent] = False
                else:
                    result[ent] = True
    return result


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
    index = message.find(first_word, 0)
    n = 0
    datype = 0
    for i in range(index):
        if message[i] == " " or message[i] == ",":
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

    url = 'http://www.flightstats.com/v2/api-next/search/airline-airport?query={}&type=airport&rqid=wz0b7ty387c'.format(text)
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
