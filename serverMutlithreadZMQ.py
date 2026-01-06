# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 15:23:22 2022

@author: LOA
Server To send shot number
read the Ni card and add +1 each time receive  a trig signal 

"""
#pip install  firebird-driver
# pip install zmq
from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtWidgets import QApplication, QLineEdit, QFileDialog, QSpacerItem, QSizePolicy
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QSpinBox, QCheckBox
import pathlib
import socket as _socket
import h5py
import time
import sys
import os
import qdarkstyle
import nidaqmx #  https://github.com/ni/nidaqmx-python
import moteurRSAIFDB
import uuid
import zmq


class SERVERGUI(QWidget):
    """
    User interface for shooting class : 
    
    """
    
    def __init__(self, parent=None):
        super(SERVERGUI, self).__init__(parent)
        
        self.p = pathlib.Path(__file__)
        self.sepa = os.sep
        pathini = str(self.p.parent) + self.sepa + 'configTir.ini'
        self.confTir = QtCore.QSettings(pathini, QtCore.QSettings.Format.IniFormat) 
        self.pub_port = int(self.confTir.value('TIR'+"/pub_port")) # Pour publier les événements
        self.sub_port = int(self.confTir.value('TIR'+"/sub_port"))  # pour ecouter les clients
        self.rep_port = int(self.confTir.value('TIR'+"/rep_port"))  # pour reponde au request des clients
        self.tcpip_port = int(self.confTir.value('TIR'+"/tcpip_port")) # pour dialoguer en TCPIP (labview)
        self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
        
        hostname = _socket.gethostname()
        self.IPAddr = _socket.gethostbyname(hostname)
        
        #  connection base de données RSAI
        self.cursor = moteurRSAIFDB.con.cursor()
        self.listRack = moteurRSAIFDB.rEquipmentList()
        self.rackName = []
        for IP in self.listRack:
            self.rackName.append(moteurRSAIFDB.nameEquipment(IP))
        self.listMotor = []
        for IPadress in self.listRack:
            self.listMotor.append(moteurRSAIFDB.listMotorName(IPadress))
            print(IPadress)
        

        self.setup()
        self.actionButton()
        self.setWindowTitle('Shot number Server ')
        self.icon = str(self.p.parent) + self.sepa + 'icons' + self.sepa
        self.setWindowIcon(QIcon(self.icon + 'LOA.png'))
        
        # start server ZMQ
        self.ser = ZMQSERVER(self)
        self.ser.start()

        # serveur start TCP/IP
        self.serTCP = TCPIPServer(parent=self)
        self.serTCP.start()
        self.serTCP.signalServerTCPIPThread.connect(self.UpdateListClientTCPIP)

        # start daq from NI ( to collect trigger) 
        self.daq = NIDAQ(self)
        self.daq.TRIGSHOOT.connect(self.ChangeTrig)
        self.daq.setZero()
        self.daq.start()

        foldername = time.strftime("%Y_%m_%d")  # Save in a new folder with the time as namefile
        filename = 'SauvegardeMot' + time.strftime("%Y_%m_%d")
        print('Backup motor position file created : ', foldername)

        pathAutoSave = str(self.p.parent)+self.sepa+'SauvPosition'
        
        folder = pathAutoSave + self. sepa + foldername
        # print("folder '%s' " %folder)
        if not os.path.isdir(folder):
            os.mkdir(folder)
        self.fichier = folder + self.sepa + filename + '.txt'

    def setup(self):
        
        vbox1 = QVBoxLayout()
        hbox1 = QHBoxLayout()
        label = QLabel('Shoot server ')
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hbox1.addWidget(label)
        vbox1.addLayout(hbox1)

        self.pathBoxMain = QLineEdit(self.confTir.value('TIR'+"/pathMain"))
        self.buttonPathMain = QPushButton('Path : ')
        hbox = QHBoxLayout()
        hbox.addWidget(self.buttonPathMain)
        hbox.addWidget(self.pathBoxMain)
        vbox1.addLayout(hbox)

        hbox0 = QHBoxLayout()
        labelIP = QLabel()
        labelIP.setText('IP:'+self.IPAddr)
        labelPort = QLabel(f"Port PUB : {self.pub_port}   Port SUB : {self.sub_port}   Port REQ : {self.rep_port}   Port TCPIP : {self.tcpip_port}")
        hbox0.addWidget(labelIP)
        hbox0.addWidget(labelPort)
        vbox1.addLayout(hbox0)
        hbox2 = QHBoxLayout()
        labelNbShoot = QLabel('Actual Shot Number : ')
        labelNbShoot.setStyleSheet('color : red;')
        labelNbShoot.setFont(QFont("Arial", 24))
        self.nbShoot = QSpinBox()
        self.nbShoot.setFont(QFont("Arial", 26))
        self.nbShoot.setStyleSheet('color : red;')
        self.nbShoot.setMaximum(100000)
        self.nbShoot.setValue(int(self.confTir.value('TIR'+"/shootNumber")))
        # self.nbShoot.editingFinished.connect(self.nbShootEdit)
        self.nbShoot.valueChanged.connect(self.nbShootEdit)
        hbox2.addWidget(labelNbShoot)
        hbox2.addWidget(self.nbShoot)  
        vbox1.addLayout(hbox2)
        hbox_tcpip = QHBoxLayout()
        Qlabel_listClientTitle = QLabel('Client list TCPIP connected : ')
        hbox_tcpip.addWidget(Qlabel_listClientTitle)
        self.Qlabel_listClient = QLabel()
        hbox_tcpip.addWidget(self.Qlabel_listClient)
        vbox1.addLayout(hbox_tcpip)

        hbox3 = QHBoxLayout()
        
        vbox1.addLayout(hbox3)
        self.old_value = self.nbShoot.value()
        self.nbShootTri = self.nbShoot.value() - 1 
        # sav moteurs
        self.vbox = QVBoxLayout()
        hboxRack = QVBoxLayout()
        LabelRack = QLabel('     Rack NAME to save : ')
        hboxRack.addWidget(LabelRack)
        self.box = []
        i = 0 
        for name in self.rackName: # create QCheckbox for each rack
            self.box.append(checkBox(name=str(name), ip=self.listRack[i], parent=self))
            hboxRack.addWidget(self.box[i])
            i+=1

        self.vbox.addLayout(hboxRack)
        self.vCamBox = QVBoxLayout()
        HCamlayoutLabel = QHBoxLayout()
        labelcam = QLabel(' Camera connected :')
        labelcam.setStyleSheet('color : green;')
        HCamlayoutLabel.addWidget(labelcam)
        self.autoSave = QCheckBox('autoSave')
        HCamlayoutLabel.addWidget(self.autoSave)
        self.vCamBox.addLayout(HCamlayoutLabel)
        spacer0 = QSpacerItem(20, 50, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        vbox1.addSpacerItem(spacer0)
        widgetCam = QWidget()
        widgetCam.setLayout(self.vCamBox)
        rgbcolor_gray = 'rgb(0,48,57)'
        widgetCam.setStyleSheet("background-color:%s" % rgbcolor_gray)
        vbox1.addWidget(widgetCam)
        self.butt = QPushButton('Test Trig')
        self.vbox.addWidget(self.butt)
        spacer = QSpacerItem(20, 50, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        vbox1.addSpacerItem(spacer)
        vbox1.addLayout(self.vbox)
        self.setLayout(vbox1)
       
    def actionButton(self):
        # for b in self.box:
        #     b.stateChanged.connect(self.clik)

        self.butt.clicked.connect(self.Action)
        self.buttonPathMain.clicked.connect(self.PathButtonChanged)
        self.pathBoxMain.editingFinished.connect(self.pathBoxChanged)
        self.nbShoot.valueChanged.connect(self.nbShootChanged)
        self.autoSave.stateChanged.connect(self.autoSaveButtonChanged)

    def allPosition(self, IpAdress):
        listPosi = []
        listNameMotor = []
        IdEquipt = moteurRSAIFDB.rEquipmentIdNbr(IpAdress)
        for NoMotor in range(1, 15):
            NoMod = moteurRSAIFDB.getSlotNumber(NoMotor)
            NoAxis = moteurRSAIFDB.getAxisNumber(NoMotor)
            PkIdTbBoc = moteurRSAIFDB.readPkModBim2BOC(self.cursor, IdEquipt, NoMod, NoAxis, FlgReadWrite=1)
            pos = moteurRSAIFDB.getValueWhere1ConditionAND(self.cursor, "TbBim2BOC_1Axis_R", "PosAxis", "PkId", str(PkIdTbBoc))
            step = moteurRSAIFDB.rStepperParameter(self.cursor, PkIdTbBoc, NoMotor, 1106)
            listPosi.append(pos*step)
            name = moteurRSAIFDB.rStepperParameter(self.cursor, PkIdTbBoc, NoMotor, 2)
            listNameMotor.append(name)
            # print('list posi',listPosi)
        return listPosi, listNameMotor
    
    def clik(self):
        print('click')
        sender = QtCore.QObject.sender(self)
        print(str(sender.objectName()))
    
    def Action(self):
        self.nbShoot.setValue(int(self.old_value+1))  # le tri a eu lieu  on +1 le tir
        self.savePostionMotor()

    def ChangeTrig(self, trigShot):

        print('receive new trig')
        # self.NIShoot.setValue(trigShot)
        self.old_value = self.nbShoot.value()  # self.old_value numero du tir en cours
        # on envoi a la camera old_value c'est a dire le tir en cour (le trig arrive 100ms avant le tir et la camera prend du tps a lire)
        self.nbShoot.setValue(int(self.old_value+1))  # le tri a eu lieu  on +1 le tir 
        self.nbShootTrig = self.nbShootTri + 1
        self.confTir.setValue('TIR'+"/shootNumber", int(self.old_value+1))
        self.savePostionMotor()

    def savePostionMotor(self):   # save motor postion 
        foldernameMot = time.strftime("%Y_%m_%d")  # Save in a new folder with the time as namefile
        pathMain = self.pathBoxMain.text()
        folderMot = pathMain + '/' + foldernameMot
        print("folder '%s' " % folderMot)
        if not os.path.isdir(folderMot):
            os.mkdir(folderMot)
        filenameMot = 'MotorsPosition_' + time.strftime("%Y_%m_%d")
        self.fichier = folderMot + self.sepa + filenameMot + '.txt'
        self.file = open(self.fichier, "a")
        date = time.strftime("%Y/%m/%d @ %H:%M:%S")
        self.file.write('Shoot number : '+str(self.old_value) + ' done the ' + date + "\n")
        self.file.write("Position Motors :" + "\n")
        # creer npm fichier hdf5
        filenameMot = 'MotorsPosition_' + time.strftime("%Y_%m_%d")
        fichierHDF5 = folderMot + self.sepa + filenameMot + '.hdf5'
    
        # Ouvrir/créer le fichier HDF5
        with h5py.File(fichierHDF5, 'a') as hdf_file:
            # Créer un groupe pour ce tir avec timestamp
            timestamp = time.strftime("%Y/%m/%d @ %H:%M:%S")
            group_name = f"Shoot_{self.old_value}_{time.strftime('%H%M%S')}"
            shoot_group = hdf_file.create_group(group_name)
            
            # Sauvegarder les métadonnées
            shoot_group.attrs['shoot_number'] = int(self.old_value)
            shoot_group.attrs['timestamp'] = timestamp
            shoot_group.attrs['date'] = time.strftime("%Y/%m/%d @ %H:%M:%S")
            
            # Sauvegarder les positions des moteurs hdf5 
            for b in self.box:
                if b.isChecked():
                    listPosi, listNameMotor = self.allPosition(b.ip)
                    
                    # Créer un sous-groupe pour ce rack
                    rack_name = moteurRSAIFDB.nameEquipment(b.ip)
                    rack_group = shoot_group.create_group(f"Rack_{rack_name}")
                    rack_group.attrs['ip'] = b.ip
                    
                    # Sauvegarder chaque moteur
                    for i, (mot, pos) in enumerate(zip(listNameMotor, listPosi)):
                        motor_dataset = rack_group.create_dataset(
                            f"motor_{i}_{mot}", 
                            data=pos
                        )
                        motor_dataset.attrs['name'] = mot
                        motor_dataset.attrs['position'] = pos

        for b in self.box:
            if b.isChecked():
                listPosi, listNameMotor = self.allPosition(b.ip)
                i = 0
                self.file.write('Rack: ' + moteurRSAIFDB.nameEquipment(b.ip) + "  " + str(b.ip)+ "\n" )
                for mot in listNameMotor:
                    self.file.write(str(mot) + ' : ' + str(listPosi[i]) + "\n")
                    i = i+1

            self.file.write(' ' + "\n") 
        self.file.write('' + "\n")      
        self.file.close()
        
    def PathButtonChanged(self):
        self.pathMain = str(QFileDialog.getExistingDirectory())
        self.pathBoxMain.setText(self.pathMain)
        self.confTir.setValue('TIR' + '/pathMain', self.pathMain)
        self.ser.update_all_client_paths(base_path=self.pathMain)

    def nbShootChanged(self):
        print('nex shoot')
        self.ser.publish_shoot_event(self.old_value)

    def pathBoxChanged(self):
        print(self.pathMain.text())
        self.confTir.setValue('TIR'+'/pathMain', self.pathMain)
        self.ser.update_all_client_paths(base_path=self.pathMain)

    def nbShootEdit(self):
        self.old_value = self.nbShoot.value()
        self.confTir.setValue('TIR'+"/shootNumber",int(self.old_value+1))
        self.nbShootTri = self.nbShoot.value() - 1

    def autoSaveButtonChanged(self):
        self.ser.update_all_client_autosave(autosave=self.autoSave.isChecked())

    # def shootAct(self):
    #     print('shoot')
    #     self.ChangeTrig(1)

    def UpdateListClientTCPIP(self, clientlist):
        print('update client list TCPIP', clientlist)
        print('number of client TCPIP connected : ', len(clientlist))
        # Convertir le dict en string lisible
        if len(clientlist) == 0:
            text = "Aucun client connecté"
        else:
            text = f"Clients connectés ({len(clientlist)}):\n"
            for client_id, address in clientlist.items():
                # Afficher seulement l'adresse IP et le port
                text += f"  • {address[0]}:{address[1]}\n"
        
        self.Qlabel_listClient.setText(text)

    def closeEvent(self, event):
        """ when closing the window
        """
        self.ser.stopThread()
        moteurRSAIFDB.closeConnection()
        self.daq.stopThread()
        self.serTCP.stopThread()
        time.sleep(2)
        event.accept()


class ZMQSERVER(QtCore.QThread):
    '''
    Serveur ZMQ 100% événementiel
    - PUB socket (5009): Publie SHOOT, CONFIG, REGISTERED
    - SUB socket (5010): Écoute REGISTER, UNREGISTER des clients
    '''
    
    def __init__(self, parent=None):
        super(ZMQSERVER, self).__init__(parent)
        self.parent = parent
        self.pub_port = self.parent.pub_port  # Pour publier les événements
        self.sub_port = self.parent.sub_port  # Pour écouter les clients
        self.rep_port = self.parent.rep_port  # Pour répondre aux requêtes des clients
        
        self.client_widget = {}
        self.isRunning = True
        
        # Heartbeat settings : on envoie au client un heartbeat 
        self.heartbeat_interval = 5.0  # Envoyer heartbeat toutes les 5 secondes
        self.last_heartbeat = time.time()

        # Suivi heratbeats clients
        self.client_last_seen={}
        self.client_timeout = 30

        # Create ZMQ context
        self.context = zmq.Context()
        
        # PUB socket pour publier les événements
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.bind(f"tcp://*:{self.pub_port}")
        
        # SUB socket pour écouter les clients
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.bind(f"tcp://*:{self.sub_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "REGISTER")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "UNREGISTER")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE,"CLIENT_HEARTBEAT")
        
        print(f'ZMQ PUB server ready on port {self.pub_port}')
        print(f'ZMQ SUB server ready on port {self.sub_port}')
        # REP socket pour répondre aux requêtes
        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(f"tcp://*:{self.rep_port}")

    def run(self):
        """Boucle principale - Écouter les enregistrements clients"""
        print('Start listening (ZMQ)')
        
        poller = zmq.Poller()
        poller.register(self.sub_socket, zmq.POLLIN)
        poller.register(self.rep_socket, zmq.POLLIN)
        try:
            while self.isRunning:
                time.sleep(0.01)
                socks = dict(poller.poll(1000))  # 1 second timeout
                
                if self.sub_socket in socks and socks[self.sub_socket] == zmq.POLLIN:
                    try:
                        # Recevoir l'événement client
                        topic = self.sub_socket.recv_string()
                        event = self.sub_socket.recv_json()
                        
                        if topic == "REGISTER":
                            self._handle_client_register(event)
                        elif topic == "UNREGISTER":
                            self._handle_client_unregister(event)
                        elif topic == "CLIENT_HEARTBEAT":
                            self._handel_client_heartbeat(event)
                        
                    except Exception as e:
                        print(f'Error processing client event: {e}')
                        import traceback
                        traceback.print_exc()
                
                # Gérer les requêtes REP (GET_SHOOT_NUMBER)
                if self.rep_socket in socks and socks[self.rep_socket] == zmq.POLLIN:
                    print('client  request ')
                    try:
                        request = self.rep_socket.recv_string()
                        print('request : ', request)
                        if request == 'shot:':
                            # Répondre avec le numéro de tir actuel
                            response = {
                                'shoot_number': self.parent.old_value,
                                'timestamp': time.time()
                            }
                            self.rep_socket.send_string(str(self.parent.old_value))
                            print(f"Responded to shot request: # {self.parent.old_value}")
                        else:
                            # Requête inconnue
                            self.rep_socket.send_json({'error': 'Unknown request type'})
                    
                    except Exception as e:
                        print(f'Error processing REP request: {e}')
                        import traceback
                        traceback.print_exc()
                        # Envoyer une réponse d'erreur pour ne pas bloquer le client
                        try:
                            self.rep_socket.send_json({'error': str(e)})
                        except:
                            pass
                now = time.time()
                if now - self.last_heartbeat >= self.heartbeat_interval: # on envoie au client un hearbeat du serveur 
                    # print('Sending HEARTBEAT', now - self.last_heartbeat )
                    self.pub_socket.send_string("HEARTBEAT", zmq.SNDMORE)
                    self.pub_socket.send_json({"timestamp": now})
                    self.last_heartbeat = now
                
                self._check_client_timeouts(now) # verifier client inactifs (beatheart client)

        except Exception as e:
            print(f'Exception in ZMQ server: {e}')
        finally:
            self.sub_socket.close()
            self.pub_socket.close()
            self.context.term()

    def _handel_client_heartbeat(self,event):
        #print('nouveau heat beat du client')
        # enregistrement hearbeat nouveau client"
        client_id = event.get('client_id')
        if client_id:
            self.client_last_seen[client_id] = time.time()

    def _check_client_timeouts(self,curent_time):
        # verifie quels client n'a pas envoyer de heratbeat
        disconnected_clients = []
        client_id = None
        for client_id, last_seen in list(self.client_last_seen.items()):
            if curent_time-last_seen > self.client_timeout:
                disconnected_clients.append(client_id)
        
                 # supprime les client deconnectés
        
                if client_id:
                    self.client_last_seen.pop(client_id,None)
                    print('client deconnecté',client_id)
                    # supprime l'ui du client
                    label, checkbox, Hcam, pathBox, buttonPath = self.client_widget.pop(client_id)
                    label.deleteLater()
                    checkbox.deleteLater()
                    pathBox.deleteLater()
                    buttonPath.deleteLater() 
                    #self._remove_client_ui(client_id)

            # QtCore.QTimer.singleShot(1000, lambda cid=client_id: self._remove_client_ui(cid))

    def _handle_client_register(self, event):
        """Gérer l'enregistrement d'un nouveau client"""
        client_id = event.get('client_id')
        name_visu = event.get('name', 'Unknown')
        
        print(f'New client registering: {name_visu} ({client_id})')
        self.client_last_seen[client_id] = time.time()
        # Créer l'interface utilisateur
        QtCore.QMetaObject.invokeMethod(
            self,
            '_create_client_ui',
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, client_id),
            QtCore.Q_ARG(str, name_visu)
        )
        
        # Envoyer la confirmation avec la config initiale
        # (petite pause pour que l'UI soit créée)
        time.sleep(0.1)
        self._send_registration_confirmation(client_id)
    
    def _send_registration_confirmation(self, client_id):
        """Envoyer la confirmation d'enregistrement avec config initiale"""
        if client_id in self.client_widget:
            label, checkbox, Hcam, pathBox, buttonPath = self.client_widget[client_id]
            
            confirmation = {
                'client_id': client_id,
                'status': 'ok',
                'path': pathBox.text(),
                'autosave': checkbox.isChecked() and self.parent.autoSave.isChecked()
            }
            
            self.pub_socket.send_string("REGISTERED", zmq.SNDMORE)
            self.pub_socket.send_json(confirmation)
            print(f"Sent registration confirmation to {client_id}")
            self.publish_shoot_event(self.parent.old_value) # maj tir actuel
    
    def _handle_client_unregister(self, event):
        """Gérer la déconnexion d'un client"""
        client_id = event.get('client_id')
        name = event.get('name', 'Unknown')
        
        print(f'Client unregistering: {name} ({client_id})')
        self.client_last_seen.pop(client_id,None)
        if client_id in self.client_widget:
            QtCore.QMetaObject.invokeMethod(
                self,
                '_remove_client_ui',
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, client_id)
            )
    
    @QtCore.pyqtSlot(str, str)
    def _create_client_ui(self, client_id, name_visu):
        """Créer l'interface utilisateur pour le client"""
        
        Hcam = QHBoxLayout()
        label = QLabel(name_visu)
        label.setStyleSheet("background-color : green;")
        
        # Setup folder
        foldername = time.strftime("%Y_%m_%d")
        pathMain = self.parent.pathBoxMain.text()
        # print('client path,', pathMain)
        folder = os.path.join(pathMain, foldername, name_visu)
        os.makedirs(folder, exist_ok=True)
        
        pathBox = QLineEdit(folder)
        buttonPath = QPushButton('Path : ')
        self.pathBox = pathBox
        # Quand le path change, envoyer un événement CONFIG
        buttonPath.clicked.connect(lambda: self.path_changed(buttonPath, pathBox, client_id))
        
        checkbox = QCheckBox('select')
        checkbox.setChecked(True)
        
        # Quand le checkbox change, envoyer un événement CONFIG
        #checkbox.stateChanged.connect(lambda: self._autosave_changed(checkbox, client_id))
        
        self.client_widget[client_id] = (label, checkbox, Hcam, pathBox, buttonPath)
        
        Hcam.addWidget(label)
        Hcam.addWidget(buttonPath)
        Hcam.addWidget(pathBox)
        Hcam.addWidget(checkbox)
        self.parent.vCamBox.addLayout(Hcam)
    
    def path_changed(self, button, pathBox, client_id):
        """Gérer le changement de path dans le widget client"""
        
        pathAutoSave = str(QFileDialog.getExistingDirectory())
        if pathAutoSave:
            pathBox.setText(pathAutoSave)
            
            # Publier l'événement CONFIG pour ce client
            self.publish_config_update(client_id, path=pathAutoSave)

    def update_all_client_paths(self, base_path=None):
        """
        Mettre à jour les paths de tous les clients quand le path principal change
        Cette méthode est appelée depuis SERVERGUI quand pathBoxMain change
        """
        foldername = time.strftime("%Y_%m_%d")
        
        for client_id, widgets in self.client_widget.items():
            label, checkbox, Hcam, pathBox, buttonPath = widgets
            camera_name = label.text()
            
            # Créer le nouveau path pour ce client
            new_path = os.path.join(base_path, foldername, camera_name)
            
            # Créer le dossier s'il n'existe pas
            os.makedirs(new_path, exist_ok=True)
            
            # Mettre à jour l'UI
            pathBox.setText(new_path)
            
            # Publier l'événement CONFIG pour ce client
            self.publish_config_update(client_id, path=new_path)
        
        print(f"Updated all client paths based on: {base_path}")

    def update_all_client_autosave(self, autosave=False):

        """Gérer le changement d'autosave"""
        # print('update all client autosave', autosave)
        for client_id, widgets in self.client_widget.items():
            label, checkbox, Hcam, pathBox, buttonPath = widgets
            if checkbox.isChecked():  # Publier l'événement CONFIG pour ce client
                self.publish_config_update(client_id, autosave=autosave)
    
    @QtCore.pyqtSlot(str)
    def _remove_client_ui(self, client_id):
        """Supprimer l'interface utilisateur du client"""
        
        if client_id in self.client_widget:
            label, checkbox, Hcam, pathBox, buttonPath = self.client_widget.pop(client_id)
            label.deleteLater()
            checkbox.deleteLater()
            pathBox.deleteLater()
            buttonPath.deleteLater()
    
    def publish_shoot_event(self, shoot_number):
        """
        Publier un événement de tir 
        """
        event = {
            'number': shoot_number,
            'timestamp': time.strftime("%Y%m%d_%H%M%S")
        }
        
        # Publier sur le topic SHOOT
        self.pub_socket.send_string("SHOOT", zmq.SNDMORE)
        self.pub_socket.send_json(event)
        
        print(f"📡 Published SHOOT event: #{shoot_number}")
    
    def publish_config_update(self, client_id=None, path=None, autosave=None):
        """
        Publier un événement de mise à jour de configuration (path/autosave)
        Si client_id est None, envoie à tous les clients
        """
        event = {
            'timestamp': time.time()
        }
        
        if client_id:
            event['client_id'] = client_id
        
        if path is not None:
            event['path'] = path
        
        if autosave is not None:
            event['autosave'] = autosave
        
        # Publier sur le topic CONFIG
        self.pub_socket.send_string("CONFIG", zmq.SNDMORE)
        self.pub_socket.send_json(event)
        
        print(f"Published CONFIG update: {event}")
    
    def stopThread(self):
        """Arrêter le serveur"""
        print('Closing ZMQ server')
        self.isRunning = False
        time.sleep(0.5)
        print('ZMQ server stopped')


class NIDAQ(QtCore.QThread) : 
    TRIGSHOOT = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super(NIDAQ, self).__init__(parent)
        self.parent = parent
        self.stop = False
       
    def run(self):
        a = 0
        with nidaqmx.Task() as task:
            task.ci_channels.add_ci_count_edges_chan("Dev1/ctr0", edge=nidaqmx.constants.Edge.FALLING)
            task.start()
            while True:
                if self.stop is True:
                    break
                else:
                    time.sleep(0.01)
                    b = task.read()
                    # print('daq nb',b)
                    if b != a:
                        a = b
                        self.TRIGSHOOT.emit(a)

    def stopThread(self):
        self.stop = True
        time.sleep(0.1)
        self.terminate()

    def setZero(self):
        #   with nidaqmx.Task() as task:
        print('set daq to zero')


class checkBox(QCheckBox):
    # homemade QCheckBox

    def __init__(self, name='test', ip='', parent=None):
        super(checkBox, self).__init__()
        self.parent = parent
        self.ip = ip
        self.name = name
        self.setText(self.name+' ( ' + self.ip + ')')
        self.setObjectName(self.ip)


###### 2 eme serveur en TCPIP pour les clients non ZMQ (ex labview)!

class TCPIPServer(QtCore.QThread):
    '''Server class with multi clients

    '''
    signalServerTCPIPThread = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        
        super(TCPIPServer, self).__init__(parent)
        self.parent = parent
        hostname = _socket.gethostname()
        self.IPAddr = _socket.gethostbyname(hostname)
        self.serverHost = self.IPAddr
        self.serverPort = self.parent.tcpip_port
        print('server TCPIP port', self.serverPort, self.serverHost)
        self.clientList = dict()
        self.client_widget = {}
        self.serversocket = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)      # create socket
        try :
            self.serversocket.bind((self.serverHost, self.serverPort))
            self.isConnected = True
            print('server shot TCPI ready')
        except :
            print('error connection server')
            self.isConnected = False
       
        self.listClient = []
        self.clientsConnectedSocket = []
        self.clients_ids = []

    def run(self):  #run
        print('start lisenning')

        try:
            while self.isConnected:
                print('thread server TCPIP en cours')
                self.serversocket.listen(20)
                client_socket, client_adress = self.serversocket.accept()
                print('new client connected TCPIP from ', client_adress)
                client_thread = CLIENTTHREAD(client_socket,client_adress,parent=self)
                client_thread.signalClientThread_TCPIP.connect(self.signalFromClient)
                self.listClient.append(client_thread)
                client_thread.start()
                
        except Exception as e:
            print('exception server', e)
            # print('error connection')
            
    def signalFromClient(self, sig):
        print('signal recu du client TCPIP', sig)
        client_id = sig[0]
        client_adresse = sig[1]
        nameVisu = sig[2]
        
        if client_adresse == 0:  # Client déconnecté
            if client_id in self.clientList:
                del self.clientList[client_id]
                print(f'Client {client_id} removed from {client_adresse}')
            if client_id in self.client_widget:
                del self.client_widget[client_id]
        else:  # Nouveau client
            self.clientList[client_id] = client_adresse
            print(f'Client {client_id} added from {client_adresse}')
        
        # Émettre la liste mise à jour des clients
        self.signalServerTCPIPThread.emit(self.clientList.copy())
        print(f'Clients connectés: {len(self.clientList)}')

    def stopThread(self):
        self.isConnected = False
        print('clossing server')
        time.sleep(0.1)
        for client in self.listClient:
            client.stopThread()
        self.serversocket.close()
        time.sleep(0.1)                   
        print('stop server')
        time.sleep(0.1)


class CLIENTTHREAD(QtCore.QThread):
    '''client class 
    '''
    signalClientThread_TCPIP = QtCore.pyqtSignal(object)

    def __init__(self, client_socket, client_adresse, parent=None):
        super(CLIENTTHREAD, self).__init__()
        self.client_socket = client_socket
        
        # self.client_socket.settimeout(3)
        self.client_adresse = client_adresse
        self.parent = parent
        self.client_id = str(uuid.uuid4())
        self.stop = False
          
    def run(self):
        print('start new thread client TCPIP')
        # Émettre signal pour ajouter le client
        if self.parent:
            print('emit new client TCPIP')
            self.signalClientThread_TCPIP.emit([self.client_id, self.client_adresse, None])
        try: 
            while True:
                if self.stop is True:
                    break
                try:
                    data = self.client_socket.recv(1024)
                    msgReceived = data.decode()
                    if not msgReceived:
                        # print('pas de message')
                        self.signalClientThread_TCPIP.emit([self.client_id,0,0])
                        break
                    else: 
                            try:
                                msgsplit = msgReceived.split(',')
                                msgsplit = [msg.strip() for msg in msgsplit]
                                # print(msgReceived)
                                if len(msgsplit) == 1 :
                                    msgReceived = msgsplit[0]
                                    if msgReceived == 'numberShoot?':
                        
                                        number = str(self.parent.parent.old_value) # send the shoot nuber not the n+1
                                        # print('server number',number)
                                        self.client_socket.send(number.encode())
        
                                    elif msgReceived == 'idShoot?':
                                        numberId = str(self.parent.parent.old_value)  +"@"+self.parent.date2 # send the shoot nuber not the n+1
                                        self.client_socket.send(numberId.encode())

                            except:
                                print('error')
                                sendmsg = 'error'
                                traceback.print_exc()
                                self.client_socket.sendall(sendmsg.encode())

                except ConnectionResetError:
                    print('deconnection du client')
                    self.client_socket.close()
                    self.signalClientThread_TCPIP.emit([self.client_id,0,0])
                    break

        except Exception as e: 
            print('exception server',e)
            self.client_socket.close()
            self.signalClientThread_TCPIP.emit([self.client_id,0,0])

    def stopThread(self):
        self.stop = True 


if __name__ == '__main__':
    appli = QApplication(sys.argv)
    e = SERVERGUI()
    e.show()
    appli.exec_()