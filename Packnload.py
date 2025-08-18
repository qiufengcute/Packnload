import json
import os
import shutil
import tempfile
import zipfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import requests

APP_TITLE = "Packnload"
ICON_IMG = "icon.ico"
BASE_URL = "https://api.modrinth.com/v2"
UA = {"User-Agent": "Packnload/1.0 (+https://modrinth.com/)"}


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


def stream_download(url: str, dst_path: str, on_bytes=None, pause_event: threading.Event | None = None):
    """
    把远程文件流式下载到本地。
    on_bytes(inc_bytes, total_bytes or None) 用于进度回调。
    pause_event 可选；若提供，则在每个 chunk 写入前 wait()，用于“暂停/继续”。
    """
    with requests.get(url, stream=True, headers=UA, timeout=(10, 120)) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        with open(dst_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                if pause_event is not None:
                    pause_event.wait()  # 暂停控制：暂停中会在此处卡住
                f.write(chunk)
                if on_bytes:
                    on_bytes(len(chunk), total if total > 0 else None)


# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        try:
            self.iconbitmap(ICON_IMG)
        except Exception:
            pass
        self.minsize(760, 420)
        self.grid_columnconfigure(1, weight=1)

        # 运行时状态
        self.pack_data = None   # 已解析的 .modpack
        self.total_mods = 0     # 总模组数
        self.progress = 0.0     # 总进度

        # 控制标志（新增）
        self.cancel_flag = False
        self.pause_event = threading.Event()
        self.pause_event.set()  # 初始允许下载

        # 保存按钮引用
        self.start_btn = None
        self.cancel_btn = None

        self._build_ui()

    def _build_ui(self):
        # 大标题
        title_lbl = ttk.Label(self, text=APP_TITLE, font=("Segoe UI", 20, "bold"))
        title_lbl.grid(row=0, column=0, columnspan=3, pady=(14, 10))

        # .modpack 路径选择
        ttk.Label(self, text=".modpack 文件路径:").grid(row=1, column=0, sticky="e", padx=12, pady=6)
        self.entry_modpack = ttk.Entry(self)
        self.entry_modpack.grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="选择文件", command=self.choose_modpack).grid(row=1, column=2, padx=12, pady=6)

        # 信息展示（名称/作者/版本）
        info = ttk.Frame(self)
        info.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 6))
        info.grid_columnconfigure(1, weight=1)

        ttk.Label(info, text="名称:").grid(row=0, column=0, sticky="e")
        self.lbl_name = ttk.Label(info, text="-")
        self.lbl_name.grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(info, text="作者:").grid(row=0, column=2, sticky="e", padx=(20, 0))
        self.lbl_author = ttk.Label(info, text="-")
        self.lbl_author.grid(row=0, column=3, sticky="w", padx=6)

        ttk.Label(info, text="版本:").grid(row=0, column=4, sticky="e", padx=(20, 0))
        self.lbl_version = ttk.Label(info, text="-")
        self.lbl_version.grid(row=0, column=5, sticky="w", padx=6)

        self.btn_view_list = ttk.Button(info, text="查看模组列表", command=self.view_mod_list, state="disabled")
        self.btn_view_list.grid(row=0, column=6, padx=(20, 0))

        # 游戏版本
        ttk.Label(self, text="游戏版本:").grid(row=3, column=0, sticky="e", padx=12, pady=6)
        self.entry_game_version = ttk.Entry(self)
        self.entry_game_version.grid(row=3, column=1, sticky="ew", padx=6, pady=6)

        # 加载器选择
        ttk.Label(self, text="加载器:").grid(row=4, column=0, sticky="e", padx=12, pady=6)
        self.loader_var = tk.StringVar()
        self.combo_loader = ttk.Combobox(
            self, textvariable=self.loader_var, state="readonly",
            values=["fabric", "forge", "quilt", "neoforge"], width=12
        )
        self.combo_loader.current(0)
        self.combo_loader.grid(row=4, column=1, sticky="w", padx=6, pady=6)

        # 模组存储路径
        ttk.Label(self, text="模组存储路径:").grid(row=5, column=0, sticky="e", padx=12, pady=6)
        self.entry_save_dir = ttk.Entry(self)
        self.entry_save_dir.grid(row=5, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(self, text="选择文件夹", command=self.choose_save_dir).grid(row=5, column=2, padx=12, pady=6)

        # 是否打包 ZIP
        self.zip_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self, text="是否打包 ZIP", variable=self.zip_var).grid(
            row=6, column=1, sticky="w", padx=6, pady=(6, 2)
        )

        # 控制按钮：并排 & 居中
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=7, column=0, columnspan=3, pady=12)
        self.start_btn = ttk.Button(btn_frame, text="开始下载", command=self.start_or_pause)
        self.start_btn.pack(side="left", padx=10)
        self.cancel_btn = ttk.Button(btn_frame, text="取消下载", command=self.cancel_download, state="disabled")
        self.cancel_btn.pack(side="left", padx=10)

        # 进度条
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progressbar = ttk.Progressbar(
            self, orient="horizontal", mode="determinate",
            maximum=100.0, variable=self.progress_var, length=560
        )
        self.progressbar.grid(row=8, column=0, columnspan=3, pady=(6, 8))

        # 状态栏
        self.status = tk.StringVar(value="准备就绪")
        ttk.Label(self, textvariable=self.status, foreground="#666").grid(
            row=9, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10)
        )

    # ---------- Actions ----------
    def choose_modpack(self):
        path = filedialog.askopenfilename(
            title="选择 .modpack 文件",
            filetypes=[("Modpack files", "*.modpack"), ("All files", "*.*")]
        )
        if not path:
            return
        self.entry_modpack.delete(0, tk.END)
        self.entry_modpack.insert(0, path)
        self.load_modpack_meta(path)

    def load_modpack_meta(self, path: str):
        """读取并展示模组包基本信息"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                pack = json.load(f)
        except Exception:
            self.pack_data = None
            self.btn_view_list.config(state="disabled")
            self.lbl_name.config(text="-")
            self.lbl_author.config(text="-")
            self.lbl_version.config(text="-")
            messagebox.showerror("错误", "模组包格式错误！")
            return

        required = ["name", "author", "version", "mod_list"]
        if not all(k in pack for k in required) or not isinstance(pack.get("mod_list"), list):
            self.pack_data = None
            self.btn_view_list.config(state="disabled")
            self.lbl_name.config(text="-")
            self.lbl_author.config(text="-")
            self.lbl_version.config(text="-")
            messagebox.showerror("错误", "模组包缺少必要字段或格式不正确！")
            return

        # 去掉空白和重复的 modid
        mod_list = [m.strip() for m in pack["mod_list"] if isinstance(m, str) and m.strip()]
        pack["mod_list"] = list(dict.fromkeys(mod_list))

        self.pack_data = pack
        self.lbl_name.config(text=str(pack["name"]))
        self.lbl_author.config(text=str(pack["author"]))
        self.lbl_version.config(text=str(pack["version"]))
        self.btn_view_list.config(state="normal")

    def view_mod_list(self):
        """显示模组列表"""
        if not self.pack_data:
            return
        top = tk.Toplevel(self)
        top.title("模组列表")
        top.geometry("420x360")
        frm = ttk.Frame(top)
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frm, orient="vertical")
        lb = tk.Listbox(frm, yscrollcommand=sb.set)
        sb.config(command=lb.yview)
        lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        for modid in self.pack_data.get("mod_list", []):
            lb.insert(tk.END, modid)

    def choose_save_dir(self):
        path = filedialog.askdirectory(title="选择存储路径")
        if path:
            self.entry_save_dir.delete(0, tk.END)
            self.entry_save_dir.insert(0, path)

    # ---------- 合并按钮：开始 / 暂停 / 继续 ----------
    def start_or_pause(self):
        text = self.start_btn.cget("text")
        if text == "开始下载":
            self.start_download_thread()
        elif text == "暂停下载":
            # 进入暂停
            self.pause_event.clear()
            self.start_btn.config(text="继续下载")
            self._safe_status("已暂停")
        elif text == "继续下载":
            # 继续
            self.pause_event.set()
            self.start_btn.config(text="暂停下载")
            self._safe_status("继续下载…")

    def cancel_download(self):
        """取消下载：如果正在暂停，先强制恢复，再设置取消标记"""
        # 关键点：强制恢复，避免线程卡在 wait() 中
        self.pause_event.set()
        self.cancel_flag = True
        self._safe_status("取消中…")

    # ---------- 线程与安全更新 ----------
    def start_download_thread(self):
        """启动后台下载线程，同时更新按钮状态"""
        self.start_btn.config(text="暂停下载")
        self.cancel_btn.config(state="normal")
        self.cancel_flag = False
        self.pause_event.set()
        t = threading.Thread(target=self._download_main, daemon=True)
        t.start()

    def _safe_status(self, text: str):
        """安全更新状态栏"""
        self.after(0, lambda: self.status.set(text))

    def _safe_progress(self, value: float):
        """安全更新进度条"""
        self.after(0, lambda: self.progress_var.set(value))

    def _download_main(self):
        """下载主逻辑入口，确保收尾恢复按钮"""
        try:
            self._do_download()
        finally:
            # 收尾：无论正常结束或被取消都恢复按钮
            self.after(0, lambda: (
                self.start_btn.config(text="开始下载"),
                self.cancel_btn.config(state="disabled")
            ))

    # ---------- 下载逻辑 ----------
    def _do_download(self):
        """执行实际的下载过程"""
        modpack_path = self.entry_modpack.get().strip()
        game_version = self.entry_game_version.get().strip()
        loader = self.loader_var.get().strip().lower()
        save_dir = self.entry_save_dir.get().strip()
        pack_zip = self.zip_var.get()

        # 基本校验
        if not os.path.isfile(modpack_path):
            messagebox.showerror("错误", "请正确选择 .modpack 文件")
            return
        if not game_version:
            messagebox.showerror("错误", "请输入游戏版本")
            return
        if loader not in {"fabric", "forge", "quilt", "neoforge"}:
            messagebox.showerror("错误", "请选择有效的加载器")
            return
        if not os.path.isdir(save_dir):
            messagebox.showerror("错误", "请选择有效的模组存储路径")
            return

        try:
            with open(modpack_path, "r", encoding="utf-8") as f:
                pack = json.load(f)
        except Exception:
            messagebox.showerror("错误", "模组包格式错误！")
            return

        required = ["name", "author", "version", "mod_list"]
        if not all(k in pack for k in required) or not isinstance(pack.get("mod_list"), list):
            messagebox.showerror("错误", "模组包缺少必要字段或格式不正确！")
            return

        mod_list = [m.strip() for m in pack["mod_list"] if isinstance(m, str) and m.strip()]
        if not mod_list:
            messagebox.showerror("错误", "模组包的 mod_list 为空！")
            return

        self.total_mods = len(mod_list)
        self.progress = 0.0
        self._safe_progress(0.0)
        self._safe_status("开始下载…")

        # 临时目录
        jartemp = tempfile.mkdtemp(prefix="packnload_")
        fails = []

        try:
            for idx, modid in enumerate(mod_list, start=1):
                # 若收到取消请求：不再开始下一个文件；删除临时目录并退出
                if self.cancel_flag:
                    self._safe_status("已取消")
                    return  # finally 会清理临时目录

                self._safe_status(f"[{idx}/{self.total_mods}] 解析 {modid} …")

                versions = get_project_versions_filtered(modid, game_version, loader)
                if not versions:
                    fails.append(modid)
                    self._bump_progress_to(idx)
                    continue

                file_obj = None
                for v in versions:
                    file_obj = pick_primary_file(v.get("files", []))
                    if file_obj:
                        break
                if not file_obj or "url" not in file_obj:
                    fails.append(modid)
                    self._bump_progress_to(idx)
                    continue

                url = file_obj["url"]
                filename = file_obj.get("filename") or url.split("/")[-1]
                size_hint = int(file_obj.get("size") or 0)
                dst_path = os.path.join(jartemp, filename)

                self._safe_status(f"[{idx}/{self.total_mods}] 下载 {modid} …")

                base = (idx - 1) * (100.0 / self.total_mods)
                weight = 100.0 / self.total_mods
                downloaded = 0

                def on_bytes(inc, total_or_none):
                    nonlocal downloaded
                    downloaded += inc
                    total_bytes = size_hint or (total_or_none or 0)
                    if total_bytes > 0:
                        frac = min(downloaded / total_bytes, 1.0)
                        self.progress = base + frac * weight
                    else:
                        step = weight * (inc / 1_000_000)
                        self.progress = min(base + step, base + weight)
                    self._safe_progress(self.progress)

                try:
                    # 传入 pause_event：支持暂停；取消不会中断当前文件
                    stream_download(url, dst_path, on_bytes=on_bytes, pause_event=self.pause_event)
                except Exception:
                    fails.append(modid)
                    self._bump_progress_to(idx)
                    continue

                # 当前文件完成，推进到该文件应有的进度
                self._bump_progress_to(idx)

                # 若取消是在下载该文件过程中发起，此处文件已完整，立刻退出
                if self.cancel_flag:
                    self._safe_status("已取消")
                    return  # finally 会清理临时目录

            # 打包或复制
            self._safe_status("整理文件…")
            if pack_zip:
                zip_path = os.path.join(save_dir, f"{pack['name']}-{pack['version']}.zip")
                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
                    for file in os.listdir(jartemp):
                        z.write(os.path.join(jartemp, file), arcname=file)
            else:
                for file in os.listdir(jartemp):
                    shutil.copy2(os.path.join(jartemp, file), save_dir)

        finally:
            # 始终清理临时目录
            shutil.rmtree(jartemp, ignore_errors=True)

        self._safe_progress(100.0)
        self._safe_status("完成")

        if fails:
            top = tk.Toplevel(self)
            top.title("下载失败模组列表")
            top.geometry("400x300")
            ttk.Label(top, text=f"成功下载!\n其中 {len(fails)} 个模组下载失败:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))

            frm = ttk.Frame(top)
            frm.pack(fill="both", expand=True, padx=10, pady=10)

            sb = ttk.Scrollbar(frm, orient="vertical")
            lb = tk.Listbox(frm, yscrollcommand=sb.set)
            sb.config(command=lb.yview)
            lb.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")

            for modid in fails:
                lb.insert(tk.END, modid)
        else:
            messagebox.showinfo("完成", "成功下载!\n没有任何模组下载失败!")

    def _bump_progress_to(self, i_done: int):
        """把进度推进到第 i_done 个模组完成应有的位置"""
        target = min(i_done * (100.0 / max(self.total_mods, 1)), 100.0)
        if target > self.progress:
            self.progress = target
            self._safe_progress(self.progress)

if __name__ == "__main__":
    app = App()
    app.mainloop()
