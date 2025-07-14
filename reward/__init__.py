from otree.api import *


doc = """
Your app description
"""


class Constants(BaseConstants):
    name_in_url = 'reward'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass


# PAGES
class PaymentInfo(Page):
    form_model = 'player'

    def is_displayed(player):
        participant = player.participant
        return participant.consent == True

    @staticmethod
    def js_vars(player):
        return dict(
            completionlink=
              player.subsession.session.config['completionlink']
        )
    pass

page_sequence = [PaymentInfo]
