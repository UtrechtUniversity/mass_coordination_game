from locust import HttpUser, TaskSet, task, between

class oTreeTasks(TaskSet):

    @task
    def play_experiment(self):
        self.client.get("/room/your_study")

class WebsiteUser(HttpUser):
    tasks = [oTreeTasks]

    host = "http://game.robfranken.net"

    wait_time = between(1, 3)
