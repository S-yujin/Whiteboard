import sys
import socket
import threading
import json
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

class WhiteboardClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.nickname, _ = QInputDialog.getText(self, "닉네임 설정", "사용할 닉네임을 입력하세요:")
        if not self.nickname: self.nickname = "Anonymous"

        self.initUI()
        self.initNetwork()
        
        # 드로잉 변수
        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(Qt.black)
        self.pen_width = 3
        self.is_eraser = False

    def initUI(self):
        self.setWindowTitle(f"공유 화이트보드 - {self.nickname}")
        self.setGeometry(100, 100, 1000, 700)

        # 메인 레이아웃
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 왼쪽: 캔버스
        self.canvas = QLabel()
        canvas_pixmap = QPixmap(700, 600)
        canvas_pixmap.fill(Qt.white)
        self.canvas.setPixmap(canvas_pixmap)
        main_layout.addWidget(self.canvas, 7)

        #닉네임 표시 전용 플로팅 레이블
        self.nick_label =  QLabel(self)
        self.nick_label.setStyleSheet("background-color: rgba(255, 255, 255, 200); border: 1px solid black;")
        self.nick_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.nick_label.hide()


        # 오른쪽: 컨트롤 패널
        control_panel = QVBoxLayout()
        
        # 1. 색상/굵기 조절
        btn_color = QPushButton("색상 선택")
        btn_color.clicked.connect(self.change_color)
        control_panel.addWidget(btn_color)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 20)
        self.slider.setValue(3)
        control_panel.addWidget(QLabel("선 굵기"))
        control_panel.addWidget(self.slider)

        # 2. 기능 버튼 (선택 사항 포함)
        btn_eraser = QPushButton("지우개 모드")
        btn_eraser.setCheckable(True)
        btn_eraser.clicked.connect(self.toggle_eraser)
        control_panel.addWidget(btn_eraser)

        btn_clear = QPushButton("전체 화면 초기화(Clear)")
        btn_clear.clicked.connect(self.send_clear_command)
        control_panel.addWidget(btn_clear)

        btn_save = QPushButton("이미지 저장(PNG)")
        btn_save.clicked.connect(self.save_image)
        control_panel.addWidget(btn_save)

        # 3. 채팅창
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        control_panel.addWidget(self.chat_area)

        self.chat_input = QLineEdit()
        self.chat_input.returnPressed.connect(self.send_chat)
        control_panel.addWidget(self.chat_input)

        main_layout.addLayout(control_panel, 3)

    def initNetwork(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client.connect(('127.0.0.1', 5000))
            threading.Thread(target=self.receive_data, daemon=True).start()
        except:
            QMessageBox.critical(self, "오류", "서버에 연결할 수 없습니다.")
            sys.exit()

    # --- 네트워크 수신 처리 ---
    def receive_data(self):
        while True:
            try:
                msg = self.client.recv(4096).decode('utf-8')
                if not msg: break
                data = json.loads(msg)
                
                if data['type'] == 'draw':
                    self.draw_on_canvas(data)
                elif data['type'] == 'label':
                    self.fix_nickname_on_canvas(data)
                elif data['type'] == 'chat':
                    self.chat_area.append(f"<b>{data['nick']}:</b> {data['msg']}")
                elif data['type'] == 'clear':
                    self.clear_canvas()
            except: break
            
    def fix_nickname_on_canvas(self, data):
        # 캔버스(Pixmap)에 닉네임을 영구적으로 그립니다.
        painter = QPainter(self.canvas.pixmap())
        painter.setPen(QColor("gray")) # 과거 기록은 약간 연한 색이 보기 좋습니다.
        painter.setFont(QFont("Arial", 9))
        painter.drawText(data['pos'][0] + 5, data['pos'][1] - 5, data['nick'])
        painter.end()
        self.update()

    # --- 드로잉 로직 ---
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = e.pos() - self.canvas.pos()

    def mouseMoveEvent(self, e):
        if (e.buttons() & Qt.LeftButton) and self.drawing:
            current_point = e.pos() - self.canvas.pos()
            color = "#FFFFFF" if self.is_eraser else self.pen_color.name()
            
            data = {
                "type": "draw",
                "nick": self.nickname,
                "start": [self.last_point.x(), self.last_point.y()],
                "end": [current_point.x(), current_point.y()],
                "color": color,
                "width": self.slider.value()
            }
            self.client.send(json.dumps(data).encode('utf-8'))
            self.last_point = current_point

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drawing = False

            final_pos = e.pos() - self.canvas.pos()
            data = {
                "type": "label",
                "nick": self.nickname,
                "pos": [final_pos.x(), final_pos.y()]
            }
            self.client.send(json.dumps(data).encode('utf-8'))

    def draw_on_canvas(self, data):
        painter = QPainter(self.canvas.pixmap())
        
        # 펜 설정
        pen = QPen(QColor(data['color']), data['width'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(data['start'][0], data['start'][1], data['end'][0], data['end'][1])

        painter.end()

        # 실시간 위치 정보는 현재 펜 끝을 보여주기 위해 유지
        self.last_user_pos = {'nick': data['nick'], 'pos': QPoint(data['end'][0], data['end'][1])}
        self.update()
    
    def paintEvent(self, event):
        # 1. 기본 배경 위젯들을 먼저 그린다.
        super().paintEvent(event)
        
        # 2. 닉네임 정보가 있을 때만 실행
        if hasattr(self, 'last_user_pos'):
            # 중요: 보드(QLabel) 위에서도 글자가 보이도록 QPainter를 창 전체에 띄우기.
            painter = QPainter(self)
            
            # 3. 닉네임 스타일 (눈에 확 띄는 색상과 굵기)
            painter.setPen(QPen(QColor("#FF0000"), 2)) # 빨간색으로 변경해서 테스트
            painter.setFont(QFont("Arial", 11, QFont.Bold))
            
            # 4. 캔버스의 현재 위치를 실시간으로 계산
            # 레이아웃 때문에 캔버스 위치가 변해도 정확히 따라가기
            canvas_rect = self.canvas.geometry()
            
            # 캔버스 절대 좌표 + 마우스 상대 좌표
            target_x = canvas_rect.x() + self.last_user_pos['pos'].x()
            target_y = canvas_rect.y() + self.last_user_pos['pos'].y()

            # 5. 닉네임 그리기 (캔버스 영역 안쪽인지 확인 후 그리기)
            # 텍스트가 캔버스 영역보다 위에 그려지도록 강제
            painter.drawText(target_x + 10, target_y - 10, self.last_user_pos['nick'])
            
            painter.end()

    # --- 기능 함수들 ---
    def change_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.pen_color = color
            self.is_eraser = False

    def toggle_eraser(self, checked):
        self.is_eraser = checked

    def send_chat(self):
        msg = self.chat_input.text()
        if msg:
            data = {"type": "chat", "nick": self.nickname, "msg": msg}
            self.client.send(json.dumps(data).encode('utf-8'))
            self.chat_input.clear()

    def send_clear_command(self):
        data = {"type": "clear"}
        self.client.send(json.dumps(data).encode('utf-8'))

    def clear_canvas(self):
        self.canvas.pixmap().fill(Qt.white)
        self.update()

    def save_image(self):
        path, _ = QFileDialog.getSaveFileName(self, "저장", "", "PNG Files (*.png)")
        if path:
            self.canvas.pixmap().save(path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WhiteboardClient()
    window.show()
    sys.exit(app.exec_())