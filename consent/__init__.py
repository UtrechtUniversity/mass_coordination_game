import datetime, random
from otree.api import *

# import central parameters
from settings import (
    title as TITLE,
    majority_role as MAJORITY,
    minority_role as MINORITY,
    base_payment as base,
    max_payment as maxp,
    p_minority as p_m,
    testing as TEST,
)

doc = """
Participants arrive at a consent form.
After consenting, they are assigned a role.
"""

class Constants(BaseConstants):
    title = TITLE
    name_in_url = 'consent'
    players_per_group = None
    num_rounds = 1

    majority = MAJORITY
    minority = MINORITY

    p_minority = p_m # the target minority share in the network
    p_assign_minority = 2 * p_m # oversample minorities (here, x2)

    base_payment = base
    max_payment = maxp

class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    consent = models.BooleanField(
        label="",
        choices=[[True, 'I consent']],
        blank=True
    )
    consent_timestamp = models.StringField(blank=True)


class ConsentPage(Page):
    form_model = 'player'
    form_fields = ['consent']

    def is_displayed(player: Player):
        # Only show consent page if the group has NOT been formed yet
        return not player.session.vars.get("group_formed", False)

    def error_message(player, values):
        if not values.get('consent'):
            return "You must check the box to give your consent in order to participate in this study."

    def before_next_page(player: Player, timeout_happened):
        if not player.consent:
            player.participant.vars['consent'] = False
            return

        # timestamp
        player.consent_timestamp = datetime.datetime.now().isoformat()

        """
        Previously, the first players arriving become a minority, until the required
        number of minorities is reached; after which entrants become minority with a probability
        equal to the proportion of minorities in the network condition.
        Current assignment: players become minority with a probability p that is twice 
        the proportion of minorities in the network condition (p_assign_minority = 2 * p_m);
        Also, I reserve a few spots (participant number between 200-250) that will always be the minority 
        (to efficiently fill potential lacking spots in the network with bots...)
        """
        if 200 <= player.participant.id_in_session <= 250:
            role = Constants.minority
        else:
            role = (
                Constants.minority
                if random.random() < Constants.p_assign_minority
                else Constants.majority
            )

        # store for downstream apps
        player.participant.vars['role'] = role
        player.participant.vars['consent'] = True

        print(f"[assign] P{player.participant.id_in_session} -> {role}")

    def vars_for_template(player):
        return dict(
            base="{:.2f}".format(Constants.base_payment),
            maxp="{:.2f}".format(Constants.max_payment),
            dif="{:.2f}".format(Constants.max_payment - Constants.base_payment),
            test = TEST,
        )

page_sequence = [ConsentPage]
