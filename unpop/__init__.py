from otree.api import *
import json
import os
import math
import random
import logging
from .functions import compute_utility, payoff_table

doc = """
“The spread of an unpopular norm in a social network experiment"

Add description

"""

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    fh = logging.FileHandler("otree_log.txt", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

class Constants(BaseConstants):
    title = "The Fashion Dilemma"
    name_in_url = "fashion_dilemma"
    players_per_group = None
    group_size = 5
    num_rounds = 3
    majority_role = 'Red'
    minority_role = 'Blue'
    s = 15
    e = 10
    z = 50
    w = 40  #
    lambda1 = 4.3
    lambda2 = 1.8
    min_group_participation = 0.5
    introduction_timeout_seconds = 420
    comprehension_timeout_seconds = 180
    other_pages_timeout_seconds = 120
    density = .30
    min_prop = .30
    points_per_euro_majority = 85
    points_per_euro_minority = 22
    base_payment = 2.5
    max_payment = 5.5

class Subsession(BaseSubsession):
    def creating_session(self):
        if self.round_number == 1:
            for p in self.get_players():
                p.participant.is_dropout = False
        else:
            self.group_like_round(1)

class Player(BasePlayer):
    choice = models.BooleanField(
        verbose_name="Make your choice: Will you wear a Blue or a Red T-shirt today?",
        widget=widgets.RadioSelect,
        choices=[(True, 'Blue'), (False, 'Red')],
    )
    inactive = models.BooleanField(initial=False)
    prolific_id = models.StringField(default=str(" "))

    # comprehension questions
    q_red_zero = models.IntegerField(min=0, label="")
    q_blue_zero = models.IntegerField(min=0, label="")
    q_red_half = models.IntegerField(min=0, label="")
    q_blue_half = models.IntegerField(min=0, label="")

    payoff_red_zero = models.IntegerField()
    payoff_blue_zero = models.IntegerField()
    payoff_red_half = models.IntegerField()
    payoff_blue_half = models.IntegerField()

class Group(BaseGroup):
    failed = models.BooleanField(initial=False)
    inactive_players = models.IntegerField(initial=0)

    def set_first_stage_earnings(self):
        players = self.get_players()
        for player in players:
            if player.participant.is_dropout:
                player.payoff = 0
                continue

            my_choice = player.choice
            my_node = player.participant.node
            adj_matrix = player.participant.adj_matrix

            # neighbors
            neighbors = []
            for i, connection in enumerate(adj_matrix[my_node]):
                if connection == 1:
                    neighbor_player = next(p for p in players if p.participant.node == i)
                    if not neighbor_player.participant.is_dropout:
                        neighbors.append(i)

            neighbor_choices = []
            for neighbor_id in neighbors:
                neighbor_player = next(p for p in players if p.participant.node == neighbor_id)
                neighbor_choices.append(neighbor_player.choice)

            utility = compute_utility(
                player_choice=my_choice,
                player_role=player.participant.role,
                neighbors_choices=neighbor_choices,
            )

            player.payoff = max(utility, 0)

def timeout_check(player, timeout_happened):
    participant = player.participant
    groupsize = len(player.subsession.get_players())

    if timeout_happened and not participant.is_dropout:
        player.group.inactive_players += 1
        player.inactive = True
        participant.is_dropout = True

    if groupsize - player.group.inactive_players < round(groupsize * Constants.min_group_participation):
        player.group.failed = True


def timeout_time(player, timeout_seconds):
    participant = player.participant
    if participant.is_dropout or player.group.failed:
        return 1
    else:
        return timeout_seconds

def group_by_arrival_time_method(subsession, waiting_players):
    logger.info("Entered group_by_arrival_time_method")
    group_size = Constants.group_size

    if not subsession.session.vars.get("group_formed", False):
        if len(waiting_players) >= group_size:
            logger.info(f"Creating the one and only group of {group_size} players.")
            subsession.session.vars["group_formed"] = True
            return waiting_players[:group_size]
        else:
            logger.info(
                f"Not enough players yet ({len(waiting_players)}/{group_size}) to create the group."
            )
            return
    else:
        # mark excess players as dropouts and let them continue to ExitPage
        for p in waiting_players:
            p.participant.vars["exit_early"] = True
            p.participant.is_dropout = True
        return waiting_players

class NetworkFormationWaitPage(WaitPage):
    group_by_arrival_time = True

    title_text = "Please wait"
    body_text = (
        "Waiting for others to join...<br><br>"
        "<b>Please stay on this page.</b> If you switch tabs or windows, you’ll become inactive "
        "and won’t be grouped until you return."
    )

    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def after_all_players_arrive(group):
        players = [p for p in group.get_players() if p.participant.vars.get("consent", False)]
        num_players = len(players)
        if num_players == 0:
            return

        def generate_network(n, edge_prob):
            adj_matrix = [[0] * n for _ in range(n)]
            nodes = list(range(n))
            random.shuffle(nodes)

            # spanning tree for connectivity
            for i in range(1, n):
                a = nodes[i]
                b = random.choice(nodes[:i])
                adj_matrix[a][b] = 1
                adj_matrix[b][a] = 1

            # add extra edges
            for i in range(n):
                for j in range(i + 1, n):
                    if adj_matrix[i][j] == 0 and random.random() < edge_prob:
                        adj_matrix[i][j] = 1
                        adj_matrix[j][i] = 1
            return adj_matrix

        net_condition = group.session.config.get("network_condition")
        if net_condition:
            file_path = os.path.join("networks", f"network_{net_condition}.json")
            with open(file_path, 'r') as f:
                net = json.load(f)
            adj_matrix = net['adj_matrix']
            role_vector = net['role_vector']
        else:
            adj_matrix = generate_network(num_players, edge_prob=Constants.density)
            degrees = [sum(row) for row in adj_matrix]
            num_minority = max(1, int(Constants.min_prop * num_players))
            nodes_srt_by_deg = sorted(range(num_players), key=lambda x: degrees[x], reverse=True)
            role_vector = [0] * num_players
            for i in nodes_srt_by_deg[:num_minority]:
                role_vector[i] = 1

        # assign to players
        for i, player in enumerate(players):
            role = Constants.minority_role if role_vector[i] == 1 else Constants.majority_role
            player.participant.role = role
            player.participant.node = i
            player.participant.is_dropout = False
            player.participant.adj_matrix = adj_matrix

class IntroductionPage(Page):
    def vars_for_template(player):
        adj_matrix = player.participant.adj_matrix
        my_node = player.id_in_group
        degree = sum(adj_matrix[my_node - 1])

        table_data = payoff_table(degree)

        return dict(
            role=player.participant.role,
            network_condition=player.session.config.get("network_condition"),
            punishment_condition=player.session.config.get("punishment_condition"),
            group_size=len(player.subsession.get_players()),
            degree=degree,
            range_neighbors=list(range(degree + 1)) if degree > 0 else [],
            table_data=table_data,
            base="{:.2f}".format(Constants.base_payment),
            max="{:.2f}".format(Constants.max_payment),
        )

    def is_displayed(player):
        return (
                player.round_number == 1
                and not player.participant.is_dropout
                and not player.participant.vars.get("exit_early", False)
        )


    def get_timeout_seconds(player):
        return timeout_time(player, Constants.introduction_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)
        player.prolific_id = player.participant.label
class ComprehensionPage(Page):
    form_model = 'player'
    form_fields = ['q_red_zero', 'q_blue_zero', 'q_red_half', 'q_blue_half']

    def is_displayed(player):
        return (
                player.round_number == 1
                and player.participant.role == Constants.majority_role
                and not player.participant.is_dropout
                and not player.participant.vars.get("exit_early", False)
        )

    def vars_for_template(player):
        adj_matrix = player.participant.adj_matrix
        my_node = player.id_in_group - 1
        degree = sum(adj_matrix[my_node])

        table_data = payoff_table(degree)

        blue_neighbors = degree
        red_neighbors = 0
        payoff_red_zero = Constants.s + Constants.w * (1 - math.exp(-Constants.lambda2 * (red_neighbors / max(1, degree)))) / (1 - math.exp(-Constants.lambda2))
        payoff_blue_zero = Constants.z * (1 - math.exp(-Constants.lambda1 * (blue_neighbors / max(1, degree)))) / (1 - math.exp(-Constants.lambda1))

        blue_neighbors_half = degree // 2
        red_neighbors_half = degree - blue_neighbors_half
        payoff_red_half = Constants.s + Constants.w * (1 - math.exp(-Constants.lambda2 * (red_neighbors_half / max(1, degree)))) / (1 - math.exp(-Constants.lambda2))
        payoff_blue_half = Constants.z * (1 - math.exp(-Constants.lambda1 * (blue_neighbors_half / max(1, degree)))) / (1 - math.exp(-Constants.lambda1))

        player.payoff_red_zero = round(payoff_red_zero)
        player.payoff_blue_zero = round(payoff_blue_zero)
        player.payoff_red_half = round(payoff_red_half)
        player.payoff_blue_half = round(payoff_blue_half)

        return dict(
            role=player.participant.role,
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
            'q_blue_half': player.payoff_blue_half
        }
        incorrect_fields = []
        labels = {'q_red_zero': 'A', 'q_blue_zero': 'B', 'q_red_half': 'C', 'q_blue_half': 'D'}

        for field_name, correct_value in correct_answers.items():
            if values.get(field_name) != correct_value:
                incorrect_fields.append(labels[field_name])

        if incorrect_fields:
            return "Incorrect answers: " + ", ".join(incorrect_fields) + ".  Your total points = reward for picking a color (Table 1) + reward for matching neighbors (Table 2)."

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.comprehension_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)

class DecisionPage(Page):
    form_model = 'player'
    form_fields = ['choice']

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)

    def is_displayed(player):
        return not player.group.failed and not player.participant.is_dropout and not player.participant.vars.get("exit_early", False)

    def vars_for_template(player):
        adj_matrix = player.participant.adj_matrix
        my_node = player.id_in_group
        degree = sum(adj_matrix[my_node - 1])

        table_data = payoff_table(degree)

        num_blue_previous_round = 0
        num_red_previous_round = 0
        if player.round_number > 1:
            neighbors = []
            for i, connection in enumerate(adj_matrix[my_node - 1]):
                if connection == 1:
                    neighbors.append(i)

            prev_round = player.round_number - 1
            num_blue_previous_round = sum(
                1 for p in player.group.get_players()
                if (p.id_in_group - 1) in neighbors
                and not p.participant.is_dropout
                and p.in_round(prev_round).choice is True
            )
            num_red_previous_round = sum(
                1 for p in player.group.get_players()
                if (p.id_in_group - 1) in neighbors
                and not p.participant.is_dropout
                and p.in_round(prev_round).choice is False
            )

        return dict(
            group_size=len(player.subsession.get_players()),
            network_condition=player.session.config.get("network_condition"),
            role=player.participant.role,
            round_number=player.round_number,
            degree=degree,
            range_neighbors=list(range(degree + 1)),
            table_data=table_data,
            num_blue_previous_round=num_blue_previous_round,
            num_red_previous_round=num_red_previous_round,
        )

class ResultsWaitPage(WaitPage):
    def after_all_players_arrive(group):
        group.set_first_stage_earnings()

    def is_displayed(player):
        return not player.group.failed and not player.participant.is_dropout and not player.participant.vars.get("exit_early", False)


class ResultsPage(Page):
    def vars_for_template(player):
        my_choice = player.choice
        my_payoff = player.payoff

        my_node = player.participant.node
        adj_matrix = player.participant.adj_matrix

        neighbors = []
        for i, connection in enumerate(adj_matrix[my_node]):
            if connection == 1:
                neighbors.append(i)

        neighbors_info = []
        for idx, neighbor_id in enumerate(neighbors, start=1):
            neighbor_player = next((p for p in player.group.get_players() if p.participant.node == neighbor_id), None)
            if neighbor_player:
                if neighbor_player.participant.is_dropout or neighbor_player.choice is None:
                    choice_display = 'Missing'
                else:
                    choice_display = 'Blue' if neighbor_player.choice else 'Red'

                neighbors_info.append({
                    'neighbor': idx,
                    'id': neighbor_player.id,
                    'choice': choice_display,
                    'payoff': neighbor_player.payoff,
                })

        my_choice_display = 'Blue' if my_choice else 'Red'

        return dict(
            my_choice=my_choice_display,
            my_payoff=my_payoff,
            neighbors_info=neighbors_info,
            role=player.participant.role,
            round_number=player.round_number,
        )

    def is_displayed(player):
        return not player.group.failed and not player.participant.is_dropout and not player.participant.vars.get("exit_early", False)

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)


class FinalGameResults(Page):
    @staticmethod
    def is_displayed(player):
        return (
            player.round_number == Constants.num_rounds
            and not player.group.failed
            and not player.participant.is_dropout
        )

    @staticmethod
    def js_vars(player):
        return dict(completionlink=player.subsession.session.config['completionlink'])

    @staticmethod
    def vars_for_template(player):
        accumulated_earnings = player.participant.payoff
        base = Constants.base_payment

        conversion = (
            Constants.points_per_euro_majority
            if player.participant.role == Constants.majority_role
            else Constants.points_per_euro_minority
        )

        euros = float(accumulated_earnings) / conversion
        euros = min(euros, Constants.max_payment)
        euros = max(euros, Constants.base_payment)
        bonus = max(euros - base, 0)

        player.participant.bonus = round(bonus, 2)

        return dict(
            accumulated_earnings=accumulated_earnings,
            raw_euros=float(accumulated_earnings) / conversion,
            base="{:.2f}".format(base),
            bonus="{:.2f}".format(bonus),
            euros="{:.2f}".format(euros),
        )


class FailedGamePage(Page):
    def vars_for_template(player):
        return dict(one_dropout=player.participant.is_dropout and player.round_number == Constants.num_rounds)

    def is_displayed(player):
        return player.group.failed or (player.participant.is_dropout and player.round_number == Constants.num_rounds)

class ExitPage(Page):
    """
    Displayed to participants who arrive after the main group is full.
    """
    def is_displayed(player):
        return player.participant.vars.get("exit_early", False)

    def vars_for_template(player):
        return dict(
            message="Unfortunately, the group for this session is already full. "
                    "You will not be participating in the experiment this time. "
                    "Please return to Prolific to complete your submission."
        )

page_sequence = [
    NetworkFormationWaitPage,
    IntroductionPage,
    #ComprehensionPage,
    DecisionPage,
    ResultsWaitPage,
    ResultsPage,
    FinalGameResults,
    FailedGamePage,
    ExitPage,
]