from visu.WinCut import GRAPHCUT 
from visu.visual import SEE

import sys
from PyQt6.QtWidgets import QApplication
import qdarkstyle

appli = QApplication(sys.argv) 
graph1 = SEE()
graph1.show()
appli.exec_() 