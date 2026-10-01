import sys
from pathlib import Path
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QObject, QThread, Signal, Qt, QSize
from PySide6.QtWidgets import QApplication, QMessageBox, QTreeWidgetItem, QListWidgetItem
from PySide6.QtGui import QIcon
from src.backend import scan_app_leftovers, move_to_trash, remove_rpm_package, get_installed_packages
import src.resources_rc


# thread classes
class LoadAppsThread(QThread):
    finished_signal = Signal(list)
    def run(self):
        # Fetches the RPM list in the background so the app opens instantly
        packages = get_installed_packages()
        self.finished_signal.emit(packages)

class ScanThread(QThread):
    finished_signal = Signal(dict)
    def __init__(self, app_name):
        super().__init__()
        self.app_name = app_name
    def run(self):
        results = scan_app_leftovers(self.app_name)
        self.finished_signal.emit(results)

class TrashThread(QThread):
    finished_signal = Signal(dict)
    def __init__(self, paths):
        super().__init__()
        self.paths = paths
    def run(self):
        results = move_to_trash(self.paths)
        self.finished_signal.emit(results)

class UninstallThread(QThread):
    finished_signal = Signal(dict)
    def __init__(self, app_name):
        super().__init__()
        self.app_name = app_name
    def run(self):
        results = remove_rpm_package(self.app_name)
        self.finished_signal.emit(results)

# ==========================================
# MAIN GUI CLASS
# ==========================================

class KRemoverApp(QObject):
    def __init__(self):
        super().__init__()
        
        ui_file_path = Path(__file__).parent.parent / "ui" / "mainwindow.ui"
        loader = QUiLoader()
        ui_file = QFile(str(ui_file_path))
        ui_file.open(QFile.ReadOnly)
        self.window = loader.load(ui_file)
        ui_file.close()
        
        self.window.setWindowTitle("kRemover - Fedora KDE Uninstaller")
        self.window.resize(1280, 720)
        
        # setup Tree Widget
        self.window.results_tree.setHeaderLabels(["Path / File", "Size"])
        self.window.results_tree.setColumnWidth(0, 450)
        
        self.window.trash_btn.setEnabled(False)
        self.window.uninstall_btn.setEnabled(False)
        self.window.scan_btn.setEnabled(False) 
        
        # ui conncections
        self.window.scan_btn.clicked.connect(self.run_scan)
        self.window.trash_btn.clicked.connect(self.run_trash)
        self.window.uninstall_btn.clicked.connect(self.run_uninstall)
        
        # connections app List & Menu
        self.window.search_input.setPlaceholderText("Filter installed applications...")
        self.window.search_input.textChanged.connect(self.filter_app_list)
        self.window.app_list.itemClicked.connect(self.on_app_selected)
        self.window.actionAbout.triggered.connect(self.show_about_dialog)
        
        # start fetching the packages in the background directly
        self.load_apps_thread = LoadAppsThread()
        self.load_apps_thread.finished_signal.connect(self.on_apps_loaded)
        self.load_apps_thread.start()

        # size hint for app list 
        self.window.app_list.setIconSize(QSize(32, 32)) 
        self.window.app_list.setSpacing(2) 

    def on_apps_loaded(self, packages):
        fallback_icon = QIcon.fromTheme("package-x-generic")
        
        # important sort the apps with logo and no logos
        apps_with_logos = []
        apps_without_logos = []
        
        for app_name in packages:
            if QIcon.hasThemeIcon(app_name):
                apps_with_logos.append(app_name)
            else:
                apps_without_logos.append(app_name)
                
        apps_with_logos.sort()
        apps_without_logos.sort()
        
        prioritized_packages = apps_with_logos + apps_without_logos
        
        for app_name in prioritized_packages:
            item = QListWidgetItem(app_name)
            icon = QIcon.fromTheme(app_name, fallback_icon)
            item.setIcon(icon)
            self.window.app_list.addItem(item)
        
    def filter_app_list(self, text):
        for i in range(self.window.app_list.count()):
            item = self.window.app_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def on_app_selected(self, item):
        self.window.scan_btn.setEnabled(True)
        #TODO auto Trigger also possible may lead to lag

    def show_about_dialog(self):
        QMessageBox.about(
            self.window, 
            "About kRemover", 
            "<h3>kRemover v0.9</h3>"
            "<p>A deep-cleaning uninstaller for Fedora KDE.</p>"
            "<p>Safely locates and trashes leftover user configuration data "
            "that the standard DNF package manager leaves behind.</p>"
        )

    # scanning logic
    def run_scan(self):
        selected_items = self.window.app_list.selectedItems()
        if not selected_items:
            return
            
        app_name = selected_items[0].text()
            
        self.window.scan_btn.setText("Scanning...")
        self.window.scan_btn.setEnabled(False)
        self.window.results_tree.clear()
        
        self.scan_thread = ScanThread(app_name)
        self.scan_thread.finished_signal.connect(self.on_scan_finished)
        self.scan_thread.start()
        
    def on_scan_finished(self, results):
        self.window.scan_btn.setText("Scan for Leftovers")
        self.window.scan_btn.setEnabled(True)
        
        if not results["paths"]:
            self.window.uninstall_btn.setEnabled(True)
            QMessageBox.information(self.window, "Result", f"No user data found for '{results['app_name']}'.")
            return
            
        for path_data in results["paths"]:
            parent_item = QTreeWidgetItem(self.window.results_tree)
            parent_item.setText(0, path_data["target_path"])
            parent_item.setText(1, path_data["size_str"]) 
            
            parent_item.setFlags(parent_item.flags() | Qt.ItemIsUserCheckable)
            parent_item.setCheckState(0, Qt.Checked)
            
            for file_data in path_data.get("files", []):
                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, file_data["path"])
                child_item.setText(1, file_data["size_str"]) 
                
        self.window.results_tree.expandAll()
        self.window.trash_btn.setEnabled(True)
        self.window.uninstall_btn.setEnabled(True)

    # trashing logic
    def run_trash(self):
        paths_to_delete = []
        for i in range(self.window.results_tree.topLevelItemCount()):
            item = self.window.results_tree.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                paths_to_delete.append(item.text(0))
                
        if not paths_to_delete:
            QMessageBox.warning(self.window, "Warning", "No paths selected to trash.")
            return
            
        self.window.trash_btn.setText("Moving...")
        self.window.trash_btn.setEnabled(False)
        
        self.trash_thread = TrashThread(paths_to_delete)
        self.trash_thread.finished_signal.connect(self.on_trash_finished)
        self.trash_thread.start()
        
    def on_trash_finished(self, results):
        self.window.trash_btn.setText("Move Selected to Trash")
        success_count = len(results["success"])
        fail_count = len(results["failed"])
        QMessageBox.information(self.window, "Trash Results", f"Successfully trashed: {success_count}\nFailed: {fail_count}")
        self.run_scan()

    # uninstall (remove) logic
    def run_uninstall(self):
        selected_items = self.window.app_list.selectedItems()
        if not selected_items:
            return
            
        app_name = selected_items[0].text()
        
        reply = QMessageBox.question(
            self.window, "Confirm", 
            f"Are you sure you want to uninstall {app_name} via DNF?", 
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.No:
            return
            
        self.window.uninstall_btn.setText("Uninstalling...")
        self.window.uninstall_btn.setEnabled(False)
        
        self.uninstall_thread = UninstallThread(app_name)
        self.uninstall_thread.finished_signal.connect(self.on_uninstall_finished)
        self.uninstall_thread.start()
        
    def on_uninstall_finished(self, results):
        self.window.uninstall_btn.setText("Uninstall via DNF")
        self.window.uninstall_btn.setEnabled(True)
        
        if results["success"]:
            QMessageBox.information(self.window, "Success", results["message"] + "\n\n" + results["details"])
            # remove unistalled app from list
            selected_items = self.window.app_list.selectedItems()
            if selected_items:
                self.window.app_list.takeItem(self.window.app_list.row(selected_items[0]))
        else:
            QMessageBox.critical(self.window, "Error", results["message"] + "\n\n" + results["details"])