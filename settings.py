from os import environ
import random

SESSION_CONFIGS = [

    dict(
        name="unpopular_norm_small",
        display_name="test_n6",
        num_demo_participants=6,
        network_condition= "test",
        punishment_condition=False,
        app_sequence=["unpop"],
        participant_label_file='_rooms/test.txt',
        use_secure_urls=True,
        completionlink='https://app.prolific.co/submissions/complete?cc=11111111'
    ),

    dict(
        name="unpopular_norm_big",
        display_name="test_n20",
        num_demo_participants=20,
        network_condition = "test_n20",
        punishment_condition = False,
        app_sequence=["unpop"],
    ),

    dict(
        name="unpopular_norm_flexible",
        display_name="test_flex",
        num_demo_participants=2,
        punishment_condition=False,
        app_sequence=["unpop"],
        participant_label_file='_rooms/test.txt',
        use_secure_urls=True,
        completionlink='https://app.prolific.co/submissions/complete?cc=11111111'
    ),

]

ROOMS = [
    dict(
        name='test',
        display_name='Test room'
    )
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1/30,
    participation_fee=5.00,
    doc="",
)

PARTICIPANT_FIELDS = ["is_dropout", "role", 'has_dropped_out', 'too_many_inactive_in_group', 'guesses', 'choices', 'lobby_id', 'node', 'adj_matrix', 'role_vector', 'MPCR', 'groupsize']

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = "en"

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = "EUR"
USE_POINTS = True

ADMIN_USERNAME = "admin"
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get("OTREE_ADMIN_PASSWORD")

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = "secret"