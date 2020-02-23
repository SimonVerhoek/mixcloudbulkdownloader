import sys
from PySide2.QtWidgets import QApplication, QPushButton
from PySide2.QtCore import Slot

# greetings
@Slot()     # identifies function as a slot
def say_hello():
    print('button clicked, Hello!')

# Create the Qt Application
app = QApplication(sys.argv)

# Create a button
button = QPushButton('Click me')

# Connect the button to the function
button.clicked.connect(say_hello)

button.show()
app.exec_()
