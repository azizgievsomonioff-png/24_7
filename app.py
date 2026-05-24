import telebot

bot = telebot.TleleBot("8679262246:AAGWLU6W2HcgckWRNJzuwg7rWft2lM_tLc4")

@bot.message_handler(func=lambda _: True)
def reply(message):
    bot.reply_to(message, "I'm alive")

bot.polling(none_stop=True)
