import zmq
import time
from PyQt6 import QtCore

from laplace_server.server_lhc import ServerLHC
from laplace_server.protocol import DEVICE_SHOT

class ServerShotBridge(QtCore.QThread):
    """
    Bridge between LAPLACE-LHC ZMQ server and PUB/SUB system.
    """
    def __init__(self,
                 name: str,
                 address: str,
                 pub_port: int,  # This is the PUB port of SERVERGUI/ZMQSERVER (5009)
                 sub_port: int,  # This is the SUB port of SERVERGUI/ZMQSERVER (5010)
                 bridge_pub_port: int,  # This is the port for the bridge's own PUB socket (e.g., 5012)
                 empty_data_after_get: bool=False,
                 parent=None):

        super().__init__(parent)

        self.server_lhc = ServerLHC(
            name=name,
            address=address,
            freedom=0,
            device=DEVICE_SHOT,
            data={},
            empty_data_after_get=empty_data_after_get
        )

        self.pub_port = pub_port  # SERVERGUI/ZMQSERVER PUB port (5009)
        self.sub_port = sub_port  # SERVERGUI/ZMQSERVER SUB port (5010)
        self.bridge_pub_port = bridge_pub_port  # Bridge's own PUB port (5012)
        self.is_running = True

        # ZMQ context
        self.context = zmq.Context()

        # SUB socket for PUB/SUB system (connect to SERVERGUI/ZMQSERVER PUB)
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://localhost:{pub_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "SHOOT")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "HEARTBEAT")

        # PUB socket for PUB/SUB system (bind to bridge's own port)
        self.pub_socket = self.context.socket(zmq.PUB)
        # self.pub_socket.setsockopt(zmq.SNDTIMEO, 1000)
        self.pub_socket.setsockopt(4, 1)
        self.pub_socket.bind(f"tcp://*:{bridge_pub_port}")

        self.server_lhc.start()
        print(f"Server bridge running on {self.server_lhc.address_for_client}")

    def run(self):
        poller = zmq.Poller()
        poller.register(self.sub_socket, zmq.POLLIN)

        while self.is_running:
            socks = dict(poller.poll(100))
            if self.sub_socket in socks:
                topic = self.sub_socket.recv_string()
                event = self.sub_socket.recv_json()
                if topic == "SHOOT":
                    self._handle_shoot_event(event)

    def _handle_shoot_event(self, event):
        """
        Handle a shot event: update the server_lhc data dictionary.
        """
        nbshot = event.get('number')
        timestamp = event.get('timestamp')
        print('Shot received, number:', nbshot)

        # Update the server_lhc data dictionary
        new_data = {
            "shot_number": nbshot,
            "timestamp": timestamp,
        }
        self.server_lhc.set_data(new_data)

        # Optionally, publish the event to the bridge's own PUB socket
        self.pub_socket.send_string("SHOT_DATA", zmq.SNDMORE)
        self.pub_socket.send_json(new_data)

    def stop(self):
        self.is_running = False
        self.server_lhc.stop()
        self.sub_socket.close()
        self.pub_socket.close()
        self.context.term()


if __name__ == "__main__":

    bridge = ServerShotBridge(
        "Shot bridge test",
        "tcp://*:7891",  # LAPLACE-LHC server address
        5009,            # SERVERGUI/ZMQSERVER PUB port (connect)
        5010,            # SERVERGUI/ZMQSERVER SUB port (not used here, but for completeness)
        5012,            # Bridge's own PUB port (bind)
    )
    bridge.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()
