import queue
from multiprocessing.managers import BaseManager

COMMAND_QUEUE_HOST = "127.0.0.1"
COMMAND_QUEUE_PORT = 5001
AUTHKEY = b"moonserver"


class QueueManager(BaseManager):
    pass


def start_manager_server():
    command_queue = queue.Queue()
    response_queue = queue.Queue()

    class ServerQueueManager(BaseManager):
        pass

    ServerQueueManager.register("get_command_queue", callable=lambda: command_queue)
    ServerQueueManager.register("get_response_queue", callable=lambda: response_queue)

    manager = ServerQueueManager(
        address=(COMMAND_QUEUE_HOST, COMMAND_QUEUE_PORT),
        authkey=AUTHKEY,
    )
    manager.start()

    return manager


def connect_to_manager():
    class ClientQueueManager(BaseManager):
        pass

    ClientQueueManager.register("get_command_queue")
    ClientQueueManager.register("get_response_queue")

    manager = ClientQueueManager(
        address=(COMMAND_QUEUE_HOST, COMMAND_QUEUE_PORT),
        authkey=AUTHKEY,
    )
    manager.connect()

    return manager.get_command_queue(), manager.get_response_queue()
