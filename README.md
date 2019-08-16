# Chatbot

In this chatbot project, we build an intelligent chatbot using natural language that can help you search flights and get their information on Telegram.

For the interpretation of natural language, we mainly use Rasa NLU framework, spaCy package and pattern matching to extract intention and entities. Besides, some other techniques have been applied: SQL for temporary flights storage and suggestion providing; State machine for implement multi-round query technique; Incremental slot filling for constructing params in filtering.

Furthermore, the project uses python-telegram-bot library for Telegram access, lxml library for processing HTML, and pytesseract library for optical character recognition in the website.

In conclusion, our chatbot is able to get information about what you asked from the Internet and add filters by your request, thus provide you with various details about the flight you need.
