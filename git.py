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
            output = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False).communicate()[0]
            # if sublime's python gets bumped to 2.7 we can just do:
            # output = subprocess.check_output(self.command)
            main_thread(self.on_done, True, output)
        except subprocess.CalledProcessError, e:
            main_thread(self.on_done, False, e.returncode)

class GitCommand(sublime_plugin.TextCommand):
    def run_command(self, command, callback, show_status = True, filter_empty_args = True, **kwargs):
        if filter_empty_args:
            command = [arg for arg in command if arg]
        if 'working_dir' not in kwargs:
            kwargs['working_dir'] = self.get_file_location()
        
        thread = CommandThread(command, callback, **kwargs)
        thread.start()

        if show_status:
            message = kwargs.get('status_message', False) or ' '.join(command)
            sublime.status_message(message)

    def _output_to_view(self, output_file, output, clear = False, syntax = "Packages/Diff/Diff.tmLanguage"):
        output_file.set_syntax_file(syntax)
        edit = output_file.begin_edit()
        if clear:
            region = sublime.Region(0, self.output_view.size())
            output_file.erase(edit, region)
        # The unicode cast here is because sublime converts to unicode inside insert,
        # and there's no way to tell what's coming out of git in output. So...
        output_file.insert(edit, 0, unicode(output, errors="replace"))
        output_file.end_edit(edit)

    def scratch(self, output, title = False, **kwargs):
        scratch_file = self.view.window().new_file()
        if title:
            scratch_file.set_name(title)
        scratch_file.set_scratch(True)
        self._output_to_view(scratch_file, output, **kwargs)
        scratch_file.set_read_only(True)
        return scratch_file
    
    def panel(self, output, **kwargs):
        if not hasattr(self, 'output_view'):
            self.output_view = self.view.window().get_output_panel("git")
        self.output_view.set_read_only(False)
        self._output_to_view(self.output_view, output, clear = True, **kwargs)
        self.output_view.set_read_only(True)
        self.view.window().run_command("show_panel", {"panel": "output.git"})

    def is_enabled(self):
        # Just "is the file a saved file?"
        return self.view.file_name() and len(self.view.file_name()) > 0
    def get_file_name(self):
        return os.path.basename(self.view.file_name())
    def get_file_location(self):
        return os.path.dirname(self.view.file_name())

class GitBlameCommand(GitCommand):
    def run(self, edit):
        # somewhat custom blame command:
        # -w: ignore whitespace changes
        # -M: retain blame when moving lines
        # -C: retain blame when copying lines between files
        command = ['git', 'blame', '-w', '-M', '-C']

        selection = self.view.sel()[0] # todo: multi-select support?
        if not selection.empty():
            # just the lines we have a selection on
            begin_line, begin_column = self.view.rowcol(selection.begin())
            end_line, end_column = self.view.rowcol(selection.end())
            lines = str(begin_line) + ',' + str(end_line)
            command.extend(('-L', lines))

        command.append(self.get_file_name())
        self.run_command(command, self.blame_done)
    def blame_done(self, success, result):
        self.scratch(result, title = "Git Blame")

class GitLogCommand(GitCommand):
    def run(self, edit):
        ## the ASCII bell (\a) is just a convenient character I'm pretty sure won't ever come
        ## up in the subject of the commit (and if it does then you positively deserve broken
        ## output...)
        self.run_command(['git', 'log', '--pretty=%s\a%h %an <%aE>\a%ad (%ar)', '--date=local', self.get_file_name()], self.log_done)
    
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
        self.run_command(['git', 'log', '-p', ref, self.get_file_name()], self.details_done)
    
    def details_done(self, success, result):
        self.scratch(result, title = "Git Commit Details")

class GitLogAllCommand(GitLogCommand):
    def get_file_name(self):
        return ''

class GitDiffCommand(GitCommand):
    def run(self, edit):
        self.run_command(['git', 'diff', self.get_file_name()], self.diff_done)
    
    def diff_done(self, success, result):
        self.scratch(result, title = "Git Diff")

class GitDiffAllCommand(GitDiffCommand):
    def get_file_name(self):
        return ''

class GitCommitCommand(GitCommand):
    def run(self, edit):
        self.view.window().show_input_panel("Message", "", self.on_input, None, None)
    
    def on_input(self, message):
        if message.strip() == "":
            # Okay, technically an empty commit message is allowed, but I don't want to encourage that sort of thing
            sublime.error_message("No commit message provided")
            return
        self.run_command(['git', 'add', self.get_file_name()], functools.partial(self.add_done, message))
    
    def add_done(self, message, success, result):
        if result.strip():
            sublime.error_message("Error adding file:\n" + result)
            return
        self.run_command(['git', 'commit', '-m', message], self.commit_done)
    
    def commit_done(self, success, result):
        self.panel(result)
