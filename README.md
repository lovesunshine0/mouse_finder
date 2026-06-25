# 🖱️ Mouse Finder — 鼠标定位神器

> 三屏/多屏办公必备工具：**右键快速双击**，立即在鼠标位置触发醒目的彩色波纹特效，让你瞬间找到光标！

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## ✨ 功能特性

- **闪电定位**：0.5 秒内连续按下鼠标右键（双击），立即触发全屏定位特效。
- **视觉醒目**：多层彩色波纹扩散 + 十字准星 + 中心高亮光晕，在任意背景色下都清晰可见。
- **极致轻量**：窗口仅在鼠标位置覆盖一小块区域，不遮挡屏幕、不抢焦点、不导致其他窗口闪烁。
- **后台静默**：Windows 下运行无黑框（使用 `pythonw`），系统托盘常驻，随用随启。
- **跨平台支持**：Windows 10/11（主要）、macOS、Linux 均可运行。
- **开机自启**（Windows）：托盘菜单一键设置开机自动运行。

---

## 📦 安装依赖

本工具依赖 `pynput`（鼠标监听）和 `PyQt5`（特效渲染），请使用 pip 安装：

```bash
pip install pynput pyqt5
```

> 💡 如果遇到权限问题，可尝试 `pip install --user pynput pyqt5`。

---

## 🚀 使用方法

### 1. 直接运行源码

- **Windows（推荐，无黑框）**：
  ```bash
  pythonw mouse_finder.py
  ```
- **macOS / Linux**：
  ```bash
  python3 mouse_finder.py
  ```

运行后，系统托盘会出现一个红色圆形图标，表示工具已启动。

### 2. 触发定位特效

在任意位置 **快速双击鼠标右键**（0.5 秒内），鼠标光标处即会播放彩色波纹 + 准星特效，持续约 2.5 秒后自动消失。

### 3. 系统托盘菜单

右键单击托盘图标，可进行以下操作：

- ✅ 开启/关闭定位功能（无需退出程序）
- 🔁 设置或取消 Windows 开机自启
- ❌ 退出程序

---

## 📦 打包为独立可执行文件（可选）

如果你不想安装 Python 环境，可以使用 PyInstaller 打包成单个 `.exe` 文件。

1. 安装打包工具：
   ```bash
   pip install pyinstaller
   ```

2. 执行打包命令（Windows 推荐）：
   ```bash
   pyinstaller --onefile --noconsole --name MouseFinder mouse_finder.py
   ```

3. 打包完成后，在 `dist` 文件夹中找到 `MouseFinder.exe`，直接运行即可。

> 💡 若在 macOS/Linux 下打包，去掉 `--noconsole` 即可（或保留以隐藏终端）。

---

## ⚙️ 配置与自定义

你可以直接修改源码顶部的 **可调节参数** 区域，调整特效风格和触发灵敏度：

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `DOUBLE_CLICK_WINDOW` | `0.5` | 右键双击的判定时间窗口（秒） |
| `RIPPLE_RINGS` | `4` | 波纹圈数 |
| `RIPPLE_DURATION_MS` | `900` | 单圈动画时长（毫秒） |
| `RIPPLE_MAX_RADIUS` | `320` | 最大波纹半径（像素） |
| `CENTER_RADIUS` | `24` | 中心光晕半径 |
| `EFFECT_TOTAL_MS` | `2500` | 特效总时长（毫秒） |
| `C_RING_1` / `C_RING_2` | 红/橙 | 波纹颜色（RGB） |

修改后保存文件，重新运行即可生效。

---

## 🪟 开机自启（仅 Windows）

- 在系统托盘菜单中，点击 **“🔁 开机自动启动”** 即可开启。
- 再次点击可取消自启。
- 该功能通过写入 Windows 注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 实现，无需管理员权限。

---

## 📂 文件结构

```
mouse_finder.py    # 主程序源码（所有逻辑 + 特效）
README.md          # 本文档
dist/              # 打包后的可执行文件目录（由 PyInstaller 生成）
```

---

## 🧠 工作原理

1. **监听层**：使用 `pynput` 在后台线程监听全局鼠标右键事件，计算两次点击的时间差。
2. **判定层**：若时间差在 `DOUBLE_CLICK_WINDOW` 内，则判定为“双击”，触发信号。
3. **渲染层**：信号通过 Qt 事件传递至主线程，创建透明覆盖窗口，使用 `QPainter` 绘制多层波纹和准星。
4. **穿透设计**：覆盖窗口设置 `WA_TransparentForMouseEvents` 和 `WindowDoesNotAcceptFocus`，确保不干扰其他程序操作。

---

## 🤝 贡献与反馈

如果你有任何建议或发现 Bug，欢迎提交 Issue 或 Pull Request。

---

## 📄 许可证

本项目基于 **MIT 许可证** 开源，自由使用、修改和分发。
