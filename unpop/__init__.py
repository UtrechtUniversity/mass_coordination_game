from otree.api import *
import json
import os
import math
import random

doc = """
“The spread of an unpopular norm in a social network experiment"
"""
class Constants(BaseConstants):
    """
    This class defines the constants used in the game.
    """
    title = "The Fashion Dilemma"
    name_in_url = "fashion_dilemma"
    players_per_group = None # one session constitutes one group.
    num_rounds = 12
    # Roles
    majority_role = 'Red'
    minority_role = 'Blue'
    # fixed rewards for following one's private norm
    s = 15 # for majority
    e = 10 # for minority (e>0)
    # minority receives variable rewards for coordinating with neighbors
    z = 50 # for coordinating with the minority
    w = 40 # for coordinating with the majority
    # diminishing returns on coordination (such that the "unpopular norm" is a Pareto-suboptimal equilibrium).
    lambda1 = 4.3
    lambda2 = 1.8
    min_group_participation = 0.5  # minimum group participation required for the game to continue
    introduction_timeout_seconds = 420  # timeout for the introduction stage
    comprehension_timeout_seconds = 180 # for comprehension test
    other_pages_timeout_seconds = 120  # timeout for other stages
    # in case no network condition is specified, a network will be generated; based on the following targets:
    density = .30
    min_prop = .30
    #rewards
    points_per_euro_majority = 85
    points_per_euro_minority = 22
    base_payment = 2.5
    max_payment = 5.5

class Subsession(BaseSubsession):
    """
    This class represents a subsession of the game.
    """
    pass

def creating_session(subsession):
    """
    Initializes the network structure for the session based on the experimental condition:
    - If a 'network_condition' is specified, it loads a predefined network from a JSON file.
        + Randomly assigns players to roles based on the predefined role distribution
    - If not, it generates a random network structure for the current number of players (and puts minorities on central positions)
    """
    def generate_network(n, edge_prob):
        """
        generates a simple, connected, undirected network with no isolates.
        """
        adj_matrix = [[0] * n for _ in range(n)]
        nodes = list(range(n))
        random.shuffle(nodes)

        # spanning tree to ensure connectivity
        for i in range(1, n):
            a = nodes[i]
            b = random.choice(nodes[:i])
            adj_matrix[a][b] = 1
            adj_matrix[b][a] = 1

        # add extra random edges
        for i in range(n):
            for j in range(i + 1, n):
                if adj_matrix[i][j] == 0 and random.random() < Constants.density:
                    adj_matrix[i][j] = 1
                    adj_matrix[j][i] = 1
        return adj_matrix

    if subsession.round_number == 1:
        players = subsession.get_players()
        num_players = len(players)

        net_condition = subsession.session.config.get("network_condition")

        if net_condition:
            file_path = os.path.join("networks", f"network_{net_condition}.json")
            try:
                with open(file_path, 'r') as f:
                    net = json.load(f)
                adj_matrix = net['adj_matrix'] # connections between players
                role_vector = net['role_vector'] # player roles
                print(f"Loaded network from {file_path}")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading network file: {e}")
                return
        else:
            print("No network_condition specified. Generating simple, connected, undirected graph ...")
            # create a random undirected simple graph
            edge_prob = Constants.density
            adj_matrix = generate_network(num_players, edge_prob=edge_prob)

            # get degree of each node
            degrees = [sum(row) for row in adj_matrix]

            # number of minorities
            minority_share = Constants.min_prop
            num_minority = max(1, int(minority_share * num_players))

            # sort nodes by degree descending (most central first)
            nodes_srt_by_deg = sorted(range(num_players), key=lambda x: degrees[x], reverse=True)

            # assign minority role (1) to nodes with highest degree
            role_vector = [0] * num_players  # majority default = 0
            for i in nodes_srt_by_deg[:num_minority]:
                role_vector[i] = 1  # minority

            # print network matrix:
            print("Generated adjacency matrix:")
            for row in adj_matrix:
                print(row)
            print("Role vector with minorities assigned to most central nodes:")
            print(role_vector)

        # sanity check
        if len(players) != len(role_vector):
            print(f"Error: Number of players ({len(players)}) does not match role vector length ({len(role_vector)}).")
            return

        for i, player in enumerate(players):
            role = Constants.minority_role if role_vector[i] == 1 else Constants.majority_role
            player.participant.role = role
            player.participant.node = i
            player.participant.is_dropout = False
            player.participant.adj_matrix = adj_matrix

class Player(BasePlayer):
    """
    This represents the (dynamic) player class
    """
    choice = models.BooleanField(
        verbose_name="Make your choice: Will you wear a Blue or a Red T-shirt today?",
        widget=widgets.RadioSelect,
        choices=[
            (True, 'Blue'),
            (False, 'Red')
            ],
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

def timeout_check(player, timeout_happened):
    """
    This function checks if a timeout has occurred for a player.
    If a timeout has occurred and the participant is not a dropout, it marks the player as inactive and sets the
    participant as a dropout. If the number of inactive players reaches the minimum required number
    (i.e., proportion of group size), it marks the group as failed.
    """
    participant = player.participant
    groupsize = len(player.subsession.get_players())

    if timeout_happened and not participant.is_dropout:
        player.group.inactive_players += 1
        # in order to check the status of players over rounds, set the attribute at the player-level:
        player.inactive = True
        participant.is_dropout = True

    if groupsize - player.group.inactive_players < round(groupsize * Constants.min_group_participation):
        player.group.failed = True

def timeout_time(player, timeout_seconds):
    """
    This function calculates the timeout time for a player.
    If the participant is a dropout or the group has failed, it returns an instant timeout of 1 second.
    Otherwise, it returns the specified timeout_seconds.

    Args:
        player (Player): The player for whom to calculate the timeout time.
        timeout_seconds (int): The timeout duration in seconds.

    Returns:
        int: The calculated timeout time in seconds.
    """
    participant = player.participant
    if participant.is_dropout or player.group.failed:
        return 1  # instant timeout, 1 second
    else:
        return timeout_seconds

class Group(BaseGroup):
    """
    This represents the group class
    """
    failed = models.BooleanField(initial=False)
    inactive_players = models.IntegerField(initial=0)

    def set_first_stage_earnings(self):
        """
        This function calculates the earnings for each player in the group.
        It calculates players' earnings as a function of their role-specific utility function.
        """
        players = self.get_players()

        for player in players:
            # skip players who dropped out!
            if player.participant.is_dropout:
                player.payoff = 0
                continue

            my_choice = player.choice
            my_node = player.participant.node
            adj_matrix = player.participant.adj_matrix

            # find the neighbors of the current player who are no dropouts:
            neighbors = []
            for i, connection in enumerate(adj_matrix[my_node]):
                if connection == 1:
                    neighbor_player = next(p for p in players if p.participant.node == i)
                    if not neighbor_player.participant.is_dropout:
                        neighbors.append(i)

            # retrieve the neighbors' choices based on the player's id_in_subsession
            neighbor_choices = []
            for neighbor_id in neighbors:
                neighbor_player = next(p for p in players if p.participant.node == neighbor_id)
                neighbor_choices.append(neighbor_player.choice)

            # count the number of neighbors who picked Blue and Red
            blue_neighbors = neighbor_choices.count(True)
            red_neighbors = neighbor_choices.count(False)

            # initialize utility
            utility = 0
            if player.participant.role == Constants.minority_role:
                if my_choice:
                    utility = Constants.e
                else:
                    utility = 0  # fallback if minority chooses Red
            elif player.participant.role == Constants.majority_role:
                num_nbh = len(neighbors)
                if num_nbh > 0:
                    if my_choice:
                        utility = Constants.z * (1 - math.exp(-Constants.lambda1 * (blue_neighbors / num_nbh))) / (
                                1 - math.exp(-Constants.lambda1))
                    else:
                        utility = Constants.s + Constants.w * (
                                    1 - math.exp(-Constants.lambda2 * (red_neighbors / num_nbh))) / (
                                          1 - math.exp(-Constants.lambda2))
                else:
                    if my_choice:
                        utility = 0
                    else:
                        utility = Constants.s

            # assign payoff
            player.payoff = max(utility, 0)

class IntroductionPage(Page):
    """
    This class represents the introduction page of the game.
    """

    def vars_for_template(player):
        """
        This function provides the template variables for the introduction page.
        Args:
            player (Player): The player for whom to provide the template variables.
        Returns:
            dict: The template variables.
        """
        # access adjacency matrix
        adj_matrix = player.participant.adj_matrix
        my_node = player.id_in_group
        degree = sum(adj_matrix[my_node - 1])

        # generate a table illustrating coordination rewards
        table_data = []
        for n in range(degree + 1):  # Number of coordinating alters (neighbors) ranges from 0 to degree
            p = n / degree  # Proportion of neighbors coordinating

            # Compute the utility for coordinating with neighbors who adopted the behavior
            zstar = Constants.z * (1 - math.exp(-Constants.lambda1 * p)) / (1 - math.exp(-Constants.lambda1))

            # Compute the utility for coordinating with neighbors who resisted the behavior
            wstar = Constants.w * (1 - math.exp(-Constants.lambda2 * p)) / (1 - math.exp(-Constants.lambda2))

            # Append the result to the table_data with the number of neighbors and corresponding zstar, wstar
            table_data.append({
                'c_n': n,  # Number of coordinating alters
                'zstar': int(zstar),  # Computed value for zstar
                'wstar': int(wstar)  # Computed value for wstar
            })

        return dict(
            role=player.participant.role,
            network_condition=player.session.config.get("network_condition"),
            punishment_condition=player.session.config.get("punishment_condition"),
            group_size = len(player.subsession.get_players()),
            degree=degree,
            range_neighbors=list(range(degree + 1)),
            table_data=table_data,
            )

    def is_displayed(player):
        """
        This function determines whether the introduction page should be displayed.
        It returns True if it is the first round, False otherwise.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the page should be displayed, False otherwise.
        """
        # Show this page only on the first round
        return player.round_number == 1

    def get_timeout_seconds(player):
        """
        This function calculates the timeout time for the introduction page.
        If the participant is a dropout or the group has failed, it returns an instant timeout of 1 second.
        Otherwise, it returns the specified introduction timeout seconds.

        Args:
            player (Player): The player for whom to calculate the timeout time.

        Returns:
            int: The calculated timeout time in seconds.
        """
        return timeout_time(player, Constants.introduction_timeout_seconds)

    def before_next_page(player, timeout_happened):
        """
        This function is called before moving to the next page.
        It checks if a timeout has occurred and updates the player's status accordingly.

        Args:
            player (Player): The player for whom to perform the before_next_page actions.
            timeout_happened (bool): True if a timeout has occurred, False otherwise.
        """
        timeout_check(player, timeout_happened)
        player.prolific_id = player.participant.label

class ComprehensionPage(Page):
    form_model = 'player'
    form_fields = ['q_red_zero', 'q_blue_zero', 'q_red_half', 'q_blue_half']

    def is_displayed(player):
        return player.round_number == 1 and player.participant.role == Constants.majority_role

    def vars_for_template(player):

        adj_matrix = player.participant.adj_matrix
        my_node = player.id_in_group - 1
        degree = sum(adj_matrix[my_node])

        table_data = []
        for n in range(degree + 1):
            p = n / degree
            zstar = Constants.z * (1 - math.exp(-Constants.lambda1 * p)) / (1 - math.exp(-Constants.lambda1))
            wstar = Constants.w * (1 - math.exp(-Constants.lambda2 * p)) / (1 - math.exp(-Constants.lambda2))
            table_data.append({
                'c_n': n,
                'zstar': int(zstar),
                'wstar': int(wstar)
            })

        blue_neighbors = degree
        red_neighbors = 0
        payoff_red_zero = Constants.s + Constants.w * (1 - math.exp(-Constants.lambda2 * (red_neighbors / max(1, degree)))) / (1 - math.exp(-Constants.lambda2))
        payoff_blue_zero = Constants.z * (1 - math.exp(-Constants.lambda1 * (blue_neighbors / max(1, degree)))) / (1 - math.exp(-Constants.lambda1))

        blue_neighbors_half = degree // 2
        red_neighbors_half = degree - blue_neighbors_half
        payoff_red_half = Constants.s + Constants.w * (1 - math.exp(-Constants.lambda2 * (red_neighbors_half / max(1, degree)))) / (1 - math.exp(-Constants.lambda2))
        payoff_blue_half = Constants.z * (1 - math.exp(-Constants.lambda1 * (blue_neighbors_half / max(1, degree)))) / (1 - math.exp(-Constants.lambda1))

        # store correct answers in player so we can check them later
        player.payoff_red_zero = int(payoff_red_zero)
        player.payoff_blue_zero = int(payoff_blue_zero)
        player.payoff_red_half = int(payoff_red_half)
        player.payoff_blue_half = int(payoff_blue_half)

        return dict(
            role=player.participant.role,
            degree=degree,
            table_data=table_data,
            blue_neighbors_half=blue_neighbors_half,
            red_neighbors_half=red_neighbors_half,
        )

    def error_message(player, values):
        # Use the stored payoffs
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
            return (
                    "Incorrect answers: " + ", ".join(incorrect_fields)  +
                    ".  Your total points = reward for picking a color (Table 1) + reward for matching neighbors (Table 2)."
            )

    def get_timeout_seconds(player):
        return timeout_time(player, Constants.comprehension_timeout_seconds)

    def before_next_page(player, timeout_happened):
        timeout_check(player, timeout_happened)

class DecisionPage(Page):
    """
    This class represents the decision page of the game.
    """
    form_model = 'player'
    form_fields = ['choice']

    def get_timeout_seconds(player):
        """
        This function calculates the timeout time for the decision page.
        If the participant is a dropout or the group has failed, it returns an instant timeout of 1 second.
        Otherwise, it returns the specified other pages timeout seconds.

        Args:
            player (Player): The player for whom to calculate the timeout time.

        Returns:
            int: The calculated timeout time in seconds.
        """
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        """
        This function is called before moving to the next page.
        It checks if a timeout has occurred and updates the player's status accordingly.

        Args:
            player (Player): The player for whom to perform the before_next_page actions.
            timeout_happened (bool): True if a timeout has occurred, False otherwise.
        """
        timeout_check(player, timeout_happened)

    def is_displayed(player):
        """
        This function determines whether the contribution page should be displayed.
        It returns True if the group has not failed and the participant is not a dropout, False otherwise.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the page should be displayed, False otherwise.
        """
        return not player.group.failed and not player.participant.is_dropout

    def vars_for_template(player):
        # access adjacency matrix
        adj_matrix = player.participant.adj_matrix
        my_node = player.id_in_group
        degree = sum(adj_matrix[my_node - 1])

        # generate a table illustrating coordination rewards
        table_data = []
        for n in range(degree + 1):  # number of coordinating alters (neighbors) ranges from 0 to degree
            p = n / degree  # proportion of neighbors coordinating

            # compute the utility for coordinating with neighbors who adopted the behavior
            zstar = Constants.z * (1 - math.exp(-Constants.lambda1 * p)) / (1 - math.exp(-Constants.lambda1))

            # compute the utility for coordinating with neighbors who resisted the behavior
            wstar = Constants.w * (1 - math.exp(-Constants.lambda2 * p)) / (1 - math.exp(-Constants.lambda2))

            # append the result to the table_data with the number of neighbors and corresponding zstar, wstar
            table_data.append({
                'c_n': n,  # Number of coordinating alters
                'zstar': int(zstar),  # Computed value for zstar
                'wstar': int(wstar)  # Computed value for wstar
            })

            # initialize variables for the previous round (only available for rounds > 1)
            num_blue_previous_round = 0
            num_red_previous_round = 0

            if player.round_number > 1:
                neighbors = []
                for i, connection in enumerate(adj_matrix[my_node - 1]):
                    if connection == 1:
                        neighbors.append(i)
                # get previous round number
                prev_round = player.round_number - 1

                # count Blue neighbors who were active and chose Blue in prev round
                num_blue_previous_round = sum(
                    1
                    for p in player.group.get_players()
                    if (p.id_in_group - 1) in neighbors
                    and not p.participant.is_dropout
                    and p.in_round(prev_round).choice is True
                )

                # count Red neighbors who were active and chose Red in prev round
                num_red_previous_round = sum(
                    1
                    for p in player.group.get_players()
                    if (p.id_in_group - 1) in neighbors
                    and not p.participant.is_dropout
                    and p.in_round(prev_round).choice is False
                )

                # return all the data to the template
        return dict(
            group_size=len(player.subsession.get_players()),
            network_condition=player.session.config.get("network_condition"),
            role=player.participant.role,
            round_number=player.round_number,
            degree=degree,
            range_neighbors=list(range(degree + 1)),
            table_data=table_data,  #pass the whole table to the template
            num_blue_previous_round=num_blue_previous_round,
            num_red_previous_round=num_red_previous_round,
        )

class ResultsWaitPage(WaitPage):
    """
    This class represents the wait page of the game.
    """
    def after_all_players_arrive(group):
        """
        This function is called after all players in the group have arrived.
        It retrieves the decisions of all players;
        and it updates the payoffs of players accordingly.
        """
        group.set_first_stage_earnings()

    def is_displayed(player):
        """
        This function determines whether the group wait page should be displayed.
        It returns True if the group has not failed and the participant is not a dropout, False otherwise.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the page should be displayed, False otherwise.
        """
        return not player.group.failed and not player.participant.is_dropout

    def vars_for_template(player):
        return dict(
            group_size=len(player.subsession.get_players()),
            network_condition=player.session.config.get("network_condition"),
            role=player.participant.role,
            round_number=player.round_number,
        )

class ResultsPage(Page):
    """
    This class represents the results page of the game.
    """
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
                # only neighbors get 'Missing' if dropout or choice None
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
        """
        This function determines whether the results page should be displayed.
        It returns True if the group has not failed and the participant is not a dropout, False otherwise.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the page should be displayed, False otherwise.
        """
        return not player.group.failed and not player.participant.is_dropout

    def get_timeout_seconds(player):
        """
        This function calculates the timeout time for the results page.
        If the participant is a dropout or the group has failed, it returns an instant timeout of 1 second.
        Otherwise, it returns the specified other pages timeout seconds.

        Args:
            player (Player): The player for whom to calculate the timeout time.

        Returns:
            int: The calculated timeout time in seconds.
        """
        return timeout_time(player, Constants.other_pages_timeout_seconds)

    def before_next_page(player, timeout_happened):
        """
        This function is called before moving to the next page.
        It checks if a timeout has occurred and updates the player's status accordingly.
        Args:
            player (Player): The player for whom to perform the before_next_page actions.
            timeout_happened (bool): True if a timeout has occurred, False otherwise.
        """
        timeout_check(player, timeout_happened)

class FinalGameResults(Page):
    """
    This class represents the final game results page of the game.
    """
    @staticmethod
    def is_displayed(player):
        """
        Determines whether the final game results page should be displayed for a player.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the final game results page should be displayed, False otherwise.
        """
        return (
            player.round_number == Constants.num_rounds
            and not player.group.failed
            and not player.participant.is_dropout
        )

    @staticmethod
    def js_vars(player):
        return dict(
            completionlink=player.subsession.session.config['completionlink']
        )

    @staticmethod
    def vars_for_template(player):
        """
        Provides the variables for the template of the final game results page.

        Args:
            player (Player): The player for whom to provide the variables.

        Returns:
            dict: The variables for the template.
        """

        accumulated_earnings = player.participant.payoff
        base = Constants.base_payment

        conversion = (
            Constants.points_per_euro_majority
            if player.participant.role == Constants.majority_role
            else Constants.points_per_euro_minority
        )

        euros = accumulated_earnings * 1/conversion
        euros = min(euros, Constants.max_payment)
        euros = max(euros, Constants.base_payment)
        bonus = max(euros - base, 0)

        player.participant.bonus = bonus


        return dict(
            accumulated_earnings=accumulated_earnings,
            base=base,
            bonus=bonus,
            euros=euros,
        )

class FailedGamePage(Page):
    """
    This class represents the failed game page of the game.
    """
    def vars_for_template(player):
        """
        Provides the variables for the template of the failed game page.

        Args:
            player (Player): The player for whom to provide the variables.

        Returns:
            dict: The variables for the template.
        """
        return dict(one_dropout=player.participant.is_dropout and player.round_number == Constants.num_rounds)

    def is_displayed(player):
        """
        Determines whether the failed game page should be displayed for a player.

        Args:
            player (Player): The player for whom to determine the display status.

        Returns:
            bool: True if the failed game page should be displayed, False otherwise.
        """
        return player.group.failed or (player.participant.is_dropout and player.round_number == Constants.num_rounds)

page_sequence = [IntroductionPage,
                 #ComprehensionPage,
                 DecisionPage,
                 ResultsWaitPage,
                 ResultsPage,
                 FinalGameResults,
                 FailedGamePage,]