import json
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PacknloadEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("./icon.ico"))
        self.current_file = None
        self.init_ui()
        self.setup_theme()

    def init_ui(self):
        self.setWindowTitle("Packnload Editor")
        self.setMinimumSize(850, 750)

        # 创建中央部件和滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.NoFrame)

        central_widget = QWidget()
        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # 标题
        title_label = QLabel("Packnload Editor")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 关于链接
        self.about_label = QLabel()
        self.about_label.setOpenExternalLinks(True)
        self.about_label.setText(
            "<a href='https://www.yuque.com/qiufengqiufeng-qxav8/fgoums/okxkynz4oyx41kk6'>关于 Packnload</a>"
        )
        self.about_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.about_label.setFont(font)
        main_layout.addWidget(self.about_label)

        # 主容器
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(25)
        container_layout.setContentsMargins(35, 35, 35, 35)

        # 打开文件按钮
        self.open_file_btn = QPushButton("打开文件")
        self.open_file_btn.setObjectName("openFileButton")
        self.open_file_btn.clicked.connect(self.open_file)
        self.open_file_btn.setMinimumHeight(50)
        container_layout.addWidget(self.open_file_btn)

        # 文件信息
        self.file_info = QLabel("当前打开文件: 无")
        self.file_info.setObjectName("fileInfo")
        self.file_info.hide()
        container_layout.addWidget(self.file_info)

        # 模组包名
        pack_name_group = QGroupBox("模组包名")
        pack_name_group.setObjectName("packNameGroup")
        pack_name_layout = QVBoxLayout(pack_name_group)
        self.pack_name_input = QLineEdit()
        self.pack_name_input.setObjectName("packNameInput")
        self.pack_name_input.setPlaceholderText("输入模组包名称")
        self.pack_name_input.setMinimumHeight(45)
        pack_name_layout.addWidget(self.pack_name_input)
        container_layout.addWidget(pack_name_group)

        # 作者
        author_group = QGroupBox("作者")
        author_group.setObjectName("authorGroup")
        author_layout = QVBoxLayout(author_group)
        self.author_input = QLineEdit()
        self.author_input.setObjectName("authorInput")
        self.author_input.setPlaceholderText("输入作者名称")
        self.author_input.setMinimumHeight(45)
        author_layout.addWidget(self.author_input)
        container_layout.addWidget(author_group)

        # 版本
        version_group = QGroupBox("版本")
        version_group.setObjectName("versionGroup")
        version_layout = QVBoxLayout(version_group)
        self.version_input = QLineEdit()
        self.version_input.setObjectName("versionInput")
        self.version_input.setPlaceholderText("输入版本号")
        self.version_input.setMinimumHeight(45)
        version_layout.addWidget(self.version_input)
        container_layout.addWidget(version_group)

        # 模组列表
        mods_group = QGroupBox("模组")
        mods_group.setObjectName("modsGroup")
        mods_layout = QVBoxLayout(mods_group)
        self.mods_text = QTextEdit()
        self.mods_text.setObjectName("modsText")
        self.mods_text.setPlaceholderText(
            "每行输入一个 Modrinth Slug\n例如:\nmod1\nmod2\nmod3"
        )
        self.mods_text.setMinimumHeight(250)
        mods_layout.addWidget(self.mods_text)
        container_layout.addWidget(mods_group)

        # 按钮容器
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setSpacing(20)
        btn_layout.setContentsMargins(0, 10, 0, 0)

        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.clicked.connect(self.save_file)
        self.save_btn.setMinimumSize(120, 50)
        btn_layout.addWidget(self.save_btn)

        # 另存为按钮
        self.save_as_btn = QPushButton("另存为")
        self.save_as_btn.setObjectName("saveAsButton")
        self.save_as_btn.clicked.connect(self.save_as_file)
        self.save_as_btn.hide()
        self.save_as_btn.setMinimumSize(120, 50)
        btn_layout.addWidget(self.save_as_btn)

        btn_layout.addStretch()
        container_layout.addWidget(btn_container)

        # 设置容器样式
        container.setObjectName("container")
        main_layout.addWidget(container)

        # 应用样式
        self.apply_stylesheet()

        # 监听系统主题变化
        QApplication.instance().paletteChanged.connect(self.on_palette_changed)

    def setup_theme(self):
        """设置主题 - 让Qt自动管理"""
        # 不强制设置调色板，让Qt使用系统主题
        self.setAttribute(Qt.WA_StyledBackground, True)

    def on_palette_changed(self, palette):
        """系统主题变化时的处理"""
        self.apply_stylesheet()
        if hasattr(self, "about_label"):
            self.about_label.update_style()

    def apply_stylesheet(self):
        """应用样式表 - 基于系统主题"""
        # 获取当前系统调色板
        palette = self.palette()
        is_dark = palette.color(QPalette.Window).lightness() < 128

        if is_dark:
            # 暗色主题样式
            stylesheet = f"""
                QMainWindow {{
                    background-color: {palette.color(QPalette.Window).name()};
                }}
                
                QLabel {{
                    color: {palette.color(QPalette.WindowText).name()};
                }}
                
                QWidget#container {{
                    background-color: {palette.color(QPalette.Base).name()};
                    border-radius: 12px;
                }}
                
                QPushButton {{
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    font-weight: bold;
                    font-size: 14px;
                    min-height: 40px;
                }}
                
                QPushButton#openFileButton, QPushButton#saveButton {{
                    background-color: #2980b9;
                    color: white;
                }}
                
                QPushButton#openFileButton:hover, QPushButton#saveButton:hover {{
                    background-color: #1c6ea4;
                }}
                
                QPushButton#saveAsButton {{
                    background-color: #27ae60;
                    color: white;
                }}
                
                QPushButton#saveAsButton:hover {{
                    background-color: #1e8449;
                }}
                
                QLabel#fileInfo {{
                    background-color: {palette.color(QPalette.AlternateBase).name()};
                    color: {palette.color(QPalette.WindowText).name()};
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #2980b9;
                    font-size: 14px;
                }}
                
                QGroupBox {{
                    font-size: 16px;
                    font-weight: bold;
                    color: {palette.color(QPalette.WindowText).name()};
                    border: 1px dashed #555555;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                }}
                
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: {palette.color(QPalette.WindowText).name()};
                }}
                
                QLineEdit, QTextEdit {{
                    background-color: {palette.color(QPalette.Base).name()};
                    color: {palette.color(QPalette.Text).name()};
                    padding: 12px 15px;
                    border: 1px solid #444444;
                    border-radius: 8px;
                    font-size: 14px;
                    selection-background-color: #2980b9;
                }}
                
                QLineEdit:focus, QTextEdit:focus {{
                    border-color: #2980b9;
                }}
                
                QTextEdit {{
                    font-family: monospace;
                }}
                
                QScrollArea {{
                    border: none;
                    background-color: transparent;
                }}
                
                QScrollBar:vertical {{
                    background-color: #2d2d32;
                    width: 12px;
                    border-radius: 6px;
                }}
                
                QScrollBar::handle:vertical {{
                    background-color: #444444;
                    border-radius: 6px;
                    min-height: 20px;
                }}
                
                QScrollBar::handle:vertical:hover {{
                    background-color: #555555;
                }}
            """
        else:
            # 亮色主题样式 - 保持原始设计
            stylesheet = """
                QMainWindow {
                    background-color: #f5f7fa;
                }
                
                QLabel {
                    color: #333333;
                }
                
                QWidget#container {
                    background-color: white;
                    border-radius: 12px;
                    box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08);
                }
                
                QPushButton {
                    border: none;
                    border-radius: 8px;
                    padding: 12px 28px;
                    font-weight: 600;
                    font-size: 15px;
                    min-height: 50px;
                    min-width: 120px;
                }
                
                QPushButton#openFileButton, QPushButton#saveButton {
                    background-color: #3498db;
                    color: white;
                }
                
                QPushButton#openFileButton:hover, QPushButton#saveButton:hover {
                    background-color: #2980b9;
                }
                
                QPushButton#saveAsButton {
                    background-color: #2ecc71;
                    color: white;
                }
                
                QPushButton#saveAsButton:hover {
                    background-color: #27ae60;
                }
                
                QLabel#fileInfo {
                    background-color: #f8f9fa;
                    color: #2c3e50;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #3498db;
                    font-size: 14px;
                    font-weight: 500;
                }
                
                QGroupBox {
                    font-size: 16px;
                    font-weight: bold;
                    color: #3a506b;
                    border: 1px dashed #d8e2e9;
                    border-radius: 6px;
                    margin-top: 15px;
                    padding-top: 15px;
                }
                
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 8px 0 8px;
                    color: #3a506b;
                }
                
                QLineEdit, QTextEdit {
                    padding: 12px 18px;
                    border: 1px solid #dce4ec;
                    border-radius: 8px;
                    font-size: 14px;
                }
                
                QLineEdit:focus, QTextEdit:focus {
                    border-color: #3498db;
                    box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.2);
                }
                
                QTextEdit {
                    font-family: 'Consolas', 'Monaco', monospace;
                }
                
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                
                QScrollBar:vertical {
                    background-color: #f0f0f0;
                    width: 10px;
                    border-radius: 5px;
                }
                
                QScrollBar::handle:vertical {
                    background-color: #c0c0c0;
                    border-radius: 5px;
                    min-height: 20px;
                }
                
                QScrollBar::handle:vertical:hover {
                    background-color: #a0a0a0;
                }
            """

        self.setStyleSheet(stylesheet)

    def open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 ModPack", "", "ModPack Files (*.modpack *.json);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # 检查文件扩展名
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in [".json", ".modpack"]:
                QMessageBox.critical(self, "错误", "此文件不是 JSON 或 .modpack 文件")
                return

            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查文件是否为 JSON
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError:
                QMessageBox.critical(self, "错误", "此文件不是有效的 JSON 格式")
                return

            # 检查必需字段
            required_fields = ["name", "author", "version", "mod_list"]
            missing_fields = [
                field for field in required_fields if field not in json_data
            ]

            if missing_fields:
                QMessageBox.critical(
                    self,
                    "错误",
                    f'这不是一个标准的 ModPack,缺少字段: {", ".join(missing_fields)}',
                )
                return

            # 读取并填充数据
            try:
                # 模组包名
                self.pack_name_input.setText(str(json_data.get("name", "")))

                # 作者
                self.author_input.setText(str(json_data.get("author", "")))

                # 版本
                self.version_input.setText(str(json_data.get("version", "")))

                # 模组列表
                if isinstance(json_data.get("mod_list"), list):
                    self.mods_text.setPlainText("\n".join(json_data["mod_list"]))
                else:
                    self.mods_text.setPlainText("")

                # 更新当前文件信息
                self.current_file = file_path
                self.file_info.setText(f"当前打开文件: {os.path.basename(file_path)}")
                self.file_info.show()

                # 显示"另存为"按钮
                self.save_as_btn.show()

            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取文件内容时出错: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件时出错: {str(e)}")

    def validate_form_data(self):
        """验证表单数据"""
        if not self.pack_name_input.text().strip():
            QMessageBox.critical(self, "错误", "模组包名不能为空")
            return False

        if not self.author_input.text().strip():
            QMessageBox.critical(self, "错误", "作者不能为空")
            return False

        if not self.version_input.text().strip():
            QMessageBox.critical(self, "错误", "版本不能为空")
            return False

        return True

    def collect_form_data(self):
        """收集表单数据"""
        mods_text = self.mods_text.toPlainText().strip()
        mod_list = [mod.strip() for mod in mods_text.split("\n") if mod.strip()]

        return {
            "name": self.pack_name_input.text().strip(),
            "author": self.author_input.text().strip(),
            "version": self.version_input.text().strip(),
            "mod_list": mod_list,
        }

    def save_file(self):
        """保存文件"""
        if not self.validate_form_data():
            return

        data = self.collect_form_data()

        if self.current_file:
            # 覆盖保存当前文件
            try:
                with open(self.current_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "成功", "文件保存成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件时出错: {str(e)}")
        else:
            # 没有打开文件，走另存为逻辑
            self.save_as_file()

    def save_as_file(self):
        """另存为文件"""
        if not self.validate_form_data():
            return

        data = self.collect_form_data()

        # 生成默认文件名
        default_name = f"{data['name']}_{data['version']}.modpack"
        default_name = "".join(
            c if c.isalnum() or c in "._- " else "_" for c in default_name
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            default_name,
            "ModPack Files (*.modpack);;JSON Files (*.json);;All Files (*)",
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 更新当前文件信息
            self.current_file = file_path
            self.file_info.setText(f"当前打开文件: {os.path.basename(file_path)}")
            self.file_info.show()
            self.save_as_btn.show()

            QMessageBox.information(
                self, "成功", f"文件已另存为: {os.path.basename(file_path)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"另存为文件时出错: {str(e)}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置应用程序字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = PacknloadEditor()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
