import re

import telegram
from telegram.ext import CommandHandler, BaseFilter, MessageHandler, DispatcherHandlerStop

from tg_bot import dispatcher
from tg_bot.modules.sql import cust_filters_sql as sql

HANDLER_GROUP = 10


class RegexSearcher(BaseFilter):
    def __init__(self, chat_id, word):
        super().__init__()
        self.matched_word = word
        self.pattern = "( |^)" + self.matched_word + "( |$)"
        self.chat_id = chat_id

    def filter(self, message):
        return bool(message.text
                    and message.chat_id == self.chat_id
                    and re.search(self.pattern, message.text, flags=re.IGNORECASE))

    def __eq__(self, other):
        return other == (self.matched_word, self.chat_id)

    def __str__(self):
        return self.matched_word

    def __repr__(self):
        return "<RegexSearcher for {} by {} in chat {}>".format(self.matched_word, self.pattern, self.chat_id)


def load_filters():
    all_filters = sql.get_all_filters()

    print("Loading {} filters".format(len(all_filters)))
    if not all_filters:
        return

    for filt in all_filters:
        add_filter(filt.chat_id, filt.keyword, filt.reply)


def add_filter(chat_id, keyword, reply):
    custom_handler = MessageHandler(RegexSearcher(int(chat_id), keyword),
                                    lambda b, u: u.effective_message.reply_text(reply))
    dispatcher.add_handler(custom_handler, HANDLER_GROUP)


def list_handlers(bot, update):
    chat = update.effective_chat
    handlers = dispatcher.handlers.get(HANDLER_GROUP, [])

    filter_list = "Current filters in this chat:\n"
    for h in handlers:
        if h.filters.chat_id == chat.id:
            entry = " - {}\n".format(h.filters.matched_word)
            if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
                update.effective_message.reply_text(filter_list)
                filter_list = entry
            else:
                filter_list += entry

    if not filter_list == "Current filters in this chat:\n":
        update.effective_message.reply_text(filter_list)
    else:
        update.effective_message.reply_text("No filters are active here!")


def filters(bot, update):
    text = update.effective_message.text
    args = text.split(None, 2)  # use python's maxsplit to separate Cmd, keyword, and reply_text
    keyword = args[1]
    reply = args[2]

    sql.add_filter(update.effective_chat.id, keyword, reply)

    add_filter(update.effective_chat.id, keyword, reply)

    update.effective_message.reply_text("Handler Added!")
    raise DispatcherHandlerStop


def stop_filter(bot, update, args):
    chat = update.effective_chat
    for handler in dispatcher.handlers.get(HANDLER_GROUP):
        if handler.filters == (args[0], chat.id):
            sql.remove_filter(chat.id, args[0])
            dispatcher.remove_handler(handler, HANDLER_GROUP)
            update.effective_message.reply_text("Yep, I'll stop replying to that.")
            return

    update.effective_message.reply_text("That's not a current filter - run /list for all filters.")

__help__ = """
 - /filter <keyword> <reply message>: add a filter to this chat. bot will now reply the message whenever 'keyword' is mentioned.
 - /stop <filter keyword>: stop that filter.
 - /list: list all active filters in this chat
"""


FILTER_HANDLER = CommandHandler("filter", filters)
STOP_HANDLER = CommandHandler("stop", stop_filter, pass_args=True)
LIST_HANDLER = CommandHandler("list", list_handlers)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(LIST_HANDLER)

load_filters()
print("All filters loaded")