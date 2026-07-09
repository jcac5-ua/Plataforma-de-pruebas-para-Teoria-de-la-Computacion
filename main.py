from PySide6.QtGui import QColor, QPalette, QAction, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QStackedLayout,
    QPushButton,
    QTextEdit,
    QToolBar,
    QStatusBar,
    QCheckBox,
    QMessageBox,
    QLabel,
    QInputDialog,
    QToolBar,
)
from PySide6.QtCore import Qt, QSize

import interpreter
import encoder
import expander

#pyinstaller --name InterpreteL --windowed --onefile main.py

def error_msg(tipo, línea, error):
    tipo_error = ""
    match tipo:
        case -1:
            tipo_error = "léxico"
        case -2:
            tipo_error = "sintáctico"
        case -3:
            tipo_error = "semántico"
        case -4:
            return f"Error de ejecución: {error}"

    return f"Error {tipo_error} en la línea {línea}: {error}"

def compose_code(code):
    s = ""
    for line in code:
        s = s + line + "\n"
    return s

#Se puede añadir un layout vertical aparte
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")
        self.goto_button = False
        self.suma_button = False
        self.resta_button =False
        self.equal_button =False

        pagelayout = QVBoxLayout()
        filelayout = QHBoxLayout()
        button_layout = QHBoxLayout()

        asig_op = QAction(QIcon("bug.png"), "&T2 = T1 -> COPIA", self)
        asig_op.triggered.connect(self.equal_button_clicked)
        asig_op.setCheckable(True)

        add_op = QAction(QIcon("bug.png"), "T3 = T1 + T2 -> SUMA", self)
        add_op.triggered.connect(self.suma_button_clicked)
        add_op.setCheckable(True)

        sub_op = QAction(QIcon("bug.png"), "T3 = T1 - T2 -> RESTA", self)
        sub_op.triggered.connect(self.resta_button_clicked)
        sub_op.setCheckable(True)

        goto_op = QAction(QIcon("bug.png"), "GOTO T1 -> SALTO", self)
        goto_op.triggered.connect(self.goto_button_clicked)
        goto_op.setCheckable(True)

        self.setStatusBar(QStatusBar(self))

        menu = self.menuBar()

        file_menu = menu.addMenu("&Macros predeterminadas")

 
        file_submenu1 = file_menu.addMenu("Asignaciones")
        file_submenu1.addAction(asig_op)

        file_menu.addSeparator()

        arit_op = file_menu.addMenu("Operaciones aritméticas")
        arit_op.addAction(add_op)
        arit_op.addAction(sub_op)

        file_menu.addSeparator()

        jump_op = file_menu.addMenu("Salto incondicional")
        jump_op.addAction(goto_op)

        pagelayout.addLayout(button_layout)
        pagelayout.addLayout(filelayout)

        self.code_text = QTextEdit()
        self.output_code = QTextEdit()
        self.output_code.setReadOnly(True)
        filelayout.addWidget(self.code_text)
        filelayout.addWidget(self.output_code)

        self.code_text.setHtml("<i><font color= grey>#Escribe tu código aquí</font></i>")

        self.chk = QCheckBox("Mostrar codificación")
        run_btn = QPushButton("Run")
        run_btn.pressed.connect(self.run_code)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setDisabled(True)
        button_layout.addWidget(self.chk)
        button_layout.addWidget(run_btn)

        widget = QWidget()
        widget.setLayout(pagelayout)
        self.setCentralWidget(widget)

    def goto_button_clicked(self, s):
        self.goto_button = s

    def suma_button_clicked(self, s):
        self.suma_button = s

    def resta_button_clicked(self, s):
        self.resta_button = s

    def equal_button_clicked(self, s):
        self.equal_button = s

    def run_code(self):
        USAGE = "\n\nInstrucciones validas:\n\n* VARIABLE OPERACION\n\n* ETIQUETA:\n\n* IF VARIABLE != 0 GOTO ETIQUETA\n\n* CALL NOMBRE_MACRO\n\n* MACRO NOMBRE_MACRO ... END\n\nVARIABLE = Y, X1, Z1, X2, Z2, ...\nVARIABLE MACRO = T1, W1, T2, W2, ...\nOPERACION = ++, --, ==\nETIQUETA = A1, B1, C1, D1, S1, A2, ...\nETIQUETA MACRO = G1, G2, G3, ..."
        equal_text = ["MACRO COPIA","IF T2 != 0 GOTO G4","W1 ++","IF W1 != 0 GOTO G5","G4: T2 --","IF T2 != 0 GOTO G4","G5: IF T1 != 0 GOTO G2","W2 ++","IF W1 != 0 GOTO F","G2: T1 --","T2 ++","W3 ++","IF T1 != 0 GOTO G2","G3: W3 --","T1 ++","IF W3 != 0 GOTO G3","END"]
        suma_text = ["MACRO SUMA","IF T3 != 0 GOTO G1","CALL SALTO G2","G1: T3 --","IF T3 != 0 GOTO G1","G2: CALL COPIA T2 W2","CALL COPIA T1 T3","IF T2 != 0 GOTO G3","CALL SALTO G4","G3: T3 ++","T2 --","IF T2 != 0 GOTO G3","G4: CALL COPIA W2 T2", "END"]
        goto_text = ["MACRO SALTO", "W1 ++", "IF W1 != 0 GOTO T1", "END"]
        resta_text = ["MACRO RESTA","CALL COPIA T1 T3","CALL COPIA T2 W1","IF T2 != 0 GOTO G1","CALL SALTO F","G1: W1 --","T3 --","IF W1 != 0 GOTO G1","END"]
        self.output_code.setPlainText("")
        QApplication.processEvents()
        text = self.code_text.toPlainText().splitlines()
        check_str = ""

        if self.equal_button:
            text = equal_text + text
        if self.goto_button:
            text = goto_text + text
        if self.suma_button:
            funcs = []
            if not self.equal_button:
                funcs = equal_text
            if not self.goto_button:
                funcs = funcs + goto_text
            text = funcs + suma_text + text
        if self.resta_button:
            funcs = []
            if not self.suma_button:
                if not self.equal_button:
                    funcs = equal_text
                if not self.goto_button:
                    funcs = funcs + goto_text
            text = funcs + resta_text + text


        result = interpreter.interpreter(text)
        if result[0] < 0:
            self.output_code.setPlainText(error_msg(result[0], result[1], result[2]) + "\n" + USAGE)
        else:
            init_vars = {}
            for arg in result[1]:
                valor, _ = QInputDialog.getText(self, "Asignación de valores", f"Introduce el valor de la variable {arg}")
                while valor.isnumeric() == False:
                    valor, _ = QInputDialog.getText(self, "Asignación de valores", f"Introduce el valor de la variable {arg}")
                init_vars[arg] = int(valor)
            code = expander.expander(text, result[4], result[5])
            if code[0] < 0:
                self.output_code.setPlainText(error_msg(code[0], code[1], code[2]))
            else:
                result = interpreter.interpreter(code[1])
                if result[0] < 0:
                    self.output_code.setPlainText("Después de la expansión: \n\n" + error_msg(result[0], result[1], result[2]) + "\nDe la expansión:\n\n" + compose_code(code[1]))
                else:
                    result = interpreter.execute(result[2], result[3], init_vars)
                    if result[0] < 0:
                        self.output_code.setPlainText(f"Para los valores de entrada {init_vars}\n" + error_msg(result[0], result[1], result[2]))
                    else:
                        if self.chk.isChecked():
                            print("Encoder:")
                            check_str = "Codificación:\n" + encoder.encoder(code[1]) + "\n"
                        self.output_code.setPlainText(check_str + f"Para los valores de entrada {init_vars}\nResult: " + str(result[0]))

app = QApplication([])
window = MainWindow()
window.show()
app.exec()