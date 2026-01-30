from otree.api import *
import json
import os
import random
import logging
import datetime
from .functions import compute_utility, payoff_table

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
    p_minority as p_minority,
    testing as TEST,
)

doc = """
Once enough participants (of both roles) reach the NetworkFormationPage, the network is populated 
(players who arrive after this proceed directly to the next app). 
Participants receive updated instructions including an updated payoff matrix based on their degree.
"""

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_dir = "otree_log"
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(
    log_dir, f"otree_log_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.txt"
)

if not logger.handlers:
    fh = logging.FileHandler(log_filename, encoding="utf-8")
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)

class Constants(BaseConstants):
    title = TITLE
    name_in_url = "fashion_dilemma"
    players_per_group = None
    num_rounds = nrounds
    majority = MAJORITY
    minority = MINORITY
    s = S
    e = E
    z = Z
    w = W
    lambda1 = L1
    lambda2 = L2
    introduction_timeout_seconds = 60
    other_pages_timeout_seconds = 60
    points_per_euro_majority = PPE1
    points_per_euro_minority = PPE2
    base_payment = base
    max_payment = maxp

class Subsession(BaseSubsession):
    def creating_session(self):
        if self.round_number == 1:
            for p in self.get_players():
                p.participant.is_dropout = False  # set dropout flag to False

            # cache network condition at session level
            net_condition = self.session.config.get("network_condition")
            logger.debug(f"creating_session: round = {self.round_number}")
            logger.debug(f"creating_session: session config name = {self.session.config.get('name')}")
            logger.debug(f"creating_session: network_condition = {net_condition}")

            if net_condition and "net_spec" not in self.session.vars:
                file_path = os.path.join("networks", f"network_{net_condition}.json")
                logger.debug(f"creating_session: loading net_spec from {file_path}")
                with open(file_path, "r") as f:
                    net = json.load(f)
                self.session.vars["net_spec"] = net
                logger.debug(f"creating_session: net_spec keys = {list(net.keys())}")

            self.session.vars["group_formed"] = False
        else:
            self.group_like_round(1)

class Player(BasePlayer):
    choice = models.BooleanField(
        verbose_name="Make your choice: Will you wear a Blue or a Red T-shirt today?",
        widget=widgets.RadioSelect,
        choices=[(True, "Blue"), (False, "Red")],
    )
    prolific_id = models.StringField(default=str(" "))
    is_dropout = models.BooleanField(initial=False)
    bonus = models.FloatField(initial=0)
    arrived_waitpage = models.BooleanField(initial=False) # also track who is on the resultswaitpage (and thus, who has made a choice)
    arrived_grouppage = models.BooleanField(initial=False) # the same for the groupformationpage


class Group(BaseGroup):
    def set_first_stage_earnings(self):
        players = self.get_players()
        for player in players:
            if player.participant.vars.get("exit_early", False):
                player.payoff = 0
                continue

            my_choice = player.choice
            my_node = player.participant.node
            adj_matrix = player.session.vars["net_spec"]["adj_matrix"]

            neighbors = []
            for i, connection in enumerate(adj_matrix[my_node]):
                if connection == 1:
                    neighbor_player = next(
                        p for p in players if p.participant.node == i
                    )
                    if not neighbor_player.participant.vars.get("exit_early", False):
                        neighbors.append(i)

            neighbor_choices = []
            for neighbor_id in neighbors:
                neighbor_player = next(
                    p for p in players if p.participant.node == neighbor_id
                )
                neighbor_choices.append(neighbor_player.choice)

            utility = compute_utility(
                player_choice=my_choice,
                player_role=player.participant.role,
                neighbors_choices=neighbor_choices,
            )

            player.payoff = max(utility, 0)

def timeout_check(player, timeout_happened):
    """
    If a player times out, mark them as dropout
    They will be replaced by bots

    @RF when running in prodserver (but not devserver) the page always submits even if the user closes their browser
    """
    participant = player.participant
    if timeout_happened and not participant.is_dropout:
        participant.is_dropout = True
        player.is_dropout = True
        logger.info(
            f"[R{player.round_number:02d}] P{player.id_in_group} ({participant.label}) | "
            f"MARKED DROPOUT (AUTO PLAY)"
        )


def timeout_time(player, timeout_seconds):
    participant = player.participant
    if participant.is_dropout:
        return 1
    else:
        return timeout_seconds


def group_by_arrival_time_method(subsession, waiting_players):

    logger.info("Entered group_by_arrival_time_method")
    session = subsession.session
    group_size = session.config["group_size"]

    # ensure net_spec is loaded
    if "net_spec" not in session.vars:
        net_condition = session.config.get("network_condition")
        logger.debug(f"group_by_arrival_time_method: net_spec missing, trying to load. network_condition = {net_condition}")

        if net_condition:
            file_path = os.path.join("networks", f"network_{net_condition}.json")
            logger.debug(f"group_by_arrival_time_method: loading net_spec from {file_path}")
            try:
                with open(file_path, "r") as f:
                    net = json.load(f)
                session.vars["net_spec"] = net
                logger.debug(f"group_by_arrival_time_method: net_spec loaded, keys = {list(net.keys())}")
            except Exception as e:
                logger.error(f"group_by_arrival_time_method: FAILED to load net_spec: {repr(e)}")

    logger.debug(f"group_by_arrival_time_method: group_formed = {session.vars.get('group_formed')}")
    logger.debug(f"group_by_arrival_time_method: net_spec present = {'net_spec' in session.vars}")

    # form a single group in this session
    if session.vars.get("group_formed", False):
        # excess arrivals: mark as exit-early so they skip to ExitPage
        for p in waiting_players:
            p.participant.vars["exit_early"] = True
            p.participant.is_dropout = True
        return waiting_players  # let them proceed

    net_spec = session.vars.get("net_spec", None)

    if not net_spec:
        logger.warning(
            "group_by_arrival_time_method: STILL no net_spec after fallback – "
            "check network_condition and JSON path."
        )
        return

    logger.debug("group_by_arrival_time_method: USING PREDEFINED net_spec")

    # helper function to assign nodes and push adj_matrix to all selected players
    def assign_nodes_and_matrix(selected_players, adj_matrix):
        for i, p in enumerate(selected_players):
            p.participant.node = i
            #p.participant.adj_matrix = adj_matrix
            p.participant.is_dropout = False

        logger.debug("=== NETWORK DEBUG START ===")
        logger.debug(f"Adjacency matrix: {adj_matrix}")

        logger.debug("Player -> Node assignment:")
        for p in selected_players:
            logger.debug(
                f"Player {p.id_in_group} (label={p.participant.label}, role={p.participant.role}) "
                f"assigned to node {p.participant.node}"
            )

        logger.debug("=== NETWORK DEBUG END ===")

    adj_matrix = net_spec["adj_matrix"]
    role_vector = net_spec["role_vector"]
    n = len(role_vector)
    if n != group_size:
        logger.warning(
            f"Configured group_size={group_size} but role_vector has length {n}. Using n={n}."
        )

    # map role_vector to assigned role labels
    role_for_idx = [
        Constants.minority if v == 1 else Constants.majority
        for v in role_vector
    ]

    # waiting players by role
    by_role = {
        Constants.majority: [
            p for p in waiting_players if p.participant.role == Constants.majority
        ],
        Constants.minority: [
            p for p in waiting_players if p.participant.role == Constants.minority
        ],
    }

    # do we have enough players of each required role?
    required_counts = {
        Constants.majority: sum(1 for r in role_for_idx if r == Constants.majority),
        Constants.minority: sum(1 for r in role_for_idx if r == Constants.minority),
    }
    have_counts = {
        Constants.majority: len(by_role[Constants.majority]),
        Constants.minority: len(by_role[Constants.minority]),
    }

    if (
        have_counts[Constants.majority] >= required_counts[Constants.majority]
        and have_counts[Constants.minority] >= required_counts[Constants.minority]
    ):
        players_ordered = []
        buckets = {
            Constants.majority: by_role[Constants.majority][:],
            Constants.minority: by_role[Constants.minority][:],
        }
        for i in range(n):
            needed_role = role_for_idx[i]
            if not buckets[needed_role]:
                logger.error(
                    f"Unexpected shortage for role {needed_role} at node {i}."
                )
                return  # wait for more players
            players_ordered.append(buckets[needed_role].pop(0))

        assign_nodes_and_matrix(players_ordered, adj_matrix)
        session.vars["group_formed"] = True
        logger.info(f"Populated network with {n} players.")
        return players_ordered
    else:
        logger.info(
            f"Waiting: need {required_counts} but have {have_counts} "
            f"(waiting={len(waiting_players)})"
        )
        return  # keep waiting


class NetworkFormationWaitPage(WaitPage):
    template_name = "unpop/GroupFormationPage.html"
    group_by_arrival_time = True

    def is_displayed(player):
        return player.round_number == 1

    def vars_for_template(player):
        if not player.arrived_grouppage:
            player.arrived_grouppage = True

        waiting_players = player.subsession.get_players()
        total_arrived = sum(p.arrived_grouppage for p in waiting_players)

        group_size = player.session.config.get("group_size", len(waiting_players))
        total_needed = int(group_size * 1.3)  # buffer

        if total_needed == 0:
            percent = 0
            return dict(percent=percent)

        percent = (total_arrived / total_needed) * 100
        percent = min(int(percent), 99)
        return dict(percent=percent)

    @staticmethod
    def after_all_players_arrive(group):
        logger.info("All players for the group have arrived.")


class IntroductionPage(Page):
    def vars_for_template(player):
        adj_matrix = player.session.vars["net_spec"]["adj_matrix"]
        my_node = player.participant.node
        degree = sum(adj_matrix[my_node])
        table_data = payoff_table(degree)
        group_size = player.session.config["group_size"]

        return dict(
            role=player.participant.role,
            network_condition=player.session.config.get("network_condition"),
            group_size=group_size,
            others=group_size-1,
            degree=degree,
            range_neighbors=list(range(degree + 1)) if degree > 0 else [],
            table_data=table_data,
            base="{:.2f}".format(Constants.base_payment),
            max="{:.2f}".format(Constants.max_payment),
        )

    def is_displayed(player):
        return player.round_number == 1 and not player.participant.vars.get(
            "exit_early", False
        )

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.introduction_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)
        player.prolific_id = player.participant.label


class DecisionPage(Page):
    form_model = "player"
    form_fields = ["choice"]

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)

        if timeout_happened or player.participant.is_dropout:
            if player.participant.role == Constants.minority:
                player.choice = True  # minorities stick to their preference
            else:
                player.choice = (random.random() < p_minority) # majority pick their preference with 1-p_minority
                #player.choice = random.random() < 0.5 # or fully random...

    def is_displayed(player):
        return not player.participant.vars.get("exit_early", False)

    def vars_for_template(player):
        adj_matrix = player.session.vars["net_spec"]["adj_matrix"]
        my_node = player.participant.node
        degree = sum(adj_matrix[my_node])

        table_data = payoff_table(degree)

        num_blue_previous_round = 0
        num_red_previous_round = 0
        if player.round_number > 1:
            neighbors = [
                i for i, connection in enumerate(adj_matrix[my_node]) if connection == 1
            ]

            prev_round = player.round_number - 1
            num_blue_previous_round = sum(
                1
                for p in player.group.get_players()
                if p.participant.node in neighbors
                and not p.participant.vars.get("exit_early", False)
                and p.in_round(prev_round).choice is True
            )
            num_red_previous_round = sum(
                1
                for p in player.group.get_players()
                if p.participant.node in neighbors
                and not p.participant.vars.get("exit_early", False)
                and p.in_round(prev_round).choice is False
            )

        return dict(
            group_size=player.session.config["group_size"],
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
    template_name = "unpop/ResultsWaitPage.html"

    def is_displayed(player):
        return not player.participant.vars.get("exit_early", False)

    def vars_for_template(player):
        # mark this player as arrived ONLY ONCE
        if not player.arrived_waitpage:
            player.arrived_waitpage = True

        players = player.group.get_players()
        arrived = sum(p.arrived_waitpage for p in players)
        total = len(players)

        percent = 100 * arrived / total if total > 0 else 0

        return dict(
            arrived=arrived,
            total=total,
            percent=percent,
        )

    def after_all_players_arrive(group):
        group.set_first_stage_earnings()

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(player, 5)


class ResultsPage(Page):
    def vars_for_template(player):
        my_choice = player.choice
        my_payoff = player.payoff

        my_node = player.participant.node
        adj_matrix =player.session.vars["net_spec"]["adj_matrix"]

        neighbors = []
        for i, connection in enumerate(adj_matrix[my_node]):
            if connection == 1:
                neighbors.append(i)

        neighbors_info = []
        for idx, neighbor_id in enumerate(neighbors, start=1):
            neighbor_player = next(
                (
                    p
                    for p in player.group.get_players()
                    if p.participant.node == neighbor_id
                ),
                None,
            )
            if neighbor_player:
                if neighbor_player.choice is None:
                    choice_display = "Missing"
                else:
                    choice_display = "Blue" if neighbor_player.choice else "Red"

                neighbors_info.append(
                    {
                        "neighbor": idx,
                        "id": neighbor_player.id,
                        "choice": choice_display,
                        "payoff": neighbor_player.payoff,
                    }
                )

        my_choice_display = "Blue" if my_choice else "Red"

        return dict(
            my_choice=my_choice_display,
            my_payoff=my_payoff,
            neighbors_info=neighbors_info,
            role=player.participant.role,
            round_number=player.round_number,
        )

    def is_displayed(player):
        return not player.participant.vars.get("exit_early", False)

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)


class FinalGameResults(Page):
    @staticmethod
    def is_displayed(player):
        return (
            player.round_number == Constants.num_rounds
            and not player.participant.vars.get("exit_early", False)
        )

    @staticmethod
    def js_vars(player):
        return dict(completionlink=player.subsession.session.config["completionlink"])

    @staticmethod
    def vars_for_template(player):
        accumulated_earnings = player.participant.payoff
        base = Constants.base_payment

        conversion = (
            Constants.points_per_euro_majority
            if player.participant.role == Constants.majority
            else Constants.points_per_euro_minority
        )

        euros = float(accumulated_earnings) / conversion
        euros = min(euros, Constants.max_payment)
        euros = max(euros, Constants.base_payment)
        bonus = max(euros - base, 0)

        player.participant.vars['bonus'] = round(bonus, 2)

        return dict(
            accumulated_earnings=accumulated_earnings,
            raw_euros=float(accumulated_earnings) / conversion,
            base="{:.2f}".format(base),
            bonus="{:.2f}".format(bonus),
            euros="{:.2f}".format(euros),
            test = TEST,
        )

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.bonus = player.participant.vars.get('bonus', 0) #replace to next page; after_arrive?

class ExitPage(Page):
    """
    Displayed to participants who either:
    - Arrive after the main group is full
    - Did not consent
    """

    @staticmethod
    def is_displayed(player: Player):
        # Only show exit page if the participant was flagged to exit early
        return player.participant.vars.get("exit_early", False)

    @staticmethod
    def vars_for_template(player: Player):
        # Determine which message to show and which completion link to use
        consented = player.participant.vars.get("consent", False)

        if consented:
            message = (
                "The group for this session is already full. "
                "You will not be participating in the experiment this time, "
                "but you will still receive the base payment for your time and effort."
            )
            completionlink = player.subsession.session.config.get("completionlink_nogroup")
        else:
            message = (
                "The group for this session is already full. "
                "You will not be participating in the experiment this time. Please return your submission."
            )
            completionlink = player.subsession.session.config.get("completionlink_late")

        return dict(
            message=message,
            completionlink=completionlink
        )

    @staticmethod
    def js_vars(player: Player):

        consented = player.participant.vars.get("consent", False)
        completionlink = (
            player.subsession.session.config.get("completionlink_nogroup")
            if consented
            else player.subsession.session.config.get("completionlink_late")
        )
        return dict(completionlink=completionlink)


page_sequence = [
    NetworkFormationWaitPage,
    IntroductionPage,
    DecisionPage,
    ResultsWaitPage,
    ResultsPage,
    FinalGameResults,
    ExitPage,
]
