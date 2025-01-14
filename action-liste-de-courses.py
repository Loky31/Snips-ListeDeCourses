#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import configparser
import io
import requests
from hermes_python.hermes import Hermes
from hermes_python.ffi.utils import MqttOptions

state = {'confirmationPurge': False}


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

def send():
    liste = load_list()
    if not liste:
        return "La liste de courses est vide"
    config = read_configuration_file()
    telegramData = {
        "my_token": config['secret']['token'],
        "my_chat_id": config['secret']['chat_id'],
        "msg": "Liste de courses: {}".format(", ".join(liste))
    }
    #print ("https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}".format(telegramData.get("my_token"),telegramData.get("my_chat_id"),telegramData.get("msg")))
    try:
        response = requests.get(
            "https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}".format(telegramData.get("my_token"),telegramData.get("my_chat_id"),telegramData.get("msg"))
        )
    except requests.exceptions.Timeout:
        return "Telegram ne répond pas"
    #print (response.text)
    #code = response.status_code
    if b"\"ok\":true" in response.content:
        return "J'ai envoyé la liste de courses par Telegram"
    else:
        return "Oups, Ca n'a pas marché"

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
