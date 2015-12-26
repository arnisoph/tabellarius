# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from re import compile as regex_compile


class MailFilter():
    def __init__(self, logger, imap, mail, config, mailbox):
        self.logger = logger
        self.imap = imap
        self.mail = mail
        self.config = config
        self.mailbox = mailbox

    def check_rules_match(self, rules=None, commands=None, apply_commands=True):
        """
        Check filter rules against a mail
        """
        if rules is None:
            rules = self.config.get('rules', {})

        if commands is None:
            commands = self.config.get('commands')

        match = False
        for row in rules:
            for left, right in row.items():
                if left.lower() == 'or':
                    match = False
                    for rule in right:
                        match = self.check_rule_match(rule)

                        if match:
                            break
                elif left.lower() == 'and':
                    match = False
                    for rule in right:
                        match = self.check_rule_match(rule)

                        if not match:
                            break
                else:
                    raise NotImplementedError('Sorry, operator \'{0}\' isn\'t supported yet!'.format(left))
            if match:
                break

        if match:
            self.logger.info('Found rule match for mail with message-id={0}, going to apply desired commands now'.format(
                self.mail.get_header('message-id')))
            self.apply_commands(commands)
        return match

    def check_rule_match(self, rule):
        """
        Check a particular filter rule against a mail
        """
        field_name = next(iter(rule))
        field_pattern = rule[next(iter(rule))]
        field_value = self.mail.get_header(field_name, None)

        # Skip if that header doesn't exist in the mail
        if field_value is None:
            return False

        if isinstance(field_pattern, list):
            for pattern in field_pattern:
                match = self.check_match(field_value, pattern)
                if match:
                    return True
        else:
            return self.check_match(field_value, field_pattern)

        return False

    def check_match(self, string, pattern):
        """
        Test whether a string matches a string pattern
        """
        if string is None or len(string) == 0:
            return False

        # Basic match
        if pattern in string:
            return True

        # RegEx match
        pattern_re = regex_compile(pattern)
        if pattern_re.match(string):
            return True
        else:
            return False

    def apply_commands(self, commands):
        """
        Apply commands to mails
        """
        self.logger.info('Applying commands (%s) to mail message-id="%s"', commands, self.mail.get_header('message-id'))
        for command in commands:
            cmd_type = command.get('type')
            cmd_flags_set = command.get('set_flags', [])
            cmd_flags_add = command.get('add_flags', None)
            #cmd_flags_remove = command.get('remove_flags', [])

            uid = None
            if cmd_type == 'move':
                cmd_target = command.get('target')
                uid = self.imap.move_mail(message_ids=[self.mail.get_header('message-id')],
                                          source=self.mailbox,
                                          destination=cmd_target,
                                          add_flags=cmd_flags_add,
                                          set_flags=cmd_flags_set)[0]
            else:
                raise NotImplementedError('Sorry, command \'{0}\' isn\'t supported yet!'.format(command))

        return uid

    def clean_field_name(self, field):
        """
        Parse a rule field name and return a tuple

        'from' results to ('from', 'from', false)
        'from!' results to ('from!', 'from', true)
        'to!' results to ('to!', 'to', true)
        """
        if field[-1:] == '!':
            return (field, field[0:-1], True)
        else:
            return (field, field, False)
