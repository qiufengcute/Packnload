import json
import os
import shutil
import sys
import tempfile
import threading
import zipfile

import requests
from PacknloadEditor import PacknloadEditor
from PySide6.QtCore import (
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

APP_TITLE = "Packnload"
ICON_IMG = "icon.ico"
BASE_URL = "https://api.modrinth.com/v2"
UA = {"User-Agent": "Packnload/1.2 (+https://modrinth.com/)"}


# ---------- Modrinth API helpers ----------
def get_project_versions_filtered(modid: str, game_version: str, loader: str):
    """
    用 Modrinth API v2 获取指定项目的版本。
    GET /project/{id|slug}/version?loaders=["fabric"]&game_versions=["1.21.1"]
    返回版本数组，可能为空。
    """
    url = f"{BASE_URL}/project/{modid}/version"
    params = {
        "loaders": json.dumps([loader]),
        "game_versions": json.dumps([game_version]),
    }
    try:
        r = requests.get(url, params=params, headers=UA, timeout=30)
        if r.status_code != 200:
            return []
        return r.json() or []
    except Exception:
        return []


def pick_primary_file(files: list):
    """从文件列表里挑出一个下载文件，优先选择 primary=true 的"""
    if not files:
        return None
    for f in files:
        if f.get("primary"):
            return f
    return files[0]


def stream_download(url: str, dst_path: str, on_bytes=None, pause_event=None):
    """
    把远程文件流式下载到本地。
    on_bytes(inc_bytes, total_bytes or None) 用于进度回调。
    pause_event 可选；若提供，则在每个 chunk 写入前 wait()，用于"暂停/继续"。
    """
    with requests.get(url, stream=True, headers=UA, timeout=(10, 120)) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        with open(dst_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                if pause_event is not None:
                    pause_event.wait()
                f.write(chunk)
                if on_bytes:
                    on_bytes(len(chunk), total if total > 0 else None)


# ---------- Download Worker Thread ----------
class DownloadWorker(QThread):
    progress_updated = Signal(float)
    status_updated = Signal(str)
    download_finished = Signal(
        bool, list, str, str
    )  # success, fails, pack_name, pack_version
    log_updated = Signal(str)

    def __init__(self, modpack_path, game_version, loader, save_dir, zip_enabled):
        super().__init__()
        self.modpack_path = modpack_path
        self.game_version = game_version
        self.loader = loader
        self.save_dir = save_dir
        self.zip_enabled = zip_enabled

        self.cancel_flag = False
        self.pause_event = threading.Event()
        self.pause_event.set()

    def cancel(self):
        self.cancel_flag = True
        self.pause_event.set()

    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            return True  # paused
        else:
            self.pause_event.set()
            return False  # resumed

    def run(self):
        try:
            self._do_download()
        except Exception as e:
            self.status_updated.emit(f"错误: {str(e)}")
            self.download_finished.emit(False, [], "", "")

    def _do_download(self):
        modpack_path = self.modpack_path
        game_version = self.game_version
        loader = self.loader
        save_dir = self.save_dir
        pack_zip = self.zip_enabled

        # 基本校验
        if not os.path.isfile(modpack_path):
            self.status_updated.emit("错误: 请正确选择 .modpack 文件")
            self.download_finished.emit(False, [], "", "")
            return

        if not game_version:
            self.status_updated.emit("错误: 请输入游戏版本")
            self.download_finished.emit(False, [], "", "")
            return

        if loader not in {"fabric", "forge", "quilt", "neoforge"}:
            self.status_updated.emit("错误: 请选择有效的加载器")
            self.download_finished.emit(False, [], "", "")
            return

        if not os.path.isdir(save_dir):
            self.status_updated.emit("错误: 请选择有效的模组存储路径")
            self.download_finished.emit(False, [], "", "")
            return

        try:
            with open(modpack_path, "r", encoding="utf-8") as f:
                pack = json.load(f)
        except Exception:
            self.status_updated.emit("错误: 模组包格式错误！")
            self.download_finished.emit(False, [], "", "")
            return

        required = ["name", "author", "version", "mod_list"]
        if not all(k in pack for k in required) or not isinstance(
            pack.get("mod_list"), list
        ):
            self.status_updated.emit("错误: 模组包缺少必要字段或格式不正确！")
            self.download_finished.emit(False, [], "", "")
            return

        # 处理 mod_list，支持两种格式：
        # 1. 字符串列表: ["mod1", "mod2"]
        # 2. 嵌套列表: [["mod1", "mod2"], "mod3", ["mod4", "mod5"]]
        raw_mod_list = pack["mod_list"]
        mod_groups = []

        for item in raw_mod_list:
            if isinstance(item, list):
                # 如果是列表，过滤掉空字符串并去重
                group = [m.strip() for m in item if isinstance(m, str) and m.strip()]
                if group:
                    mod_groups.append(list(dict.fromkeys(group)))
            elif isinstance(item, str) and item.strip():
                # 如果是字符串，作为单个元素的组
                mod_groups.append([item.strip()])

        if not mod_groups:
            self.status_updated.emit("错误: 模组包的 mod_list 为空！")
            self.download_finished.emit(False, [], "", "")
            return

        total_mods = len(mod_groups)  # 注意：这里是组的数量，不是模组数量
        progress = 0.0
        self.progress_updated.emit(0.0)
        self.status_updated.emit("开始下载…")

        jartemp = tempfile.mkdtemp(prefix="packnload_")
        fails = []

        try:
            for idx, mod_group in enumerate(mod_groups, start=1):
                if self.cancel_flag:
                    self.status_updated.emit("已取消")
                    self.download_finished.emit(False, [], "", "")
                    return

                # 显示当前组信息
                group_display = ", ".join(mod_group)
                self.status_updated.emit(
                    f"[{idx}/{total_mods}] 解析组: {group_display} …"
                )

                # 尝试组内的每个模组，直到有一个成功
                success_mod = None
                failed_mods = []

                for modid in mod_group:
                    if self.cancel_flag:
                        self.status_updated.emit("已取消")
                        self.download_finished.emit(False, [], "", "")
                        return

                    self.status_updated.emit(f"[{idx}/{total_mods}] 尝试 {modid} …")

                    versions = get_project_versions_filtered(
                        modid, game_version, loader
                    )
                    if not versions:
                        failed_mods.append(modid)
                        continue

                    file_obj = None
                    for v in versions:
                        file_obj = pick_primary_file(v.get("files", []))
                        if file_obj:
                            break
                    if not file_obj or "url" not in file_obj:
                        failed_mods.append(modid)
                        continue

                    url = file_obj["url"]
                    filename = file_obj.get("filename") or url.split("/")[-1]
                    size_hint = int(file_obj.get("size") or 0)
                    dst_path = os.path.join(jartemp, filename)

                    self.status_updated.emit(f"[{idx}/{total_mods}] 下载 {modid} …")

                    base = (idx - 1) * (100.0 / total_mods)
                    weight = 100.0 / total_mods
                    downloaded = 0

                    def on_bytes(inc, total_or_none):
                        nonlocal downloaded, progress
                        downloaded += inc
                        total_bytes = size_hint or (total_or_none or 0)
                        if total_bytes > 0:
                            frac = min(downloaded / total_bytes, 1.0)
                            progress = base + frac * weight
                        else:
                            step = weight * (inc / 1_000_000)
                            progress = min(base + step, base + weight)
                        self.progress_updated.emit(progress)

                    try:
                        stream_download(
                            url,
                            dst_path,
                            on_bytes=on_bytes,
                            pause_event=self.pause_event,
                        )
                        # 下载成功
                        success_mod = modid
                        break
                    except Exception:
                        failed_mods.append(modid)
                        continue

                # 处理组的结果
                if success_mod is not None:
                    # 组内有成功的，忽略其他失败的
                    self._bump_progress(progress, idx, total_mods)
                else:
                    # 组内所有模组都失败了
                    fails.append(mod_group)  # 将整个组加入失败列表
                    self._bump_progress(progress, idx, total_mods)

                if self.cancel_flag:
                    self.status_updated.emit("已取消")
                    self.download_finished.emit(False, [], "", "")
                    return

            self.status_updated.emit("整理文件…")
            if pack_zip:
                zip_path = os.path.join(
                    save_dir, f"{pack['name']}-{pack['version']}.zip"
                )
                with zipfile.ZipFile(
                    zip_path, "w", compression=zipfile.ZIP_DEFLATED
                ) as z:
                    for file in os.listdir(jartemp):
                        z.write(os.path.join(jartemp, file), arcname=file)
            else:
                for file in os.listdir(jartemp):
                    shutil.copy2(os.path.join(jartemp, file), save_dir)

        finally:
            shutil.rmtree(jartemp, ignore_errors=True)

        self.progress_updated.emit(100.0)
        self.status_updated.emit("完成")

        if fails:
            self.download_finished.emit(
                True, fails, pack.get("name", ""), pack.get("version", "")
            )
        else:
            self.download_finished.emit(
                True, [], pack.get("name", ""), pack.get("version", "")
            )

    def _bump_progress(self, progress, i_done, total_mods):
        target = min(i_done * (100.0 / max(total_mods, 1)), 100.0)
        if target > progress:
            progress = target
            self.progress_updated.emit(progress)
        return progress


# ---------- Main Window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(820, 480)

        try:
            self.setWindowIcon(QIcon(ICON_IMG))
        except Exception:
            pass

        self.editor_window = None
        self.worker = None
        self.pack_data = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel(APP_TITLE)
        title_font = QFont("Segoe UI", 20, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # 打开 Editor
        open_editor_layout = QHBoxLayout()
        open_editor_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.open_editor_btn = QPushButton("打开 Editor")
        self.open_editor_btn.setMinimumWidth(150)
        self.open_editor_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        open_editor_layout.addWidget(self.open_editor_btn)
        main_layout.addLayout(open_editor_layout)

        # .modpack 路径选择
        modpack_layout = QHBoxLayout()
        modpack_layout.addWidget(QLabel(".modpack 文件路径:"))
        self.modpack_entry = QLineEdit()
        self.modpack_entry.setEnabled(False)
        modpack_layout.addWidget(self.modpack_entry, 1)
        self.modpack_btn = QPushButton("选择文件")
        modpack_layout.addWidget(self.modpack_btn)
        main_layout.addLayout(modpack_layout)

        # 信息展示
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        info_layout = QHBoxLayout(info_frame)

        self.name_label = QLabel("名称: -")
        info_layout.addWidget(self.name_label)
        info_layout.addStretch()

        self.author_label = QLabel("作者: -")
        info_layout.addWidget(self.author_label)
        info_layout.addStretch()

        self.version_label = QLabel("版本: -")
        info_layout.addWidget(self.version_label)
        info_layout.addStretch()

        self.view_list_btn = QPushButton("查看模组列表")
        self.view_list_btn.setEnabled(False)
        info_layout.addWidget(self.view_list_btn)

        main_layout.addWidget(info_frame)

        # 游戏版本
        game_version_layout = QHBoxLayout()
        game_version_layout.addWidget(QLabel("游戏版本:"))
        self.game_version_entry = QLineEdit()
        self.game_version_entry.setPlaceholderText("例如: 1.21.1")
        game_version_layout.addWidget(self.game_version_entry)
        main_layout.addLayout(game_version_layout)

        # 加载器选择
        loader_layout = QHBoxLayout()
        loader_layout.addWidget(QLabel("加载器:"))
        self.loader_combo = QComboBox()
        self.loader_combo.addItems(["fabric", "forge", "quilt", "neoforge"])
        loader_layout.addWidget(self.loader_combo)
        loader_layout.addStretch()
        main_layout.addLayout(loader_layout)

        # 模组存储路径
        save_dir_layout = QHBoxLayout()
        save_dir_layout.addWidget(QLabel("模组存储路径:"))
        self.save_dir_entry = QLineEdit()
        self.save_dir_entry.setEnabled(False)
        save_dir_layout.addWidget(self.save_dir_entry, 1)
        self.save_dir_btn = QPushButton("选择文件夹")
        save_dir_layout.addWidget(self.save_dir_btn)
        main_layout.addLayout(save_dir_layout)

        # ZIP 选项
        self.zip_checkbox = QCheckBox("是否打包 ZIP")
        main_layout.addWidget(self.zip_checkbox)

        # 控制按钮
        control_layout = QHBoxLayout()
        control_layout.addStretch()
        self.start_btn = QPushButton("开始下载")
        self.start_btn.setMinimumWidth(120)
        control_layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("取消下载")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMinimumWidth(120)
        control_layout.addWidget(self.cancel_btn)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # 状态栏
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #666;")
        main_layout.addWidget(self.status_label)

        # 开源仓库链接
        repo_link_layout = QHBoxLayout()
        repo_link_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.repo_link = QLabel(
            '<a href="https://github.com/qiufengcute/Packnload" style="color: #0366d6; text-decoration: none;">开源仓库</a>'
        )
        self.repo_link.setOpenExternalLinks(True)  # 允许点击打开外部链接
        self.repo_link.setStyleSheet("font-size: 12px; padding: 5px;")
        repo_link_layout.addWidget(self.repo_link)
        main_layout.addLayout(repo_link_layout)

    def _connect_signals(self):
        self.open_editor_btn.clicked.connect(self.open_editor)
        self.modpack_btn.clicked.connect(self.choose_modpack)
        self.save_dir_btn.clicked.connect(self.choose_save_dir)
        self.view_list_btn.clicked.connect(self.view_mod_list)
        self.start_btn.clicked.connect(self.start_or_pause)
        self.cancel_btn.clicked.connect(self.cancel_download)

    def open_editor(self):
        # 检查 Editor 窗口是否存在且可见
        if self.editor_window is None:
            # Editor 窗口不存在 -> 创建新的 Editor 窗口
            self.editor_window = PacknloadEditor()
            self.editor_window.show()
        elif self.editor_window.isVisible():
            # Editor 窗口存在且可见 -> 激活它
            self.editor_window.raise_()  # 置顶
            self.editor_window.activateWindow()  # 获取焦点
            # 如果窗口被最小化了，还原它
            if self.editor_window.isMinimized():
                self.editor_window.showNormal()
        else:
            # Editor 窗口隐藏了 -> 显示它
            self.editor_window.show()

    def choose_modpack(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 .modpack 文件",
            "",
            "Modpack files (*.modpack);;All files (*.*)",
        )
        if path:
            self.modpack_entry.setText(path)
            self.load_modpack_meta(path)

    def load_modpack_meta(self, path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                pack = json.load(f)
        except Exception:
            self.pack_data = None
            self.view_list_btn.setEnabled(False)
            self.name_label.setText("名称: -")
            self.author_label.setText("作者: -")
            self.version_label.setText("版本: -")
            QMessageBox.critical(self, "错误", "模组包格式错误！")
            return

        required = ["name", "author", "version", "mod_list"]
        if not all(k in pack for k in required) or not isinstance(
            pack.get("mod_list"), list
        ):
            self.pack_data = None
            self.view_list_btn.setEnabled(False)
            self.name_label.setText("名称: -")
            self.author_label.setText("作者: -")
            self.version_label.setText("版本: -")
            QMessageBox.critical(self, "错误", "模组包缺少必要字段或格式不正确！")
            return

        # 清理 mod_list，保留嵌套结构
        cleaned_mod_list = []
        for item in pack["mod_list"]:
            if isinstance(item, list):
                # 清理列表中的空字符串和空白
                cleaned_item = [
                    m.strip() for m in item if isinstance(m, str) and m.strip()
                ]
                if cleaned_item:
                    # 去重
                    cleaned_mod_list.append(list(dict.fromkeys(cleaned_item)))
            elif isinstance(item, str) and item.strip():
                cleaned_mod_list.append(item.strip())

        pack["mod_list"] = cleaned_mod_list

        self.pack_data = pack
        self.name_label.setText(f"名称: {pack['name']}")
        self.author_label.setText(f"作者: {pack['author']}")
        self.version_label.setText(f"版本: {pack['version']}")
        self.view_list_btn.setEnabled(True)

    def view_mod_list(self):
        if not self.pack_data:
            return

        dialog = QMainWindow(self)
        dialog.setWindowTitle("模组列表")
        dialog.setMinimumSize(420, 360)

        central = QWidget()
        dialog.setCentralWidget(central)
        layout = QVBoxLayout(central)

        list_widget = QListWidget()
        for modid in self.pack_data.get("mod_list", []):
            if isinstance(modid, list):
                # 如果是列表，显示为 mod1/mod2 格式
                display_text = "/".join(modid)
            else:
                # 如果是字符串，直接显示
                display_text = str(modid)
            list_widget.addItem(display_text)
        layout.addWidget(list_widget)

        dialog.show()

    def choose_save_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择存储路径")
        if path:
            self.save_dir_entry.setText(path)

    def start_or_pause(self):
        text = self.start_btn.text()
        if text == "开始下载":
            self.start_download()
        elif text == "暂停下载":
            if self.worker:
                is_paused = self.worker.toggle_pause()
                self.start_btn.setText("继续下载" if is_paused else "暂停下载")
                self.status_label.setText("已暂停" if is_paused else "继续下载…")
        elif text == "继续下载":
            if self.worker:
                is_paused = self.worker.toggle_pause()
                self.start_btn.setText("暂停下载")
                self.status_label.setText("继续下载…")

    def cancel_download(self):
        if self.worker and self.worker.isRunning():
            self.cancel_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            self.worker.cancel()
            self.status_label.setText("取消中…")

    def start_download(self):
        modpack_path = self.modpack_entry.text().strip()
        game_version = self.game_version_entry.text().strip()
        loader = self.loader_combo.currentText()
        save_dir = self.save_dir_entry.text().strip()
        zip_enabled = self.zip_checkbox.isChecked()

        # 基本校验
        if not os.path.isfile(modpack_path):
            QMessageBox.critical(self, "错误", "请正确选择 .modpack 文件")
            return
        if not game_version:
            QMessageBox.critical(self, "错误", "请输入游戏版本")
            return
        if not os.path.isdir(save_dir):
            QMessageBox.critical(self, "错误", "请选择有效的模组存储路径")
            return

        self.worker = DownloadWorker(
            modpack_path, game_version, loader, save_dir, zip_enabled
        )
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.status_updated.connect(self.update_status)
        self.worker.download_finished.connect(self.on_download_finished)

        self.start_btn.setText("暂停下载")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("开始下载…")

        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(int(value))

    def update_status(self, text):
        self.status_label.setText(text)

    def on_download_finished(self, success, fails, pack_name, pack_version):
        self.start_btn.setText("开始下载")
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if not success:
            return

        if fails:
            dialog = QMainWindow(self)
            dialog.setWindowTitle("下载失败模组列表")
            dialog.setMinimumSize(400, 300)

            central = QWidget()
            dialog.setCentralWidget(central)
            layout = QVBoxLayout(central)

            info_label = QLabel(f"成功下载!\n其中 {len(fails)} 个模组下载失败:")
            layout.addWidget(info_label)

            list_widget = QListWidget()
            for fail_group in fails:
                if isinstance(fail_group, list):
                    # 显示为 mod1/mod2 格式
                    display_text = "/".join(fail_group)
                else:
                    display_text = str(fail_group)
                list_widget.addItem(display_text)
            layout.addWidget(list_widget)

            dialog.show()
        else:
            QMessageBox.information(self, "完成", "成功下载!\n没有任何模组下载失败!")

    def closeEvent(self, event):
        if self.editor_window is not None:
            if self.editor_window.is_modified:
                self.editor_window.show()
            self.editor_window.close()

            # 检查 Editor 窗口是否还在显示（用户可能点击了Cancel）
            if self.editor_window.isVisible():
                # 用户取消了 Editor 窗口的关闭
                reply = QMessageBox.information(
                    self,
                    "操作取消",
                    "Editor 窗口的关闭操作被取消",
                    QMessageBox.StandardButton.Ok,
                )
                event.ignore()  # 取消A的关闭
                return

        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "确认退出",
                "下载正在进行中，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.cancel()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
