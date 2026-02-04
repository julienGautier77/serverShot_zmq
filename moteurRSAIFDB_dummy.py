#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 01 January 2026
@author: Julien Gautier (LOA)
last modified 01 January 2026

Dummy class Dialog to RSAI motors rack via firebird database
Modified to support 2 racks with 14 motors each

"""

import time
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox, QApplication
import socket
from PyQt6.QtCore import QUuid, QMutex
import sys

IPSoft = socket.gethostbyname(socket.gethostname())
UUIDSoftware = QUuid.createUuid()
UUIDSoftware = str(UUIDSoftware.toString()).replace("{","")
UUIDSoftware = UUIDSoftware.replace("}","")

mut = QMutex()

class DummyCursor:
    """Dummy cursor for Firebird database"""
    def execute(self, query):
        pass
    
    def fetchone(self):
        return None
    
    def fetchall(self):
        return []


class DummyConnection:
    """Dummy connection for Firebird database"""
    def cursor(self):
        return DummyCursor()
    
    def commit(self):
        pass
    
    def close(self):
        pass


class FirebirdConnect():
    """Dummy class to simulate a connexion to a firebird data base"""
    con = DummyConnection()

    def __init__(self):
        # Dict for table values
        self.listParaStr = {'nomAxe': 2,'nomEquip': 10, 'nomRef1': 1201, 'nomRef2':1202, 'nomRef3':1203, 'nomRef4':1204, 'nomRef5':1205, 'nomRef6':1206, 'nomRef7':1207, 'nomRef8':1208, 'nomRef9':1209, 'nomRef10':1210}
        self.listParaReal = {'Step': 1106, 'Ref1Val': 1211, 'Ref2Val': 1212, 'Ref3Val':1213, 'Ref4Val':1214, 'Ref5Val':1215, 'Ref6Val':1216, 'Ref7Val':1217, 'Ref8Val':1218, 'Ref9Val':1219, 'Ref10Val':1220}
        self.listParaInt = {'ButLogPlus': 1009, 'ButLogNeg': 1010}
        self.mut = QMutex()
        
        # Définition des noms de moteurs pour le Rack 1
        self.listNameMotorRack1 = [
            'X_Translation', 'Y_Translation', 'Z_Translation', 
            'Theta_Rotation', 'Phi_Tilt', 'Focus_Lens',
            'Filter_Wheel', 'Polarizer', 'Analyzer',
            'Beam_Splitter', 'Slit_Width', 'Slit_Height',
            'Delay_Line', 'Sample_Stage'
        ]
        
        # Définition des noms de moteurs pour le Rack 2
        self.listNameMotorRack2 = [
            'Mirror_X', 'Mirror_Y', 'Grating_Angle',
            'Detector_Pos', 'Iris_Diameter', 'Pinhole_Z',
            'Attenuator', 'Shutter_Pos', 'Camera_Focus',
            'Lens_Position', 'Prism_Angle', 'Wedge_Pos',
            'Compensator', 'Reference_Arm'
        ]
        
        # Mapping des noms vers les listes correspondantes
        self.rack_motor_names = {
            '10.0.0.0': self.listNameMotorRack1,
            '10.0.0.1': self.listNameMotorRack2
        }
        
        # Adresses IP des deux racks
        self.rack_addresses = {
            '10.0.0.0': 'Rack_Optique_1',
            '10.0.0.1': 'Rack_Detection_2'
        }
        
        # Données des moteurs organisées par rack
        self.motor_data = {}
        
        # Initialisation Rack 1 (10.0.0.0)
        self.motor_data['10.0.0.0'] = {}
        for i in range(1, 15):
            self.motor_data['10.0.0.0'][i] = {
                'name': self.listNameMotorRack1[i-1],
                'position': 0,
                'step': 1.0,
                'butPlus': 5000,
                'butMoins': -6000,
                'refNames': [f'Ref{j}_{self.listNameMotorRack1[i-1]}' for j in range(1, 7)],
                'refValues': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                'status': 0x0080,  # status 'ok'
                'is_moving': False
            }
        
        # Initialisation Rack 2 (10.0.0.1)
        self.motor_data['10.0.0.1'] = {}
        for i in range(1, 15):
            self.motor_data['10.0.0.1'][i] = {
                'name': self.listNameMotorRack2[i-1],
                'position': 0,
                'step': 1.0,
                'butPlus': 5000,
                'butMoins': -6000,
                'refNames': [f'Ref{j}_{self.listNameMotorRack2[i-1]}' for j in range(1, 7)],
                'refValues': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                'status': 0x0080,  # status 'ok'
                'is_moving': False
            }

    def closeConnection(self):
        print('Closing connection to database')

    def rEquipmentList(self):
        '''
        Read the list of Equipment connected to database
        Returns list of IP addresses
        '''
        return list(self.rack_addresses.keys())

    def nameMoteur(self, IpAdress, NoMotor):
        '''
        Get motor name from IP address and motor number
        '''
        if IpAdress in self.motor_data and NoMotor in self.motor_data[IpAdress]:
            return self.motor_data[IpAdress][NoMotor]['name']
        return 'Unknown'

    def setNameMoteur(self, IpAdress, NoMotor, nom):
        if IpAdress in self.motor_data and NoMotor in self.motor_data[IpAdress]:
            self.motor_data[IpAdress][NoMotor]['name'] = nom

    def setNameRef(self, IpAdress, NoMotor, nRef, name):
        if IpAdress in self.motor_data and NoMotor in self.motor_data[IpAdress]:
            self.motor_data[IpAdress][NoMotor]['refNames'][nRef - 1] = name

    def setPosRef(self, IpAdress, NoMotor, nRef, pos):
        if IpAdress in self.motor_data and NoMotor in self.motor_data[IpAdress]:
            self.motor_data[IpAdress][NoMotor]['refValues'][nRef - 1] = pos

    def listMotorName(self, IpAdress):
        '''List of motors on equipment at IpAdress
        Returns the list of motor names, properly formatted for server compatibility
        '''
        if IpAdress in self.motor_data:
            # Retourner les noms en remplaçant les caractères spéciaux
            motor_names = [self.motor_data[IpAdress][i]['name'] for i in range(1, 15)]
            # Nettoyer les noms comme le fait le serveur
            motor_names = [name.replace(' ', '_') for name in motor_names]
            motor_names = [name.replace('°', '_') for name in motor_names]
            motor_names = [name.replace('Â', '_') for name in motor_names]
            return motor_names
        return []
    
    def getMotorNames(self, IpAdress):
        '''Get the predefined motor names for a rack (for compatibility)'''
        return self.rack_motor_names.get(IpAdress, [])

    def nameEquipment(self, IpAdress):
        '''Return the equipment name defined by IpAdress'''
        return self.rack_addresses.get(IpAdress, 'Unknown_Rack')

    def rEquipmentStatus(self, IpAddress):
        '''Read the status of an equipment from its IP Address'''
        if IpAddress in self.rack_addresses:
            return f'Status_{self.rack_addresses[IpAddress]}_OK'
        return 'Unknown_Status'
    
    def rEquipmentIdNbr(self, IpAddress):
        """Return equipment ID number"""
        if IpAddress == '10.0.0.0':
            return 1
        elif IpAddress == '10.0.0.1':
            return 2
        return 0
    
    def getSlotNumber(self, motor_num):
        """Get slot number for a motor"""
        return (motor_num - 1) // 4 + 1  # Simule 4 moteurs par slot
    
    def getAxisNumber(self, motor_num):
        """Get axis number for a motor"""
        return (motor_num - 1) % 4 + 1  # Axe 1-4 dans chaque slot
    
    def readPkModBim2BOC(self, cursor, id_equipt, no_mod, no_axis, FlgReadWrite=1):
        """Read primary key from database (dummy)"""
        return id_equipt * 1000 + no_mod * 10 + no_axis
    
    def getValueWhere1ConditionAND(self, cursor, table, column, condition, value):
        """Get value from database (dummy)"""
        # Retourner une position fictive
        return 100.0 + float(value) * 0.1
    
    def rStepperParameter(self, cursor, pk_id, no_motor, param):
        """Read stepper parameter"""
        if param == 1106:  # Step value
            return 1.0
        elif param == 2:  # Motor name
            # Déterminer le rack et le moteur à partir du pk_id
            equipt_id = pk_id // 1000
            if equipt_id == 1:
                ip = '10.0.0.0'
            elif equipt_id == 2:
                ip = '10.0.0.1'
            else:
                return 'Unknown'
            
            if ip in self.motor_data and no_motor in self.motor_data[ip]:
                return self.motor_data[ip][no_motor]['name']
        return None


class MOTORRSAI():
    """
    dummy MOTORRSAI(IpAdrress, NoMotor) 
    Class defined by IP address of the rack and axis number
    """

    def __init__(self, IpAdrress, NoMotor, db: FirebirdConnect, parent=None):
        self.IpAdress = IpAdrress
        self.NoMotor = NoMotor
        self.db = db
        
        print(f"Initializing motor {NoMotor} on rack {IpAdrress}")

        if IpAdrress not in self.db.motor_data or NoMotor not in self.db.motor_data[IpAdrress]:
            raise ValueError(f"Invalid IP address {IpAdrress} or motor number {NoMotor}")
        
        self._name = self.db.motor_data[IpAdrress][NoMotor]['name']
        self.update()

    def update(self):
        """Update motor parameters"""
        self.name = self.getName()
        self.step = self.getStepValue()
        self.butPlus = self.getButLogPlusValue()
        self.butMoins = self.getButLogMoinsValue()
        
        self.refName = []
        for i in range(1, 7):
            r = self.getRefName(i)
            self.refName.append(r)
        
        self.refValue = []
        for i in range(1, 7):
            if self.step == 0:
                self.step = 1
            rr = self.getRefValue(i)
            self.refValue.append(rr)

    def position(self):
        """Return motor position"""
        return self.db.motor_data[self.IpAdress][self.NoMotor]['position']
    
    def getName(self):
        """Get motor name"""
        self._name = self.db.motor_data[self.IpAdress][self.NoMotor]['name']
        return self._name
    
    def setName(self, nom):
        """Set motor name"""
        self.db.motor_data[self.IpAdress][self.NoMotor]['name'] = nom
        self._name = nom
        time.sleep(0.05)

    def getRefName(self, nRef):
        """Get reference name"""
        return self.db.motor_data[self.IpAdress][self.NoMotor]['refNames'][nRef - 1]
    
    def setRefName(self, nRef, name):
        """Set reference name"""
        self.db.motor_data[self.IpAdress][self.NoMotor]['refNames'][nRef - 1] = name
    
    def getRefValue(self, nRef):
        """Get reference position value"""
        return self.db.motor_data[self.IpAdress][self.NoMotor]['refValues'][nRef - 1]
    
    def setRefValue(self, nRef, value):
        """Set reference position value"""
        self.db.motor_data[self.IpAdress][self.NoMotor]['refValues'][nRef - 1] = value

    def getStepValue(self):
        """Get step value in units"""
        return self.db.motor_data[self.IpAdress][self.NoMotor]['step']

    def getButLogPlusValue(self):
        """Get logical button plus value"""
        return self.db.motor_data[self.IpAdress][self.NoMotor]['butPlus']
    
    def setButLogPlusValue(self, butPlus):
        """Set logical button plus value"""
        self.db.motor_data[self.IpAdress][self.NoMotor]['butPlus'] = butPlus

    def getButLogMoinsValue(self):
        """Get logical button minus value"""
        return self.db.motor_data[self.IpAdress][self.NoMotor]['butMoins']
    
    def setButLogMoinsValue(self, butMoins):
        """Set logical button minus value"""
        self.db.motor_data[self.IpAdress][self.NoMotor]['butMoins'] = butMoins

    def rmove(self, posrelatif, vitesse=1000):
        """
        Relative move of motor
        posrelatif = position to move in steps
        """
        posrelatif = int(posrelatif)
        print(f'{self._name} (Rack {self.IpAdress}) relative move of {posrelatif} steps')
        self.db.motor_data[self.IpAdress][self.NoMotor]['position'] += posrelatif
        self.db.motor_data[self.IpAdress][self.NoMotor]['is_moving'] = True

        # Simulate movement
        time.sleep(0.1)
        self.db.motor_data[self.IpAdress][self.NoMotor]['is_moving'] = False

    def move(self, pos, vitesse=1000):
        """
        Absolute move of motor
        pos = position to move in steps
        """
        print(f'{self._name} (Rack {self.IpAdress}) absolute move to {pos} steps')
        self.db.motor_data[self.IpAdress][self.NoMotor]['position'] = pos
        self.db.motor_data[self.IpAdress][self.NoMotor]['is_moving'] = True 
        # Simulate movement
        time.sleep(0.1)
        self.db.motor_data[self.IpAdress][self.NoMotor]['is_moving'] = False

    def setzero(self):
        """Set Zero"""
        self.db.motor_data[self.IpAdress][self.NoMotor]['position'] = 0
        print(f'{self._name} (Rack {self.IpAdress}) set to zero')

    def stopMotor(self):
        """Stop the motor"""
        self.db.motor_data[self.IpAdress][self.NoMotor]['is_moving'] = False
        print(f'{self._name} (Rack {self.IpAdress}) stopped')

    def etatMotor(self):
        """Read status of the motor"""
        status = self.db.motor_data[self.IpAdress][self.NoMotor]['status']
        is_moving = self.db.motor_data[self.IpAdress][self.NoMotor]['is_moving']
        
        if is_moving:
            return 'mvt'
        elif (status & 0x0800) != 0:
            return 'Poweroff'
        elif (status & 0x0200) != 0:
            return 'Phasedebranche'
        elif (status & 0x0400) != 0:
            return 'courtcircuit'
        elif (status & 0x0001) != 0:
            return 'FDD+'
        elif (status & 0x0002) != 0:
            return 'FDC-'
        elif (status & 0x0004) != 0:
            return 'Log+'
        elif (status & 0x0008) != 0:
            return 'Log-'
        elif (status & 0x0020) != 0:
            return 'mvt'
        elif (status & 0x0080) != 0:
            return 'ok'
        elif (status & 0x8000) != 0:
            return 'etatCameOrigin'
        else:
            return '?'

    def getEquipementName(self):
        """Return the name of the equipment"""
        return self.db.nameEquipment(self.IpAdress)


if __name__ == '__main__':
    # Test avec les deux racks
    db = FirebirdConnect()
    
    print("=== Liste des équipements ===")
    equipments = db.rEquipmentList()
    print(f"Equipements disponibles: {equipments}")
    
    print("\n=== Rack 1 (10.0.0.0) ===")
    print(f"Nom: {db.nameEquipment('10.0.0.0')}")
    motors_rack1 = db.listMotorName('10.0.0.0')
    print(f"Moteurs Rack 1:")
    for i, name in enumerate(motors_rack1, 1):
        print(f"  Moteur {i}: {name}")
    
    print("\n=== Rack 2 (10.0.0.1) ===")
    print(f"Nom: {db.nameEquipment('10.0.0.1')}")
    motors_rack2 = db.listMotorName('10.0.0.1')
    print(f"Moteurs Rack 2:")
    for i, name in enumerate(motors_rack2, 1):
        print(f"  Moteur {i}: {name}")
    
    # Test de mouvement sur un moteur de chaque rack
    print("\n=== Test de mouvement ===")
    motor1 = MOTORRSAI('10.0.0.0', 1, db)
    print(f"Position initiale {motor1.getName()}: {motor1.position()}")
    motor1.move(1000)
    print(f"Nouvelle position {motor1.getName()}: {motor1.position()}")
    
    motor2 = MOTORRSAI('10.0.0.1', 1, db)
    print(f"Position initiale {motor2.getName()}: {motor2.position()}")
    motor2.rmove(500)
    print(f"Nouvelle position {motor2.getName()}: {motor2.position()}")
    
    print("\n=== Génération du fichier de configuration pour le serveur ===")
    # Cette partie simule ce que fait le serveur dans initFromRSAIDB()
    from PyQt6 import QtCore
    conf = QtCore.QSettings('confMoteurRSAIServer.ini', QtCore.QSettings.Format.IniFormat)
    
    for rack_idx, ip in enumerate(equipments):
        listMotor = db.listMotorName(ip)
        rackName = db.nameEquipment(ip)
        
        for motor_idx, motor_name in enumerate(listMotor):
            name = f"{rackName}M{motor_idx + 1}"  # Format: Rack_Optique_1M1, etc.
            
            # Créer une instance pour récupérer les paramètres
            motor = MOTORRSAI(ip, motor_idx + 1, db)
            
            conf.setValue(name + "/nom", motor_name)
            conf.setValue(name + "/nomRack", rackName)
            conf.setValue(name + "/IPRack", ip)
            conf.setValue(name + "/numESim", rack_idx)
            conf.setValue(name + "/numMoteur", motor_idx + 1)
            conf.setValue(name + "/stepmotor", 1 / float(motor.step))
            conf.setValue(name + "/buteePos", motor.butPlus)
            conf.setValue(name + "/buteeNeg", motor.butMoins)
            conf.setValue(name + "/moteurType", "RSAI")
            
            for ref_idx in range(6):
                conf.setValue(name + f"/ref{ref_idx}Name", motor.refName[ref_idx])
                conf.setValue(name + f"/ref{ref_idx}Pos", motor.refValue[ref_idx])
            
            print(f"  ✓ Configuré: {name} ({motor_name})")
    
    print(f"\n✅ Fichier de configuration généré: confMoteurRSAIServer.ini")
    print("⚠️  IMPORTANT: Utilisez ce fichier avec votre serveur ZMQ")
    
    db.closeConnection()
