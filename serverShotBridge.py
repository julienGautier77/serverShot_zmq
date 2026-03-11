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
                 pub_port: int,  # publication port from the ZMQ shot server
                 rep_port: int,
                #  bridge_pub_port: int,  # This is the port for the bridge's own PUB socket (e.g., 5012)
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

        self.pub_port = pub_port
        self.rep_port = rep_port
        self.is_running = True

        # ZMQ context
        self.context = zmq.Context()

        # SUB socket for PUB/SUB system (connect to SERVERGUI/ZMQSERVER PUB)
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://localhost:{pub_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "SHOOT")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "HEARTBEAT")

        # REQ socket for requesting the current shot number (on first connection)
        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://localhost:{rep_port}")

        self.server_lhc.start()
        print(f"Server bridge running on {self.server_lhc.address_for_client}")
        self._request_initial_shot_number()


    def _request_initial_shot_number(self):
        """Request the current shot number from the ZMQSERVER and set it in server_lhc."""
        try:
            self.req_socket.send_string('shot:')
            response = self.req_socket.recv_string()
            initial_shot_number = int(response)
            print(f"Initial shot number received: {initial_shot_number}")
            self.server_lhc.set_data({
                "shot_number": initial_shot_number,
                "timestamp": time.strftime("%Y%m%d_%H%M%S"),
            })
        except Exception as e:
            print(f"Error requesting initial shot number: {e}")


    def run(self):
        poller = zmq.Poller()
        poller.register(self.sub_socket, zmq.POLLIN)

        try:
            while self.is_running:
                socks = dict(poller.poll(100))
                if self.sub_socket in socks:
                    topic = self.sub_socket.recv_string()
                    event = self.sub_socket.recv_json()
                    if topic == "SHOOT":
                        self._handle_shoot_event(event)
        except Exception as e:
            print(f"Exception in ServerShotBridge: {e}")
        finally:
            self.sub_socket.close()
            self.req_socket.close()
            self.context.term()
            self.server_lhc.stop()


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

    def stop(self):
        self.is_running = False


if __name__ == "__main__":

    bridge = ServerShotBridge(
        "Shot bridge test",
        "tcp://*:7891",  # LAPLACE-LHC server address
        5009,            # SERVERGUI/ZMQSERVER PUB port (connect)
        5008             # SERVERGUI/ZMQSERVER REP port (connect)
    )
    bridge.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()
