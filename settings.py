from os import environ

# configure the session
SESSION_CONFIGS = [
    dict(
        name="unpopular_norm1",
        display_name="test_n20_2min",
        num_demo_participants=50, #number of people allowed to enter the game lobby
        group_size=20, #number of people needed to populate the network (num_demo_part - group_size == n.excess_players)
        network_condition = "test_n20", #specificy a network condition (based on the group_size; e.g., test_n20)
        app_sequence=["consent", "comprehension", "unpop", "survey", "reward", "exit"],
        completionlink='https://app.prolific.com/submissions/complete?cc=C7NZ9ZUY',
        use_browser_bots=False,
    ),

dict(
        name="unpopular_norm2",
        display_name="test_n4(star)_1min",
        num_demo_participants=10,
        group_size=4,
        network_condition = "test_n4",
        app_sequence=["consent", "comprehension", "unpop", "survey", "reward", "exit"],
        completionlink='https://app.prolific.com/submissions/complete?cc=C7NZ9ZUY',
        use_browser_bots=False,
    ),
]

# set some central parameters to be used across apps:
title = 'The Fashion Dilemma'
majority_role = 'Red'
minority_role = 'Blue'
p_minority = 0.10 # !!this needs to correspond to the proportion of minorities in the network configuration!!
num_rounds = 15

# including also the incentive structure
s = 15
e = 10
z = 50
w = 40
lambda1 = 4.3
lambda2 = 1.8

# and payment variables (base pay; conversion rates; etc.)
base_payment = 2.5
max_payment = 5.5
points_per_euro_majority = 85
points_per_euro_minority = 22

#configure a room
ROOMS = [
    dict(
        name='fashion_dilemma',
        display_name='The "Fashion Dilemma"',
        #participant_label_file='_rooms/fashion_dilemma.txt',
        #use_secure_urls=True,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1/30,
    participation_fee=3.00,
    doc="",
)

PARTICIPANT_FIELDS = [ "bonus", "consent", "is_dropout", "role", 'has_dropped_out', 'too_many_inactive_in_group','node', 'adj_matrix', 'role_vector', 'exit_early']
LANGUAGE_CODE = "en"
REAL_WORLD_CURRENCY_CODE = "EUR"
USE_POINTS = True
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = environ.get("OTREE_ADMIN_PASSWORD")
DEMO_PAGE_INTRO_HTML = """ """
SECRET_KEY = "secret"