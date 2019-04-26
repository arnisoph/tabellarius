# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import email.charset
import email.header
import email.message
import email.utils
from sys import version_info as python_version

from tabellarius.misc import CaseInsensitiveDict


class Mail():
    """
    A dict representing a mail
    """

    def __init__(self, logger, charset='utf-8', headers={}, body='', mail_native=None):
        self.logger = logger
        self.charset = charset
        self.mail_native = mail_native

        self._headers = CaseInsensitiveDict(headers)
        self._body = body

        if mail_native:
            self.__parse_native_mail()

#    def clean_value(self, value, encoding=None):
#        """
#        Converts value to a given encoding
#        """
#        if isinstance(value, bytes) and encoding:
#            return value.decode(encoding)
#        elif isinstance(value, bytes):
#            return value.decode('unicode_escape')
#
#        return value

    def set_header(self, name, value):
        """
        Set mail header
        """
        self._headers[name] = value
        return self._headers

    def get_header(self, name, default=None):
        """
        Return mail header by name
        """
        return self._headers.get(name.lower(), default)

    def update_headers(self, headers):
        """
        Update mail headers
        """
        self._headers.update(headers)
        return self._headers

    def get_headers(self):
        """
        Get all mail headers
        """
        return self._headers

    def set_body(self, body):
        """
        Set mail body
        """
        self._body = body
        return self._body

    def get_body(self):
        """
        Return mail body
        """
        return self._body

    def get_native(self):
        """
        Returns a native (email.message.Message()) object
        """
        if not self.mail_native:
            self.mail_native = email.message.Message()

            email.charset.add_charset(self.charset, email.charset.QP, email.charset.QP)
            c = email.charset.Charset(self.charset)
            self.mail_native.set_charset(c)

            if 'message-id' not in [header.lower() for header in self.get_headers()]:
                self.reset_message_id()

            for field_name, field_value in self.get_headers().items():
                self.mail_native.add_header(field_name, field_value)

            self.mail_native.set_payload(self._body, charset=self.charset)
        return self.mail_native

    def reset_message_id(self, target='self'):
        """
        Reset the Message-Id or add it if missing
        """
        message_id = email.utils.make_msgid()

        if target == 'native':
            self.mail_native['Message-Id'] = message_id

        return self.set_header('Message-Id', message_id)

    def __parse_native_mail(self):
        """
        Parses a native (email.message.Message()) object
        """
        self._headers = CaseInsensitiveDict()
        self._body = ''

        if not self.mail_native.is_multipart():  # TODO handle multipart mails
            charset = self.mail_native.get_content_charset()
            if python_version[1] == 2 or charset is None:
                self.set_body(self.mail_native.get_payload())  # pragma: no cover
            else:
                self.set_body(self.mail_native.get_payload(decode=True).decode(charset))

        for field_name in self.mail_native.keys():
            if field_name in self._headers.keys():
                continue
            field_value = self.mail_native.get_all(field_name)

            # Change parsing behaviour for headers that could contain encoded strings
            if field_name in ['Subject', 'From', 'To', 'Cc', 'Bcc']:
                field_value = str(email.header.make_header(email.header.decode_header(self.mail_native.get(field_name))))
                #if isinstance(field_value, list):
                #    field_value_list = field_value
                #    field_value = ''
                #    for val in field_value_list:
                #        if val[1]:
                #            field_value += self.clean_value(val[0], val[1])
                #        elif isinstance(val[0], bytes):
                #            field_value += self.clean_value(val[0])
                #        else:
                #            field_value += val[0]
                #else:
                #    field_value = self.clean_value(field_value[0][0], field_value[0][1])
                self._headers[field_name] = field_value
            elif len(field_value) > 1:
                self._headers[field_name] = field_value
            else:
                self._headers[field_name] = field_value[0]

        if 'message-id' not in [header.lower() for header in self.mail_native.keys()]:
            self.reset_message_id(target='native')
