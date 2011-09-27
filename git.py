import os
import sublime
import sublime_plugin
import threading
import subprocess
import functools

def selection(view):
    pass

class CommandThread(threading.Thread):
    def __init__(self, command, on_done, working_dir = ""):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.working_dir = working_dir

    def run(self):
        try:
            if self.working_dir != "":
                os.chdir(self.working_dir)
            output = subprocess.Popen(self.command, stdout=subprocess.PIPE).communicate()[0]
            # if st's python gets bumped to 2.7 we can just do:
            # output = subprocess.check_output(self.command)
            sublime.set_timeout(functools.partial(self.on_done, True, output), 0)
        except subprocess.CalledProcessError, e:
            sublime.set_timeout(functools.partial(self.on_done, False, e.returncode), 0)

        # self.package_list = self.make_package_list(override_action='visit')
        # def show_quick_panel():
        #     if not self.package_list:
        #         sublime.error_message(__name__ + ': There are no packages ' +
        #             'available for discovery.')
        #         return
        #     self.window.show_quick_panel(self.package_list, self.on_done)
        # sublime.set_timeout(show_quick_panel, 10)
        
        # def on_done(self, picked):
        #     if picked == -1:
        #         return
        #     package_name = self.package_list[picked][0]
        #     packages = self.manager.list_available_packages()
        #     def open_url():
        #         sublime.active_window().run_command('open_url',
        #             {"url": packages.get(package_name).get('url')})
        #     sublime.set_timeout(open_url, 10)

class BaseGitCommand(sublime_plugin.TextCommand):
    def is_enabled(self):
        # Just "is the file a saved file?"
        return self.view.file_name() and len(self.view.file_name()) > 0

class GitBlameCommand(BaseGitCommand):
    def run(self, edit):
        folder_name, file_name = os.path.split(self.view.file_name())
        begin_line, begin_column = self.view.rowcol(self.view.sel()[0].begin())
        end_line, end_column = self.view.rowcol(self.view.sel()[0].end())
        begin_line = str(begin_line)
        end_line = str(end_line)
        lines = begin_line + ',' + end_line
        self.view.window().run_command('exec', {'cmd': ['git', 'blame', '-L', lines, file_name], 'working_dir': folder_name})
        sublime.status_message("git blame -L " + lines + " " + file_name)

class GitLogCommand(BaseGitCommand):
    def run(self, edit):
        folder_name, file_name = os.path.split(self.view.file_name())
        # self.view.window().run_command('exec', {'cmd': ['git', 'log', file_name], 'working_dir': folder_name})
        # sublime.status_message("git log " + file_name)
        thread = CommandThread(['git', 'log', '--oneline', file_name], self.command_done, working_dir=folder_name)
        thread.start()
        # ThreadProgress(thread, 'Loading repositories', '')
    def command_done(self, success, result):
        if not success:
            return
        self.results = result.strip().split('\n')
        self.view.window().show_quick_panel(self.results, self.panel_done)
    def panel_done(self, picked):
        if picked == -1:
            return;
        print "done", picked


class GitDiffCommand(BaseGitCommand):
    def run(self, edit):
        folder_name, file_name = os.path.split(self.view.file_name())
        self.view.window().run_command('exec', {'cmd': ['git', 'diff', file_name], 'working_dir': folder_name})
        sublime.status_message("git diff " + file_name)
