import requests
import json
import config
from random import randint
import unidecode
import time

import logging
from telegram import Update
import telegram.ext
from telegram.ext import Updater, CommandHandler, CallbackContext, Filters


mesenaatti_json = "https://api-mesenaatti.karolina.io/agitator/campaigns/1854/fi/"
emoji_list = ["👌", "🏅", "👍", "🦾"]
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def read_mesenaatti_json():
    r = requests.get(mesenaatti_json)
    if r.status_code == 200:
        return r.json()

def write_json_file(mese_json, file_name):
    with open(file_name, 'w') as outfile:
        json.dump(mese_json, outfile)

def compare_file_json(mese_json_url, file_name):
    try:
        with open(file_name) as json_file:
            file_json = json.load(json_file)
        if mese_json_url != file_json:
            return parse_changes(file_json, mese_json_url)
    except IOError:
        write_json_file(read_mesenaatti_json(), file_name)

def parse_changes(file_json, url_json):
    url_backers = url_json['campaign']['number_of_backers']
    file_backers = file_json['campaign']['number_of_backers']
    ammounts = {"dona" : [], "start_amount":  file_json["campaign"]["funding_reached"]}
    for i in range(url_backers - file_backers):
        for k in range(len(url_json['campaign']['rewards'])):
            if url_json['campaign']['rewards'][k]['stock_reserved'] != file_json['campaign']['rewards'][k]['stock_reserved']:
                ammounts["dona"].append(file_json['campaign']['rewards'][k]['amount'])
                file_json['campaign']['rewards'][k]['stock_reserved'] += 1
    return ammounts

def callback_compare_files(context: telegram.ext.CallbackContext):
    if context.job.context.chat.title == None:
        file_name = 'mese_json_' + unidecode.unidecode(str(context.job.context.chat.username)).replace(" ", "_") + '.txt'
    else:
        file_name = 'mese_json_' + unidecode.unidecode(str(context.job.context.chat.title)).replace(" ", "_") + '.txt'
    mese_json = read_mesenaatti_json()
    ammounts = compare_file_json(mese_json, file_name)
    if ammounts != None and ammounts["dona"]:
        for message in ammounts["dona"]:
            ammounts["start_amount"] += int(message)
            context.bot.send_message(chat_id=context.job.context.chat_id, text=str(message) + " € lahjoitettu! 🎉 Kiitos!" +emoji_list[randint(0, len(emoji_list) - 1)] +" Lahjoituksia yhteensä " + str(ammounts["start_amount"]) + " €. " + str(round(100 * (ammounts["start_amount"] + 1600) / 6000)) + "% saavutettu(6000 €)")
            time.sleep(1)
        write_json_file(mese_json, file_name)

def callback_timer(update, context):
    job_name = "mesenaatti_job" + str(update.message.chat_id)
    # print(context.job_queue.jobs())
    # print(context.job_queue.get_jobs_by_name(job_name))
    if len(context.job_queue.get_jobs_by_name(job_name)) == 0:
        context.job_queue.run_repeating(callback_compare_files, 60*30, first = 1, context=update.message, name=job_name)

def Stop_timer(update, context):
    job = context.job_queue.get_jobs_by_name("mesenaatti_job" + str(update.message.chat_id))
    if len(job) == 1:
        context.bot.send_message(chat_id=update.message.chat_id,
        text='Pysäytetty!')
        job[0].schedule_removal()

def main():
    updater = Updater(config.TOKEN, use_context=True)
    dp = updater.dispatcher
    updater.dispatcher.add_handler(CommandHandler('aloita_clippy', callback_timer, Filters.user(username="@Karli_K"), pass_job_queue=True))
    updater.dispatcher.add_handler(CommandHandler('pysayta', Stop_timer, Filters.user(username="@Karli_K"), pass_job_queue=True))
    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
