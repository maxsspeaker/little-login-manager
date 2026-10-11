from PySide6.QtCore import QUrl, QDateTime, Qt,QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineScript
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply, QNetworkCookie
import argparse,sys,os

class MiniBrowser(QWidget):
    def __init__(self, little_login_folder,exportCookies,openUrl):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("LittleLoginManager - browser")
        self.resize(1024, 768)
        self.setContentsMargins(0, 0, 0, 0)

        # 1. ОПРЕДЕЛЯЕМ ПУТИ К ПАПКАМ
        self.browser_data_folder = os.path.join(little_login_folder, "BrowserData")
        self.export_folder = os.path.join(little_login_folder, "ExportedCookies")
        
        if not os.path.exists(self.browser_data_folder):
            os.makedirs(self.browser_data_folder)
        if not os.path.exists(self.export_folder):
            os.makedirs(self.export_folder)

        self.cookies_dict = {}

        # 2. СОЗДАЕМ И НАСТРАИВАЕМ ПРОФИЛЬ
        self.profile = QWebEngineProfile("MyCustomProfile", self)

        # Антидетект
        firefox_user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) "
            "Gecko/20100101 Firefox/130.0"
        )
        self.profile.setHttpUserAgent(firefox_user_agent)

        stealth_script = QWebEngineScript()
        stealth_script.setSourceCode("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        stealth_script.setInjectionPoint(QWebEngineScript.DocumentCreation)
        stealth_script.setWorldId(QWebEngineScript.MainWorld)
        stealth_script.setName("stealth_webdriver")
        self.profile.scripts().insert(stealth_script)

        self.profile.setPersistentStoragePath(self.browser_data_folder)
        self.profile.setCachePath(self.browser_data_folder)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)

        self.cookie_store = self.profile.cookieStore()
        self.cookie_store.cookieAdded.connect(self.handle_cookie_added)
        self.cookie_store.cookieRemoved.connect(self.handle_cookie_removed)
        self.cookie_store.loadAllCookies()

        # 3. ИНИЦИАЛИЗИРУЕМ СТРАНИЦУ И БРАУЗЕР С НАШИМ ПРОФИЛЕМ
        self.web_page = QWebEnginePage(self.profile, self)
        self.browser = QWebEngineView()
        self.browser.setPage(self.web_page)
        
        # ВАЖНО: Стартуем сразу с YouTube, чтобы получить куки .youtube.com!
        self.browser.setUrl(QUrl(openUrl))#"https://www.youtube.com"))

        # 4. ИНТЕРФЕЙС И ЭЛЕМЕНТЫ УПРАВЛЕНИЯ
        self.back_btn = QPushButton("◀")
        self.forward_btn = QPushButton("▶")
        self.reload_btn = QPushButton("🔄")
        self.url_bar = QLineEdit()
        
        self.export_btn = QPushButton("💾 Экспорт Cookies")
        self.export_btn.setStyleSheet("font-weight: bold; color: #2d8a39;")

        self.browser.urlChanged.connect(self.update_url_bar)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.back_btn.clicked.connect(self.browser.back)
        self.forward_btn.clicked.connect(self.browser.forward)
        self.reload_btn.clicked.connect(self.browser.reload)
        self.export_btn.clicked.connect(self.export_cookies_to_file)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.forward_btn)
        nav_layout.addWidget(self.reload_btn)
        nav_layout.addWidget(self.url_bar)
        nav_layout.addWidget(self.export_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(self.browser)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(main_layout)

        if(exportCookies):
            self.browser.loadFinished.connect(self.auto_export_cookies)
            QTimer.singleShot(10, self.hide)
            

    def auto_export_cookies(self):
        self.export_cookies_to_file()
        QTimer.singleShot(5, self.show)
        QTimer.singleShot(10, self.close)


    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        self.browser.setUrl(QUrl(url))

    def update_url_bar(self, qurl):
        self.url_bar.setText(qurl.toString())

    def handle_cookie_added(self, cookie: QNetworkCookie):
        domain = cookie.domain()
        name = cookie.name().data().decode('utf-8', errors='replace')
        self.cookies_dict[f"{domain}_{name}"] = cookie

    def handle_cookie_removed(self, cookie: QNetworkCookie):
        domain = cookie.domain()
        name = cookie.name().data().decode('utf-8', errors='replace')
        key = f"{domain}_{name}"
        if key in self.cookies_dict:
            del self.cookies_dict[key]

    def export_cookies_to_file(self):
        export_path = os.path.join(self.export_folder, "cookies.txt")
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This file was generated by LittleLoginManager (PySide6)\n\n")
                
                for cookie in self.cookies_dict.values():
                    domain = cookie.domain()
                    if not domain:
                        continue
                        
                    # ВАЖНО: Добавляем #HttpOnly_ для защищенных кук, иначе yt-dlp/Python их игнорирует
                    prefix = "#HttpOnly_" if cookie.isHttpOnly() else ""
                    
                    include_subdomains = "TRUE" if domain.startswith('.') else "FALSE"
                    path = cookie.path()
                    secure = "TRUE" if cookie.isSecure() else "FALSE"
                    
                    if cookie.isSessionCookie():
                        expiration = 0
                    else:
                        expiration = cookie.expirationDate().toSecsSinceEpoch()
                        
                    name = cookie.name().data().decode('utf-8', errors='replace')
                    value = cookie.value().data().decode('utf-8', errors='replace')
                    
                    f.write(f"{prefix}{domain}\t{include_subdomains}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")
                    
            print(f"[LittleLoginManager] Успешно экспортировано {len(self.cookies_dict)} куки в: {export_path}")
            self.export_btn.setText("✅ Успешно!")
            
        except Exception as e:
            print(f"[LittleLoginManager] Ошибка при экспорте куки: {e}")
            self.export_btn.setText("❌ Ошибка")

    # --- ПРИНУДИТЕЛЬНАЯ ОЧИСТКА ПАМЯТИ ПРИ ЗАКРЫТИИ ---
    def closeEvent(self, event):
        print("[LittleLoginManager] Браузер закрыт. Выполняется выгрузка движка из памяти...")
        
        if self.browser:
            self.browser.setPage(None)
            self.browser.deleteLater()
            
        if hasattr(self, 'web_page') and self.web_page:
            self.web_page.deleteLater()
            
        if hasattr(self, 'profile') and self.profile:
            self.profile.deleteLater()

        event.accept()


def main() -> int:

    parser = argparse.ArgumentParser(description="Little login manager for login website")
    parser.add_argument(
        '-f', '--folder', 
        type=str, 
        required=True,
        help="Savefolder for local files"
    )
    parser.add_argument(
        '-u', '--openUrl', 
        type=str, 
        required=True,
        help="Savefolder for local files"
    )
    parser.add_argument(
        '-e', '--export', 
        action='store_true', 
        help="Export cookies for browser"
    )
    args, unknown = parser.parse_known_args()

    app = QApplication(sys.argv)
    if (sys.platform == "win32"):
        app.setStyle("Fusion")

    #sys.excepthook
    window = MiniBrowser(str(args.folder),bool(args.export),str(args.openUrl))
    window.show() 
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
