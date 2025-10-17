from os import environ

SESSION_CONFIGS = [
    dict(
        name="unpopular_norm_flexible",
        display_name="test_flex",
        num_demo_participants=50,
        group_size=10,
        #network_condition = "test_n20",
        #app_sequence=["consent", "unpop", "survey", "reward"],
        app_sequence=["consent", "unpop"],
        completionlink='https://app.prolific.com/submissions/complete?cc=C104VFED',
        use_browser_bots=True
    ),
]

ROOMS = [
    dict(
        name='your_study',
        display_name='your_study',
        #participant_label_file='_rooms/your_study.txt',
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