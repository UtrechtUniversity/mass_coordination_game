from otree.api import *


doc = """
some questions about the experiment
"""


class Constants(BaseConstants):
    name_in_url = 'questionnaire'
    players_per_group = None
    num_rounds = 1



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

    comments = models.LongStringField(
        blank=True,
        label="Can you explain why you gave these answers? If you have any other comments or feedback, you can also write that here."
    )

    perceived_rq = models.LongStringField(
        blank=True,
        label="What do you think this experiment was about? What question do you think the researchers are trying to answer?"
    )
# PAGES
class Questionnaire(Page):
    form_model = 'player'
    form_fields = ['enjoyment', 'clarity', 'comments', 'perceived_rq']


page_sequence = [Questionnaire]
