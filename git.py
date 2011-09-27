import os
import sublime
import sublime_plugin
import threading
import subprocess
import functools

def main_thread(callback, *args, **kwargs):
    # sublime.set_timeout gets used to send things onto the main thread
    # most sublime.[something] calls need to be on the main thread
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)

def run_command(command, callback, show_status = True, filter_empty_args = True, **kwargs):
    if filter_empty_args:
        command = [arg for arg in command if arg]
    thread = CommandThread(command, callback, **kwargs)
    thread.start()
    if show_status:
        message = ' '.join(command)
        sublime.status_message(message)

def scratch(window, output, title = False):
    f = window.new_file()
    if title:
        f.set_name(title)
    f.set_scratch(True)
    f.set_syntax_file("Packages/Diff/Diff.tmLanguage")
    e = f.begin_edit()
    f.insert(e, 0, output)
    f.end_edit(e);
    return f

def open_url(url):
    sublime.active_window().run_command('open_url', {"url": url})

class CommandThread(threading.Thread):
    def __init__(self, command, on_done, working_dir = "", ):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.working_dir = working_dir

    def run(self):
        try:
            if self.working_dir != "":
                os.chdir(self.working_dir)
            output = subprocess.Popen(self.command, stdout=subprocess.PIPE, shell=False).communicate()[0]
            # if sublime's python gets bumped to 2.7 we can just do:
            # output = subprocess.check_output(self.command)
            main_thread(self.on_done, True, output)
        except subprocess.CalledProcessError, e:
            main_thread(self.on_done, False, e.returncode)

class GitCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        pass
    def command_done(self, success, result):
        pass
    def is_enabled(self):
        # Just "is the file a saved file?"
        return self.view.file_name() and len(self.view.file_name()) > 0
    def get_file_name(self):
        return os.path.split(self.view.file_name())[1]
    def get_file_location(self):
        return os.path.split(self.view.file_name())[0]

class GitBlameCommand(GitCommand):
    def run(self, edit):
        folder_name, file_name = os.path.split(self.view.file_name())
        begin_line, begin_column = self.view.rowcol(self.view.sel()[0].begin())
        end_line, end_column = self.view.rowcol(self.view.sel()[0].end())
        begin_line = str(begin_line)
        end_line = str(end_line)
        lines = begin_line + ',' + end_line
        self.view.window().run_command('exec', {'cmd': ['git', 'blame', '-L', lines, file_name], 'working_dir': folder_name})
        sublime.status_message("git blame -L " + lines + " " + file_name)

class GitLogCommand(GitCommand):
    def run(self, edit):
        ## the ASCII bell (\a) is just a convenient character I'm pretty sure won't ever come
        ## up in the subject of the commit (and if it does then you positively deserve broken
        ## output...)
        run_command(['git', 'log', '--pretty=%s\a%h %an <%aE>\a%ad (%ar)', '--date=local', self.get_file_name()], self.log_done, working_dir = self.get_file_location())
    
    def log_done(self, success, result):
        if not success:
            return
        self.results = [r.split('\a', 2) for r in result.strip().split('\n')]
        self.view.window().show_quick_panel(self.results, self.panel_done)
    
    def panel_done(self, picked):
        if picked == -1:
            return
        if 0 > picked > len(self.results):
            return
        item = self.results[picked]
        # the commit hash is the first thing on the second line
        ref = item[1].split(' ')[0]
        # I'm not certain I should have the file name here; it restricts the details to just
        # the current file. Depends on what the user expects... which I'm not sure of.
        run_command(['git', 'log', '-p', ref, self.get_file_name()], self.details_done, working_dir = self.get_file_location())
    
    def details_done(self, success, result):
        self.diff_file = f = scratch(self.view.window(), result, title = "Git Commit Details")

class GitLogAllCommand(GitLogCommand):
    def get_file_name(self):
        return ''

class GitDiffCommand(GitCommand):
    def run(self, edit):
        run_command(['git', 'diff', self.get_file_name()], self.diff_done, working_dir = self.get_file_location())
    
    def diff_done(self, success, result):
        self.diff_file = f = scratch(self.view.window(), result, title = "Git Diff")

class GitDiffAllCommand(GitDiffCommand):
    def get_file_name(self):
        return ''
