import json
import os
import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

isAlone = False


class PacknloadEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("./icon.ico"))
        self.current_file = None
        self.is_modified = False
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
        self.pack_name_input.textChanged.connect(self.mark_modified)
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
        self.author_input.textChanged.connect(self.mark_modified)
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
        self.version_input.textChanged.connect(self.mark_modified)
        version_layout.addWidget(self.version_input)
        container_layout.addWidget(version_group)

        # 模组列表
        mods_group = QGroupBox("模组")
        mods_group.setObjectName("modsGroup")
        mods_layout = QVBoxLayout(mods_group)

        # 创建 QListWidget 并设置属性
        self.mods_list = QListWidget()
        self.mods_list.setObjectName("modsList")
        self.mods_list.setMinimumHeight(200)
        self.mods_list.setMaximumHeight(200)
        self.mods_list.setIconSize(QSize(16, 16))

        # 添加初始的加号按钮
        self.add_add_button()

        mods_layout.addWidget(self.mods_list)
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

    def mark_modified(self):
        """标记文件已被修改"""
        self.is_modified = True
        if self.current_file:
            self.setWindowTitle(
                f"Packnload Editor - {os.path.basename(self.current_file)}*"
            )
        else:
            self.setWindowTitle("Packnload Editor*")

    def clear_modified(self):
        """清除修改标记"""
        self.is_modified = False
        if self.current_file:
            self.setWindowTitle(
                f"Packnload Editor - {os.path.basename(self.current_file)}"
            )
        else:
            self.setWindowTitle("Packnload Editor")

    def add_add_button(self):
        """添加加号按钮到列表末尾（使用自定义widget）"""
        # 先移除旧的加号按钮
        for i in range(self.mods_list.count()):
            item = self.mods_list.item(i)
            if item and item.data(Qt.UserRole) == "add_button":
                self.mods_list.takeItem(i)
                break

        # 创建加号按钮的widget
        add_widget = QWidget()
        add_layout = QHBoxLayout(add_widget)
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.setAlignment(Qt.AlignCenter)

        add_btn = QPushButton("+ 添加模组")
        add_btn.setObjectName("addModButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setMinimumHeight(64)
        add_btn.clicked.connect(self.on_add_button_clicked)

        add_layout.addWidget(add_btn)

        # 创建列表项
        add_item = QListWidgetItem()
        add_item.setData(Qt.UserRole, "add_button")
        add_item.setSizeHint(add_widget.sizeHint())

        self.mods_list.addItem(add_item)
        self.mods_list.setItemWidget(add_item, add_widget)

    def create_mod_item(self, text=""):
        """创建一个模组条目（包含减号按钮和输入框）"""
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(5, 5, 5, 5)
        item_layout.setSpacing(8)

        # 减号按钮
        delete_btn = QPushButton("−")
        delete_btn.setFixedSize(40, 40)
        delete_btn.setObjectName("deleteButton")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.delete_mod_item(item_widget))

        # 输入框
        input_field = QLineEdit()
        input_field.setText(text)
        input_field.setObjectName("modInput")
        input_field.setPlaceholderText("输入 Modrinth Slug")
        input_field.textChanged.connect(self.mark_modified)
        input_field.setMinimumWidth(200)
        input_field.setFixedHeight(40)

        item_layout.addWidget(delete_btn)
        item_layout.addWidget(input_field)

        return item_widget

    def delete_mod_item(self, widget):
        """删除指定的模组条目"""
        for i in range(self.mods_list.count()):
            item = self.mods_list.item(i)
            if item and self.mods_list.itemWidget(item) == widget:
                if item.data(Qt.UserRole) == "add_button":
                    return
                self.mods_list.takeItem(i)
                self.mark_modified()
                break

    def ensure_add_button_last(self):
        """确保加号按钮在列表最后"""
        add_index = -1
        for i in range(self.mods_list.count()):
            item = self.mods_list.item(i)
            if item and item.data(Qt.UserRole) == "add_button":
                add_index = i
                break

        if add_index >= 0 and add_index < self.mods_list.count() - 1:
            item = self.mods_list.takeItem(add_index)
            self.mods_list.addItem(item)
        elif add_index == -1:
            self.add_add_button()

    def on_add_button_clicked(self):
        """点击加号按钮时添加新条目"""
        # 找到加号按钮的位置
        add_index = -1
        for i in range(self.mods_list.count()):
            item = self.mods_list.item(i)
            if item and item.data(Qt.UserRole) == "add_button":
                add_index = i
                break

        if add_index == -1:
            return

        # 创建新条目
        new_item = QListWidgetItem()
        new_item.setData(Qt.UserRole, "mod_item")
        new_widget = self.create_mod_item("")
        new_item.setSizeHint(QSize(new_widget.sizeHint().width(), 55))

        # 插入到加号按钮前
        self.mods_list.insertItem(add_index, new_item)
        self.mods_list.setItemWidget(new_item, new_widget)

        self.mark_modified()

        # 聚焦到新添加的输入框
        input_field = new_widget.findChild(QLineEdit)
        if input_field:
            input_field.setFocus()

    def setup_theme(self):
        """设置主题 - 让Qt自动管理"""
        self.setAttribute(Qt.WA_StyledBackground, True)

    def on_palette_changed(self, palette):
        """系统主题变化时的处理"""
        self.apply_stylesheet()
        if hasattr(self, "about_label"):
            self.about_label.update_style()

    def apply_stylesheet(self):
        """应用样式表 - 基于系统主题"""
        palette = self.palette()
        is_dark = palette.color(QPalette.Window).lightness() < 128

        if is_dark:
            stylesheet = f"""
                QWidget#container {{
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
                
                QPushButton#deleteButton {{
                    background-color: #c0392b;
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 0px;
                    min-height: 0px;
                    border-radius: 6px;
                }}
                
                QPushButton#deleteButton:hover {{
                    background-color: #e74c3c;
                }}
                
                QPushButton#addModButton {{
                    background-color: #27ae60;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 6px 20px;
                    border: 2px solid #2ecc71;
                    border-radius: 8px;
                    min-height: 28px;
                }}
                
                QPushButton#addModButton:hover {{
                    background-color: #2ecc71;
                    border-color: #27ae60;
                }}
                
                QLabel#fileInfo {{
                    background-color: rgba(255, 255, 255, 0.08);
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #2980b9;
                    font-size: 14px;
                }}
                
                QGroupBox {{
                    font-size: 16px;
                    font-weight: bold;
                    border: 1px dashed #555555;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                }}
                
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }}

                QLineEdit, QTextEdit {{
                    padding: 8px 15px;
                    border: 1px solid #444444;
                    border-radius: 8px;
                    font-size: 14px;
                    selection-background-color: #2980b9;
                    line-height: 1.5;
                }}
                
                QLineEdit:focus, QTextEdit:focus {{
                    border-color: #2980b9;
                }}
                
                QTextEdit {{
                    font-family: monospace;
                }}

                QListWidget {{
                    border: 1px solid #444444;
                    border-radius: 8px;
                    padding: 5px;
                    outline: none;
                }}
                
                QListWidget::item {{
                    padding: 2px 0px;
                    border: none;
                }}
                
                QListWidget::item:selected {{
                    background-color: transparent;
                }}
                
                QListWidget::item:hover {{
                    background-color: transparent;
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

                QMessageBox QPushButton {{
                    background-color: #27ae60;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 20px;
                    min-width: 80px;
                    min-height: 30px;
                }}
                
                QMessageBox QPushButton:hover {{
                    background-color: #1e8449;
                }}
            """
        else:
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
                
                QPushButton#deleteButton {
                    background-color: #e74c3c;
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 0px;
                    min-height: 0px;
                    border-radius: 6px;
                }
                
                QPushButton#deleteButton:hover {
                    background-color: #c0392b;
                }
                
                QPushButton#addModButton {
                    background-color: #27ae60;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 6px 20px;
                    border: 2px solid #2ecc71;
                    border-radius: 8px;
                    min-height: 28px;
                }
                
                QPushButton#addModButton:hover {
                    background-color: #2ecc71;
                    border-color: #27ae60;
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
                    padding: 8px 15px;
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

                QListWidget {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #dce4ec;
                    border-radius: 8px;
                    padding: 5px;
                    outline: none;
                }
                
                QListWidget::item {
                    padding: 2px 0px;
                    border: none;
                }
                
                QListWidget::item:selected {
                    background-color: transparent;
                    color: #333333;
                }
                
                QListWidget::item:hover {
                    background-color: transparent;
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

                QMessageBox QPushButton {
                    background-color: #27ae60;
                    color: white;
                    border-radius: 8px;
                    padding: 8px 20px;
                    min-width: 80px;
                    min-height: 30px;
                }
                
                QMessageBox QPushButton:hover {
                    background-color: #1e8449;
                }
            """

        self.setStyleSheet(stylesheet)

    def open_file(self, fp=None):
        """打开文件"""
        if self.is_modified:
            reply = QMessageBox.question(
                self,
                "未保存的更改",
                "当前文件有未保存的更改，是否继续？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        if fp:
            file_path = fp
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择 ModPack",
                "",
                "ModPack Files (*.modpack *.json);;All Files (*)",
            )

        if not file_path:
            return

        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in [".json", ".modpack"]:
                QMessageBox.critical(self, "错误", "此文件不是 JSON 或 .modpack 文件")
                return

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                json_data = json.loads(content)
            except json.JSONDecodeError:
                QMessageBox.critical(self, "错误", "此文件不是有效的 JSON 格式")
                return

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

            try:
                self.pack_name_input.setText(str(json_data.get("name", "")))
                self.author_input.setText(str(json_data.get("author", "")))
                self.version_input.setText(str(json_data.get("version", "")))

                self.clear_mod_list()
                self.add_add_button()

                mod_list = json_data.get("mod_list", [])
                if isinstance(mod_list, list):
                    for mod in mod_list:
                        if isinstance(mod, list):
                            self.add_mod_item(", ".join([i.strip() for i in mod]))
                        else:
                            self.add_mod_item(str(mod).strip())

                self.current_file = file_path
                self.file_info.setText(f"当前打开文件: {os.path.basename(file_path)}")
                self.file_info.show()
                self.save_as_btn.show()
                self.clear_modified()

            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取文件内容时出错: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件时出错: {str(e)}")

    def clear_mod_list(self):
        """清空模组列表（保留加号按钮）"""
        items_to_remove = []
        for i in range(self.mods_list.count()):
            item = self.mods_list.item(i)
            if item and item.data(Qt.UserRole) != "add_button":
                items_to_remove.append(i)

        for i in reversed(items_to_remove):
            self.mods_list.takeItem(i)

    def add_mod_item(self, text=""):
        """添加一个模组条目（在加号按钮前插入）"""
        add_index = -1
        for i in range(self.mods_list.count()):
            item = self.mods_list.item(i)
            if item and item.data(Qt.UserRole) == "add_button":
                add_index = i
                break

        new_item = QListWidgetItem()
        new_item.setData(Qt.UserRole, "mod_item")
        new_widget = self.create_mod_item(text)
        new_item.setSizeHint(QSize(new_widget.sizeHint().width(), 55))

        if add_index >= 0:
            self.mods_list.insertItem(add_index, new_item)
        else:
            self.mods_list.addItem(new_item)
        self.mods_list.setItemWidget(new_item, new_widget)

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
        mod_list = []
        for i in range(self.mods_list.count()):
            item = self.mods_list.item(i)
            if item and item.data(Qt.UserRole) != "add_button":
                widget = self.mods_list.itemWidget(item)
                if widget:
                    input_field = widget.findChild(QLineEdit)
                    if input_field:
                        text = input_field.text().strip()
                        if text:
                            text_split = [i.strip() for i in text.split(",")]
                            if len(text_split) > 1:
                                mod_list.append(text_split)
                            else:
                                mod_list.append(text)

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
            try:
                with open(self.current_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.clear_modified()
                QMessageBox.information(self, "成功", "文件保存成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件时出错: {str(e)}")
        else:
            self.save_as_file()

    def save_as_file(self):
        """另存为文件"""
        if not self.validate_form_data():
            return

        data = self.collect_form_data()

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

            self.current_file = file_path
            self.file_info.setText(f"当前打开文件: {os.path.basename(file_path)}")
            self.file_info.show()
            self.save_as_btn.show()
            self.clear_modified()

            QMessageBox.information(
                self, "成功", f"文件已另存为: {os.path.basename(file_path)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"另存为文件时出错: {str(e)}")

    def closeEvent(self, event):
        """关闭事件 - 检查是否有未保存的修改"""
        if not event.spontaneous() and not isAlone and self.is_modified:
            reply = QMessageBox.question(
                self,
                "未保存的更改",
                "文件尚未保存，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )

            if reply == QMessageBox.Save:
                self.save_file()
                if self.is_modified:
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                event.ignore()

        if isAlone:
            event.accept()
        else:
            self.hide()
            event.ignore()  # 忽略真正的关闭，改为隐藏


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = PacknloadEditor()
    if len(sys.argv) > 1:
        fp = sys.argv[1]
        if os.path.exists(fp):
            window.open_file(fp)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    isAlone = True
    main()
