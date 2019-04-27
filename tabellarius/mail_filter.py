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
                    raise NotImplementedError('Sorry, operator \'{0}\' isn\'t supported yet!'.format(left.lower()))
            if match:
                break

        if match:
            self.logger.info('Found rule match for mail with message-id={0}, going to apply desired commands now'.format(
                self.mail.get_message_id()))
            result = self.apply_commands(commands)
            if not result:
                raise RuntimeError('Failed to apply commands \'%s\'', commands)
        return match

    def check_rule_match(self, rule):
        """
        Check a particular filter rule against a mail
        """
        header_name = next(iter(rule)).lower()
        header_pattern_list = rule[next(iter(rule))]
        header_value = self.mail.get_header(header_name, None)

        # Skip if that header doesn't exist in the mail
        if header_value is None:
            return False

        self.logger.debug('Process rule with field name \'{}\' matches patterns \'{}\''.format(header_name, header_pattern_list))

        for pattern in header_pattern_list:
            if isinstance(header_value, list):
                for single_header_value in header_value:
                    match = self.check_match(single_header_value.lower(), pattern)
                    if match:
                        return True
            else:
                match = self.check_match(header_value.lower(), pattern)
                if match:
                    return True

        return False

    def check_match(self, string, pattern):
        """
        Test whether a string matches a string pattern
        """
        if string is None or len(string) == 0:
            return False

        string = string.lower()
        pattern = pattern.lower()

        self.logger.debug('Checking whether string pattern \'{}\' matches to string \'{}\''.format(pattern, string))

        # Basic match
        if pattern in string:
            self.logger.debug('Pattern matches!')
            return True

        # RegEx match
        pattern_re = regex_compile(pattern)
        if pattern_re.match(string):
            self.logger.debug('Pattern matches!')
            return True
        else:
            self.logger.debug('Pattern does NOT match!')
            return False

    def apply_commands(self, commands):
        """
        Apply commands to mails
        """
        self.logger.info('Applying commands (%s) to mail message-id="%s"', commands, self.mail.get_message_id())
        for command in commands:
            cmd_type = command.get('type')
            cmd_flags_set = command.get('set_flags', [])
            cmd_flags_add = command.get('add_flags', None)

            result = None
            if cmd_type == 'move':
                cmd_target = command.get('target')
                result = self.imap.move_mail(message_ids=[self.mail.get_message_id()],
                                             source=self.mailbox,
                                             destination=cmd_target,
                                             add_flags=cmd_flags_add,
                                             set_flags=cmd_flags_set)
            else:
                raise NotImplementedError('Sorry, command \'{0}\' isn\'t supported yet!'.format(command))

        return result[0]
