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
            self['body'] = self.mail_native.get_payload(decode=True).decode('utf-8')
            #else:
            #    self['body'] = self.mail_native.get_payload(decode=True)

        for field_name in self.mail_native.keys():
            field_name = field_name.lower()
            field_value = self.mail_native.get(field_name)
            if field_name in ['subject', 'from', 'to']:
                field_value = decode_header(field_value)
                field_value = self.clean_value(field_value[0][0], field_value[0][1])

            self[field_name] = field_value

#        # from
#        # cleanup header
#        from_header_cleaned = re.sub('[\n\r\t]+', ' ', self.email_obj['from'])
#        msg_from = decode_header(from_header_cleaned)
#        msg_txt = ''
#        for part in msg_from:
#            msg_txt += self.clean_value(part[0], part[1])
#        if '<' in msg_txt and '>' in msg_txt:
#            result = re.match('(?P<from>.*)?(?P<email>\<.*\>)', msg_txt, re.U)
#            self['from_whom'] = result.group('from').strip()
#            self['from_email'] = result.group('email').strip('<>')
#            self['from'] = msg_txt
#        else:
#            self['from_whom'] = ''
#            self['from_email'] = self['from'] = msg_txt.strip()
#
#        # to
#        if 'to' in self.email_obj:
#            msg_to = decode_header(self.email_obj['to'])
#            self['to'] = self.clean_value(
#                msg_to[0][0], msg_to[0][1]).strip('<>')
#
#        # cc
#        msg_cc = decode_header(str(self.email_obj['cc']))
#        cc_clean = self.clean_value(msg_cc[0][0], msg_cc[0][1])
#        if cc_clean and cc_clean.lower() != 'none':
#            # split recepients
#            recepients = cc_clean.split(',')
#            for recepient in recepients:
#                if '<' in recepient and '>' in recepient:
#                    # (name)? + email
#                    matches = re.findall('((?P<to>.*)?(?P<to_email>\<.*\>))',
#                                         recepient, re.U)
#                    if matches:
#                        for match in matches:
#                            self['cc'].append(
#                                {
#                                    'cc': match[0],
#                                    'cc_to': match[1].strip(" \n\r\t"),
#                                    'cc_email': match[2].strip("<>"),
#                                }
#                            )
#                    else:
#                        raise EmailParsingError(
#                            "Error parsing CC message header. "
#                            "Header value: {header}".format(header=cc_clean)
#                        )
#                else:
#                    # email only
#                    self['cc'].append(
#                        {
#                            'cc': recepient,
#                            'cc_to': '',
#                            'cc_email': recepient,
#                        }
#                    )
#
#        # Date
#        self['date'] = self.email_obj['Date']
#
#        # message headers
#        for header, val in self.email_obj.items():
#            if header in self['headers']:
#                self['headers'][header].append(val)
#            else:
#                self['headers'][header] = [val]
