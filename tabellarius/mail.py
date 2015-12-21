# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from email.header import decode_header

#class Mail(dict):
#    mail_native = email.message.Message()
#
#    def __init__(self, logger, uid, mail=None):
#        self.logger = logger
#        self.uid = uid
#        self.mail_native = mail
#        self.parse_email_object()
#
#    def parse_email_object(self):
#        fields_to_store = {
#            # TODO store as much as possible, get rid of this static list
#            'content-type': None,
#            'date': None,
#            'delivered-to': {'multiple': True},
#            'from': None,
#            'list-id': None,
#            'message-id': None,
#            'received': {'multiple': True,
#                         'split': True},
#            'return-path': None,
#            'subject': None,
#            'to': None,
#            'user-agent': None,
#            'x-redmine-project': None,
#            'x-redmine-host': None,
#            'x-gitlab-project': None,
#        }
#
#        for field, properties in fields_to_store.items():
#            if type(properties) is dict:
#                if properties.get('multiple', None):
#                    fields = self.mail_native.get_all(field)
#                    if fields is None:
#                        continue
#                    #    self.logger.debug('Unable to parse raw mail with uid=%s: %s %s', self.uid, self.mail_native, field)
#                    #    raise ValueError('Unable to parse raw mail with uid=%s' % (self.uid))
#
#                    if properties.get('split', None):
#                        _fields = []
#                        for f in fields:
#                            _fields.append(f.split('\r\n'))
#                        _fields = fields
#                    self[field] = fields
#                else:
#                    field_value = self.mail_native.get(field)
#                    if field_value:
#                        self[field] = field_value
#            else:
#                field_value = self.mail_native.get(field)
#                if field_value:
#                    self[field] = field_value


class Mail(dict):
    """
    A dict representing a mail
    """

    def __init__(self, logger, mail=None, **kwargs):
        super(Mail, self).__init__()
        self.logger = logger
        self.mail_native = mail
        self.headers = {}

        self.parse_email_object()

    def clean_value(self, value, encoding):
        """
        Converts value to utf-8 encoding
        """
        #if PY3:
        if isinstance(value, bytes):
            return value.decode(encoding)
        #elif encoding not in ['utf-8', None]:
        #    return value.decode(encoding).encode('utf-8')
        return value

#    def _normalize_string(self, text):
#        '''Removes excessive spaces, tabs, newlines, etc.'''
#        conversion = {
#            # newlines
#            '\r\n\t': ' ',
#            # replace excessive empty spaces
#            '\s+': ' '
#        }
#        for find, replace in six.iteritems(conversion):
#            text = re.sub(find, replace, text, re.UNICODE)
#        return text

    def parse_email_object(self):
        """
        Parses the native (email.message.Message()) object
        """
        if not self.mail_native.is_multipart():
            #if PY3:
            self.headers['body'] = self.mail_native.get_payload(decode=True).decode('utf-8')
            #else:
            #    self['body'] = self.mail_native.get_payload(decode=True)

        for field_name in self.mail_native.keys():
            field_name = field_name.lower()
            field_value = self.mail_native.get(field_name)
            if field_name in ['subject', 'from', 'to']:
                field_value = decode_header(field_value)
                field_value = self.clean_value(field_value[0][0], field_value[0][1])

            if field_name in self.headers.keys():
                self.headers[field_name].append(field_value)
            else:
                if field_name in ['received']:
                    self.headers[field_name] = [field_value]
                else:
                    self.headers[field_name] = field_value

    def get_header(self, name):
        """
        Return mail header by name
        """
        return self.headers.get(name, None)

    def set_header(self, name, value):
        """
        Set mail header
        """
        self.headers[name] = value
        return self.headers
