# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
import imaplib

    #result, data = imap_conn.uid('COPY', mail_uid, target)
    #if result == 'OK':
    #    imap_conn.debug = 10
    #    mov, data = imap_conn.uid('STORE', mail_uid , '+FLAGS', '(\Deleted)')
    #    imap_conn.expunge()
    #    message_id = mail.get('message-id')
    #    imap_conn.select(mailbox=target)
    #    c.select(mailbox=target)
    #    #result, data = imap_conn.uid('SEARCH', None, 'HEADER MESSAGE-ID "{0}"'.format(message_id))
    #    result, data = imap_conn.uid('SEARCH', None, 'SUBJECT "{0}"'.format(mail.get('subject')))
    #    new_mail_uid = data[0].split()[-1]
    #    result, data = imap_conn.uid('STORE', new_mail_uid, '-FLAGS', '\SEEN')
    #else:
    #    print("w00t")
    #    pass #TOOD


#list_response_pattern = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')
#def parse_list_response(line):
#    print(line)
#    flags, delimiter, mailbox_name = list_response_pattern.match(line).groups()
#    mailbox_name = mailbox_name.strip('"')
#    return (flags, delimiter, mailbox_name)

#c = open_connection(verbose=True)
#try:
#    c.select(mailbox='PreInbox')
#    result, data = c.uid('search', None, 'ALL')
#    mail_uids = data[0].split()
#
#    mails = []
#
#    for uid in mail_uids:
#        mail_result, mail_data = c.uid('fetch', uid, '(RFC822)')
#        msg = email.message_from_bytes(mail_data[0][1])
#
#        mail = Mail(mail=msg)
#        mails.append(mail)
#
#    for mail in mails:
#        #print(mail)
#        print('Running filters for mail with subject="{0}" message-id={1}'.format(mail.get('subject'), mail.get('message-id')))
#        filters = tabellarius_config.get('filters', {})
#        match = False
#        for filter_name, filter_settings in filters.items():
#            match = parse_filter(mail, filter_name, filter_settings)
#            if match:
#                print("match!")
#                commands = filter_settings.get('commands', [])
#                process_filter_commands(c, mail, uid, commands)
#            if not match:
#                imap_move_mail(c, mail, uid, 'INBOX')
#finally:
#    try:
#        c.close()
#    except:
#        pass
#    c.logout()
