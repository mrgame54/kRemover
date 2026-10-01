import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox, QTreeWidgetItem
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QObject, QThread, Signal, Qt
from src.backend import scan_app_leftovers, move_to_trash, remove_rpm_package

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
        self.window.resize(800, 600)
        self.window.results_tree.setHeaderLabels(["Path / File", "Size (MB/KB)"])
        self.window.results_tree.setColumnWidth(0, 500)
        
        self.window.trash_btn.setEnabled(False)
        self.window.uninstall_btn.setEnabled(False)
        
        self.window.scan_btn.clicked.connect(self.run_scan)
        self.window.trash_btn.clicked.connect(self.run_trash)
        self.window.uninstall_btn.clicked.connect(self.run_uninstall)

    # scanning logic
    def run_scan(self):
        app_name = self.window.search_input.text().strip()
        if not app_name:
            QMessageBox.warning(self.window, "Error", "Please enter an application name.")
            return
            
        # update UI state while loading
        self.window.scan_btn.setText("Scanning...")
        self.window.scan_btn.setEnabled(False)
        self.window.results_tree.clear()
        
        # launch the background thread
        self.scan_thread = ScanThread(app_name)
        self.scan_thread.finished_signal.connect(self.on_scan_finished)
        self.scan_thread.start()
        
    def on_scan_finished(self, results):
        # reset button
        self.window.scan_btn.setText("Scan for Leftovers")
        self.window.scan_btn.setEnabled(True)
        self.window.uninstall_btn.setEnabled(True) 
        
        if not results["paths"]:
            QMessageBox.information(self.window, "Result", f"No user data found for '{results['app_name']}'.")
            return
            
        # populate the Tree Widget
        for path_data in results["paths"]:
            parent_item = QTreeWidgetItem(self.window.results_tree)
            parent_item.setText(0, path_data["target_path"])
            parent_item.setText(1, f"{path_data['size_mb']} MB")
            
            # checkbox and check it by default
            parent_item.setFlags(parent_item.flags() | Qt.ItemIsUserCheckable)
            parent_item.setCheckState(0, Qt.Checked)
            
            # add the child files nested underneath
            for file_data in path_data.get("files", []):
                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, file_data["path"])
                child_item.setText(1, f"{file_data['size_kb']} KB")
                
        self.window.results_tree.expandAll()
        self.window.trash_btn.setEnabled(True)

    # trash logic
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

    # uninstall logic
    def run_uninstall(self):
        app_name = self.window.search_input.text().strip()
        
        # extra confirm
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
        else:
            QMessageBox.critical(self.window, "Error", results["message"] + "\n\n" + results["details"])