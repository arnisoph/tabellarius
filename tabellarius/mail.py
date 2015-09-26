# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
#from time import sleep
import sys

# Third party libs
import email.message
sys.path.insert(0, './imapclient/imapclient')  # TODO this is ugly, improve it


class Mail(dict):
    mail_native = email.message.Message()

    def __init__(self, mail=None):
        self.mail_native = mail
        self.parse_email_object()

    def parse_email_object(self):
        fields_to_store = {
            'content-type': None,
            'date': None,
            'delivered-to': {'multiple': True},
            'from': None,
            'list-id': None,
            'message-id': None,
            'received': {'multiple': True, 'split': True},
            'return-path': None,
            'subject': None,
            'to': None,
            'user-agent': None,
        }

        for field, properties in fields_to_store.items():
            if type(properties) is dict:
                if properties.get('multiple', None):
                    fields = self.mail_native.get_all(field)
                    if properties.get('split', None):
                        _fields = []
                        for f in fields:
                            _fields.append(f.split('\r\n'))
                        _fields = fields
                    self[field] = fields
                else:
                    self[field] = self.mail_native.get(field)
            else:
                self[field] = self.mail_native.get(field)
