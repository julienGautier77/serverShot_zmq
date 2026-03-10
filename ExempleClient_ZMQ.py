import time
import sys
import zmq
from PyQt6.QtCore import pyqtSignal as Signal
from PyQt6 import QtCore
import uuid
import pathlib
from PyQt6.QtWidgets import QApplication


class THREADCLIENT(QtCore.QThread):
    '''
    Thread client ZMQ 
    Tous les événements (SHOOT, CONFIG) sont reçus via PUB/SUB
    Le fichier de configuration confServer.ini doit être présent dans le même dossier que ce script, avec les paramètres du serveur
    '''
    newShotnumber = Signal(int)   # Signal pour le numéro de tir
    pathSignal = Signal(str)      # Signal pour le path
    autoSignal = Signal(str)      # Signal pour autosave
    
    def __init__(self, parent=None):
        super(THREADCLIENT, self).__init__()

        p = pathlib.Path(__file__)
        self.conf = QtCore.QSettings(str(p.parent / 'confServer.ini'), QtCore.QSettings.Format.IniFormat)
        self.name ="Client test"
        
        # Lire la configuration
        self.serverHost = str(self.conf.value(self.name + "/server"))
        self.serverPort = int(self.conf.value(self.name + "/serverPort"))#, "5009")) # ? ??
        print(f"Config loaded: server={self.serverHost}, port={self.serverPort}")
        self.ClientIsConnected = False
        self.client_id = str(uuid.uuid4())
        
        # envoyer heartbeat au serveur 
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 10 # interval de temps pour envoyer les heartbeat au serveur 
        
        # ZMQ context et sockets
        self.context = None
        self.sub_socket = None
        self.pub_socket = None
        
    def run(self):

        print(f"Connecting to ZMQ server: {self.serverHost}:{self.serverPort}")
        
        try:
            # Créer le contexte ZMQ
            self.context = zmq.Context()
            
            # Socket SUB pour recevoir les événements du serveur
            self.sub_socket = self.context.socket(zmq.SUB)
            self.sub_socket.connect(f"tcp://{self.serverHost}:{self.serverPort}")
            
            # S'abonner à tous les types d'événements
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "SHOOT")      # Événements de tir
            #self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "CONFIG")     # Mises à jour path/autosave
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "REGISTERED") # Confirmation d'enregistrement client
            self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "HEARTBEAT")  # Heartbeat serveur pour gerer si deconnection

            # Socket PUB pour envoyer notre enregistrement
            self.pub_socket = self.context.socket(zmq.PUB)
            self.pub_socket.connect(f"tcp://{self.serverHost}:{self.serverPort + 1}")
            
            # Petite pause pour que la connexion s'établisse
            time.sleep(0.1)
            
            # S'enregistrer auprès du serveur
            self._send_register()
            
            self.ClientIsConnected = True
            #print(f'Client connected to server {self.serverHost}')
            
            
        except Exception as e:
            print(f'Connection error: {e}')
            print('Do you start the server?')
            self.ClientIsConnected = False
            return
        
        # Poller pour gérer les timeouts
        poller = zmq.Poller()
        poller.register(self.sub_socket, zmq.POLLIN)
        
        # Variables pour détecter la déconnexion
        last_heartbeat = time.time()
        self.heartbeat_timeout = 15.0  # 10 secondes sans heartbeat = serveur déconnecté

        # Boucle principale - Écouter les événements
        while self.ClientIsConnected:
            try:
                # Attendre un événement avec timeout de 100ms
                socks = dict(poller.poll(100))
                
                if self.sub_socket in socks and socks[self.sub_socket] == zmq.POLLIN:
                    # Recevoir l'événement
                    topic = self.sub_socket.recv_string()
                    event = self.sub_socket.recv_json()
                    
                    # Dispatcher selon le type d'événement
                    if topic == "SHOOT":
                        #print('client : shoot nb received')
                        self._handle_shoot_event(event)
                        last_heartbeat = time.time()  # Reset heartbeat
        
                    elif topic == "REGISTERED":
                        self._handle_registered_event(event)
                        last_heartbeat = time.time()  # Reset heartbeat
                    elif topic == "HEARTBEAT":
                        last_heartbeat = time.time()
                        # print("💓 Heartbeat received")
                else:
                    # vérifier si serveur toujours vivant
                    time_since_heartbeat = time.time() - last_heartbeat
                    
                    if time_since_heartbeat > self.heartbeat_timeout:
                        print(f"❌ Server timeout ({time_since_heartbeat:.1f}s without response)")
                        self.ClientIsConnected = False
                        # Fermer les sockets
                        if self.sub_socket:
                            self.sub_socket.close()
                        if self.pub_socket:
                            self.pub_socket.close()
                        if self.context:
                            self.context.term()
    
                        time.sleep(1)
                        break

                # Petite pause pour ne pas surcharger le CPU
                time.sleep(0.01)
                if time.time() - self.last_heartbeat > self.heartbeat_interval :
                    self.send_hearbeat()

            except zmq.ZMQError as e:
                if e.errno == zmq.ETERM:
                    break  # Context terminé
                #print(f'ZMQ Error: {e}')
                self.ClientIsConnected = False
                
                break
            except Exception as e:
                #print(f'Error in client loop: {e}')
                import traceback
                traceback.print_exc()
                self.ClientIsConnected = False

                break
        
        # Nettoyage
        self._cleanup()
    
    def _send_register(self):
        """Envoyer notre enregistrement au serveur"""
        register_event = {
            'client_id': self.client_id,
            'name': self.name,
            'timestamp': time.time()
        }
        
        # Publier sur le topic REGISTER
        self.pub_socket.send_string("REGISTER", zmq.SNDMORE)
        self.pub_socket.send_json(register_event)
        
       # print(f"Sent registration for {self.name}")
    
    def _handle_registered_event(self, event):
        """Gérer la confirmation d'enregistrement"""
        client_id = event.get('client_id')
        if client_id == self.client_id:
            print(f"Registration confirmed by server")
            # Optionnel: traiter la config initiale si le serveur l'envoie
            
    
    def _handle_shoot_event(self, event):
        """
        Gérer un événement de tir reçu
    
        """
        nbshot = event.get('number')
        timestamp = event.get('timestamp') # pour aline si besoin
        print('clien shoot receveid,nbshot', nbshot)
        # Émettre le signal si le numéro a changé
        # if int(self.parent.tirNumberBox.value()) != nbshot:
        #     self.newShotnumber.emit(nbshot)
        
    
    def _handle_config_event(self, event):
        """
        Gérer un événement de mise à jour de configuration
        Permet au serveur de pousser des changements de config en temps réel
        """
        # Vérifier si c'est pour nous
        client_id = event.get('client_id')
        if client_id and client_id != self.client_id:
            return  # Pas pour nous
        
    
    def _cleanup(self):
        """Nettoyer les ressources"""
        try:
            # Envoyer un événement de déconnexion
            unregister_event = {
                'client_id': self.client_id,
                'name': self.name
            }
            self.pub_socket.send_string("UNREGISTER", zmq.SNDMORE)
            self.pub_socket.send_json(unregister_event)
        except:
            pass
        
        # Fermer les sockets
        if self.sub_socket:
            self.sub_socket.close()
        if self.pub_socket:
            self.pub_socket.close()
        if self.context:
            self.context.term()
    
    def send_hearbeat(self):
        """fct pouur envoyer heartbeat au serveur """

        self.pub_socket.send_string("CLIENT_HEARTBEAT",zmq.SNDMORE)
        self.pub_socket.send_json({
            'client_id':self.client_id,
            'timestamp':time.time()
        })
        self.last_heartbeat = time.time()

    def stopClientThread(self):
        """Arrêter le thread client"""
        self.ClientIsConnected = False
        time.sleep(0.1)
        self.quit()
        self.wait()


if __name__ == "__main__":
    appli = QApplication(sys.argv)
    
    e = THREADCLIENT()
    e.start()
    appli.exec() 
