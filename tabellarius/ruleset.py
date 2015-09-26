# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from misc import Helper


class RuleSet(object):
    def __init__(self, logger, name, mailbox, mail, ruleset=[], commands=[], imap=None):
        self.logger = logger
        self.name = name
        self.mailbox = mailbox
        self.mail = mail
        self.ruleset = ruleset
        self.commands = commands
        self.imap = imap
        self.supported_rule_operators = ['or', 'and']

    def process(self):
        match = False
        uid, mail = self.mail
        self.logger.debug('Checking whether mail uid="%s"; message-id="%s"; subject="%s" matches to ruleset %s', uid,
                          mail.get('message-id'), mail.get('subject'), self.name)
        match = self.parse_ruleset(mail, self.ruleset)
        if match:
            self.logger.debug('Ruleset matches!')
            self.apply_commands(uid, mail, self.mailbox)

        return match

    def apply_commands(self, uid, mail, mailbox):
        self.logger.debug('Applying commands for mail message-id="%s" of ruleset %s', mail.get('message-id'), self.name)

        for command in self.commands:
            cmd_type = command.get('type')
            cmd_flags_set = command.get('all_flags', [])
            #cmd_flags_delete = command.get('delete_flags', [])
            #cmd_flags_add = command.get('add_flags', [])

            if cmd_type == 'move':
                cmd_target = command.get('target')
                self.imap.move_mail(mail, mailbox, cmd_target, set_flags=cmd_flags_set)

    def parse_ruleset(self, mail, ruleset):
        for rule in ruleset:
            operator = sorted(rule.keys())[0]
            conditions = rule.get(operator)
            match = self.filter_match(mail, operator, conditions)
            if match:
                return match

    def filter_match(self, mail, operator, conditions):
        #print('Check match: operator={0} conditions={1}'.format(operator, conditions))
        if operator == 'or':
            last_match = True
            for condition in conditions:
                field_original, field, invert = Helper().clean_field_names(sorted(condition.keys())[0])
                pattern = condition.get(field_original)
                #print('field: {0}/ {1}'.format(field, pattern))
                if field in self.supported_rule_operators:
                    last_match = self.filter_match(mail=mail, operator=field, conditions=pattern)
                    if last_match:
                        return True
                else:
                    lines = mail.get(field)
                    if lines is None:
                        last_match = False
                        continue
                    if type(lines) is not list:
                        lines = [lines]
                    for line in lines:
                        last_match = Helper().check_match(line, pattern)  # TODO improve
                        if last_match:
                            break
                    if invert:
                        last_match = not last_match
                    if last_match:
                        return True
            return last_match
        elif operator == 'and':
            for condition in conditions:
                field_original, field, invert = Helper().clean_field_names(sorted(condition.keys())[0])
                pattern = condition.get(field_original)
                if field in self.supported_rule_operators:
                    last_match = self.filter_match(mail=mail, operator=field, conditions=pattern)
                    if not last_match:
                        return False
                else:
                    lines = mail.get(field)
                    #if lines is None:
                    #    continue
                    if type(lines) is not list:
                        lines = [lines]
                    for line in lines:
                        last_match = Helper().check_match(line, pattern)  # TODO improve
                        if not last_match:
                            break
                    if invert:
                        last_match = not last_match
                    if not last_match:
                        return False
            return True
        else:
            print('operator {0} is not supported yet'.format(operator))
