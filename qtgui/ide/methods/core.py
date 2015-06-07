#! /usr/bin/python2
#-*- coding: utf-8 -*-

import os
import codecs
import pickle
import logging
import webbrowser
import shutil
from math import ceil

from PySide import QtGui, QtCore

from ..custom_widgets import PinguinoCodeEditor

from .decorators import Decorator
from .dialogs import Dialogs
from ..tools.files import Files
from ..tools.search_replace import SearchReplace
from ..tools.project_manager import ProjectManager
from ..tools.boardconfig import BoardConfig
from ..tools.code_navigator import CodeNavigator
# from ..methods.library_manager import Librarymanager
# from ..widgets.output_widget import START

from .timed_methods import TimedMethods
# from .event_methods import EventMethods

from ..child_windows.about import About
from ..child_windows.libraries import LibManager
from ..child_windows.paths import Paths
from ..child_windows.hex_viewer import HexViewer
from ..child_windows.insert_block_dialog import InsertBlock
# from ..child_windows.environ_viewer import EnvironViewer
from ..child_windows.submit_bug import SubmitBug
from ..child_windows.patches import Patches

# Python3 compatibility
if os.getenv("PINGUINO_PYTHON") is "3":
    #Python3
    from ..commons.intel_hex3 import IntelHex
else:
    #Python2
    from ..commons.intel_hex import IntelHex


########################################################################
class PinguinoCore(TimedMethods, SearchReplace, ProjectManager, Files, BoardConfig, CodeNavigator):

    #----------------------------------------------------------------------
    def __init__(self):
        """"""
        BoardConfig.__init__(self)
        SearchReplace.__init__(self)
        CodeNavigator.__init__(self)
        Files.__init__(self)
        ProjectManager.__init__(self)
        # super(BoardConfig, self).__init__()


    #----------------------------------------------------------------------
    #@Decorator.debug_time()
    def open_file_from_path(self, *args, **kwargs):
        filename = kwargs["filename"]
        readonly = kwargs.get("readonly", False)

        if self.__check_duplicate_file__(filename): return

        self.update_recents(filename)

        if filename.endswith(".gpde"):
            self.switch_ide_mode(True)
            self.PinguinoKIT.open_file_from_path(filename=filename)
            return

        if filename.endswith(".ppde"):
            self.open_project_from_path(filename=filename)
            return

        elif filename.endswith(".pde"):
            self.switch_ide_mode(False)

        self.new_file(filename=filename)
        editor = self.main.tabWidget_files.currentWidget()
        #pde_file = open(path, mode="r")
        pde_file = codecs.open(filename, "r", "utf-8")
        content = "".join(pde_file.readlines())
        pde_file.close()
        editor.text_edit.setPlainText(content)
        editor.text_edit.setReadOnly(readonly)
        setattr(editor, "path", filename)
        setattr(editor, "last_saved", content)
        self.main.tabWidget_files.setTabToolTip(self.main.tabWidget_files.currentIndex(), filename)
        if readonly: extra_name = " (r/o)"
        else: extra_name = ""
        self.main.tabWidget_files.setTabText(self.main.tabWidget_files.currentIndex(), os.path.basename(filename)+extra_name)
        self.check_backup_file(editor=editor)
        self.tab_changed()



    #----------------------------------------------------------------------
    @Decorator.call_later(100)
    #@Decorator.debug_time()
    def open_last_files(self):
        self.recent_files = self.configIDE.get_recents()
        self.update_recents_menu()

        self.recent_projects = self.configIDE.get_recents(section="RecentsProjects")
        self.update_recents_menu_project()

        opens = self.configIDE.get_recents_open()
        if not opens:
            self.pinguino_ide_manual()
            return

        #files = "\n".join(opens)
        #dialogtext = QtGui.QApplication.translate("Dialogs", "Do you want open files of last sesion?")
        #if not Dialogs.confirm_message(self, dialogtext+"\n"+files):
            #return

        self.setCursor(QtCore.Qt.WaitCursor)
        for file_ in opens:
            if os.path.exists(file_):
                try: self.open_file_from_path(filename=file_)
                except: pass

        self.main.actionSwitch_ide.setChecked(file_.endswith(".gpde"))
        self.switch_ide_mode(file_.endswith(".gpde"))
        self.setCursor(QtCore.Qt.ArrowCursor)


    #----------------------------------------------------------------------
    def jump_to_line(self, line):
        self.highligh_line(line, "#DBFFE3")


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def select_block_edit(self):
        editor = self.main.tabWidget_files.currentWidget()
        cursor = editor.text_edit.textCursor()
        prevCursor = editor.text_edit.textCursor()

        text = cursor.selectedText()
        selected = bool(text)

        if text == "":  #no selected, single line
            start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
            startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()
            endPosition = editor.text_edit.document().findBlockByLineNumber(start+1).position() - 1

            cursor.setPosition(startPosition)
            cursor.setPosition(endPosition, QtGui.QTextCursor.KeepAnchor)
            editor.text_edit.setTextCursor(cursor)

        else:
            start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
            startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()

            end = editor.text_edit.document().findBlock(cursor.selectionEnd()).firstLineNumber()

            endPosition = editor.text_edit.document().findBlockByLineNumber(end+1).position() - 1

            cursor.setPosition(startPosition)
            cursor.setPosition(endPosition, QtGui.QTextCursor.KeepAnchor)
            editor.text_edit.setTextCursor(cursor)


        text = cursor.selectedText()

        lines = text.split(u'\u2029')
        firstLine = False
        for line in lines:
            if not line.isspace() and not line == "":
                firstLine = line
                break
        return editor, cursor, prevCursor, selected, firstLine



    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def highligh_line(self, line=None, color="#ff0000", text_cursor=None):
        editor = self.main.tabWidget_files.currentWidget()

        if line:
            content = editor.text_edit.toPlainText()
            #line_content = content.split("\n")[line-1]
            content = content.split("\n")[:line]
            position = len("\n".join(content))
            text_cur = editor.text_edit.textCursor()
            text_cur.setPosition(position)
            text_cur.clearSelection()
            editor.text_edit.setTextCursor(text_cur)
        else:
            text_cur = editor.text_edit.textCursor()
            text_doc = editor.text_edit.document()
            text_cur.clearSelection()
            editor.text_edit.setDocument(text_doc)
            editor.text_edit.setTextCursor(text_cur)

        selection = QtGui.QTextEdit.ExtraSelection()
        selection.format.setBackground(QtGui.QColor(color))
        selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        selection.cursor = editor.text_edit.textCursor()
        editor.text_edit.setExtraSelections(editor.text_edit.extraSelections()+[selection])

        selection.cursor.clearSelection()

        if text_cursor: editor.text_edit.setTextCursor(text_cursor)


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def clear_highlighted_lines(self):
        editor = self.main.tabWidget_files.currentWidget()
        editor.text_edit.setExtraSelections([])


    #----------------------------------------------------------------------
    def get_tab(self):
        if self.main.actionSwitch_ide.isChecked(): return self.main.tabWidget_graphical
        else: return self.main.tabWidget_files


    #----------------------------------------------------------------------
    @Decorator.connect_features()
    def __save_file__(self, *args, **kwargs):

        editor = kwargs.get("editor", self.get_tab())
        content = editor.text_edit.toPlainText()
        pde_file = codecs.open(editor.path, "w", "utf-8")
        pde_file.write(content)
        pde_file.close()
        setattr(editor, "last_saved", content)
        self.__remove_backup_file__(editor=editor)
        self.__text_saved__()

    #----------------------------------------------------------------------
    def __remove_backup_file__(self, *args, **kwargs):

        editor = kwargs.get("editor", self.get_tab())
        filename = getattr(editor, "path", None)
        filename_backup = filename + "~"
        if os.path.exists(filename_backup):
            os.remove(filename_backup)


    #----------------------------------------------------------------------
    def __get_name__(self, ext=".pde"):

        index = 1
        name = "untitled-%d" % index + ext
        #filenames = [self.main.tabWidget_files.tabText(i) for i in range(self.main.tabWidget_files.count())]
        filenames = [self.get_tab().tabText(i) for i in range(self.get_tab().count())]
        while name in filenames or name + "*" in filenames:
            index += 1
            name = "untitled-%d" % index + ext
        return name + "*"


    #----------------------------------------------------------------------
    def __text_changed__(self, *args, **kwargs):

        index = self.main.tabWidget_files.currentIndex()
        filename = self.main.tabWidget_files.tabText(index)
        if not filename.endswith("*"):
            self.main.tabWidget_files.setTabText(index, filename+"*")
            self.main.actionSave_file.setEnabled(True)
        self.clear_highlighted_lines()


    #----------------------------------------------------------------------
    def __text_saved__(self, *args, **kwargs):

        index = self.get_tab().currentIndex()
        filename = self.get_tab().tabText(index)
        if filename.endswith("*"):
            self.get_tab().setTabText(index, filename[:-1])
        self.main.actionSave_file.setEnabled(False)


    #----------------------------------------------------------------------
    def __text_can_undo__(self, *args, **kwargs):

        state = not self.main.actionUndo.isEnabled()
        self.main.actionUndo.setEnabled(state)
        editor = self.main.tabWidget_files.currentWidget()
        editor.tool_bar_state["undo"] = state


    #----------------------------------------------------------------------
    def __text_can_redo__(self, *args, **kwargs):

        state = not self.main.actionRedo.isEnabled()
        self.main.actionRedo.setEnabled(state)
        editor = self.main.tabWidget_files.currentWidget()
        editor.tool_bar_state["redo"] = state


    #----------------------------------------------------------------------
    def __text_can_copy__(self, *args, **kwargs):

        state = not self.main.actionCopy.isEnabled()
        self.main.actionCopy.setEnabled(state)
        self.main.actionCut.setEnabled(state)
        editor = self.main.tabWidget_files.currentWidget()
        editor.tool_bar_state["copy"] = state


    #----------------------------------------------------------------------
    def __check_duplicate_file__(self, filename):

        filenames = [getattr(self.get_tab().widget(i), "path", None) for i in range(self.get_tab().count())]
        if filename in filenames:
            # Dialogs.file_duplicated(self, filename)
            self.get_tab().setCurrentIndex(filenames.index(filename))
            return True
        return False


    #----------------------------------------------------------------------
    @Decorator.call_later()
    def load_main_config(self):

        if self.configIDE.config("Main", "maximized", True):
            self.showMaximized()
            self.setWindowState(QtCore.Qt.WindowMaximized)

        else:
            pos = self.configIDE.config("Main", "position", "(0, 0)")
            self.move(*eval(pos))

            size = self.configIDE.config("Main", "size", "(1050, 550)")
            self.resize(*eval(size))


        visible = self.configIDE.config("Main", "menubar", True)
        self.main.actionMenubar.setChecked(not visible)
        self.main.menubar.setVisible(visible)
        self.main.toolBar_menu.setVisible(not visible)

        self.switch_ide_mode(self.configIDE.config("Features", "graphical", False))

        self.main.actionAutocomplete.setChecked(self.configIDE.config("Features", "autocomplete", True))

        self.load_tabs_config()


    #----------------------------------------------------------------------
    def get_all_open_files(self):

        opens = []

        for tab in [self.main.tabWidget_files, self.main.tabWidget_graphical]:
            widgets = map(tab.widget, range(tab.count()))
            for widget in widgets:
                if not tab.tabText(tab.indexOf(widget)).endswith("(r/o)"):
                    path = getattr(widget, "path", False)
                    if path: opens.append(path)

        return opens


    #----------------------------------------------------------------------
    def update_recents(self, filename):

        if filename in self.recent_files:
            self.recent_files.remove(filename)
        self.recent_files.insert(0, filename)
        self.recent_files = self.recent_files[:10]

        self.update_recents_menu()


    #----------------------------------------------------------------------
    def update_recents_menu(self):

        self.main.menuRecents.clear()
        for file_ in self.recent_files:
            action = QtGui.QAction(self)
            filename = os.path.split(file_)[1]

            len_ = 40
            if len(file_) > len_:
                file_path_1 = file_[:int(len_/2)]
                file_path_2 = file_[int(-len_/2):]
                file_path = file_path_1 + "..." + file_path_2
            else: file_path = file_

            if os.path.isfile(file_):
                action.setText(filename+" ("+file_path+")")
                self.connect(action, QtCore.SIGNAL("triggered()"), self.menu_recent_event(file_))
                action.ActionEvent = self.menu_recent_event

                self.main.menuRecents.addAction(action)

        self.main.menuRecents.addSeparator()
        self.main.menuRecents.addAction(QtGui.QApplication.translate("Dialogs", "Clear recent files"), self.clear_recents_menu)

    #----------------------------------------------------------------------
    def clear_recents_menu(self):

        self.main.menuRecents.clear()
        self.main.menuRecents.addSeparator()
        self.main.menuRecents.addAction(QtGui.QApplication.translate("Dialogs", "Clear recent files"), self.clear_recents_menu)
        self.recent_files = []


    #----------------------------------------------------------------------
    def menu_recent_event(self, file_):

        def menu():
            self.open_file_from_path(filename=file_)
        return menu


    #----------------------------------------------------------------------
    def build_statusbar(self):

        #principal status
        self.status_info = QtGui.QLabel()

        #warning status
        self.status_warnnig = QtGui.QLabel()
        self.status_warnnig.setAlignment(QtCore.Qt.AlignRight)
        self.status_warnnig.setStyleSheet("""
        QLabel{
            color: red;
        }
        """)

        self.main.statusBar.addPermanentWidget(self.status_info, 1)
        self.main.statusBar.addPermanentWidget(self.status_warnnig, 2)



    # #----------------------------------------------------------------------
    # def statusbar_ide(self, status):

        # self.status_info.setText(status)

    #----------------------------------------------------------------------
    def statusbar_warnning(self, status):

        self.status_warnnig.setText(status)


    #----------------------------------------------------------------------
    def set_board(self):

        # config data
        board_name = self.configIDE.config("Board", "board", "Pinguino 2550")
        arch = self.configIDE.config("Board", "arch", 8)
        mode = self.configIDE.config("Board", "mode", "boot")
        bootloader = self.configIDE.config("Board", "bootloader", "v1_v2")


        # set board
        for board in self.pinguinoAPI._boards_:
            if board.name == board_name:
                self.pinguinoAPI.set_board(board)


        # set mode and bootloader
        if arch == 8 and mode == "bootloader":
            if bootloader == "v1_v2":
                self.pinguinoAPI.set_bootloader(*self.pinguinoAPI.Boot2)
            else:
                self.pinguinoAPI.set_bootloader(*self.pinguinoAPI.Boot4)

        # no configuration bootloader for 32 bits

        if mode == "icsp":
            # if mode is icsp overwrite all configuration
            self.pinguinoAPI.set_bootloader(*self.pinguinoAPI.NoBoot)


        # update environment
        os.environ["PINGUINO_BOARD_ARCH"] = str(arch)


        # set compilers and libraries for each arch
        # RB20150127 : modified until I can compile p32-gcc for mac os x
        #elif os.getenv("PINGUINO_OS_NAME") == "linux":
        if os.getenv("PINGUINO_OS_NAME") == "windows":
            ext = ".exe"
        else :
            ext = ""

        if arch == 8:
            compiler_path = os.path.join(self.configIDE.get_path("sdcc_bin"), "sdcc" + ext)
            libraries_path = self.configIDE.get_path("pinguino_8_libs")

        elif arch == 32:
            #RB20140615 + RB20141116 + RB20150127 :
            #- gcc toolchain has been renamed from mips-elf-gcc to p32-gcc except for MAC OS X
            if os.getenv("PINGUINO_OS_NAME") == "macosx":
                compiler_path = os.path.join(self.configIDE.get_path("gcc_bin"), "mips-elf-gcc" + ext)
            else:
                compiler_path = os.path.join(self.configIDE.get_path("gcc_bin"), "p32-gcc" + ext)
            #- except for 32-bit Windows
            #if os.getenv("PINGUINO_OS_NAME") == "windows":
            #    if os.getenv("PINGUINO_OS_ARCH") == "32bit":
            #        compiler_path = os.path.join(self.configIDE.get_path("gcc_bin"), "mips-gcc" + ext)
            libraries_path = self.configIDE.get_path("pinguino_32_libs")


        # generate messages
        status = ""
        if not os.path.exists(compiler_path):
            status = QtGui.QApplication.translate("Frame", "Missing compiler for %d-bit") % arch
            logging.warning("Missing compiler for %d-bit" % arch)
            logging.warning("Not found: %s" % compiler_path)

        if not os.path.exists(libraries_path):
            status = QtGui.QApplication.translate("Frame", "Missing libraries for %d-bit") % arch
            logging.warning("Missing libraries for %d-bit" % arch)
            logging.warning("Not found: %s" % libraries_path)

        if not os.path.exists(libraries_path) and not os.path.exists(compiler_path):
            status = QtGui.QApplication.translate("Frame", "Missing libraries and compiler for %d-bit") % arch
            #logging.warning("Missing libraries and compiler for %d-bit" % arch)
            #logging.warning("Missing: %s" % compiler_path)
            #logging.warning("Missing: %s" % libraries_path)

        if status:
            self.statusbar_warnning(status)
            os.environ["PINGUINO_CAN_COMPILE"] = "False"
        else:
            os.environ["PINGUINO_CAN_COMPILE"] = "True"
            # logging.warning("Found: %s" % compiler_path)
            # logging.warning("Found: %s" % libraries_path)


    #----------------------------------------------------------------------
    def get_description_board(self):

        board_config = []

        board = self.pinguinoAPI.get_board()
        board_config.append("Board: %s" % board.name)
        board_config.append("Proc: %s" % board.proc)
        board_config.append("Arch: %d" % board.arch)

        if board.arch == 32:
            board_config.append("MIPS 16: %s" % str(self.configIDE.config("Board", "mips16", True)))
            board_config.append("Heap size: %d bytes" % self.configIDE.config("Board", "heapsize", 512))
            board_config.append("Optimization: %s" % self.configIDE.config("Board", "optimization", "-O3"))

        if board.arch == 8 and board.bldr == "boot4":
            board_config.append("Bootloader: v4")
        elif board.arch == 8 and board.bldr == "boot2":
            board_config.append("Bootloader: v1 & v2")
        elif board.arch == 8 and board.bldr == "noboot":
            board_config.append("Mode: ICSP")

        return "\n".join(board_config)


    #----------------------------------------------------------------------
    def get_status_board(self):

        self.set_board()
        board = self.pinguinoAPI.get_board()
        board_config = board.name

        if board.arch == 8 and board.bldr == "boot4":
            board_config += " - Bootloader: v4"
        if board.arch == 8 and board.bldr == "boot2":
            board_config += " - Bootloader: v1 & v2"

        return board_config


    #----------------------------------------------------------------------
    def reload_file(self):

        editor = self.main.tabWidget_files.currentWidget()
        filename = getattr(editor, "path", False)
        file_ = codecs.open(filename, "r", "utf-8")
        editor.text_edit.clear()
        editor.text_edit.insertPlainText("".join(file_.readlines()))
        self.save_file()

    #----------------------------------------------------------------------
    def update_reserved_words(self):

        libinstructions = self.pinguinoAPI.read_lib(8)
        name_spaces_8 = map(lambda x:x[0], libinstructions)

        libinstructions = self.pinguinoAPI.read_lib(32)
        name_spaces_32 = map(lambda x:x[0], libinstructions)

        reserved_filename = os.path.join(os.getenv("PINGUINO_USER_PATH"), "reserved.pickle")

        name_spaces_commun = []

        copy_32 = name_spaces_32[:]
        for name in name_spaces_8:
            if name in copy_32:
                name_spaces_8.remove(name)
                name_spaces_32.remove(name)
                name_spaces_commun.append(name)

        namespaces = {"arch8": name_spaces_8, "arch32": name_spaces_32, "all": name_spaces_commun,}
        pickle.dump(namespaces, open(reserved_filename, "w"))

        logging.warning("Writing: " + reserved_filename)
        return("Writing: " + reserved_filename)


    #----------------------------------------------------------------------
    def update_instaled_reserved_words(self):

        libinstructions = self.pinguinoAPI.read_lib(8, include_default=False)
        name_spaces_8 = map(lambda x:x[0], libinstructions)

        libinstructions = self.pinguinoAPI.read_lib(32, include_default=False)
        name_spaces_32 = map(lambda x:x[0], libinstructions)

        reserved_filename = os.path.join(os.getenv("PINGUINO_USER_PATH"), "reserved.pickle")

        name_spaces_commun = []

        copy_32 = name_spaces_32[:]
        for name in name_spaces_8:
            if name in copy_32:
                name_spaces_8.remove(name)
                name_spaces_32.remove(name)
                name_spaces_commun.append(name)

        olds = pickle.load(open(reserved_filename, "r"))

        namespaces = {"arch8": list(set(name_spaces_8 + olds["arch8"])),
                      "arch32": list(set(name_spaces_32 + olds["arch32"])),
                      "all": list(set(name_spaces_commun + olds["all"])),}

        #pickle.dump(olds, open(reserved_filename, "w"))
        pickle.dump(namespaces, open(reserved_filename, "w"))

        logging.warning("Writing: " + reserved_filename)
        return("Writing: " + reserved_filename)


    #----------------------------------------------------------------------
    def toggle_toolbars(self, visible):

        for toolbar in self.toolbars:
            toolbar.setVisible(visible)

        if self.is_graphical():
            self.update_actions_for_graphical()
        else:
            self.update_actions_for_text()


    #----------------------------------------------------------------------
    def toggle_menubar(self, event=None):

        self.main.menubar.setVisible(not self.main.menubar.isVisible())
        if not self.main.menubar.isVisible():
            self.toggle_toolbars(True)
        self.main.toolBar_menu.setVisible(not self.main.menubar.isVisible())
        # self.configIDE.set("Main", "menubar", self.main.menubar.isVisible())
        self.configIDE.save_config()


    #----------------------------------------------------------------------
    def check_backup_file(self, *args, **kwargs):

        editor = kwargs.get("editor", self.get_tab())
        if editor:

            filename = getattr(editor, "path")
            filename_backup = filename + "~"

            if os.path.exists(filename_backup):
                backup_file = codecs.open(filename_backup, "r", "utf-8")
                content = "".join(backup_file.readlines())
                backup_file.close()

                if editor.text_edit.toPlainText() == content:
                    os.remove(filename_backup)
                    return

                reply = Dialogs.confirm_message(self, "%s\n"%filename + QtGui.QApplication.translate("Dialogs",
                        "Pinguino IDE has found changes that were not saved during your last session.\nDo you want recover it?."))

                if reply:
                    editor.text_edit.setPlainText(content)
                    os.remove(filename_backup)



    #----------------------------------------------------------------------
    def restart_now(self):

        import time
        import sys
        logging.warning("Restarting now...")
        time.sleep(1)

        # python = sys.executable
        file_ = os.path.join(os.getenv("PINGUINO_HOME"), "pinguino.py")

        os.execv(file_, sys.argv)


    #----------------------------------------------------------------------
    def get_tabs_height(self):

        return self.main.tabWidget_bottom.tabBar().height()


    #----------------------------------------------------------------------
    def toggle_right_area(self, expand=None):

        if expand is None:
            expand = (self.main.dockWidgetContents_rigth.width() <= (self.get_tabs_height()) + 5)
        min_ = self.get_tabs_height()

        if expand:
            h = self.configIDE.config("Main", "right_area_width", 400)
            if h <= (self.get_tabs_height() + 5):
                h = 400
                self.configIDE.set("Main", "right_area_width", 400)

            self.main.dockWidgetContents_rigth.setMaximumWidth(1000)
            self.main.dockWidgetContents_rigth.setMinimumWidth(h)
            self.main.actionToggle_vertical_tool_area.setText("Hide vertical tool area")
            QtCore.QTimer.singleShot(100, lambda :self.main.dockWidgetContents_rigth.setMinimumWidth(min_))
        else:
            self.configIDE.set("Main", "right_area_width", self.main.dockWidgetContents_rigth.width())
            self.main.dockWidgetContents_rigth.setMinimumWidth(0)
            self.main.dockWidgetContents_rigth.setMaximumWidth(min_)
            self.main.actionToggle_vertical_tool_area.setText("Show vertical tool area")
            QtCore.QTimer.singleShot(100, lambda :self.main.dockWidgetContents_rigth.setMaximumWidth(1000))


    #----------------------------------------------------------------------
    def toggle_bottom_area(self, expand=None):

        if expand is None:
            expand = (self.main.dockWidgetContents_bottom.height() <= (self.get_tabs_height()) + 5)
        min_ = self.get_tabs_height()

        if expand:
            h = self.configIDE.config("Main", "bottom_area_height", 200)
            if h <= (self.get_tabs_height() + 5):
                h = 200
                self.configIDE.set("Main", "bottom_area_height", 200)

            self.main.dockWidgetContents_bottom.setMaximumHeight(1000)
            self.main.dockWidgetContents_bottom.setMinimumHeight(h)
            self.main.actionToggle_horizontal_tool_area.setText("Hide horizontal tool area")
            QtCore.QTimer.singleShot(100, lambda :self.main.dockWidgetContents_bottom.setMinimumHeight(min_))
        else:
            self.configIDE.set("Main", "bottom_area_height", self.main.dockWidgetContents_bottom.height()-3)
            self.main.dockWidgetContents_bottom.setMinimumHeight(0)
            self.main.dockWidgetContents_bottom.setMaximumHeight(min_)
            self.main.actionToggle_horizontal_tool_area.setText("Show horizontal tool area")
            QtCore.QTimer.singleShot(100, lambda :self.main.dockWidgetContents_bottom.setMaximumHeight(1000))


    #----------------------------------------------------------------------
    def tab_right_changed(self, event):

        self.toggle_right_area(expand=True)


    #----------------------------------------------------------------------
    def tab_tools_resize(self, event):
        self.configIDE.set("Main", "right_area_width", self.main.dockWidgetContents_rigth.width())
        self.configIDE.set("Main", "bottom_area_height", self.main.dockWidgetContents_bottom.height()-3)
        return False


    #----------------------------------------------------------------------
    def tab_bottoms_changed(self, event):

        self.toggle_bottom_area(expand=True)


    #----------------------------------------------------------------------
    def toggle_editor_area(self, expand):

        self.toggle_right_area(not expand)
        self.toggle_bottom_area(not expand)
        self.toggle_toolbars(not expand)
        self.main.actionToolbars.setChecked(not expand)

        self.main.actionMenubar.setChecked(not expand)
        self.main.menubar.setVisible(expand)
        self.main.actionMenubar.setVisible(not expand)


    #----------------------------------------------------------------------
    def move_side_dock(self):

        side = self.dockWidgetArea(self.main.dockWidget_right)
        self.configIDE.set("Main", "dock_tools", side.name)

        if side.name == "RightDockWidgetArea":
            self.addDockWidget(QtCore.Qt.DockWidgetArea(QtCore.Qt.LeftDockWidgetArea), self.main.dockWidget_right)
            self.main.tabWidget_tools.setTabPosition(QtGui.QTabWidget.East)
            self.main.actionMove_vertical_tool_area.setText("Move vertical tool area to right")
        else:
            self.addDockWidget(QtCore.Qt.DockWidgetArea(QtCore.Qt.RightDockWidgetArea), self.main.dockWidget_right)
            self.main.tabWidget_tools.setTabPosition(QtGui.QTabWidget.West)
            self.main.actionMove_vertical_tool_area.setText("Move vertical tool area to left")


    #----------------------------------------------------------------------
    def drag_tab(self, *args, **kwargs):
        """"""
        logging.debug("DRAG")



    # #----------------------------------------------------------------------
    # def pop_out(self, widget):
        # """"""
        # index = self.main.tabWidget_bottom.indexOf(widget)
        # if index != -1:
            # tab_name = self.main.tabWidget_bottom.tabText(index)
            # self.main.tabWidget_bottom.removeTab(index)
            # self.floating_tab = Window()
            # self.floating_tab.tab.addTab(widget, tab_name)
            # self.floating_tab.show()



    #----------------------------------------------------------------------
    def get_current_editor(self):
        """"""
        return self.main.tabWidget_files.currentWidget()


    #----------------------------------------------------------------------
    def set_editable(self):
        """"""
        editor = self.get_current_editor()
        editor.text_edit.setReadOnly(False)
        self.main.tabWidget_files.setTabText(self.main.tabWidget_files.currentIndex(), os.path.basename(editor.path))


    # #----------------------------------------------------------------------
    # def open_as_blocks(self):
        # """"""
        # editor = self.get_current_editor()
        # code = editor.text_edit.toPlainText()
        # code = self.pinguinoAPI.remove_comments(code)
        # blocks = self.PinguinoKIT.code_to_blocks(code)
        # self.PinguinoKIT.open_from_source(blocks)
        # self.switch_ide_mode(graphical=True)


    #----------------------------------------------------------------------
    def check_files(self):
        """"""
        if not os.path.exists(os.path.join(os.getenv("PINGUINO_USER_PATH"), "reserved.pickle")):
            self.update_reserved_words()
            self.update_instaled_reserved_words()


    #----------------------------------------------------------------------
    def reset_instalation(self):
        """"""
        path = os.getenv("PINGUINO_USER_PATH")
        if Dialogs.confirm_message(self, "This function remove some files from {} and restart the IDE.\nthis could fix some bugs".format(path)):

            import post_install
            self.restart_now()


    #----------------------------------------------------------------------
    def resize_toolbar(self, size, action):

        def resize_icons():
            for toolbar in self.toolbars:
                toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
                toolbar.setIconSize(QtCore.QSize(size, size))

            [act.setChecked(False) for act in self.main.menuIcons_size.actions()]
            action.setChecked(True)
            self.configIDE.set("Main", "icons_size", size)

            self.toolbutton_menutoolbar.setIconSize(QtCore.QSize(size, size))

        return resize_icons



    #----------------------------------------------------------------------
    def change_icon_theme(self, theme, action):

        def set_theme():
            QtGui.QIcon.setThemeName(theme)
            self.reload_toolbar_icons()
            self.configIDE.set("Main", "theme", theme)
            self.configIDE.save_config()

            [act.setChecked(False) for act in self.main.menuIcons_theme.actions()]
            action.setChecked(True)

        return set_theme



    #----------------------------------------------------------------------
    def is_graphical(self):
        return self.main.actionSwitch_ide.isChecked()


    #----------------------------------------------------------------------
    def is_widget(self):
        tab = self.get_tab()
        editor = tab.currentWidget()
        if editor is None: return False
        return getattr(editor, "is_widget", False)


    #----------------------------------------------------------------------
    def is_autocomplete_enable(self):
        return self.main.actionAutocomplete.isChecked()


    #----------------------------------------------------------------------
    def update_actions_for_text(self):
        normal = False
        # self.main.menuGraphical.setEnabled(normal
        self.main.menubar.removeAction(self.main.menuGraphical.menuAction())

        self.main.lineEdit_blocks_search.setVisible(normal)
        self.main.label_search_block.setVisible(normal)
        self.main.tabWidget_blocks.setVisible(normal)
        self.main.tabWidget_tools.setVisible(not normal)

        # self.main.dockWidget_blocks.setVisible(normal)
        # self.main.dockWidget_right.setVisible(not normal)
        # self.main.toolBar_search_replace.setVisible(not normal)
        # self.main.toolBar_edit.setVisible(not normal)
        # self.main.toolBar_graphical.setVisible(normal)
        # self.main.toolBar_undo_redo.setVisible(not normal)

        self.main.actionSave_image.setVisible(normal)
        self.main.actionUndo.setVisible(not normal)
        self.main.actionRedo.setVisible(not normal)
        self.main.actionCopy.setVisible(not normal)
        self.main.actionCut.setVisible(not normal)
        self.main.actionPaste.setVisible(not normal)
        self.main.actionSearch.setVisible(not normal)

        #self.configIDE.set("Features", "terminal_on_graphical", self.main.dockWidget_output.isVisible())
        # self.main.dockWidget_output.setVisible(self.configIDE.config("Features", "terminal_on_text", True))
        # self.main.actionPython_shell.setChecked(self.configIDE.config("Features", "terminal_on_text", True))
        self.configIDE.save_config()


    #----------------------------------------------------------------------
    def update_actions_for_graphical(self):
        normal = True
        # self.main.menuGraphical.setEnabled(normal)
        self.main.menubar.insertMenu(self.main.menuHelp.menuAction(), self.main.menuGraphical)

        self.main.lineEdit_blocks_search.setVisible(normal)
        self.main.label_search_block.setVisible(normal)
        self.main.tabWidget_blocks.setVisible(normal)
        self.main.tabWidget_tools.setVisible(not normal)

        # self.main.dockWidget_blocks.setVisible(normal)
        # self.main.dockWidget_right.setVisible(not normal)
        # self.main.toolBar_search_replace.setVisible(not normal)
        # self.main.toolBar_edit.setVisible(not normal)
        # self.main.toolBar_graphical.setVisible(normal)
        # self.main.toolBar_undo_redo.setVisible(not normal)


        self.main.actionSave_image.setVisible(normal)
        self.main.actionUndo.setVisible(not normal)
        self.main.actionRedo.setVisible(not normal)
        self.main.actionCopy.setVisible(not normal)
        self.main.actionCut.setVisible(not normal)
        self.main.actionPaste.setVisible(not normal)
        self.main.actionSearch.setVisible(not normal)

        #self.configIDE.set("Features", "terminal_on_text", self.main.dockWidget_output.isVisible())
        # self.main.dockWidget_output.setVisible(self.configIDE.config("Features", "terminal_on_graphical", False))
        # self.main.actionPython_shell.setChecked(self.configIDE.config("Features", "terminal_on_graphical", False))
        self.configIDE.save_config()


    #----------------------------------------------------------------------
    def reload_toolbar_icons(self):

        self.toolbars = [self.main.toolBar,
                         self.main.toolBar_menu,
                         self.main.toolBar_switch,
                         ]

        for toolbar in self.toolbars:
            toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)  #explicit IconOnly for windows
            size = self.configIDE.config("Main", "icons_size", 24)
            self.resize_toolbar(size, getattr(self.main, "action%dx%d"%(size, size)))()
            getattr(self.main, "action%dx%d"%(size, size)).setChecked(True)

        icons_toolbar = [
                         (self.main.actionNew_file, "document-new"),
                         (self.main.actionOpen_file, "document-open"),
                         (self.main.actionSave_file, "document-save"),

                         (self.main.actionUndo, "edit-undo"),
                         (self.main.actionRedo, "edit-redo"),
                         (self.main.actionCut, "edit-cut"),
                         (self.main.actionCopy, "edit-copy"),
                         (self.main.actionPaste, "edit-paste"),

                         (self.main.actionSearch, "edit-find"),
                         # (self.main.actionSearch_and_replace, "edit-find"),

                         (self.main.actionSelect_board, "applications-electronics"),
                         (self.main.actionCompile, "system-run"),
                         (self.main.actionUpload, "emblem-downloads"),

                         (self.main.actionSave_image, "applets-screenshooter"),

                         (self.toolbutton_menutoolbar, "preferences-system"),

                        ]

        for action, icon_name in icons_toolbar:
            if QtGui.QIcon.hasThemeIcon(icon_name):
                icon = QtGui.QIcon.fromTheme(icon_name)
                action.setIcon(icon)
                action.setVisible(True)
            else:
                action.setVisible(False)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QIcon.fromTheme("insert-text").pixmap(size), QtGui.QIcon.Normal, QtGui.QIcon.On)
        icon.addPixmap(QtGui.QIcon.fromTheme("insert-object").pixmap(size), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.main.actionSwitch_ide.setIcon(icon)


    #----------------------------------------------------------------------
    def set_icon_theme(self):

        QtGui.QIcon.setThemeSearchPaths(QtGui.QIcon.themeSearchPaths()+[os.path.join(os.getenv("PINGUINO_DATA"), "qtgui", "resources", "themes")])
        #paths = filter(lambda path:os.path.isdir(path), QtGui.QIcon.themeSearchPaths())
        paths = [path for path in QtGui.QIcon.themeSearchPaths() if os.path.isdir(path)]
        themes = [(path, os.listdir(path)) for path in paths]

        valid_themes = []
        for path, list_themes in themes:
            for theme in list_themes:
                if os.path.isdir(os.path.join(path, theme)): valid_themes.append(theme)

        self.main.menuIcons_theme.clear()

        dict_themes = {}
        for theme in valid_themes:
            action = QtGui.QAction(self)
            action.setCheckable(True)
            action.setText(theme.capitalize().replace("-", " "))
            self.connect(action, QtCore.SIGNAL("triggered()"), self.change_icon_theme(theme, action))
            dict_themes[theme] = action
            self.main.menuIcons_theme.addAction(action)

        theme = self.configIDE.config("Main", "theme", "pinguino11")
        if not theme in valid_themes:
            theme = "pinguino11"
            self.configIDE.set("Main", "theme", "pinguino11")
        self.change_icon_theme(theme, dict_themes[theme])()
        dict_themes[theme].setChecked(True)


    #----------------------------------------------------------------------
    def get_systeminfo(self):

        data = {}
        try: data["os.name"] = str(os.name)
        except: pass
        try: data["os.environ"] = str(os.environ)
        except: pass
        try: data["os.uname"] = str(os.uname())
        except: pass
        try: data["sys.argv"] = str(sys.argv)
        except: pass
        try: data["sys.flags"] = str(sys.flags)
        except: pass
        try: data["sys.platform"] = str(sys.platform)
        except: pass
        try: data["sys.version"] = str(sys.version)
        except: pass
        try: data["platform.architecture"] = str(platform.architecture())
        except: pass
        try: data["platform.dist"] = str(platform.dist())
        except: pass
        try: data["platform.linux_distribution"] = str(platform.linux_distribution())
        except: pass
        try: data["platform.mac_ver"] = str(platform.mac_ver())
        except: pass
        try: data["platform.system"] = str(platform.system())
        except: pass
        try: data["platform.win32_ver"] = str(platform.win32_ver())
        except: pass
        try: data["platform.libc_ver"] = str(platform.libc_ver())
        except: pass
        try: data["platform.machine"] = str(platform.machine())
        except: pass
        try: data["platform.platform"] = str(platform.platform())
        except: pass
        try: data["platform.release"] = str(platform.release())
        except: pass

        return "\n" + "#" + "-" * 80 + "\n#" + "-" * 80 + "\n" + "\n".join([": ".join(item) for item in data.items()]) + "\n#" + "-" * 80 + "\n#" + "-" * 80


    #----------------------------------------------------------------------
    def build_menutoolbar(self):

        self.toolbutton_menutoolbar = QtGui.QToolButton(self)
        self.toolbutton_menutoolbar.setPopupMode(QtGui.QToolButton.MenuButtonPopup)
        menu = QtGui.QMenu()

        icon = QtGui.QIcon.fromTheme("preferences-system")
        self.toolbutton_menutoolbar.setIcon(icon)

        menu.addMenu(self.main.menuFile)
        menu.addMenu(self.main.menuEdit)
        menu.addMenu(self.main.menuProject)
        menu.addMenu(self.main.menuSettings)
        menu.addMenu(self.main.menuSource)
        menu.addMenu(self.main.menuPinguino)
        menu.addMenu(self.main.menuGraphical)
        menu.addMenu(self.main.menuTools)
        menu.addMenu(self.main.menuHelp)

        menu.addSeparator()
        menu.addAction(self.main.actionMenubar)

        self.toolbutton_menutoolbar.setMenu(menu)
        self.main.toolBar_menu.addWidget(self.toolbutton_menutoolbar)

    #----------------------------------------------------------------------
    @Decorator.connect_features()
    def new_file(self, *args, **kwargs):
        path = kwargs.get("filename", self.__get_name__())
        filename = os.path.split(path)[1]
        editor = PinguinoCodeEditor()
        self.main.tabWidget_files.addTab(editor, filename)
        #editor.text_edit.insertPlainText(Snippet["file {snippet}"][1].replace("\t", ""))
        #editor.text_edit.insertPlainText("\n")
        #editor.text_edit.insertPlainText(Snippet["Bare minimum {snippet}"][1].replace("\t", ""))

        tc = editor.text_edit.textCursor()
        editor.text_edit.insert("file {snippet}")
        tc.movePosition(tc.End)
        tc.insertText("\n\n")
        editor.text_edit.setTextCursor(tc)
        editor.text_edit.insert("Bare minimum {snippet}")

        self.main.tabWidget_files.setCurrentWidget(editor)
        editor.text_edit.textChanged.connect(self.__text_changed__)
        editor.text_edit.undoAvailable.connect(self.__text_can_undo__)
        editor.text_edit.redoAvailable.connect(self.__text_can_redo__)
        editor.text_edit.copyAvailable.connect(self.__text_can_copy__)
        editor.text_edit.dropEvent = self.__drop__
        editor.text_edit.keyPressEvent = self.__key_press__
        editor.text_edit.contextMenuEvent = self.file_edit_context_menu
        editor.text_edit.setAcceptRichText(False)
        self.main.tabWidget_files.setTabText(self.main.tabWidget_files.currentIndex(), filename[:-1])
        editor.text_edit.setFocus()


    #----------------------------------------------------------------------
    def open_files(self):

        editor = self.main.tabWidget_files.currentWidget()
        path = getattr(editor, "path", None)
        if path: path = os.path.dirname(path)
        else: path = QtCore.QDir.home().path()
        filenames = Dialogs.set_open_file(self, path)

        for filename in filenames:
            if self.__check_duplicate_file__(filename): continue

            self.update_recents(filename)
            if filename.endswith(".gpde"):
                self.switch_ide_mode(True)
                self.PinguinoKIT.open_files(filename=filename)
                return
            elif filename.endswith(".pde"):
                self.switch_ide_mode(False)

            self.new_file(os.path.split(filename)[1])
            editor = self.main.tabWidget_files.currentWidget()
            pde_file = codecs.open(filename, "r", "utf-8")
            content = "".join(pde_file.readlines())
            pde_file.close()
            editor.text_edit.setPlainText(content)
            setattr(editor, "path", filename)
            setattr(editor, "last_saved", content)
            self.main.tabWidget_files.setTabToolTip(self.main.tabWidget_files.currentIndex(), filename)
            self.main.tabWidget_files.setTabText(self.main.tabWidget_files.currentIndex(), os.path.split(filename)[1])
            #self.update_recents(filename)
            self.check_backup_file(editor=editor)

        self.tab_changed()


    #----------------------------------------------------------------------
    @Decorator.connect_features()
    def save_file(self, *args, **kwargs):

        editor = kwargs.get("editor", None)
        if not editor: editor = self.get_tab().currentWidget()
        index = self.get_tab().indexOf(editor)
        filename = self.main.tabWidget_files.tabText(index)
        save_path = getattr(editor, "path", None)

        if not save_path:
            save_path, filename = Dialogs.set_save_file(self, filename)
            if not save_path: return False
            setattr(editor, "path", save_path)
            self.main.tabWidget_files.setTabText(index, filename)
            self.main.tabWidget_files.setTabToolTip(index, save_path)
            self.setWindowTitle(os.getenv("PINGUINO_FULLNAME")+" - "+save_path)

            self.update_recents(save_path)

        self.__save_file__(editor=editor)
        return True


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def close_file(self, *args, **kwargs):
        editor = kwargs.get("editor", None)
        if not editor: editor = self.get_tab().currentWidget()
        index = self.get_tab().indexOf(editor)
        filename = self.get_tab().tabText(index)
        save_path = getattr(editor, "path", None)

        if not save_path and filename.endswith("*"):
            reply = Dialogs.set_no_saved_file(self, filename)

            if reply == True:
                save_path, filename = Dialogs.set_save_file(self, filename)
                if not save_path: return
                setattr(editor, "path", save_path)
                self.__save_file__(editor=editor)

            elif reply == None: return

        elif filename.endswith("*"):
            reply = Dialogs.set_no_saved_file(self, filename)
            #print reply
            if reply == True: self.__save_file__(editor=editor)
            elif reply == None: return

        self.get_tab().removeTab(index)


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.connect_features()
    def save_as(self, *args, **kwargs):
        editor = kwargs.get("editor", None)
        if not editor: editor = self.get_tab().currentWidget()
        index = self.get_tab().indexOf(editor)
        #editor = self.main.tabWidget_files.currentWidget()
        #index = self.main.tabWidget_files.currentIndex()
        filename = self.main.tabWidget_files.tabText(index)
        save_path = getattr(editor, "path", None)
        if save_path is None: save_path = filename

        save_path, filename = Dialogs.set_save_file(self, save_path)
        if not save_path: return False
        setattr(editor, "path", save_path)
        self.main.tabWidget_files.setTabText(index, filename)
        self.main.tabWidget_files.setTabToolTip(index, save_path)
        self.setWindowTitle(os.getenv("PINGUINO_FULLNAME")+" - "+save_path)

        self.__save_file__(editor=editor)
        return True


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def save_all(self):
        tab = self.get_tab()
        for index in range(tab.count()):
            self.save_file(editor=tab.widget(index))


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def close_all(self):
        tab = self.get_tab()
        widgets = map(tab.widget, range(tab.count()))
        for widget in widgets:
            self.close_file(editor=widget)

    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def close_others(self):
        tab = self.get_tab()
        current = tab.currentWidget()
        widgets = map(tab.widget, range(tab.count()))
        for widget in widgets:
            if widget == current: continue
            self.close_file(editor=widget)

    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def print_file(self):
        #Bug: no print to file, this is PySide bug.
        editor = self.get_tab().currentWidget()
        filename = self.get_tab().tabText(self.get_tab().currentIndex()).replace(".pde", ".pdf")
        QPrinter = QtGui.QPrinter
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.Letter)
        printer.setOutputFileName(filename)
        printer.setDocName(filename)
        printer.setPageOrder(QPrinter.FirstPageFirst)
        printer.setOutputFormat(QPrinter.PdfFormat)
        preview = QtGui.QPrintDialog(printer)
        preview.setStyleSheet("""
        font-family: inherit;
        font-weight: normal;

        """)
        if preview.exec_():
            document = editor.text_edit.document()
            document.print_(printer)


    #----------------------------------------------------------------------
    def __close_ide__(self, *args, **kwargs):

        self.configIDE.set("Main", "size", self.size().toTuple())
        self.configIDE.set("Main", "position", self.pos().toTuple())
        self.configIDE.set("Main", "maximized", self.isMaximized())
        #self.configIDE.set("Main", "terminal_height", self.main.dockWidget_output.height())

        # side = self.dockWidgetArea(self.main.dockWidget_right)
        # self.configIDE.set("Main", "dock_tools", side.name.decode())

        # side = self.dockWidgetArea(self.main.dockWidget_blocks)
        # self.configIDE.set("Main", "dock_blocks", side.name.decode())

        # side = self.dockWidgetArea(self.main.dockWidget_output)
        # self.configIDE.set("Main", "dock_shell", side.name.decode())

        self.configIDE.set("Main", "menubar", self.main.menubar.isVisible())

        count = 1
        self.configIDE.clear_recents()
        for file_ in self.recent_files:
            self.configIDE.set("Recents", "recent_"+str(count), file_)
            count += 1

        count = 1
        self.configIDE.clear_recents(section="RecentsProjects")
        for file_ in self.recent_projects:
            self.configIDE.set("RecentsProjects", "recent_"+str(count), file_)
            count += 1

        count = 1
        self.configIDE.clear_recents_open()
        for file_ in self.get_all_open_files():
            self.configIDE.set("Recents", "open_"+str(count), file_)
            count += 1

        self.configIDE.set("Features", "graphical", self.is_graphical())

        # self.configIDE.set("Features", "debug_in_output", self.main.checkBox_output_debug.isChecked())
        # self.configIDE.set("Features", "out_in_output", self.main.checkBox_output_messages.isChecked())

        self.configIDE.save_config()

        self.close()


    # Menu Edit

    #----------------------------------------------------------------------
    def undo(self):
        editor = self.main.tabWidget_files.currentWidget()
        #index = self.main.tabWidget_files.currentIndex()
        editor.text_edit.undo()


    #----------------------------------------------------------------------
    def redo(self):
        editor = self.main.tabWidget_files.currentWidget()
        #index = self.main.tabWidget_files.currentIndex()
        editor.text_edit.redo()


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def cut(self):
        editor = self.main.tabWidget_files.currentWidget()
        #index = self.main.tabWidget_files.currentIndex()
        editor.text_edit.cut()


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def copy(self):
        editor = self.main.tabWidget_files.currentWidget()
        #index = self.main.tabWidget_files.currentIndex()
        editor.text_edit.copy()


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def paste(self):
        editor = self.main.tabWidget_files.currentWidget()
        #index = self.main.tabWidget_files.currentIndex()
        editor.text_edit.paste()

    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def delete(self):
        editor = self.main.tabWidget_files.currentWidget()
        #index = self.main.tabWidget_files.currentIndex()
        tc = editor.text_edit.textCursor()
        if tc.selectedText(): tc.removeSelectedText()

    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def select_all(self):
        editor = self.main.tabWidget_files.currentWidget()
        #index = self.main.tabWidget_files.currentIndex()
        editor.text_edit.selectAll()


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def set_tab_search(self, mode):

        self.main.tabWidget_tools.setCurrentWidget(self.main.SearchReplace)

        self.main.lineEdit_search.setFocus()
        editor = self.main.tabWidget_files.currentWidget()
        cursor = editor.text_edit.textCursor()
        self.main.lineEdit_search.setText(cursor.selectedText())

        replace = (mode == "replace")
        self.main.lineEdit_replace.setVisible(replace)
        self.main.label_replace.setVisible(replace)
        self.main.pushButton_replace.setVisible(replace)
        self.main.pushButton_replace_all.setVisible(replace)

    # Menu Source

    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def commentregion(self):
        editor = self.main.tabWidget_files.currentWidget()
        comment_wildcard = "// "

        #cursor is a COPY all changes do not affect the QPlainTextEdit's cursor!!!
        cursor = editor.text_edit.textCursor()

        text = cursor.selectedText()

        if text == "":  #no selected, single line
            start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
            startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()
            endPosition = editor.text_edit.document().findBlockByLineNumber(start+1).position() - 1

            cursor.setPosition(startPosition)
            cursor.setPosition(endPosition, QtGui.QTextCursor.KeepAnchor)
            editor.text_edit.setTextCursor(cursor)

        else:
            start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
            startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()


            end = editor.text_edit.document().findBlock(cursor.selectionEnd()).firstLineNumber()

            endPosition = editor.text_edit.document().findBlockByLineNumber(end+1).position() - 1

            cursor.setPosition(startPosition)
            cursor.setPosition(endPosition, QtGui.QTextCursor.KeepAnchor)
            editor.text_edit.setTextCursor(cursor)


        cursor = editor.text_edit.textCursor()

        start_ = cursor.selectionStart()
        end_ = cursor.selectionEnd()

        #selectionEnd = cursor.selectionEnd()
        start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
        end = editor.text_edit.document().findBlock(cursor.selectionEnd()).firstLineNumber()
        startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()

        #init=(start, end)
        #Start a undo block
        cursor.beginEditBlock()

        #Move the COPY cursor
        cursor.setPosition(startPosition)
        #Move the QPlainTextEdit Cursor where the COPY cursor IS!
        editor.text_edit.setTextCursor(cursor)
        editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)

        for i in comment_wildcard:
            editor.text_edit.moveCursor(QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor)

        start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()

        editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)
        s = editor.text_edit.cursor()
        s.pos()
        for i in xrange(start, end + 1):
            editor.text_edit.textCursor().insertText(comment_wildcard)
            #cursor.insertText(comment_wildcard)
            editor.text_edit.moveCursor(QtGui.QTextCursor.Down)
            editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)

        editor.text_edit.moveCursor(QtGui.QTextCursor.EndOfLine)

        end_ += (end + 1 - start) * len(comment_wildcard)
        cursor.setPosition(start_)
        cursor.setPosition(end_, QtGui.QTextCursor.KeepAnchor)
        editor.text_edit.setTextCursor(cursor)

        #End a undo block
        cursor.endEditBlock()


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def uncommentregion(self):

        editor = self.main.tabWidget_files.currentWidget()
        comment_wildcard = "// "

        #cursor is a COPY all changes do not affect the QPlainTextEdit's cursor!!!
        cursor = editor.text_edit.textCursor()

        start_ = cursor.selectionStart()
        end_ = cursor.selectionEnd()

        start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
        end = editor.text_edit.document().findBlock(cursor.selectionEnd()).firstLineNumber()
        startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()

        #Start a undo block
        cursor.beginEditBlock()

        #Move the COPY cursor
        cursor.setPosition(startPosition)
        #Move the QPlainTextEdit Cursor where the COPY cursor IS!
        editor.text_edit.setTextCursor(cursor)
        editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)
        for i in xrange(start, end + 1):

            for i in comment_wildcard:
                editor.text_edit.moveCursor(QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor)

            text = editor.text_edit.textCursor().selectedText()
            if text == comment_wildcard:
                editor.text_edit.textCursor().removeSelectedText()
            elif u'\u2029' in text:
                #\u2029 is the unicode char for \n
                #if there is a newline, rollback the selection made above.
                editor.text_edit.moveCursor(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor)

            editor.text_edit.moveCursor(QtGui.QTextCursor.Down)
            editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)

        end_ -= (end + 1 - start) * len(comment_wildcard)
        cursor.setPosition(start_)
        cursor.setPosition(end_, QtGui.QTextCursor.KeepAnchor)
        editor.text_edit.setTextCursor(cursor)

        #End a undo block
        cursor.endEditBlock()


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def comment_uncomment(self):
        editor, cursor, prevCursor, selected, firstLine = self.select_block_edit()

        if firstLine != False:
            if firstLine.startswith("//"): self.uncommentregion()
            else: self.commentregion()

        if not selected:
            cursor.clearSelection()
            editor.text_edit.setTextCursor(prevCursor)


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def indentregion(self):
        editor, cursor, prevCursor, selected, firstLine = self.select_block_edit()

        if firstLine != False:

            editor = self.main.tabWidget_files.currentWidget()
            comment_wildcard = " " * 4

            #cursor is a COPY all changes do not affect the QPlainTextEdit's cursor!!!
            cursor = editor.text_edit.textCursor()

            text = cursor.selectedText()

            if text == "":  #no selected, single line
                start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
                startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()
                endPosition = editor.text_edit.document().findBlockByLineNumber(start+1).position() - 1

                cursor.setPosition(startPosition)
                cursor.setPosition(endPosition, QtGui.QTextCursor.KeepAnchor)
                editor.text_edit.setTextCursor(cursor)

            else:
                start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
                startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()


                end = editor.text_edit.document().findBlock(cursor.selectionEnd()).firstLineNumber()

                endPosition = editor.text_edit.document().findBlockByLineNumber(end+1).position() - 1

                cursor.setPosition(startPosition)
                cursor.setPosition(endPosition, QtGui.QTextCursor.KeepAnchor)
                editor.text_edit.setTextCursor(cursor)


            cursor = editor.text_edit.textCursor()

            start_ = cursor.selectionStart()
            end_ = cursor.selectionEnd()

            #selectionEnd = cursor.selectionEnd()
            start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
            end = editor.text_edit.document().findBlock(cursor.selectionEnd()).firstLineNumber()
            startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()

            #init=(start, end)
            #Start a undo block
            cursor.beginEditBlock()

            #Move the COPY cursor
            cursor.setPosition(startPosition)
            #Move the QPlainTextEdit Cursor where the COPY cursor IS!
            editor.text_edit.setTextCursor(cursor)
            editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)

            for i in comment_wildcard:
                editor.text_edit.moveCursor(QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor)

            start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()

            editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)
            s = editor.text_edit.cursor()
            s.pos()
            for i in xrange(start, end + 1):
                editor.text_edit.textCursor().insertText(comment_wildcard)
                #cursor.insertText(comment_wildcard)
                editor.text_edit.moveCursor(QtGui.QTextCursor.Down)
                editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)

            editor.text_edit.moveCursor(QtGui.QTextCursor.EndOfLine)

            end_ += (end + 1 - start) * len(comment_wildcard)
            cursor.setPosition(start_)
            cursor.setPosition(end_, QtGui.QTextCursor.KeepAnchor)
            editor.text_edit.setTextCursor(cursor)

            #End a undo block
            cursor.endEditBlock()


        if not selected:
            cursor.clearSelection()
            editor.text_edit.setTextCursor(prevCursor)



    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_text_mode()
    def dedentregion(self):
        editor, cursor, prevCursor, selected, firstLine = self.select_block_edit()

        if firstLine != False and firstLine.startswith(" "*4):

            editor = self.main.tabWidget_files.currentWidget()
            comment_wildcard = " " * 4

            #cursor is a COPY all changes do not affect the QPlainTextEdit's cursor!!!
            cursor = editor.text_edit.textCursor()

            start_ = cursor.selectionStart()
            end_ = cursor.selectionEnd()

            start = editor.text_edit.document().findBlock(cursor.selectionStart()).firstLineNumber()
            end = editor.text_edit.document().findBlock(cursor.selectionEnd()).firstLineNumber()
            startPosition = editor.text_edit.document().findBlockByLineNumber(start).position()

            #Start a undo block
            cursor.beginEditBlock()

            #Move the COPY cursor
            cursor.setPosition(startPosition)
            #Move the QPlainTextEdit Cursor where the COPY cursor IS!
            editor.text_edit.setTextCursor(cursor)
            editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)
            for i in xrange(start, end + 1):

                for i in comment_wildcard:
                    editor.text_edit.moveCursor(QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor)

                text = editor.text_edit.textCursor().selectedText()
                if text == comment_wildcard:
                    editor.text_edit.textCursor().removeSelectedText()
                elif u'\u2029' in text:
                    #\u2029 is the unicode char for \n
                    #if there is a newline, rollback the selection made above.
                    editor.text_edit.moveCursor(QtGui.QTextCursor.Left, QtGui.QTextCursor.KeepAnchor)

                editor.text_edit.moveCursor(QtGui.QTextCursor.Down)
                editor.text_edit.moveCursor(QtGui.QTextCursor.StartOfLine)

            end_ -= (end + 1 - start) * len(comment_wildcard)
            cursor.setPosition(start_)
            cursor.setPosition(end_, QtGui.QTextCursor.KeepAnchor)
            editor.text_edit.setTextCursor(cursor)

            #End a undo block
            cursor.endEditBlock()

        if not selected:
            cursor.clearSelection()
            editor.text_edit.setTextCursor(prevCursor)


    # Pinguino

    #----------------------------------------------------------------------
    def __show_libmanager__(self):
        self.frame_stdout = LibManager(self)
        self.frame_stdout.show()


    #----------------------------------------------------------------------
    def __config_paths__(self):
        self.frame_paths = Paths(self)
        self.frame_paths.show()


    #----------------------------------------------------------------------
    @Decorator.show_tab("BoardConfig")
    def __show_board_config__(self):
        pass


    #----------------------------------------------------------------------
    def __show_submit_bug__(self):
        self.submit_bug = SubmitBug(self)
        self.submit_bug.show()


    #----------------------------------------------------------------------
    def __show_patches__(self):
        self.patches = Patches(self)
        patches = self.patches.get_patches()

        if patches == 0:
            Dialogs.info_message(self, "There are no new updates available.\n %s is up to date" % os.getenv("PINGUINO_FULLNAME"))
            self.patches.close()
        if patches is None:
            self.patches.close()
        else:
            self.patches.show()


    #----------------------------------------------------------------------
    def __show_hex_code__(self):
        if getattr(self.get_tab().currentWidget(), "path", False):
            hex_filename = self.get_tab().currentWidget().path.replace(".gpde", ".pde").replace(".pde", ".hex")
        else:
            Dialogs.error_message(self, QtGui.QApplication.translate("Dialogs", "You must compile before."))
            return
        if os.path.isfile(hex_filename):

            hex_obj = IntelHex(open(hex_filename, "r"))
            hex_dict = hex_obj.todict()
            rows = int(ceil(max(hex_dict.keys()) / float(0x18)))

            if rows < 1e3:
                self.frame_hex_viewer = HexViewer(self, hex_obj, hex_filename)
                self.frame_hex_viewer.show()
            else:
                file_ = codecs.open(hex_filename, "r", "utf-8")
                content = file_.readlines()
                file_.close
                self.frame_hex_plain = PlainOut(hex_filename, "".join(content), highlight=True)
                self.frame_hex_plain.show()

        else:
            Dialogs.error_message(self, QtGui.QApplication.translate("Dialogs", "You must compile before."))


    #----------------------------------------------------------------------
    @Decorator.show_tab("Stdout")
    def __show_stdout__(self):
        pass
        # self.frame_stdout = PlainOut("Stdout")
        # self.frame_stdout.show()


    # #----------------------------------------------------------------------
    # def __show_environ__(self, debug):
        # self.frame_environ = EnvironViewer(self, debug)
        # self.frame_environ.show()


    #----------------------------------------------------------------------
    def __show_main_c__(self):

        source = os.path.join(os.getenv("PINGUINO_USER_PATH"), "source")
        board = self.configIDE.config("Board", "arch", 8)
        if board == 32: extra = "32"
        else: extra = ""
        filename = os.path.join(source, "main%s.c"%extra)
        self.open_file_from_path(filename=filename, readonly=True)


    #----------------------------------------------------------------------
    def __show_define_h__(self):

        filename = os.path.join(os.getenv("PINGUINO_USER_PATH"), "source", "define.h")
        self.open_file_from_path(filename=filename, readonly=True)

    #----------------------------------------------------------------------
    def __show_user_c__(self):

        filename = os.path.join(os.getenv("PINGUINO_USER_PATH"), "source", "user.c")
        self.open_file_from_path(filename=filename, readonly=True)


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_file_saved()
    @Decorator.requiere_can_compile()
    def pinguino_compile(self, dialog_upload=True):

        filename = self.get_tab().currentWidget().path

        if not self.is_graphical():
            if os.getenv("PINGUINO_PROJECT"):
                filenames = self.get_project_files()
                compile_code = lambda :self.pinguinoAPI.compile_file(filenames)
            else:
                compile_code = lambda :self.pinguinoAPI.compile_file([filename])

        else:
            compile_code = lambda :self.pinguinoAPI.compile_string(self.PinguinoKIT.get_pinguino_source_code())


        self.write_log(QtGui.QApplication.translate("Frame", "Compiling: %s")%filename)
        self.write_log(self.get_description_board())

        compile_code()
        self.update_stdout()
        self.post_compile(dialog_upload)

    #----------------------------------------------------------------------
    def post_compile(self, dialog_upload=True):

        self.main.actionUpload.setEnabled(self.pinguinoAPI.compiled())
        if not self.pinguinoAPI.compiled():

            # errors_preprocess = self.pinguinoAPI.get_errors_preprocess()
            # if errors_preprocess:
                # for error in errors_preprocess:
                    # self.write_log("ERROR: {}".format(errors_preprocess))

            errors_c = self.pinguinoAPI.get_errors_compiling_c()
            if errors_c:
                self.write_log("ERROR: {complete_message}".format(**errors_c))
                line_errors = errors_c["line_numbers"]
                for line_error in line_errors:
                    self.highligh_line(line_error, "#ff7f7f")

            errors_asm = self.pinguinoAPI.get_errors_compiling_asm()
            if errors_asm:
                for error in errors_asm["error_symbols"]:
                    self.write_log("ERROR: {}".format(error))

            errors_linking = self.pinguinoAPI.get_errors_linking()
            if errors_linking:
                for error in errors_linking["linking"]:
                    self.write_log("ERROR: "+error)

                line_errors_l = errors_linking["line_numbers"]
                for line_error in line_errors_l:
                    self.highligh_line(line_error, "#ff7f7f")


            if errors_asm or errors_c:
                Dialogs.error_while_compiling(self)
                self.__show_stdout__()
            elif errors_linking:
                Dialogs.error_while_linking(self)
                self.__show_stdout__()
            elif errors_preprocess:
                Dialogs.error_while_preprocess(self)
                self.__show_stdout__()

            else:
                Dialogs.error_while_unknow(self)
                self.__show_stdout__()

        else:
            result = self.pinguinoAPI.get_result()
            self.write_log(QtGui.QApplication.translate("Frame", "compilation done"))
            self.write_log(result["code_size"])
            self.write_log(QtGui.QApplication.translate("Frame", "%s seconds process time")%result["time"])

            if dialog_upload:
                if Dialogs.compilation_done(self):
                    self.pinguino_upload()


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def pinguino_upload(self):
        uploaded, result = self.pinguinoAPI.upload()
        self.write_log(result)
        if uploaded:
            Dialogs.upload_done(self)
        elif Dialogs.upload_fail(self, result):
            self.pinguino_upload()


    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_file_saved()
    def pinguino_compile_and_upload(self):
        self.pinguino_compile(dialog_upload=False)
        if self.pinguinoAPI.compiled():
            self.pinguino_upload()


    #----------------------------------------------------------------------
    def pinguino_upload_hex(self):

        Dialogs.warning_message(self, "Be careful with this feature, ensure that .hex file it is correct.")

        path = QtCore.QDir.home().path()
        filename = Dialogs.set_open_hex(self, path)

        if not filename: return

        self.set_board()
        reply = Dialogs.confirm_board(self)

        if reply == False:
            self.__show_board_config__()
            return False
        elif reply == None:
            return False

        board = self.pinguinoAPI.get_board()
        reply = Dialogs.confirm_message(self, "Do you want upload '%s' to %s"%(filename, board.name))

        if reply:
            self.pinguinoAPI.__hex_file__ = filename
            self.pinguino_upload()







    # Graphical

    #----------------------------------------------------------------------
    def __show_pinguino_code__(self):
        name = getattr(self.get_tab().currentWidget(), "path", "")
        if name: name = " - " + name
        self.frame_pinguino_code = PlainOut(QtGui.QApplication.translate("Dialogs", "Pinguino code"))
        self.frame_pinguino_code.show_text(self.PinguinoKIT.get_pinguino_source_code(), pde=True)
        self.frame_pinguino_code.show()

    #----------------------------------------------------------------------
    def __export_pinguino_code__(self):
        area = self.PinguinoKIT.get_work_area()
        area.export_code_to_pinguino_editor()

    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    @Decorator.requiere_graphical_mode()
    def __insert_block__(self):
        self.frame_insert_block = InsertBlock(self.PinguinoKIT)
        self.frame_insert_block.show()



    # Options

    #----------------------------------------------------------------------
    def switch_autocomplete(self):
        enable = self.main.actionAutocomplete.isChecked()
        self.configIDE.set("Features", "autocomplete", enable)
        self.configIDE.save_config()


    #----------------------------------------------------------------------
    def switch_color_theme(self, pinguino_color=True):
        default_pallete = ["toolBar", "toolBar_switch", "toolBar_menu", "menubar", "statusBar"]

        pinguino_pallete = ["dockWidget_bottom", "dockWidget_right"]

        if pinguino_color:
            self.PinguinoPallete.set_background_pinguino(self.main.centralwidget.parent())
            for element in pinguino_pallete:
                self.PinguinoPallete.set_background_pinguino(getattr(self.main, element))
            for element in default_pallete:
                self.PinguinoPallete.set_default_palette(getattr(self.main, element))
            self.main.label_logo.setPixmap(QtGui.QPixmap(":/logo/art/banner.png"))
        else:
            self.PinguinoPallete.set_default_palette(self.main.centralwidget.parent())
            for element in default_pallete + pinguino_pallete:
                self.PinguinoPallete.set_default_palette(getattr(self.main, element))
            self.main.label_logo.setPixmap(QtGui.QPixmap(":/logo/art/banner_blue.png"))

        self.configIDE.set("Main", "color_theme", pinguino_color)
        self.main.actionColor_theme.setChecked(pinguino_color)


    #----------------------------------------------------------------------
    def switch_confirm_board(self, event=None):
        enable = self.main.actionConfirm_board.isChecked()
        self.configIDE.set("Features", "confirm_board", enable)
        self.configIDE.save_config()


    # Help

    #----------------------------------------------------------------------
    def open_web_site(self, url):
        webbrowser.open_new_tab(url)


    #----------------------------------------------------------------------
    def __show_about__(self):
        self.frame_about = About()
        self.frame_about.show()

    # Tools Files



    # Tools Source


    # Tools Search
    # see search_replace.py


    # Widgets

    #----------------------------------------------------------------------
    @Decorator.update_toolbar()
    @Decorator.connect_features()
    def tab_changed(self, *args, **kwargs):
        self.main.tabWidget_files.setVisible(self.main.tabWidget_files.count() > 0)
        self.main.frame_logo.setVisible(not self.main.tabWidget_files.count() > 0)
        self.main.actionClose_file.setEnabled(self.main.tabWidget_files.count() > 0)

        editor = self.main.tabWidget_files.currentWidget()
        if getattr(editor, "path", None): self.setWindowTitle(os.getenv("PINGUINO_FULLNAME")+" - "+editor.path)
        else: self.setWindowTitle(os.getenv("PINGUINO_FULLNAME"))

        index = self.main.tabWidget_files.currentIndex()
        filename = self.main.tabWidget_files.tabText(index)
        if filename.endswith("*"): self.main.actionSave_file.setEnabled(True)
        else: self.main.actionSave_file.setDisabled(True)

        # self.__update_current_dir_on_files__()


    #----------------------------------------------------------------------
    def tab_close(self, index):
        editor = self.get_tab().widget(index)
        self.close_file(editor=editor)


    # Graphical Tool Bar

    #----------------------------------------------------------------------
    @Decorator.requiere_open_files()
    def save_screen_image(self):
        editor = self.get_tab().currentWidget()
        scroll_area = editor.scroll_area
        image = QtGui.QPixmap.grabWidget(scroll_area,
                                         QtCore.QRect(0, 0,
                                                      scroll_area.width()-13,
                                                      scroll_area.height()-13))

        filename = self.get_tab().tabText(self.get_tab().currentIndex())
        filename = os.path.splitext(filename)[0] + ".png"
        filename = Dialogs.set_save_image(self, filename)
        if filename: image.save(filename, "png")


    #----------------------------------------------------------------------
    def dialog_rename_file(self):
        """"""
        editor = self.get_tab().currentWidget()
        new_name = Dialogs.get_text(self, "Rename file", os.path.basename(editor.path))
        self.rename_file(editor, new_name)




    #----------------------------------------------------------------------
    def rename_file(self, editor, new_name):
        """"""
        filename = os.path.basename(editor.path)
        logging.debug("Renamed {} for {}".format(filename, new_name) )



    #----------------------------------------------------------------------
    def switch_ide_mode(self, graphical):
        self.main.actionSwitch_ide.setChecked(graphical)
        self.main.tabWidget_graphical.setVisible(graphical and self.main.tabWidget_graphical.count() > 0)
        self.main.tabWidget_files.setVisible(not graphical and self.main.tabWidget_files.count() > 0)


        menu = self.toolbutton_menutoolbar.menu()
        if graphical:
            self.update_actions_for_graphical()
            menu.insertMenu(self.main.menuHelp.menuAction(), self.main.menuGraphical)
        else:
            self.update_actions_for_text()
            menu.removeAction(self.main.menuGraphical.menuAction())

        self.tab_changed()



    # Events


    #----------------------------------------------------------------------
    def __key_press__(self, event):
        editor = self.main.tabWidget_files.currentWidget()
        if self.is_autocomplete_enable():
            editor.text_edit.__keyPressEvent__(event)
        else:
            editor.text_edit.force_keyPressEvent(event)


    #----------------------------------------------------------------------
    def __drop__(self, event):
        mine = event.mimeData()
        if mine.hasUrls():
            for path in mine.urls():
                self.open_file_from_path(filename=path.path())



    #----------------------------------------------------------------------
    def tab_files_context_menu(self, event):
        menu = QtGui.QMenu()

        editor = self.get_current_editor()

        if editor.text_edit.isReadOnly():
            menu.addAction("Set editable", self.set_editable)

        else:
            menu.addAction("Rename", self.dialog_rename_file)


        menu.addAction(self.main.actionSave_file)
        menu.addAction(self.main.actionSave_as)
        menu.addAction(self.main.actionSave_all)
        menu.addSeparator()
        menu.addAction(self.main.actionClose_file)
        menu.addAction(self.main.actionClose_all)
        menu.addAction(self.main.actionClose_others)

        menu.setStyleSheet("""
        font-family: inherit;
        font-weight: normal;

        """)

        menu.exec_(event.globalPos())


    #----------------------------------------------------------------------
    def file_edit_context_menu(self, event):
        menu = QtGui.QMenu()

        editor = self.main.tabWidget_files.currentWidget()
        filename = getattr(editor, "path", False)
        if filename and (filename.startswith(os.path.join(os.getenv("PINGUINO_USER_PATH"), "examples")) or filename.startswith(os.path.join(os.getenv("PINGUINO_USER_PATH"), "graphical_examples"))):
            menu.addAction(QtGui.QApplication.translate("Frame", "Restore example"), self.restore_example)
            menu.addSeparator()

        menu.addAction(self.main.actionUndo)
        menu.addAction(self.main.actionRedo)
        menu.addSeparator()
        menu.addAction(self.main.actionCut)
        menu.addAction(self.main.actionCopy)
        menu.addAction(self.main.actionPaste)
        menu.addAction(self.main.actionDelete)
        menu.addSeparator()
        menu.addAction(self.main.actionSelect_all)
        menu.addSeparator()
        menu.addAction(self.main.actionComment_out_region)
        menu.addAction(self.main.actionComment_Uncomment_region)
        menu.addSeparator()
        menu.addAction(self.main.actionIndent)
        menu.addAction(self.main.actionDedent)
        menu.addSeparator()
        menu.addAction(self.main.actionCompile)
        menu.addAction(self.main.actionUpload)
        menu.addAction(self.main.actionIf_Compile_then_Upload)
        menu.addSeparator()
        # menu.addAction(self.main.actionWiki_docs)
        menu.addAction(self.main.actionLibrary_manager)
        menu.addAction(self.main.actionHex_code)
        menu.addAction(self.main.actionSet_paths)
        # menu.addAction(self.main.actionStdout)
        menu.addSeparator()
        menu.addAction(self.main.actionAutocomplete)
        # menu.addAction("Generate blocks", self.open_as_blocks)

        menu.setStyleSheet("""
        QMenu {
            font-family: inherit;
            font-weight: normal;
            }

        """)

        menu.exec_(event.globalPos())


    #----------------------------------------------------------------------
    def restore_example(self):
        editor = self.main.tabWidget_files.currentWidget()
        filename = getattr(editor, "path", False)
        filename_install = filename.replace(os.getenv("PINGUINO_USER_PATH"), os.getenv("PINGUINO_INSTALL_PATH"))
        shutil.copyfile(filename_install, filename)
        self.reload_file()


    #----------------------------------------------------------------------
    def update_mode_output(self, visible):
        if self.is_graphical():
            self.configIDE.set("Features", "terminal_on_graphical", visible)
        else:
            self.configIDE.set("Features", "terminal_on_text", visible)


    # #----------------------------------------------------------------------
    # def toggle_pythonshell(self, visible):
        # self.main.dockWidget_output.setVisible(visible)
        # self.update_mode_output(visible)
        # #self.configIDE.config("Features", "terminal_on_text", visible)


    # #----------------------------------------------------------------------
    # def update_tab_position(self, tab, area):

        # if area.name == "RightDockWidgetArea":
            # tab.setTabPosition(QtGui.QTabWidget.West)
        # elif area.name == "LeftDockWidgetArea":
            # tab.setTabPosition(QtGui.QTabWidget.East)



    #----------------------------------------------------------------------
    def toggle_tab(self, tab_name):
        """"""
        widget = getattr(self.main, tab_name)

        if self.main.tabWidget_bottom.indexOf(widget) != -1:
            index = self.main.tabWidget_bottom.indexOf(widget)
            widget.tab_parent = self.main.tabWidget_bottom
            widget.index = index
            widget.label = self.main.tabWidget_bottom.tabText(index)
            self.main.tabWidget_bottom.removeTab(index)
            self.configIDE.set("TABS", tab_name, False)
            self.configIDE.set("TABS", "{}_name".format(tab_name), tab_name)

        elif self.main.tabWidget_tools.indexOf(widget) != -1:
            index = self.main.tabWidget_tools.indexOf(widget)
            widget.tab_parent = self.main.tabWidget_tools
            widget.index = index
            widget.label = self.main.tabWidget_tools.tabText(index)
            self.main.tabWidget_tools.removeTab(index)
            self.configIDE.set("TABS", tab_name, False)
            self.configIDE.set("TABS", "{}_name".format(tab_name), tab_name)

        else:
            widget.tab_parent.addTab(widget, widget.label)
            i = widget.tab_parent.indexOf(widget)
            widget.tab_parent.tabBar().moveTab(i, widget.index)
            widget.tab_parent.setCurrentIndex(widget.index)
            self.configIDE.set("TABS", tab_name, True)
            self.configIDE.set("TABS", "{}_name".format(tab_name), tab_name)


    #----------------------------------------------------------------------
    def load_tabs_config(self):
        """"""
        names = []
        tabs = self.main.tabWidget_bottom.tabBar()
        for index in range(tabs.count()):
            names.append(self.main.tabWidget_bottom.widget(index).objectName())

        tabs = self.main.tabWidget_tools.tabBar()
        for index in range(tabs.count()):
            names.append(self.main.tabWidget_tools.widget(index).objectName())

        for name in names:
            if not self.configIDE.config("TABS", name, True):
                name = self.configIDE.config("TABS", "{}_name".format(name), None)
                if hasattr(self.main, name):
                    getattr(self.main, "actionTab{}".format(name)).setChecked(False)

