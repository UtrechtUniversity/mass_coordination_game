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
    p_minority = p_m

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

    def error_message(player, values):
        if not values.get('consent'):
            return "You must check the box to give your consent in order to participate in this study."

    def before_next_page(player: Player, timeout_happened):
        if not player.consent:
            player.participant.vars['consent'] = False
            return

        # timestamp
        player.consent_timestamp = datetime.datetime.now().isoformat()

        s = player.session
        svars = s.vars

        # compute a quota: the first players arriving become a minority,
        # until the required number of minorities is reached.
        if 'quota' not in svars:
            group_size = s.config['group_size']
            svars['quota'] = max(1, round(group_size * Constants.p_minority))

        # probability of minority assignment after quota
        if 'p_tail_minority' not in svars:
            svars['p_tail_minority'] = 0.001  # @RF: in the in-class demonstration, we don't need a "tail probability"
            #svars['p_tail_minority'] = Constants.p_minority #@RF: uncomment before going live!!!


        svars.setdefault('minority_assigned', 0)

        quota = svars['quota']
        p_tail = svars['p_tail_minority']

        # assignment logic
        if svars['minority_assigned'] < quota:
            role = Constants.minority
            svars['minority_assigned'] += 1
            reason = f"front-load {svars['minority_assigned']}/{quota}"
        else:
            role = Constants.minority if random.random() < p_tail else Constants.majority
            reason = f"tail Bernoulli p_minority={p_tail:.3f}"

        # store for downstream apps
        player.participant.vars['role'] = role
        player.participant.vars['consent'] = True

        print(f"[assign] P{player.participant.id_in_session} -> {role} ({reason})")
        print(f"[status] minority_assigned={svars['minority_assigned']}/{quota}, next Bernoulli p={p_tail:.3f}")

    def vars_for_template(player):
        return dict(
            base="{:.2f}".format(Constants.base_payment),
            maxp="{:.2f}".format(Constants.max_payment),
            dif="{:.2f}".format(Constants.max_payment - Constants.base_payment),
        )


page_sequence = [ConsentPage]
