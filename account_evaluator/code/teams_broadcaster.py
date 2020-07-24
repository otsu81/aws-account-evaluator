import json
import logging
import os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class TeamsBroadcaster:

    def __init__(self):
        pass

    def __build_message(self, input_dict, title):

        facts = list()
        for k, v in input_dict.items():
            facts.append(
                {
                    "name": k,
                    "value": json.dumps(v, indent=4, default=str)
                }
            )

        message = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": "Lambda account evaluator result",
            "themeColor": "0072C6",
            "title": title,
            "sections": [
                {
                    "text": "Account summaries",
                    "facts": facts
                }
            ]
        }
        return message

    def send_message(self, input_dict, title=''):
        if title == '':
            title = 'Default title'
        message = self.__build_message(input_dict, title)

        req = Request(os.environ['TEAMS_HOOK_URL'], json.dumps(message).encode('utf-8'))
        try:
            response = urlopen(req)
            response.read()
            logging.info("Message posted")
        except HTTPError as e:
            logging.error(f"Request failed: {e.code} {e.reason}")
        except URLError as e:
            logging.error(f"Server connection failed: {e.reason}")
