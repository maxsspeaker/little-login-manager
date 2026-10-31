import os
import sys
import subprocess
import yaml, json, time

from PySide6.QtCore import QObject,QRunnable,Signal,Slot

from modules.types import PluginBase
from modules.other import LocalSaveDir


class BrowserSignals(QObject):
    resolved = Signal()
    close = Signal()

class BrowserRunner(QRunnable):
    def __init__(
        self,browser_folder:str,
        workfolder:str,
        signals: BrowserSignals) -> None:

        super().__init__()

        if sys.platform == "win32":
            self.browser_folder=os.path.join(browser_folder,"little-login-manager.exe")
        else:
            self.browser_folder=os.path.join(browser_folder,"little-login-manager")

        self.workfolder=workfolder
        self.signals=signals

        self.signals.close.connect(self.cancel)

    @Slot()
    def run(self) -> None:

        CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if sys.platform == "win32" else 0

        cmd=[self.browser_folder,"--folder",self.workfolder,"-u","https://www.youtube.com"]

        self._proc = subprocess.Popen(
            cmd,
           # stdout=None,   
           # stderr=subprocess.PIPE,
            text=True,creationflags=CREATE_NO_WINDOW,errors='replace'
            )

        self._proc.wait()

        self.signals.resolved.emit()

    def cancel(self) -> None:
        self._cancelled = True
        if self._proc is not None and self._proc.poll() is None:
            self._proc.kill()  

class LittleLoginManager(PluginBase):
    pluginName = "Little Login Manager"
    pluginDescription = "Little login manager for login website"
    pluginAuthor = "Maxsspeaker"

    def awake_plugin(self):
        self.main_window.cookie_data.append("LittleLoginManager")
        self.browser_signals = BrowserSignals()
        self.browserActived=False

    def init_plugin(self):
        self.my_folder = os.path.dirname(__file__)
        print(f"[LittleLoginManager] Загружен из: {self.my_folder}")

        self.thread_pool=self.main_window.thread_pool

        self.save_dir = os.path.join(LocalSaveDir(), "little-login-manager")
        if not os.path.isdir(self.save_dir):
            os.makedirs(self.save_dir, exist_ok=True)

        sys.modules['modules.extractors'].build_ytdlp_browser_args = self.build_ytdlp_browser_args

        self.loginManager_menu = self.main_window.MainMenuBar.add_submenu(
            self.main_window.PluginMenu, "Little Login Manager", hide_if_empty=False
        )

        self.toggle_action = self.loginManager_menu.addAction("Show browser", self.open_browser)

        self.browser_signals.resolved.connect(self.browser_closed)
        
    def open_browser(self):

        if not self.browserActived:
            print("[LittleLoginManager] Запуск нового экземпляра браузера...")
            self.thread_pool.start(BrowserRunner(os.path.join(self.my_folder,"browser.dist"),self.save_dir,self.browser_signals))
            self.browserActived=True
        else:
            self.browser_signals.close.emit()

    def browser_closed(self):
        self.browserActived=False


    def build_ytdlp_browser_args(self, cookie_browser: str) -> list[str]:
        browser = (cookie_browser or "").strip()
        
        if "LittleLoginManager" == cookie_browser:
            cookie_file = os.path.join(LocalSaveDir(), "little-login-manager", "ExportedCookies", "cookies.txt")
            if os.path.isfile(cookie_file):
                print(f"[LittleLoginManager] Используем файл куки: {cookie_file}")
                return ["--cookies", cookie_file]
            else:
                print("[LittleLoginManager] ПРЕДУПРЕЖДЕНИЕ: Файл cookies.txt не найден! Сначала экспортируйте их в браузере.")
                return []

        if not browser:
            return []
        return ["--cookies-from-browser", browser]


