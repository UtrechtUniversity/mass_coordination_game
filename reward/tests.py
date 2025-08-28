from . import *

class PlayerBot(Bot):
    def play_round(self):
        #if self.player.participant.consent: #@RF: UNCOMMENT! (For testing, where consentpage is not included)
            yield Submission(PaymentInfo, {}, check_html=False)
