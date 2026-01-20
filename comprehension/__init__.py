from otree.api import *

#import central parameters
from settings import (
    title as TITLE,
    majority_role as MAJORITY,
    minority_role as MINORITY,
    s as S,
    e as E,
    z as Z,
    w as W,
    lambda1 as L1,
    lambda2 as L2,
    base_payment as base,
    max_payment as maxp,
    points_per_euro_majority as PPE1,
    points_per_euro_minority as PPE2,
    num_rounds as nrounds,
    testing as TEST,
)
# import custom functions
from unpop.functions import compute_utility, payoff_table

doc = """
They receive a brief (role-based) instruction, after which they complete a set of comprehension questions.
"""

class Constants(BaseConstants):
    title = TITLE
    name_in_url = 'comprehension'
    players_per_group = None
    num_rounds = 1
    majority = MAJORITY
    minority = MINORITY
    s = S
    e = E
    z = Z
    w = W
    lambda1 = L1
    lambda2 = L2
    base_payment = base
    max_payment = maxp
    points_per_euro_majority = PPE1
    points_per_euro_minority = PPE2
    other_pages_timeout_seconds = 60

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    q_red_zero = models.IntegerField(min=0, label="")
    q_blue_zero = models.IntegerField(min=0, label="")
    q_red_half = models.IntegerField(min=0, label="")
    q_blue_half = models.IntegerField(min=0, label="")

    payoff_red_zero = models.IntegerField()
    payoff_blue_zero = models.IntegerField()
    payoff_red_half = models.IntegerField()
    payoff_blue_half = models.IntegerField()

    #we also count the number of wrong submissions during the comprehensino check (increments per wrong submission)
    comprehension_retries = models.IntegerField(initial=0)

class IntroductionPage(Page):

    @staticmethod
    def is_displayed(player):
        # show only when no group has been formed yet
        return not player.session.vars.get("group_formed", False)

    def vars_for_template(player):
        degree = 2 # for instruction, assume 2 neighbors (this can be tweaked)
        table_data = payoff_table(degree)

        return dict(
            role=player.participant.role,
            network_condition=player.session.config.get("network_condition"),
            group_size=player.session.config['group_size'],
            degree=degree,
            range_neighbors=list(range(degree + 1)) if degree > 0 else [],
            table_data=table_data,
            base="{:.2f}".format(Constants.base_payment),
            max="{:.2f}".format(Constants.max_payment),
            num_rounds_lower=round(nrounds * 0.9),
            num_rounds_upper = round(nrounds * 1.1),
            test = TEST,
        )

class ComprehensionPage(Page):
    form_model = 'player'
    form_fields = ['q_red_zero', 'q_blue_zero', 'q_red_half', 'q_blue_half']

    @staticmethod
    def is_displayed(player):
        # show only when no group has been formed yet
        return not player.session.vars.get("group_formed", False)

    def vars_for_template(player):
        degree = 2
        table_data = payoff_table(degree)

        # build neighborhood scenarios
        neighbors_all_blue = [True] * degree  # 0 red neighbors, all blue
        neighbors_half_half = [True] * (degree // 2) + [False] * (degree - degree // 2) # split

        role = player.participant.role

        # False = Red, True = Blue
        payoff_red_zero = compute_utility(False, role, neighbors_all_blue)
        payoff_blue_zero = compute_utility(True, role, neighbors_all_blue)
        payoff_red_half = compute_utility(False, role, neighbors_half_half)
        payoff_blue_half = compute_utility(True, role, neighbors_half_half)

        player.payoff_red_zero = round(payoff_red_zero)
        player.payoff_blue_zero = round(payoff_blue_zero)
        player.payoff_red_half = round(payoff_red_half)
        player.payoff_blue_half = round(payoff_blue_half)

        blue_neighbors_half = degree // 2
        red_neighbors_half = degree - blue_neighbors_half

        return dict(
            role=role,
            degree=degree,
            table_data=table_data,
            blue_neighbors_half=blue_neighbors_half,
            red_neighbors_half=red_neighbors_half,
        )

    def error_message(player, values):
        correct_answers = {
            'q_red_zero': player.payoff_red_zero,
            'q_blue_zero': player.payoff_blue_zero,
            'q_red_half': player.payoff_red_half,
            'q_blue_half': player.payoff_blue_half,
        }
        incorrect_fields = []
        labels = {
            'q_red_zero': 'A',
            'q_blue_zero': 'B',
            'q_red_half': 'C',
            'q_blue_half': 'D',
        }

        for field_name, correct_value in correct_answers.items():
            if values.get(field_name) != correct_value:
                incorrect_fields.append(labels[field_name])

        if incorrect_fields:
            player.comprehension_retries += 1
            role = player.participant.role
            labels_str = ", ".join(incorrect_fields)

            if role == Constants.minority:
                explanation = (
                    "Your payoff only depends on your own shirt choice (Table 1)."
                )
            else:
                explanation = (
                    "Your total points = reward for picking a color "
                    "(Table 1) + reward for matching neighbors (Table 2)."
                )

            return f"Incorrect answers: {labels_str}.  {explanation}"

page_sequence = [
    IntroductionPage,
    ComprehensionPage, #only turn off for testing purposes.
                 ]