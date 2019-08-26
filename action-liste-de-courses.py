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


def send_sms():
    liste = load_list()
    if not liste:
        return "La liste de courses est vide"
    config = read_configuration_file()
    TOKEN= config['secret']['TOKEN'],
    CHAT_ID= config['secret']['CHAT_ID'],
    msg = "Liste de courses: {}".format(", ".join(liste))
    
	URL="https://api.telegram.org/bot{0}/sendMessage".format(TOKEN)
	curl -s -X POST $URL -d chat_id=$CHAT_ID -d text="$msg"
    

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
        result = send_sms()

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
