import sys

from PySide6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)

label = QLabel("Personal Jarvis UI Test")
label.resize(500, 200)
label.show()

sys.exit(app.exec())