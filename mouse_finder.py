#!/usr/bin/env python3
"""
🖱️ Mouse Finder — 鼠标定位神器
三屏办公必备：右键快速双击，立即看到鼠标在哪！

触发规则：0.5 秒内连续右键 2 次（双击）
依赖：pip install pynput pyqt5
支持：Windows 10/11（主要），macOS，Linux
"""

import sys
import os
import time
import ctypes

if sys.platform == "win32":
    import winreg
else:
    winreg = None

from PyQt5.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore    import Qt, QTimer, QEvent, QObject
from PyQt5.QtGui     import QPainter, QColor, QPen, QBrush, QRadialGradient, QIcon, QPixmap
from pynput import mouse as pynput_mouse


# ═══════════════════════════════════════════════════════════════════
#  可调节参数
# ═══════════════════════════════════════════════════════════════════
DOUBLE_CLICK_WINDOW = 0.5    # 双击判定窗口（秒）
RIPPLE_RINGS        = 4      # 波纹圈数
RIPPLE_DURATION_MS  = 900    # 单圈动画时长（毫秒）
RIPPLE_MAX_RADIUS   = 320    # 最大波纹半径（像素）
CENTER_RADIUS       = 24     # 中心圆点半径
EFFECT_TOTAL_MS     = 2500   # 整体特效时长（毫秒）
REFRESH_FPS         = 60     # 渲染帧率
AUTOSTART_NAME      = "MouseFinder"

# 颜色 —— 红色系（醒目）
C_RING_1 = (220,  30,  30)
C_RING_2 = (255, 100,  60)
C_CENTER = (255,  60,  60)
C_GLOW   = (255,   0,   0)
C_CROSS  = (255, 200, 200)

# 覆盖窗口尺寸（只覆盖特效区域，不全屏，避免闪烁）
OVERLAY_SIZE = RIPPLE_MAX_RADIUS * 2 + 60   # 像素，正方形


def qc(rgb, a=255):
    return QColor(rgb[0], rgb[1], rgb[2], a)


# ═══════════════════════════════════════════════════════════════════
#  开机自启（仅 Windows）
# ═══════════════════════════════════════════════════════════════════
def _exe_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    return f'"{sys.executable}" "{os.path.abspath(__file__)}"'


def autostart_enabled():
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, AUTOSTART_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def autostart_set(enable: bool):
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if enable:
            winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, _exe_path())
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[autostart] {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
#  特效窗口
#  关键设计：
#    • 仅覆盖鼠标周围一块小区域（OVERLAY_SIZE × OVERLAY_SIZE）
#      → 不全屏，不抢焦点，不导致其他窗口闪烁/黑屏
#    • WA_ShowWithoutActivating  → 出现时不抢焦点
#    • WA_TransparentForMouseEvents → 鼠标事件完全穿透
#    • Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
#      → 无标题栏、置顶、不在任务栏出现
#    • 不使用 X11BypassWindowManagerHint（Windows 上会黑屏）
# ═══════════════════════════════════════════════════════════════════
class RippleOverlay(QWidget):

    def __init__(self, screen_cx: int, screen_cy: int):
        """
        screen_cx/cy：鼠标在屏幕坐标系中的绝对位置
        窗口以此为中心，大小为 OVERLAY_SIZE × OVERLAY_SIZE
        """
        super().__init__()
        self._t0 = time.perf_counter()

        half = OVERLAY_SIZE // 2
        win_x = screen_cx - half
        win_y = screen_cy - half

        # 绘制坐标：鼠标在窗口内的相对位置（始终是中心）
        self.cx = half
        self.cy = half

        # ── 窗口属性 ────────────────────────────────────────────────
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)   # ★ 不抢焦点
        self.setWindowFlags(
            Qt.FramelessWindowHint      |
            Qt.WindowStaysOnTopHint     |
            Qt.Tool                     |
            Qt.WindowDoesNotAcceptFocus   # ★ 拒绝焦点，防止其他窗口失焦闪烁
        )

        # 窗口大小 & 位置：只覆盖特效区域
        self.setGeometry(win_x, win_y, OVERLAY_SIZE, OVERLAY_SIZE)

        # ── 渲染定时器 ──────────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000 // REFRESH_FPS)

        QTimer.singleShot(EFFECT_TOTAL_MS + 100, self._die)

        self.show()
        self.raise_()

    def _die(self):
        self._timer.stop()
        self.hide()
        self.deleteLater()

    def paintEvent(self, _):
        now_ms = (time.perf_counter() - self._t0) * 1000.0
        if now_ms > EFFECT_TOTAL_MS:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        fade = max(0.0, 1.0 - (now_ms / EFFECT_TOTAL_MS) ** 1.8)

        # ── 波纹圈 ──────────────────────────────────────────────────
        for i in range(RIPPLE_RINGS):
            delay = i * (RIPPLE_DURATION_MS / RIPPLE_RINGS * 0.9)
            t = now_ms - delay
            if t < 0:
                continue
            prog   = min(t / RIPPLE_DURATION_MS, 1.0)
            eased  = 1.0 - (1.0 - prog) ** 3
            radius = eased * RIPPLE_MAX_RADIUS

            if prog < 0.1:
                ring_a = prog / 0.1
            else:
                ring_a = (1.0 - prog) ** 0.8
            alpha = int(ring_a * fade * 230)
            if alpha <= 0:
                continue

            color = C_RING_1 if i % 2 == 0 else C_RING_2
            width = max(1.2, 4.0 * (1.0 - prog))
            p.setPen(QPen(qc(color, alpha), width))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(
                int(self.cx - radius), int(self.cy - radius),
                int(radius * 2),       int(radius * 2)
            )

        # ── 外层光晕 ────────────────────────────────────────────────
        glow_r = CENTER_RADIUS * 3.8
        gw_a   = int(fade * 150)
        grad = QRadialGradient(self.cx, self.cy, glow_r)
        grad.setColorAt(0.0, qc(C_GLOW, gw_a))
        grad.setColorAt(0.5, qc(C_GLOW, gw_a // 4))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        gr = int(glow_r)
        p.drawEllipse(self.cx - gr, self.cy - gr, gr * 2, gr * 2)

        # ── 中心实心点 ──────────────────────────────────────────────
        da = int(fade * 255)
        inner = QRadialGradient(self.cx, self.cy, CENTER_RADIUS)
        inner.setColorAt(0.0, qc((255, 255, 255), da))
        inner.setColorAt(0.4, qc(C_CENTER,         da))
        inner.setColorAt(1.0, qc(C_CENTER,          0))
        p.setBrush(QBrush(inner))
        r = CENTER_RADIUS
        p.drawEllipse(self.cx - r, self.cy - r, r * 2, r * 2)

        # ── 十字准星 ────────────────────────────────────────────────
        ca = int(fade * 200)
        p.setPen(QPen(qc(C_CROSS, ca), 1.5))
        arm, gap = 36, CENTER_RADIUS + 5
        p.drawLine(self.cx - arm, self.cy,   self.cx - gap, self.cy)
        p.drawLine(self.cx + gap, self.cy,   self.cx + arm, self.cy)
        p.drawLine(self.cx, self.cy - arm,   self.cx, self.cy - gap)
        p.drawLine(self.cx, self.cy + gap,   self.cx, self.cy + arm)

        p.end()


# ═══════════════════════════════════════════════════════════════════
#  跨线程通知
# ═══════════════════════════════════════════════════════════════════
_TRIGGER_TYPE = QEvent.Type(QEvent.registerEventType())

class _TriggerEvent(QEvent):
    def __init__(self, x: int, y: int):
        super().__init__(_TRIGGER_TYPE)
        self.mx = x
        self.my = y


# ═══════════════════════════════════════════════════════════════════
#  主控制器
# ═══════════════════════════════════════════════════════════════════
class MouseFinder(QObject):
    """
    纯监听，不拦截任何鼠标事件。
    0.5 秒内右键 2 次 → 触发定位动画。
    """

    def __init__(self, app: QApplication):
        super().__init__(app)
        self.app      = app
        self._enabled = True
        self._last_rclick = 0.0          # 上一次右键时间戳
        self._overlay: RippleOverlay | None = None
        self._listener: pynput_mouse.Listener | None = None
        self._build_tray()

    # ── 托盘 ────────────────────────────────────────────────────────
    def _make_icon(self, active=True):
        px = QPixmap(32, 32)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(qc(C_RING_1) if active else QColor(130, 130, 130)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.setBrush(QBrush(QColor(255, 255, 255) if active else QColor(190, 190, 190)))
        p.drawEllipse(11, 11, 10, 10)
        p.end()
        return QIcon(px)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self._make_icon(True), self.app)
        self._rebuild_menu()
        self.tray.setToolTip("🖱️ 鼠标定位神器\n右键快速双击 → 触发定位特效")
        self.tray.show()
        self.tray.showMessage(
            "🖱️ 鼠标定位神器已启动",
            "右键快速双击，即可定位鼠标位置！",
            QSystemTrayIcon.Information, 3500
        )

    def _rebuild_menu(self):
        menu = QMenu()

        s = QAction("✅ 定位功能：已开启" if self._enabled else "⛔ 定位功能：已关闭", menu)
        s.setEnabled(False)
        menu.addAction(s)

        t = QAction("右键双击（0.5秒内）触发定位", menu)
        t.setEnabled(False)
        menu.addAction(t)

        menu.addSeparator()

        tog = QAction("⛔  关闭定位功能" if self._enabled else "✅  开启定位功能", menu)
        tog.triggered.connect(self._toggle_enabled)
        menu.addAction(tog)

        if sys.platform == "win32":
            is_auto  = autostart_enabled()
            auto_act = QAction("🔁  取消开机自启" if is_auto else "🔁  开机自动启动", menu)
            auto_act.triggered.connect(self._toggle_autostart)
            menu.addAction(auto_act)

        menu.addSeparator()

        q = QAction("❌  退出程序", menu)
        q.triggered.connect(self._quit)
        menu.addAction(q)

        self.tray.setContextMenu(menu)

    def _toggle_enabled(self):
        self._enabled = not self._enabled
        self.tray.setIcon(self._make_icon(self._enabled))
        self._rebuild_menu()
        self.tray.showMessage("鼠标定位神器",
            "定位功能已开启" if self._enabled else "定位功能已关闭",
            QSystemTrayIcon.Information, 2000)

    def _toggle_autostart(self):
        cur = autostart_enabled()
        ok  = autostart_set(not cur)
        msg = ("已设为开机自启动" if not cur else "已取消开机自启动") if ok \
              else "操作失败，请以管理员权限运行"
        self.tray.showMessage("鼠标定位神器", msg,
                              QSystemTrayIcon.Information, 2500)
        self._rebuild_menu()

    # ── 监听 ────────────────────────────────────────────────────────
    def start(self):
        self._listener = pynput_mouse.Listener(on_click=self._on_click)
        self._listener.daemon = True
        self._listener.start()

    def _on_click(self, x, y, button, pressed):
        """后台线程回调，只读不拦截。"""
        if not self._enabled:
            return
        if button != pynput_mouse.Button.right or not pressed:
            return

        now = time.perf_counter()
        gap = now - self._last_rclick

        if 0 < gap <= DOUBLE_CLICK_WINDOW:
            # 双击成立，触发特效
            self._last_rclick = 0.0          # 防止第三次右键再次触发
            self.app.postEvent(self, _TriggerEvent(int(x), int(y)))
        else:
            self._last_rclick = now

    # ── 接收跨线程事件 ──────────────────────────────────────────────
    def event(self, e: QEvent) -> bool:
        if e.type() == _TRIGGER_TYPE:
            self._show_ripple(e.mx, e.my)
            return True
        return super().event(e)

    def _show_ripple(self, x: int, y: int):
        if self._overlay is not None:
            try:
                self._overlay._die()
            except Exception:
                pass
            self._overlay = None
        self._overlay = RippleOverlay(x, y)

    def _quit(self):
        if self._listener:
            self._listener.stop()
        self.app.quit()


# ═══════════════════════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════════════════════
def main():
    if sys.platform == "win32":
        # 隐藏 python.exe 弹出的黑色控制台
        try:
            ctypes.windll.user32.ShowWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except Exception:
            pass
        # 告诉 Windows 本进程支持高 DPI，避免坐标偏移
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    # Qt 高 DPI 支持（坐标和绘制都使用物理像素）
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,    True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    finder = MouseFinder(app)
    finder.start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
