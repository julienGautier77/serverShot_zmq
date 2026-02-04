#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 01 December 2023
@author: Julien Gautier (LOA)
last modified 22 decembre 2023

Dialog to RSAI motors rack via firebird database
We can also move get position ...(not used)
In zmq_server we just use this 2 class to initialize and syncronize with RSAI client software 
After we dialog directly with the rack via the dll
class FirebirdConnect() : Dialog with the database 
class MOTORRSAI(IpAdrress, NoMotor, db: FirebirdConnect) : create a motor class to control mone motor via the database (used to create the ini file for the server )
"""

from firebird.driver import connect  # pip install  firebird-driver
import time
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMessageBox, QApplication
import socket
from PyQt6.QtCore import QUuid, QMutex
import sys
import os

IPSoft = socket.gethostbyname(socket.gethostname())  # get the ip adress of the computer

UUIDSoftware = QUuid.createUuid()  # create unique Id for software
UUIDSoftware = str(UUIDSoftware.toString()).replace("{", "")
UUIDSoftware = UUIDSoftware.replace("}", "")


# if not local  dsn=10.0.1.57/ ??

# connection to data base


class FirebirdConnect():
    """
    Class to connect to the firebird data base the .fDB 
    this data base is also used by RSAI server and client software
    """
    def __init__(self,):
        # " dict for table values"
        self.listParaStr = {'nomAxe': 2, 'nomEquip': 10, 'nomRef1': 1201, 'nomRef2': 1202, 'nomRef3': 1203, 'nomRef4': 1204, 'nomRef5': 1205, 'nomRef6': 1206, 'nomRef7': 1207, 'nomRef8': 1208, 'nomRef9': 1209, 'nomRef10': 1210}
        self.listParaReal = {'Step': 1106, 'Ref1Val': 1211, 'Ref2Val': 1212, 'Ref3Val': 1213, 'Ref4Val': 1214, 'Ref5Val': 1215, 'Ref6Val': 1216, 'Ref7Val': 1217, 'Ref8Val': 1218, 'Ref9Val': 1219, 'Ref10Val': 1220}
        self.listParaInt = {'ButLogPlus': 1009, 'ButLogNeg': 1010}
        self.mut = QMutex()

    def ConnectToDB(self):
        ''' Connect to firebird database PilMotConfig.fdb
        return con : connection to database
        '''
        db_path = r'C:\PilMotDB\PILMOTCONFIG.FDB'
        if not os.path.exists(db_path):
            print("Base inexistante")
            return False
        else:
            try:
                self.con = connect(db_path, user='sysdba', password='masterkey')
                self.cur = self.con.cursor()
                self.curCWD = self.con.cursor()
                self.curRef = self.con.cursor()
                self.IsServerRSAIConnected()  # le serveur RSAI doit etre lancé sur cet ordi
                return True
            except Exception as e:
                print(e)
                return False

    def closeConnection(self):
    # close connection
        print('close cursor')
        time.sleep(5)
        self.cur.close()
        self.curCWD.close()
        self.curRef.close()
        time.sleep(0.1)
        print('now close connection to db')
        self.con.close()

    def addSoftToConnectedList(self):
        # add adress ip of the soft in the data base
        # not working yet  to do ...
        # need to create new Pikd for the table ...
        insert = ("INSERT INTO TbConnectedList(d_ParaDbUUID, d_ParaDbConnectName,d_ParaDbAlias) values(%s,%s,%s)" % (str(UUIDSoftware), str(IPSoft), ""))
        self.cur.execute(insert)
        self.con.commit()

    def listProgConnected(self):
        # Read the list of programs connected to database
        # nbProgConnected :  number of programs connected into database
        # p_ListPrg (returned): Described list of programs into database
        #  (Format of the field of the list for one program: PkId, UUID, SoftName, Alias, Hostname, IpAddress, TimeConnection, HeartCnt)
        SoftName = []
        HostName = []
        IpProgram = []
        self.cur.execute("SELECT * FROM " + "TBCONNECTEDLIST" + " ORDER BY PkId;")

        for row in self.cur:
            SoftName.append(row[2])
            HostName.append(row[4])
            IpProgram.append(row[5])
        nbProgConnected = len(SoftName)
        return nbProgConnected, SoftName, HostName, IpProgram

    def IsServerRSAIConnected(self):
        if 'PilMotServer' in self.listProgConnected()[1]:
            #  print('server RSAI connected')
            return True
        else:
            print('Server RSAI not launched')
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Server RSAI not launched")
            msg.setInformativeText("Server RSAI not launched : start server ")
            msg.setWindowTitle("Warning ...")
            msg.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint)
            msg.exec()

    def rEquipmentList(self):
        '''
        Read the list of Equipment connected to database equipement =Rack =IPadress 
        Described list of equipment into database
        Format of the field of the list for one equipment: PkId, Address, Category, Status)
        '''
        addressEquipement = []
        self.cur.execute("SELECT * FROM " + "TBEQUIPMENT")
        for row in self.cur:
            addressEquipement.append(row[1])
        return addressEquipement

    def getValueWhere1ConditionAND(self, cursor, TableName, ValToRead, ConditionColName, ConditionValue):
        '''
        Read the field value in a table where the 'column' equals 'value' corresponding Query = SELECT 'ValToRead'  FROM TableName WHERE ConditionColName = ConditionValue
        TableName : Table in which execute query
        ValToRead : Field Value to read
        ConditionColName : Column name for the condition of the query search
        ConditionValue : Value name for the condition of the query search
        return param p_DataRead : values read
        '''
        # con.commit()
        Prepare1Cond = "SELECT " + ValToRead + " FROM " + TableName + " WHERE " + ConditionColName + " = '" + ConditionValue + "' ;"
        cursor.execute(Prepare1Cond)
        p_DataRead = cursor.fetchone()[0]

        return p_DataRead

    def rEquipmentIdNbr(self, IpAddress):
        ''' Get Identification number of one PilMot equipement from its IP Address
        IpAddress: IP Address
        p_IdEquipment: Identification number of the equipement
        '''
        p_IdEquipment = self.getValueWhere1ConditionAND(self.cur, "TbEquipment", "PkId", "Address", IpAddress)

        return p_IdEquipment

    def getSlotNumber(self, NoMotor):
        '''
        Get the slot number of ESBIM corresponding to the motor number
        return Slot number (value from 1 to 7)
        '''
        SlotNbr = 0
        SlotNbr = (NoMotor + 1) / 2
        return SlotNbr

    def getAxisNumber(self, NoMotor):
        '''
        Get the axis number of module corresponding to the motor number
        return Slot number (value 1 or 2)
        '''
        AxisNbr = 1
        if (NoMotor % 2) == 0:
            AxisNbr = 2
        return AxisNbr

    def readPkModBim2BOC(self, cursor, PkEsbim, NumSlotMod, NumAxis, FlgReadWrite=1):
        '''
        Read Primary key identifier of an axis module Bim2BOC :  p_PkModBim
        PkEsbim : numero Equipment on which the module is plugged
        NumSlotMod : Number of the slot of the module to get PK
        NumAxis : Axis number of the module
        param FlgReadWrite : Indicate if the function accesses to Read or Write table (value : 1=ReadTb, 0=WriteTb)
        '''
        TbToRead = "TbBim2Boc_1Axis_W"
        cursor.execute("SELECT m.PkId FROM TbModule m INNER JOIN TbEquipment e ON m.idEquipment = e.PKID WHERE (e.PkId = " + str(int(PkEsbim)) + " and m.NumSlot = " + str(int(NumSlotMod)) + ");" )
        # for row in cur :
        #     TmpPkModBim=row[0] # cle dans TbModule correspondant cle Esbim dans TbEquipement et numero du slot  
        TmpPkModBim = cursor.fetchone()[0]
        cursor.execute("SELECT b.PkId FROM " + TbToRead + " b WHERE IdModule = " + str(TmpPkModBim) + " AND NumAxis = " + str(int(NumAxis)) + ";" );
        # for row in cur :
        #     p_PKModBim = row[0]
        p_PKModBim = cursor.fetchone()[0]
        return p_PKModBim  # cle dans TbBim2Boc_1Axis_W correpondant idmodule et au numero d axe

    def nameMoteur(self, IpAdress, NoMotor):
        '''
        Get motor name from Ipadress et axe number
        '''
        IdEquipt = self.rEquipmentIdNbr(IpAdress)
        NoMod  = self.getSlotNumber(NoMotor)
        NoAxis = self.getAxisNumber(NoMotor)
        PkIdTbBoc = self.readPkModBim2BOC(self.cur, IdEquipt, NoMod, NoAxis, FlgReadWrite=1)  # Read Primary key identifier of an axis module Bim2BOC :  p_PkModBim
        name = self.rStepperParameter(self.cur, PkIdTbBoc, NoMotor, self.listParaStr['nomAxe'])
        # con.commit()
        return name

    def setNameMoteur(self, IpAdress, NoMotor, nom):
        IdEquipt = self.rEquipmentIdNbr(IpAdress)
        NoMod = self.getSlotNumber(NoMotor)
        NoAxis = self.getAxisNumber(NoMotor)
        valParam = nom
        a = self.wStepperParameter(self.cur, IdEquipt, NoMotor, self.listParaStr['nomAxe'], valParam)
        # con.commit()

    def setNameRef(self, IpAdress, NoMotor, nRef, name):
        IdEquipt = self.rEquipmentIdNbr(IpAdress)
        NoMod = self.getSlotNumber(NoMotor)
        NoAxis = self.getAxisNumber(NoMotor)
        key = self.listParaStr['nomRef'+str(nRef)]
        a = self.wStepperParameter(self.curRef, IdEquipt, NoMotor, key, name)
        # con.commit()

    def setPosRef(self, IpAdress, NoMotor, nRef, pos):
        IdEquipt = self.rEquipmentIdNbr(IpAdress)
        NoMod = self.getSlotNumber(NoMotor)
        NoAxis = self.getAxisNumber(NoMotor)
        key = self.listParaReal['Ref'+str(nRef)+'Val']
        a = self.wStepperParameter(self.curRef, IdEquipt, NoMotor, key, pos)
        # con.commit()

    def setButeePos(self, IpAdress, NoMotor, but):
        IdEquipt = self.rEquipmentIdNbr(IpAdress)
        NoMod = self.getSlotNumber(NoMotor)
        NoAxis = self.getAxisNumber(NoMotor)
        key = self.listParaInt['ButLogPlus']
        a = self.wStepperParameter(self.curRef, IdEquipt, NoMotor, key, but)

    def setButeeNeg(self, IpAdress, NoMotor, but):
        IdEquipt = self.rEquipmentIdNbr(IpAdress)
        NoMod = self.getSlotNumber(NoMotor)
        NoAxis = self.getAxisNumber(NoMotor)
        key = self.listParaInt['ButLogNeg']
        a = self.wStepperParameter(self.curRef, IdEquipt, NoMotor, key, but)

    def setStep(self, IpAdress, NoMotor, step):
        IdEquipt = self.rEquipmentIdNbr(IpAdress)
        NoMod = self.getSlotNumber(NoMotor)
        NoAxis = self.getAxisNumber(NoMotor)
        key =  self.listParaReal['Step']
        print('set set in db',step)
        a = self.wStepperParameter(self.curRef, IdEquipt, NoMotor, key, step)

    def listMotorName(self, IpAdress):
        '''List des moteurs sur l'equipement IpAdress
        '''
        IdEquipt = self.rEquipmentIdNbr(IpAdress)
        self.con.commit()
        listSlot = []  # list slot
        SELECT = 'select NumSlot from %s  where  IdEquipment= %s and NumSlot>=0' % ('TbModule', str(IdEquipt))   # list SLot
        self.cur.execute(SELECT)
        for row in self.cur:
            listSlot.append(row[0])
        # print(listSlot)
        listSlot.sort()  # tri dans l'odre croissant

        listNumMot = []  # liste num moteur
        # print(listSlot)
        for i in listSlot:
            listNumMot.append(2*i-1)
            listNumMot.append(2*i)

        listNameMotor = []
        for noMot in listNumMot:  # range (1,2*len(listSlot)+1): # dans notre cas 1...14
            listNameMotor.append(self.nameMoteur(IpAdress, noMot))

        return listNameMotor

    def nameEquipment(self, IpAdress):
        '''
        return the equipment name defined by IpAdress
        '''
        IdEquipt = self.rEquipmentIdNbr(IpAdress)
        SELECT = 'select PkId from %s  where  IdEquipment = %s and NumSlot = -1' % ('TbModule', str(IdEquipt))   # list Pkid module
        self.cur.execute(SELECT)
        PkIdMod = self.cur.fetchone()[0]

        SELECT = 'select ValParam from %s where IDMODULE = %s and IDNAME = 10 ' % ('TbParameterSTR', str(PkIdMod))
        self.cur.execute(SELECT)
        nameEquip = self.cur.fetchone()[0]
        return nameEquip

    def getValueWhere2ConditionAND(self, cursor, TableName, ValToRead, ConditionColName1, ConditionValue1, ConditionColName2, ConditionValue2):
        '''
        Read the field value in a table where the 'column' equals 'value' corresponding Query = SELECT 'ValToRead' FROM TableName WHERE 'ConditionColName1' = 'ConditionValue1' AND 'ConditionColName2' = 'ConditionValue2' "
        TableName : Table in which execute query
        ValToRead : Field Value to read
        ConditionColName1 : First column name for the condition of the query search
        ConditionValue1 : First value name for the condition of the query search
        ConditionColName2 : Second column name for the condition of the query search
        ConditionValue2 : Second value name for the condition of the query search
        return p_DataRead : values read
        '''
        cursor.execute("SELECT " + ValToRead + " FROM " + TableName + " WHERE " + ConditionColName1 + " = '" + ConditionValue1 + "' AND " + ConditionColName2 + " = '" + ConditionValue2 + "' ;" )
        p_DataRead = cursor.fetchone()[0]
        # for row in cursor:
        #     p_DataRead=row[0]
        # con.commit()
        return p_DataRead

    def getValueWhere3ConditionAND(self, cursor, TableName, ValToRead,  ConditionColName1, ConditionValue1, ConditionColName2, ConditionValue2, ConditionColName3,  ConditionValue3):
        '''
        Read the field value in a table where the 'column' equals 'value' corresponding Query = SELECT 'ValToRead' FROM TableName WHERE 'ConditionColName1' = 'ConditionValue1' AND 'ConditionColName2' = 'ConditionValue2' " ...
        param TableName : Table in which execute query
        ValToRead : Field Value to read
        ConditionColName1 : First column name for the condition of the query search
        ConditionValue1 : First value name for the condition of the query search
        ConditionColName2 : Second column name for the condition of the query search
        ConditionValue2 : Second value name for the condition of the query search
        ConditionColName3 : Third column name for the condition of the query search
        ConditionValue3 : Third value name for the condition of the query search
        '''
        cursor.execute("SELECT " + ValToRead + " FROM " + TableName + " WHERE " + ConditionColName1 + " = '" + ConditionValue1 + "' AND " + ConditionColName2 + " = '" + ConditionValue2 + "' AND " + ConditionColName3 + " = '" + ConditionValue3 + "' ;" )
        # for row in cur:
        #     p_DataRead=row[0]
        p_DataRead = cursor.fetchone()[0]
        # con.commit()
        return p_DataRead

    def rEquipmentStatus(self, IpAddress):
        '''
        Read the status of an equipment from its IP Address
        '''
        status = self.getValueWhere1ConditionAND(self.cur, "TbEquipment", "status", "Address", IpAddress)
        return status

    def rStepperParameter(self, cursor, PkIdTbBoc, NoMotor, NoParam):
        '''
        Read one stepper parameter
        PkIdTbBoc: Primary key identifier of an axis module Bim2BOC
        NoMotor: number of the motor on the equipment
        NoParam: number(Id) of the parameter to read
        '''
        NoMod  = self.getSlotNumber(NoMotor)
        NoAxis = self.getAxisNumber(NoMotor)
        # PkIdTbBoc = readPkModBim2BOC(IdEquipt, NoMod, NoAxis, FlgReadWrite=1) # Read Primary key identifier of an axis module Bim2BOC :  p_PkModBim
        PkIdModuleBIM = self.getValueWhere2ConditionAND(cursor, "TbBim2BOC_1Axis_R", "IdModule", "PkId", str(PkIdTbBoc), "NumAxis", str(NoAxis))

        if NoParam in self.listParaStr.values():  # str
            tbToread = "TbParameterSTR"
            p_ReadValue = self.getValueWhere3ConditionAND(cursor, tbToread, "ValParam", "IdName", str(NoParam), "IdModule", str(PkIdModuleBIM), "NumAxis", str(NoAxis))
            return p_ReadValue
        elif NoParam in self.listParaReal.values():  # Real
            tbToread = "TbParameterREAL"
            p_ReadValue = self.getValueWhere3ConditionAND(cursor, tbToread, "ValParam", "IdName", str(NoParam), "IdModule", str(PkIdModuleBIM), "NumAxis", str(NoAxis))
            return p_ReadValue
        elif NoParam in self.listParaInt.values():  # Int
            tbToread = "TbParameterINT"
            p_ReadValue = self.getValueWhere3ConditionAND(cursor, tbToread, "ValParam", "IdName", str(NoParam), "IdModule", str(PkIdModuleBIM), "NumAxis", str(NoAxis))
            return p_ReadValue
        else:
            print('parameter value not valid')
            return 0

    def wStepperParameter(self, cursor, IdEquipt, NoMotor, NoParam, valParam):
        '''
        write one stepper parameter
        param IdEquipt: Ident of equipment to read
        NoMotor: number of the motor on the equipment
        NoParam: number(Id) of the parameter to read
        '''
        NoMod = self.getSlotNumber(NoMotor)
        NoAxis = self.getAxisNumber(NoMotor)
        PkIdTbBoc = self.readPkModBim2BOC(cursor, IdEquipt, NoMod, NoAxis, FlgReadWrite=1) # Read Primary key identifier of an axis module Bim2BOC :  p_PkModBim
        PkIdModuleBIM = self.getValueWhere2ConditionAND( cursor, "TbBim2BOC_1Axis_R", "IdModule", "PkId", str(PkIdTbBoc), "NumAxis", str(NoAxis))

        if NoParam in self.listParaStr.values():  # str
            tbToread = "TbParameterSTR"
            UPDATE = "UPDATE %s set ValParam ='%s' WHERE IdName= %s and IdModule =%s and NumAxis =%s ;" % (tbToread, valParam, str(NoParam), str(PkIdModuleBIM), str(NoAxis))
            a = cursor.execute(UPDATE)
            self.con.commit()

        elif NoParam in self.listParaReal.values():
            tbToread = "TbParameterREAL"
            UPDATE = "UPDATE %s set ValParam =%s WHERE IdName= %s and IdModule =%s and NumAxis =%s ; " % (tbToread, valParam, str(NoParam), str(PkIdModuleBIM), str(NoAxis))
            a = cursor.execute(UPDATE)
            self.con.commit()
        elif NoParam in self.listParaInt.values():
            tbToread = "TbParameterINT"
            UPDATE = "UPDATE %s set ValParam =%s WHERE IdName= %s and IdModule =%s and NumAxis =%s ; " % (tbToread, valParam, str(NoParam), str(PkIdModuleBIM),str(NoAxis))
            a = cursor.execute(UPDATE)
            self.con.commit()
        else:
            print( 'parameter value is not valid')
            a = 0
        return a

    def wStepperCmd(self, cursor, PkIdTbBoc, RegOrder, RegPosition, RegVelocity=1000):
        '''
        Write a command to a stepper axis (BOCM) with a cursor
        cursor  firbird cursor 
        PkIdTbBoc = readPkModBim2BOC(IdEquipt, NoMod, NoAxis, FlgReadWrite=1)
        CmdRegister: command register to write
        SetpointPosition: Position setpoint
        SetpointVelocity: Velocity setpoint
        IdEquipt = rEquipmentIdNbr(IpAdress)
        NoMod  = getSlotNumber(NoMotor)
        NoAxis = getAxisNumber(NoMotor)
        '''
        # test si pas de commande en cours
        if self.getValueWhere1ConditionAND(cursor, 'TBBIM2BOC_1AXIS_W', 'Cmd', 'PkId', str(PkIdTbBoc)) == 0 or self.getValueWhere1ConditionAND(cursor, 'TBBIM2BOC_1AXIS_R', 'StateCmd', 'PkId', str(PkIdTbBoc)) == (0 or 3 or 4):
            # write parameter cmd
            UPDATE = 'UPDATE %s set RegOrder = %s, RegPosition = %s, RegVelocity = %s WHERE PkId =%s ;' % ('TBBIM2BOC_1AXIS_W', str(RegOrder), str(RegPosition), str(RegVelocity), str(PkIdTbBoc))
            cursor.execute(UPDATE)
            # take write right
            UPDATE = 'UPDATE  %s set cmd=1 WHERE PkId =%s ;' % ('TBBIM2BOC_1AXIS_W', str(PkIdTbBoc))

            cursor.execute(UPDATE)
            self.con.commit()
            time.sleep(0.15)  # ?? sinon ca marche pas ...
        #  test si commande est terminé cmd=3 ou 4 (erreur ?)
            select = "SELECT " + "StateCmd" + " FROM " + "TbBim2BOC_1Axis_R" + " WHERE " + "PkId" + " = " + str(PkIdTbBoc) + ";"
            cursor.execute(select)
            cmd = cursor.fetchone()

        # liberer le champ cmd =0
            UPDATE = 'UPDATE  %s set  Cmd = 0 WHERE PkId =%s ;' % ('TBBIM2BOC_1AXIS_W', str(PkIdTbBoc))  # clear commande right
            cursor.execute(UPDATE)
            self.con.commit()
            time.sleep(0.15)

            if cmd == 4:
                return 'cmd error'
            else:
                return 'cmd ok'


class MOTORRSAI():
    """
    MOTORRSAI(IpAdrress, NoMotor, db: FirebirdConnect, parent=None)
    class is defined by Ipadress of the rack and axis number we communicate with the data base 
    we can move have postion from the data base but it is not usefull
    """

    def __init__(self, IpAdrress, NoMotor, db: FirebirdConnect, parent=None):
        self.IpAdress = IpAdrress
        self.NoMotor = NoMotor
        self.db = db  # Une seule connection pour tous les moteurs mais plusieur cursors
        self.IdEquipt = self.db.rEquipmentIdNbr(self.IpAdress)
        self.NoMod = self.db.getSlotNumber(self.NoMotor)
        self.NoAxis = self.db.getAxisNumber(self.NoMotor)

        # each action to database have different cursor
        self.cur = self.db.con.cursor()  # def cursor to read postion
        self.curcwd = self.db.con.cursor()  # def cursor to write cmd
        self.curEtat = self.db.con.cursor()  # def cursor to read state
        self.cursorRead = self.db.con.cursor()  # def cursor to read parameter value
        self.cursorWrite = self.db.con.cursor()  # def cursor to write parameter value

        self.PkIdTbBoc = self.db.readPkModBim2BOC(self.cursorRead, self.IdEquipt, self.NoMod, self.NoAxis, FlgReadWrite=1)  # Read Primary key identifier of an axis module Bim2BOC :  p_PkModBim
        self._name = self.db.rStepperParameter(self.cursorRead, self.PkIdTbBoc, NoMotor, self.db.listParaStr['nomAxe'])
        self.update()

    def update(self):
        '''update from the data base')
        '''
        self.name = self.getName()
        self.step = self.getStepValue()
        self.butPlus = self.getButLogPlusValue()
        self.butMoins = self.getButLogMoinsValue()
        self.refName = []
        for i in range(1, 7):
            r = self.getRefName(i)
            self.refName.append(r)
            # time.sleep(0.01)
        self.refValue = []
        for i in range(1, 7):
            if self.step == 0:
                self.step = 1
            rr = self.getRefValue(i)  # /self.step JG 2025_01_20
            self.refValue.append(rr)
            # time.sleep(0.01)

    def position(self):
        '''
        return motor postion
        '''
        self.db.mut.lock()
        TableName = "TbBim2BOC_1Axis_R"
        ValToRead = "PosAxis"
        ConditionColName = "PkId"
        ConditionValue = str(self.PkIdTbBoc)
        Prepare1Cond = "SELECT " + ValToRead + " FROM " + TableName + " WHERE " + ConditionColName + " = '" + ConditionValue + "' ;"
        self.cur.execute(Prepare1Cond)
        posi = self.cur.fetchone()[0]
        self.db.mut.unlock()
        return posi

    def getName(self):
        '''
        get motor name
        '''
        self.db.mut.lock()
        self._name = self.db.rStepperParameter(self.cursorRead, self.PkIdTbBoc, self.NoMotor, self.db.listParaStr['nomAxe'])
        self.db.mut.unlock()
        return self._name

    def setName(self, nom):
        '''
        set motor name
        '''
        valParam = nom
        self.db.mut.lock()
        a = self.db.wStepperParameter(self.cursorWrite, self.IdEquipt, self.NoMotor, self.db.listParaStr['nomAxe'], valParam)
        time.sleep(0.05)
        self.db.mut.unlock()

    def getRefName(self, nRef):
        '''
        set ref n° name
        '''
        self.db.mut.lock()
        key = self.db.listParaStr['nomRef'+str(nRef)]
        self.db.mut.unlock()
        return self.db.rStepperParameter(self.cursorRead, self.PkIdTbBoc, self.NoMotor, key)

    def setRefName(self, nRef, name):
        '''
        set ref n° name
        '''
        self.db.mut.lock()
        key = self.db.listParaStr['nomRef'+str(nRef)]
        a = self.db.wStepperParameter(self.cursorWrite, self.IdEquipt, self.NoMotor, key, name)   # to do change to self.PkIdTbBoc?
        self.db.mut.unlock()

    def getRefValue(self, nRef):
        '''
        get value of the refereence position nRef
        '''
        self.db.mut.lock()
        key = self.db.listParaReal['Ref'+str(nRef)+'Val']
        ref = self.db.rStepperParameter(self.cursorRead, self.PkIdTbBoc, self.NoMotor, key)
        self.db.mut.unlock()
        return ref

    def setRefValue(self, nReff, value):
        '''
        set value of the refereence position nRef
        '''
        key = self.db.listParaReal['Ref'+str(nReff)+'Val']
        self.db.wStepperParameter(self.cursorWrite, self.IdEquipt, self.NoMotor, key, value)  # to do change to self.PkIdTbBoc? change for self.cur? 

    def getStepValue(self):
        '''Valeur de 1 pas dans l'unites
        '''
        self.db.mut.lock()
        key = self.db.listParaReal['Step']  #1106
        step = self.db.rStepperParameter(self.cursorRead, self.PkIdTbBoc, self.NoMotor, key)
        self.db.mut.unlock()
        return step
    def setStepValue(self,step):
        self.db.mut.lock()
        key = self.db.listParaReal['Step']  #1106
        step = self.db.wStepperParameter(self.cursorRead, self.PkIdTbBoc, self.NoMotor, key,step)
        self.db.mut.unlock()

    def getButLogPlusValue(self):
        key = self.db.listParaInt['ButLogPlus']
        self.db.mut.lock()
        but = self.db.rStepperParameter(self.cursorRead, self.PkIdTbBoc, self.NoMotor, key)
        self.db.mut.unlock()
        return but

    def setButLogPlusValue(self, butPlus):
        key = self.db.listParaInt['ButLogPlus']
        self.db.wStepperParameter(self.cursorWrite, self.IdEquipt, self.NoMotor, key, butPlus)  # to do change to self.PkIdTbBoc?

    def getButLogMoinsValue(self):
        key = self.db.listParaInt['ButLogNeg']
        self.db.mut.lock()
        b = self.db.rStepperParameter(self.cursorRead, self.PkIdTbBoc, self.NoMotor, key)
        self.db.mut.unlock()
        return b

    def setButLogMoinsValue(self, butMoins):
        key = self.db.listParaInt['ButLogNeg']
        self.db.wStepperParameter(self.cursorWrite, self.IdEquipt, self.NoMotor, key, butMoins)  # to do change to self.PkIdTbBoc?

    def rmove(self, posrelatif, vitesse=1000):
        '''
        relative move of NoMotor of IpAdress
        posrelatif = position to move in step
        #to do faire self.curcwd
        '''
        RegOrder = 3
        posrelatif = int(posrelatif)
        print(self._name, 'relative move of ', posrelatif, ' step')
        self.db.mut.lock()
        a = self.db.wStepperCmd(cursor=self.curcwd, PkIdTbBoc=self.PkIdTbBoc, RegOrder=RegOrder, RegPosition=posrelatif, RegVelocity=vitesse)  
        self.db.mut.unlock()

    def move(self, pos, vitesse=1000):
        '''absolue move of NoMotor  of IpAdress
        pos = position to move in step
        '''
        self.db.mut.lock()
        RegOrder = 2
        a = self.db.wStepperCmd(cursor=self.curcwd, PkIdTbBoc=self.PkIdTbBoc, RegOrder=RegOrder, RegPosition=pos, RegVelocity=vitesse)
        print(self._name, 'absolue move of ', pos, ' step')
        self.db.mut.unlock()

    def setzero(self):
        """
        setzero(self.moteurname):Set Zero
        """
        self.db.mut.lock()
        RegOrder = 10  # commande pour zero le moteur 
        a = self.db.wStepperCmd(cursor=self.curcwd, PkIdTbBoc=self.PkIdTbBoc, RegOrder=RegOrder, RegPosition=0, RegVelocity=0)
        self.db.mut.unlock()

    def stopMotor(self):  # stop le moteur motor
        """
        stopMotor(motor): stop le moteur motor
        """
        self.db.mut.lock()
        RegOrder = 4
        a = self.db.wStepperCmd(cursor=self.curcwd, PkIdTbBoc=self.PkIdTbBoc, RegOrder=RegOrder, RegPosition=0, RegVelocity=0)
        self.db.mut.unlock()

    def etatMotor(self):
        '''
        read status of the motor
        '''
        self.db.mut.lock()
        TbToRead = "TbBim2Boc_1Axis_R"
        # PkIdTbBoc = readPkModBim2BOC(self.IdEquipt, self.NoMod, self.NoAxis, FlgReadWrite=1) # Read Primary key identifier of an axis module Bim2BOC :  p_PkModBim 
        # a =str( hex(getValueWhere1ConditionAND(TbToRead , "StatusAxis", "PkId", str(self.PkIdTbBoc))))
        # ecire direct la fonction
        Prepare1Cond = "SELECT " + "StatusAxis" + " FROM " + TbToRead + " WHERE " + "PkId" + " = " + str(self.PkIdTbBoc) + ";"
        self.curEtat.execute(Prepare1Cond)
        a = self.curEtat.fetchone()[0]
        a = str(hex(a))
        self.db.con.commit()
        time.sleep(0.1)
        self.db.mut.unlock()
        if (a & 0x0800) != 0:
            etat = 'Poweroff'
        elif (a & 0x0200) != 0:
            etat = 'Phasedebranche'
        elif (a & 0x0400) != 0:
            etat = 'courtcircuit'
        elif (a & 0x0001) != 0:
            etat = ('FDD+')
        elif (a & 0x0002) != 0:
            etat = 'FDC-'
        elif (a & 0x0004) != 0:
            etat = 'Log+'
        elif (a & 0x0008) != 0:
            etat = 'Log-'
        elif (a & 0x0020) != 0:
            etat = 'mvt'
        elif (a & 0x0080) != 0:  # phase devalidé
            etat = 'ok'
        elif (a & 0x8000) != 0:  # came origin
            etat = 'etatCameOrigin'
        else:
            etat = '?'
        return etat
    
    def closeCursor(self):
        self.cur.close()
        self.curcwd.close()
        self.curEtat.close()
        self.cursorRead.close()
        self.cursorWrite.close()

    def getEquipementName(self):
        '''
        return the name of the equipement of which the motor is connected
        '''
        return self.db.nameEquipment(self.IpAdress)


if __name__ == '__main__':
    ip = '10.0.1.31'
    db = FirebirdConnect()
    db.ConnectToDB()
    # print(db.listMotorName(ip))
    db.setButeePos("10.0.1.30",1,1000)
    db.closeConnection()
