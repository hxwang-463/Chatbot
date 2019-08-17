# Flight-Search Chatbot
In this chatbot project, we build an intelligent chatbot using natural language that can help you search flights and get their information on Telegram.

## Main Function
* Search all the flight by its departure and arrival city in one certain day
* Search flights by its flight number in one certain day
* Filter the flight results by the airline, departure/ arrival time range, or the on-time performance
* Get details about scheduled departure/ arrival time, actual departure/arrival time, historical on-time performance, status (preparing, cancel, arrived, etc.), type of aircraft, length of route, etc.
*
![image](Sample_dialogues/1.gif)![image](Sample_dialogues/2.gif)![image](Sample_dialogues/3.gif)


## Getting started
**Create a new bot belongs to you on Telegram in 3 easy steps**
* search [*BotFather*](telegram.me/BotFather) on Telegram
* text **/newbot** to BotFather, and follow directions shown
* get the control TOKEN of your bot

**Replace the TOKEN in main.py, line 17**

**Run main.py, then chat to your bot.**

## Enviroments and Packages

**Python 3.7 with Anaconda**
### Rasa NLU
[**Rasa**](rasa.com) is an open source machine learning framework for building contextual AI assistants and chatbots.

Install with:

`$ pip install rasa-x --extra-index-url https://pypi.rasa.com/simple`

Using by:
```Python
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config

trainer = Trainer(config.load("config_spacy.yml"))  # Create a trainer that uses this config
training_data = load_data('rasa-flight.json')  # Load the training data
interpreter = trainer.train(training_data)  # Create an interpreter by training the model
```

### spaCy
[**spaCy**](spacy.io) is a Industrial-Strength Natural Language Processing toolkit, which contains pre-trained models for multi-language.

Install and Download pre-trained model for English with:

`$ pip install -U spacy`
`$ python -m spacy download en_core_web_sm`

Using by:
```Python
import spacy
nlp = spacy.load("en_core_web_sm") # load English model
```

### Other Packages
**Telegram API:** python-telegram-bot  `$ pip install python-telegram-bot --upgrade`

**Requests:** HTTP library for Python   `$ pip install requests`

**lxml:** Library for processing HTML  `$ pip install lxml`

**PIL:** Python Image Library  `$ pip install pillow`

**Pytesseract:** Python wrapper for Google's Tesseract-OCR  `$ pip install pytesseract`

## Notes
1. Put **config_spacy.yml** and **rasa-flight.json** in the same path as **main.py**
2. When comes to **City** and **Airlines**, **Capitalize** the first letter of each word
