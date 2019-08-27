#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import configparser
import io
import requests
import telegram
from hermes_python.hermes import Hermes
from hermes_python.ffi.utils import MqttOptions

state = {'confirmationPurge': False}

config = read_configuration_file()
my_token = 'config['secret']['TOKEN']'
my_chat_id= 'config['secret']['CHAT_ID']'

#liste = load_list()
#if not liste:
        #return "La liste de courses est vide"
#my_msg = '"Liste de courses: {}".format(", ".join(liste))'

class SnipsConfigParser(configparser.SafeConfigParser):
    def to_dict(self):
        return {
            section: {
                option_name: option
                for option_name, option in self.items(section)
            }
            for section in self.sections()
        }


def read_configuration_file():
    try:
        with io.open(
            "config.ini",
            encoding="utf-8"
        ) as f:
            conf_parser = SnipsConfigParser()
            conf_parser.readfp(f)
            return conf_parser.to_dict()
    except (IOError, configparser.Error):
        return dict()


def load_list():
    try:
        with open("liste.txt", "r") as infile:
            return set(json.load(infile))
    except IOError:
        return set()


def save_list(data):
    with open("liste.txt", "w") as outfile:
        json.dump(list(data), outfile)


def add_item(item):
    liste = load_list()
    if item in liste:
        return "Il y a déjà {} sur la liste de courses".format(item)
    liste.add(item)
    save_list(liste)
    return "J'ai ajouté {} sur la liste de courses".format(item)


def del_item(item):
    liste = load_list()
    if item not in liste:
        return "Il n'y a pas de {} sur la liste de courses".format(item)
    liste.remove(item)
    save_list(liste)
    return "J'ai supprimé {} de la liste de courses".format(item)


def get_list():
    liste = load_list()
    if not liste:
        return "La liste de courses est vide"
    return "Voici ce qu'il y a sur la liste de courses: {}".format(
        ", ".join(liste))


def del_list():
    save_list(set())
    return "J'ai purgé la liste de courses"


def send_telegram(msg,chat_id,token):
    bot = telegram.Bot(token=token)
	bot.sendMessage(chat_id=chat_id, text=msg)

def send():
    liste = load_list()
    if not liste:
        return "La liste de courses est vide"
	config = read_configuration_file()
	my_token = config['secret']['TOKEN']
	my_chat_id= config['secret']['CHAT_ID']
	my_msg = "Liste de courses: {}".format(", ".join(liste))
	send_telegram(my_msg,my_chat_id,my_token)
	return "J'ai envoyé la liste de courses par Telegram"    

def intent_callback(hermes, intent_message):
    intent_name = intent_message.intent.intent_name.replace("Loky31:", "")
    result = None
    if intent_name == "addItem":
        result = add_item(intent_message.slots.Item.first().value)
    elif intent_name == "delItem":
        result = del_item(intent_message.slots.Item.first().value)
    elif intent_name == "getList":
        result = get_list()
    elif intent_name == "sendSMS":
        result = send()

    if state['confirmationPurge']:
        state['confirmationPurge'] = False
        if intent_name == "confirmation":
            result = del_list()
        elif intent_name == "annulation":
            result = "Pardon, je conserve la liste de courses"

    if intent_name == "delList":
        state['confirmationPurge'] = True
        hermes.publish_continue_session(
            intent_message.session_id,
            "Voulez-vous vraiment purger la liste de courses ?",
            ["Loky31:confirmation", "Loky31:annulation"]
        )

    if result is not None:
        hermes.publish_end_session(intent_message.session_id, result)


if __name__ == "__main__":
    mqtt_opts = MqttOptions()
    with Hermes(mqtt_options=mqtt_opts) as h:
        h.subscribe_intents(intent_callback).start()
