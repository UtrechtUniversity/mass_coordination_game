from otree.api import *


doc = """
some questions about the experiment
"""


class Constants(BaseConstants):
    name_in_url = 'questionnaire'
    players_per_group = None
    num_rounds = 1
    majority_role = 'Red'



class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass

class Player(BasePlayer):
    enjoyment = models.IntegerField(
        choices=[[1, 'Not at all'], [2, 'A little'], [3, 'Somewhat'], [4, 'Very'], [5, 'Extremely']],
        label="Did you enjoy the experiment?",
        widget=widgets.RadioSelect
    )

    clarity = models.IntegerField(
        choices=[[1, 'Very unclear'], [2, 'Unclear'], [3, 'Neutral'], [4, 'Clear'], [5, 'Very clear']],
        label="How clear were the instructions?",
        widget=widgets.RadioSelect
    )

    strategy = models.LongStringField(
        blank=True,
        label="What strategy did you use when deciding which color to choose? Please describe your reasoning."
    )

    perceived_rq = models.LongStringField(
        blank=True,
        label="What do you think this experiment was about? What question do you think the researchers are trying to answer?"
    )

    comments = models.LongStringField(
        blank=True,
        label="If you have any other comments or feedback, you can write that here."
    )

# PAGES
class Questionnaire(Page):
    form_model = 'player'

    @staticmethod
    def get_form_fields(player: Player):
        fields = ['enjoyment', 'clarity', 'perceived_rq', 'comments']
        if player.participant.role == Constants.majority_role:
            fields.insert(2, 'strategy') # ask question about strategy only to majority members.
        return fields

page_sequence = [Questionnaire]





page_sequence = [Questionnaire]
