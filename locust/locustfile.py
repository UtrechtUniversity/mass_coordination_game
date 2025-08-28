from locust import TaskSet, task, between, HttpUser
from locust.exception import StopUser

class OtreeApplication:
    def __init__(self, client, start_url=None):
        self.client = client
        self.start_url = start_url

    def run_experiment(self):
        with self.client.get(self.start_url, name=self.start_url, catch_response=True, allow_redirects=True) as response:
            newlink = response.url
            if newlink != self.start_url and response.ok:
                response.success()
            else:
                response.failure("Failed to join room")
                return

        status = True
        first_page = True
        while status:
            name = ': '.join(newlink.strip('/').split('/')[-3:])

            if first_page:
                form_data = {"consent": "True"}
                first_page = False
            else:
                form_data = {}

            with self.client.post(newlink, data=form_data, name=name, catch_response=True, allow_redirects=True) as response:
                oldlink = newlink
                newlink = response.url

                if oldlink == newlink or not response.ok:
                    if response.ok:
                        response.success()
                    else:
                        response.failure("oTree-Locust error")
                    status = False
                else:
                    response.success()

class OtreeTaskSet(TaskSet):
    def on_start(self):
        room_path = "/room/your_study"
        full_url = self.parent.host.rstrip("/") + room_path
        self.otree_client = OtreeApplication(self.client, start_url=full_url)

    @task(1)
    def start_bot(self):
        self.otree_client.run_experiment()
        raise StopUser()

class WebsiteUser(HttpUser):
    wait_time = between(5, 9)
    host = 'http://localhost:8000'
    tasks = [OtreeTaskSet]
