import os
import sublime
import sublime_plugin
import threading
import subprocess
import functools
import tempfile

# when sublime loads a plugin it's cd'd into the plugin directory. Thus
# __file__ is useless for my purposes. What I want is "Packages/Git", but
# allowing for the possibility that someone has renamed the file.
# Fun discovery: Sublime on windows still requires posix path separators.
PLUGIN_DIRECTORY = os.getcwd().replace(os.path.normpath(os.path.join(os.getcwd(), '..', '..')) + os.path.sep, '').replace(os.path.sep, '/')


def main_thread(callback, *args, **kwargs):
    # sublime.set_timeout gets used to send things onto the main thread
    # most sublime.[something] calls need to be on the main thread
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)


def open_url(url):
    sublime.active_window().run_command('open_url', {"url": url})


def git_root(directory):
    while directory:
        if os.path.exists(os.path.join(directory, '.git')):
            return directory
        parent = os.path.realpath(os.path.join(directory, os.path.pardir))
        if parent == directory:
            # /.. == /
            return False
        directory = parent
    return False


def view_contents(view):
    region = sublime.Region(0, view.size())
    return view.substr(region)


def plugin_file(name):
    return os.path.join(PLUGIN_DIRECTORY, name)


def _make_text_safeish(text, fallback_encoding):
    # The unicode decode here is because sublime converts to unicode inside
    # insert in such a way that unknown characters will cause errors, which is
    # distinctly non-ideal... and there's no way to tell what's coming out of
    # git in output. So...
    try:
        unitext = text.decode('utf-8')
    except UnicodeDecodeError:
        unitext = text.decode(fallback_encoding)
    return unitext


class CommandThread(threading.Thread):
    def __init__(self, command, on_done, working_dir="", fallback_encoding=""):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.working_dir = working_dir
        self.fallback_encoding = fallback_encoding

    def run(self):
        try:
            # Per http://bugs.python.org/issue8557 shell=True is required to
            # get $PATH on Windows. Yay portable code.
            shell = os.name == 'nt'
            if self.working_dir != "":
                os.chdir(self.working_dir)

            proc = subprocess.Popen(self.command,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                shell=shell, universal_newlines=True)
            output = proc.communicate()[0]
            # if sublime's python gets bumped to 2.7 we can just do:
            # output = subprocess.check_output(self.command)
            main_thread(self.on_done,
                _make_text_safeish(output, self.fallback_encoding))
        except subprocess.CalledProcessError, e:
            main_thread(self.on_done, e.returncode)
        except OSError, e:
            if e.errno == 2:
                main_thread(sublime.error_message, "Git binary could not be found in PATH\n\nConsider using the git_command setting for the Git plugin\n\nPATH is: %s" % os.environ['PATH'])
            else:
                raise e


# A base for all commands
class GitCommand:
    def run_command(self, command, callback=None, show_status=True,
            filter_empty_args=True, **kwargs):
        if filter_empty_args:
            command = [arg for arg in command if arg]
        if 'working_dir' not in kwargs:
            kwargs['working_dir'] = self.get_working_dir()
        if 'fallback_encoding' not in kwargs and self.active_view() and self.active_view().settings().get('fallback_encoding'):
            kwargs['fallback_encoding'] = self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0]

        s = sublime.load_settings("Git.sublime-settings")
        if s.get('save_first') and self.active_view() and self.active_view().is_dirty():
            self.active_view().run_command('save')
        if command[0] == 'git' and s.get('git_command'):
            command[0] = s.get('git_command')
        if not callback:
            callback = self.generic_done

        thread = CommandThread(command, callback, **kwargs)
        thread.start()

        if show_status:
            message = kwargs.get('status_message', False) or ' '.join(command)
            sublime.status_message(message)

    def generic_done(self, result):
        if not result.strip():
            return
        self.panel(result)

    def _output_to_view(self, output_file, output, clear=False,
            syntax="Packages/Diff/Diff.tmLanguage"):
        output_file.set_syntax_file(syntax)
        edit = output_file.begin_edit()
        if clear:
            region = sublime.Region(0, self.output_view.size())
            output_file.erase(edit, region)
        output_file.insert(edit, 0, output)
        output_file.end_edit(edit)

    def scratch(self, output, title=False, **kwargs):
        scratch_file = self.get_window().new_file()
        if title:
            scratch_file.set_name(title)
        scratch_file.set_scratch(True)
        self._output_to_view(scratch_file, output, **kwargs)
        scratch_file.set_read_only(True)
        return scratch_file

    def panel(self, output, **kwargs):
        if not hasattr(self, 'output_view'):
            self.output_view = self.get_window().get_output_panel("git")
        self.output_view.set_read_only(False)
        self._output_to_view(self.output_view, output, clear=True, **kwargs)
        self.output_view.set_read_only(True)
        self.get_window().run_command("show_panel", {"panel": "output.git"})

    def quick_panel(self, *args, **kwargs):
        self.get_window().show_quick_panel(*args, **kwargs)


# A base for all git commands that work with the entire repository
class GitWindowCommand(GitCommand, sublime_plugin.WindowCommand):
    def active_view(self):
        return self.window.active_view()

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

    # If there's no active view or the active view is not a file on the
    # filesystem (e.g. a search results view), we can infer the folder
    # that the user intends Git commands to run against when there's only
    # only one.
    def is_enabled(self):
        if self._active_file_name() or len(self.window.folders()) == 1:
            return git_root(self.get_working_dir())

    def get_file_name(self):
        return ''

    # If there is a file in the active view use that file's directory to
    # search for the Git root.  Otherwise, use the only folder that is
    # open.
    def get_working_dir(self):
        file_name = self._active_file_name()
        if file_name:
            return os.path.dirname(file_name)
        else:
            return self.window.folders()[0]

    def get_window(self):
        return self.window


# A base for all git commands that work with the file in the active view
class GitTextCommand(GitCommand, sublime_plugin.TextCommand):
    def active_view(self):
        return self.view

    def is_enabled(self):
        # First, is this actually a file on the file system?
        if self.view.file_name() and len(self.view.file_name()) > 0:
            return git_root(self.get_working_dir())

    def get_file_name(self):
        return os.path.basename(self.view.file_name())

    def get_working_dir(self):
        return os.path.dirname(self.view.file_name())

    def get_window(self):
        # Fun discovery: if you switch tabs while a command is working,
        # self.view.window() is None. (Admittedly this is a consequence
        # of my deciding to do async command processing... but, hey,
        # got to live with that now.)
        # I did try tracking the window used at the start of the command
        # and using it instead of view.window() later, but that results
        # panels on a non-visible window, which is especially useless in
        # the case of the quick panel.
        # So, this is not necessarily ideal, but it does work.
        return self.view.window() or sublime.active_window()


class GitBlameCommand(GitTextCommand):
    def run(self, edit):
        # somewhat custom blame command:
        # -w: ignore whitespace changes
        # -M: retain blame when moving lines
        # -C: retain blame when copying lines between files
        command = ['git', 'blame', '-w', '-M', '-C']

        selection = self.view.sel()[0]  # todo: multi-select support?
        if not selection.empty():
            # just the lines we have a selection on
            begin_line, begin_column = self.view.rowcol(selection.begin())
            end_line, end_column = self.view.rowcol(selection.end())
            lines = str(begin_line + 1) + ',' + str(end_line + 1)
            command.extend(('-L', lines))

        command.append(self.get_file_name())
        self.run_command(command, self.blame_done)

    def blame_done(self, result):
        self.scratch(result, title="Git Blame", syntax=plugin_file("Git Blame.tmLanguage"))


class GitLog:
    def run(self, edit=None):
        # the ASCII bell (\a) is just a convenient character I'm pretty sure
        # won't ever come up in the subject of the commit (and if it does then
        # you positively deserve broken output...)
        # 9000 is a pretty arbitrarily chosen limit; picked entirely because
        # it's about the size of the largest repo I've tested this on... and
        # there's a definite hiccup when it's loading that
        self.run_command(
            ['git', 'log', '--pretty=%s\a%h %an <%aE>\a%ad (%ar)',
            '--date=local', '--max-count=9000', '--', self.get_file_name()],
            self.log_done)

    def log_done(self, result):
        self.results = [r.split('\a', 2) for r in result.strip().split('\n')]
        self.quick_panel(self.results, self.panel_done)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        item = self.results[picked]
        # the commit hash is the first thing on the second line
        ref = item[1].split(' ')[0]
        # I'm not certain I should have the file name here; it restricts the
        # details to just the current file. Depends on what the user expects...
        # which I'm not sure of.
        self.run_command(
            ['git', 'log', '-p', '-1', ref, '--', self.get_file_name()],
            self.details_done)

    def details_done(self, result):
        self.scratch(result, title="Git Commit Details", syntax=plugin_file("Git Commit Message.tmLanguage"))


class GitLogCommand(GitLog, GitTextCommand):
    pass


class GitLogAllCommand(GitLog, GitWindowCommand):
    pass


class GitGraph(object):
    def run(self, edit=None):
        self.run_command(
            ['git', 'log', '--graph', '--pretty=%h %aN %ci%d %s', '--abbrev-commit', '--no-color', '--decorate',
            '--date-order', '--', self.get_file_name()],
            self.log_done
        )

    def log_done(self, result):
        self.scratch(result, title="Git Log Graph", syntax=plugin_file("Git Graph.tmLanguage"))


class GitGraphCommand(GitGraph, GitTextCommand):
    pass


class GitGraphAllCommand(GitGraph, GitWindowCommand):
    pass


class GitDiff (object):
    def run(self, edit=None):
        self.run_command(['git', 'diff', '--no-color', self.get_file_name()],
            self.diff_done)

    def diff_done(self, result):
        if not result.strip():
            self.panel("No output")
            return
        self.scratch(result, title="Git Diff")


class GitDiffCommand(GitDiff, GitTextCommand):
    pass


class GitDiffAllCommand(GitDiff, GitWindowCommand):
    pass


class GitQuickCommitCommand(GitTextCommand):
    def run(self, edit):
        self.get_window().show_input_panel("Message", "",
            self.on_input, None, None)

    def on_input(self, message):
        if message.strip() == "":
            self.panel("No commit message provided")
            return
        self.run_command(['git', 'add', self.get_file_name()],
            functools.partial(self.add_done, message))

    def add_done(self, message, result):
        if result.strip():
            sublime.error_message("Error adding file:\n" + result)
            return
        self.run_command(['git', 'commit', '-m', message])


# Commit is complicated. It'd be easy if I just wanted to let it run
# on OSX, and assume that subl was in the $PATH. However... I can't do
# that. Second choice was to set $GIT_EDITOR to sublime text for the call
#  to commit, and let that Just Work. However, on Windows you can't pass
# -w to sublime, which means the editor won't wait, and so the commit will fail
# with an empty message.
# Thus this flow:
# 1. `status --porcelain --untracked-files=no` to know whether files need
#    to be committed
# 2. `status` to get a template commit message (not the exact one git uses; I
#    can't see a way to ask it to output that, which is not quite ideal)
# 3. Create a scratch buffer containing the template
# 4. When this buffer is closed, get its contents with an event handler and
#    pass execution back to the original command. (I feel that the way this
#    is done is  a total hack. Unfortunately, I cannot see a better way right
#    now.)
# 5. Strip lines beginning with # from the message, and save in a temporary
#    file
# 6. `commit -F [tempfile]`
class GitCommitCommand(GitWindowCommand):
    active_message = False

    def run(self):
        self.working_dir = self.get_working_dir()
        self.run_command(
            ['git', 'status', '--untracked-files=no', '--porcelain'],
            self.porcelain_status_done
            )

    def porcelain_status_done(self, result):
        # todo: split out these status-parsing things...
        has_staged_files = False
        result_lines = result.rstrip().split('\n')
        for line in result_lines:
            if not line[0].isspace():
                has_staged_files = True
                break
        if not has_staged_files:
            self.panel("Nothing to commit")
            return
        # Okay, get the template!
        self.run_command(['git', 'status'], self.status_done)

    def status_done(self, result):
        template = "\n".join([
            "",
            "# Please enter the commit message for your changes. Lines starting",
            "# with '#' will be ignored, and an empty message aborts the commit.",
            "# Just close the window to accept your message.",
            result.strip()
        ])
        msg = self.window.new_file()
        msg.set_scratch(True)
        msg.set_name("COMMIT_EDITMSG")
        self._output_to_view(msg, template, syntax=plugin_file("Git Commit Message.tmLanguage"))
        msg.sel().clear()
        msg.sel().add(sublime.Region(0, 0))
        GitCommitCommand.active_message = self

    def message_done(self, message):
        # filter out the comments (git commit doesn't do this automatically)
        lines = [line for line in message.split("\n")
            if not line.lstrip().startswith('#')]
        message = '\n'.join(lines)
        # write the temp file
        message_file = tempfile.NamedTemporaryFile(delete=False)
        message_file.write(message)
        message_file.close()
        self.message_file = message_file
        # and actually commit
        self.run_command(['git', 'commit', '-F', message_file.name],
            self.commit_done, working_dir=self.working_dir)

    def commit_done(self, result):
        os.remove(self.message_file.name)
        self.panel(result)


class GitCommitMessageListener(sublime_plugin.EventListener):
    def on_close(self, view):
        if view.name() != "COMMIT_EDITMSG":
            return
        command = GitCommitCommand.active_message
        if not command:
            return
        message = view_contents(view)
        command.message_done(message)


class GitStatusCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'status', '--porcelain'], self.status_done)

    def status_done(self, result):
        self.results = filter(self.status_filter, result.rstrip().split('\n'))
        if len(self.results):
            self.show_status_list()
        else:
            sublime.status_message("Nothing to show")

    def show_status_list(self):
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def status_filter(self, item):
        # for this class we don't actually care
        return len(item) > 0

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_file = self.results[picked]
        # first 2 characters are status codes, the third is a space
        picked_status = picked_file[:2]
        picked_file = picked_file[3:]
        self.panel_followup(picked_status, picked_file, picked)

    def panel_followup(self, picked_status, picked_file, picked_index):
        # split out solely so I can override it for laughs

        root = git_root(self.get_working_dir())
        if picked_status == '??':
            self.window.open_file(os.path.join(root, picked_file))
        else:
            self.run_command(['git', 'diff', '--no-color', '--', picked_file.strip('"')],
                self.diff_done, working_dir=root)

    def diff_done(self, result):
        if not result.strip():
            return
        self.scratch(result, title="Git Diff")


class GitAddChoiceCommand(GitStatusCommand):
    def status_filter(self, item):
        return not item[1].isspace()

    def show_status_list(self):
        self.results.insert(0, [" + All Files", "apart from untracked files"])
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_followup(self, picked_status, picked_file, picked_index):
        if picked_index == 0:
            args = ["--update"]
        else:
            args = ["--", picked_file.strip('"')]

        self.run_command(['git', 'add'] + args,
            working_dir=git_root(self.get_working_dir()))


class GitAdd(GitTextCommand):
    def run(self, edit):
        self.run_command(['git', 'add', self.get_file_name()])


class GitStashCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'stash'])


class GitStashPopCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'stash', 'pop'])


class GitBranchCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'branch', '--no-color'], self.branch_done)

    def branch_done(self, result):
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_branch = self.results[picked]
        if picked_branch.startswith("*"):
            return
        picked_branch = picked_branch.strip()
        self.run_command(['git', 'checkout', picked_branch])


class GitCheckoutCommand(GitTextCommand):
    def run(self, edit):
        self.run_command(['git', 'checkout', self.get_file_name()], self.checkout_done)

    def checkout_done(self, result):
        self.view.run_command('revert')


class GitPullCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'pull'])


class GitPushCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'push'])


class GitCustomCommand(GitTextCommand):
    def run(self, edit):
        self.get_window().show_input_panel("Git command", "",
            self.on_input, None, None)

    def on_input(self, command):
        command = str(command) # avoiding unicode
        if command.strip() == "":
            self.panel("No git command provided")
            return
        import shlex
        command_splitted = ['git'] + shlex.split(command)
        print command_splitted
        self.run_command(command_splitted)
