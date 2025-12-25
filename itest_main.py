import sys
import pyautogui
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QBrush, QColor, QFont
from time import sleep
from pynput import mouse, keyboard
import threading
from PIL import ImageGrab, Image
import pytesseract
import json
import difflib
from bs4 import BeautifulSoup


class DraggableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_position = None
        self._left_click_position = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._left_click_position = event.globalPos()
            self._drag_position = self.parent().pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            delta = QPoint(event.globalPos() - self._left_click_position)
            new_pos = self._drag_position + delta
            self.parent().move(new_pos)

class FramelessMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.resize(400, 100)
        self.setWindowTitle('ansShow Window')
        self.setWindowOpacity(0.1)# 设置窗口不透明度为 10%
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)#
        self.move(1000, 1350)
        # 创建一个可以拖动的区域
        self.draggable_area = DraggableWidget(self)
        self.draggable_area.setGeometry(0, 0, 100, 20)
        self.draggable_area.setStyleSheet("background-color: blue;")
        # 创建一个标签来显示文本
        self.ansLabel = QLabel(
            'None',
            self)
        self.ansLabel.setAlignment(Qt.AlignLeft)
        self.ansLabel.setGeometry(5, 20, 395, 595)
        self.ansLabel.setFont(QFont("simsun", 10) )
        self.ansLabel.setWordWrap(True)
        # 创建状态显示标签
        self.stageLabel = QLabel('No Information',self)
        self.stageLabel.setAlignment(Qt.AlignLeft)
        self.stageLabel.setGeometry(100,0,230,20)
        self.stageLabel.setWordWrap(True)
        # 创建匹配度显示标签
        self.matchPercentage = QLabel('0%',self)
        self.matchPercentage.setAlignment(Qt.AlignLeft)
        self.matchPercentage.setGeometry(230,0,250,20)
        self.matchPercentage.setWordWrap(True)
        # 创建按键显示标签
        self.clickRecord = QLabel("",self)
        self.clickRecord.setAlignment(Qt.AlignLeft)
        self.clickRecord.setGeometry(260,0,300,20)
        self.clickRecord.setWordWrap(True)

class MaskWindow(QMainWindow):
    def __init__(self, info: dict = None):
        super().__init__()
        self.initUI(info)

    def initUI(self, info: dict = None):
        self.resize(info["w"], info["h"])
        self.setWindowTitle(info["title"])
        self.setWindowOpacity(info["opacity"])# 设置窗口不透明度为 100%
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        # 设置窗口背景色
        self.setStyleSheet("background-color: "+ info["color"] +";")
        # 设置窗口生成的位置
        self.move(QPoint(info["x"], info["y"]))
        # 创建一个可以拖动的区域
        self.draggable_area = DraggableWidget(self)
        self.draggable_area.setGeometry(0, 0, 100, 20)
        self.draggable_area.setStyleSheet("background-color: blue;")


keyboardRecording: list = []
mouseListening: bool = False
allowKey: list = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z',
            'a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z']
mouseClick: list = [[0,0],[0,0]]
mainWin: FramelessMainWindow = None
matchOriginTextList: list = []
matchQuestion: object = {"len":0,"question":"", "answer":"","options":[],"text":""}
selectedAreaInFirst: bool = True
getOCRText: str = ""
windowList_Mask = []
windowInf_Mask: list = [
    {"x":2,"y":1514,"w":2556,"h":86,"title":"bottom Window","opacity":1,"color":"rgba(255,255,255, 1)"},
    {"x":2,"y":0,"w":2556,"h":116,"title":"top Window","opacity":1,"color":"rgba( 32,124,255,1)"},
    {"x":0,"y":0,"w":2,"h":1600,"title":"left Window","opacity":1,"color":"rgba(0, 0, 0, 0)"},
    {"x":2558,"y":0,"w":4,"h":1600,"title":"right Window","opacity":1,"color":"rgba(0, 0, 0, 0)"}
    # {"x":2,"y":1529,"w":2556,"h":71,"title":"bottom Window","opacity":1,"color":"rgba(255,255,255, 1)"},
    # {"x":2,"y":0,"w":2556,"h":93,"title":"top Window","opacity":1,"color":"rgba( 32,124,255,1)"},
    # {"x":0,"y":0,"w":2,"h":1600,"title":"left Window","opacity":1,"color":"rgba(0, 0, 0, 0)"},
    # {"x":2558,"y":0,"w":4,"h":1600,"title":"right Window","opacity":1,"color":"rgba(0, 0, 0, 0)"}
]
windowList_Style_Duck = [
    {"x":0,"y":1529,"w":2560,"h":71,"title":"bottom Window","opacity":1,"color":"rgba(0, 0, 0, 0)"},
    {"x":0,"y":0,"w":2560,"h":93,"title":"top Window","opacity":1,"color":"rgba(0, 0, 0, 0)"},
    {"x":0,"y":71,"w":2,"h":1529,"title":"left Window","opacity":1,"color":"rgba(0, 0, 0, 0)"},
    {"x":2556,"y":71,"w":4,"h":1529,"title":"right Window","opacity":1,"color":"rgba(0, 0, 0, 0)"}
]
questionsFile = "decode.json"


def LCSlen_old(X: str, Y: str)->int:
    m = len(X)
    n = len(Y)
    L = [[0] * (n + 1) for i in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if X[i - 1] == Y[j - 1]:
                L[i][j] = L[i - 1][j - 1] + 1
            else:
                L[i][j] = max(L[i - 1][j], L[i][j - 1])
    return L[m][n]

def Html_to_Text(html: str):
    soup = BeautifulSoup(html, 'lxml')
    return soup.get_text()

def showAns(window: FramelessMainWindow):
    global matchQuestion,getOCRText,mouseListening
    image = cutScreen()
    if image is None:
        window.stageLabel.setText("ERROR: small area")
        return
    window.stageLabel.setText("Loading...OCR")
    getOCRText = OCRcutScreen(image)
    window.stageLabel.setText("Loading...Match")
    refreshAnsRank_v2(getOCRText)
    if matchQuestion["len"] == 0:
        window.stageLabel.setText("No Match")
        return
    matchQuestion["answer"] = Html_to_Text(matchQuestion["answer"]).replace("\n","   ")
    window.ansLabel.setText(matchQuestion["answer"])
    window.stageLabel.setText("Show")
    window.matchPercentage.setText(str(len(getOCRText)))# str(matchQuestion["len"]/len(getOCRText)*100).split('.')[0] + "%")
    print(matchQuestion)

def cutScreen()->Image:
    global mouseClick
    if abs(mouseClick[0][0]-mouseClick[1][0]) < 5 or abs(mouseClick[0][1]-mouseClick[1][1]) < 5:
        return None
    im = ImageGrab.grab(bbox=(min(mouseClick[0][0],mouseClick[1][0]),
                              min(mouseClick[0][1],mouseClick[1][1]),
                              max(mouseClick[1][0],mouseClick[0][0]),
                              max(mouseClick[1][1],mouseClick[0][1])))
    im.save("cutScreen.png")
    return im

def OCRcutScreen(image):
    global mainWin
    recognized_text = pytesseract.image_to_string(image)
    # print(recognized_text)
    return recognized_text

def refreshAnsRank(OCRtext):
    global matchQuestion
    with open(questionsFile,'r',encoding='utf-8') as questionFile:
        questionData = json.load(questionFile)
    matchQuestion = {"len":0,"question":"", "answer":"","options":[],"text":""}
    for questionOne in questionData:
        lenOfLCS = LCSlen_old(questionOne["text"], OCRtext)
        if lenOfLCS > matchQuestion["len"]:
            matchQuestion = questionOne
            matchQuestion["len"] = lenOfLCS

def refreshAnsRank_v2(OCRtext):
    global matchQuestion,matchOriginTextList
    with open(questionsFile,'r',encoding='utf-8') as questionFile:
        questionData = json.load(questionFile)
    matchOriginTextList.clear()
    for questionOne in questionData:
        matchOriginTextList.append(questionOne["text"])
    matches = difflib.get_close_matches(OCRtext, matchOriginTextList, n=1, cutoff=0.1)
    matchQuestion = {"len":0,"question":"", "answer":"No Match","options":[],"text":""}
    if not matches:
        return
    for i in range(len(questionData)):
        if matches[0] == questionData[i]["text"]:
            matchQuestion = questionData[i]
            break
    matchQuestion["len"] = len(matches[0])

def selectClick(x1, y1, button, pressed):
    try:
        global mouseListening
        if not mouseListening:
            return
        if pressed:
            mouseClick[0][0] = x1
            mouseClick[0][1] = y1
            # print("Mouse clicked at ({0}, {1}) with {2} button".format(x1, y1, button))
            return
        mouseClick[1][0] = x1
        mouseClick[1][1] = y1
        # print("Mouse released at ({0}, {1}) with {2} button".format(x1, y1, button))
        mouseListening = False
        print(mouseClick)
        # 创建事件处理线程
        global mainWin
        mainWin.stageLabel.setText("Loading")
        OCRScreenThread = threading.Thread(target=showAns, args=(mainWin,))
        OCRScreenThread.start()
    except:
        pass

def selectArea():
    global mouseListening,selectedAreaInFirst
    if not mouseListening:
        return
    if selectedAreaInFirst:
        mouseClick[0][0],mouseClick[0][1] = pyautogui.position()
        selectedAreaInFirst = False
        print("Mouse clicked at ({0}, {1}) with {2} button".format(mouseClick[0][0], mouseClick[0][1], "left"))
        return
    mouseClick[1][0],mouseClick[1][1] = pyautogui.position()
    print("Mouse released at ({0}, {1}) with {2} button".format(mouseClick[1][0], mouseClick[1][1], "left"))
    '''是否连续截取 是（注释） 否（取消注释）'''
    # mouseListening = False    #是否连续截取
    selectedAreaInFirst = True
    print(mouseClick)
    # 创建事件处理线程
    global mainWin
    mainWin.stageLabel.setText("Loading...Cut")
    OCRScreenThread = threading.Thread(target=showAns, args=(mainWin,))
    OCRScreenThread.start()

def testKeyboardPress()->bool:
    global mouseListening,mainWin,keyboardRecording
    if(keyboardRecording == ['Z','Z','X']):
        mouseListening = True
        print("Mouse listening start")
        mainWin.stageLabel.setText("Select")
    elif(keyboardRecording == ['Z','Z','C']):
        mouseListening = False
        mainWin.stageLabel.setText("Cancel")
    elif(keyboardRecording == ['Z','Z','Z']):
        print("top the window")
        mainWin.show()
        mainWin.raise_()
        # mainWin.activateWindow()
        mainWin.setFocus()
    elif(keyboardRecording == ['A','A','A']):
        print("refresh the ans")
        mouseListening = False
        mainWin.stageLabel.setText("Refreshing")
        showAns(mainWin)
    elif(keyboardRecording == ['X','X','A']):
        print("create a new window")
        # createMaskWindowThread = threading.Thread(target=createMaskWindow_bottom)
        # createMaskWindowThread.start()
    elif(keyboardRecording == ['X','X','B']):
        mainWin.resize(400, 500)
        print("resize the window(Big)")
    elif(keyboardRecording == ['X','X','S']):
        mainWin.resize(400, 40)
        print("resize the window(Small)")
    elif(keyboardRecording == ['X','X','D']):
        mainWin.resize(400, 100)
        print("resize the window(Default)")
    elif(keyboardRecording == ['S','S','D']):
        print("show the duck")
        for i in range(len(windowList_Mask)):
            windowList_Mask[i].setStyleSheet(f"background-color: {windowList_Style_Duck[i]['color']};")
    elif(keyboardRecording == ['S','S','S']):
        print("show the style")
        for i in range(len(windowList_Mask)):
            windowList_Mask[i].setStyleSheet(f"background-color: {windowInf_Mask[i]['color']};")
    elif(keyboardRecording == ['H','I','D']):
        print("hide the window")
        # mainWin.hide()
        for i in range(len(windowList_Mask)):
            windowList_Mask[i].hide()
    elif(keyboardRecording == ['S','H','O']):
        print("show the window")
        # mainWin.show()
        for i in range(len(windowList_Mask)):
            windowList_Mask[i].show()
    elif(keyboardRecording == ['S','S','H']):
        print("show/hide the mainWindow")
        if mainWin.isHidden():
            mainWin.show()
        else:
            mainWin.hide()
    elif(keyboardRecording == ['H','I','B']):
        print("hide the bottom window")
        windowList_Mask[0].hide()
    elif(keyboardRecording == ['S','H','B']):
        print("show the bottom window")
        windowList_Mask[0].show()
    else:
        return False
    return True

def recordKeyboard(key):
    try:
        if not key.char in allowKey:
            return
        if mouseListening and key.char.upper() == 'A':
            selectArea()
            return
        keyboardRecording.append(key.char)
        if len(keyboardRecording) > 3:
            keyboardRecording.pop(0)
        #小写转大写
        for i in range(len(keyboardRecording)):
            if keyboardRecording[i].islower():
                keyboardRecording[i] = keyboardRecording[i].upper()
        mainWin.clickRecord.setText(str(keyboardRecording))
        if testKeyboardPress():
            keyboardRecording.clear()
    except AttributeError:
        pass

def startKeyboardListen():
    with keyboard.Listener(
            on_press=recordKeyboard,
    ) as listener:
        listener.join()

def startMouseListen():
    with mouse.Listener(
            on_click=selectClick
    )as listener:
        listener.join()

def startThread():
    KeyboardListenerThread = threading.Thread(target=startKeyboardListen)
    KeyboardListenerThread.start()
    # MainWindowThread = threading.Thread(target=startWindow_Mask)
    # MainWindowThread.start()
    # MouseListenerThread = threading.Thread(target=startMouseListen)
    # MouseListenerThread.start()

def startWindow():
    global mainWin
    app = QApplication(sys.argv)
    mainWin = FramelessMainWindow()
    mainWin.show()
    startWindow_Mask()
    # sleep(3)
    sys.exit(app.exec_())

def startWindow_Mask():
    global windowList_Mask,windowInf_Mask
    for i in range(len(windowInf_Mask)):
        windowList_Mask.append(MaskWindow(windowInf_Mask[i]))
        windowList_Mask[i].show()

def createMaskWindow_bottom():
    app = QApplication(sys.argv)
    newWin = MaskWindow(windowInf_Mask[0])
    newWin.show()
    app.exec_()

if __name__ == '__main__':
    startThread()
    startWindow()