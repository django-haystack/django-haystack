import os
import sublime
import sublime_plugin
import threading
import subprocess
import functools
import tempfile
import os.path
import re

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


def do_when(conditional, callback, *args, **kwargs):
    if conditional():
        return callback(*args, **kwargs)
    sublime.set_timeout(functools.partial(do_when, conditional, callback, *args, **kwargs), 50)


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
    def __init__(self, command, on_done, working_dir="", fallback_encoding="", **kwargs):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.working_dir = working_dir
        if "stdin" in kwargs:
            self.stdin = kwargs["stdin"]
        else:
            self.stdin = None
        if "stdout" in kwargs:
            self.stdout = kwargs["stdout"]
        else:
            self.stdout = subprocess.PIPE
        self.fallback_encoding = fallback_encoding
        self.kwargs = kwargs

    def run(self):
        try:
            # Per http://bugs.python.org/issue8557 shell=True is required to
            # get $PATH on Windows. Yay portable code.
            shell = os.name == 'nt'
            if self.working_dir != "":
                os.chdir(self.working_dir)

            proc = subprocess.Popen(self.command,
                stdout=self.stdout, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                shell=shell, universal_newlines=True)
            output = proc.communicate(self.stdin)[0]
            if not output:
                output = ''
            # if sublime's python gets bumped to 2.7 we can just do:
            # output = subprocess.check_output(self.command)
            main_thread(self.on_done,
                _make_text_safeish(output, self.fallback_encoding), **self.kwargs)
        except subprocess.CalledProcessError, e:
            main_thread(self.on_done, e.returncode)
        except OSError, e:
            if e.errno == 2:
                main_thread(sublime.error_message, "Git binary could not be found in PATH\n\nConsider using the git_command setting for the Git plugin\n\nPATH is: %s" % os.environ['PATH'])
            else:
                raise e


# A base for all commands
class GitCommand:
    may_change_files = False

    def run_command(self, command, callback=None, show_status=True,
            filter_empty_args=True, no_save=False, **kwargs):
        if filter_empty_args:
            command = [arg for arg in command if arg]
        if 'working_dir' not in kwargs:
            kwargs['working_dir'] = self.get_working_dir()
        if 'fallback_encoding' not in kwargs and self.active_view() and self.active_view().settings().get('fallback_encoding'):
            kwargs['fallback_encoding'] = self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0]

        s = sublime.load_settings("Git.sublime-settings")
        if s.get('save_first') and self.active_view() and self.active_view().is_dirty() and not no_save:
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

        if self.may_change_files and self.active_view() and self.active_view().file_name():
            if self.active_view().is_dirty():
                result = "WARNING: Current view is dirty.\n\n"
            else:
                # just asking the current file to be re-opened doesn't do anything
                print "reverting"
                position = self.active_view().viewport_position()
                self.active_view().run_command('revert')
                do_when(lambda: not self.active_view().is_loading(), lambda: self.active_view().set_viewport_position(position, False))
                # self.active_view().show(position)
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

        s = sublime.load_settings("Git.sublime-settings")
        selection = self.view.sel()[0]  # todo: multi-select support?
        if not selection.empty() or not s.get('blame_whole_file'):
            # just the lines we have a selection on
            begin_line, begin_column = self.view.rowcol(selection.begin())
            end_line, end_column = self.view.rowcol(selection.end())
            # blame will fail if last line is empty and is included in the selection
            if end_line > begin_line and end_column == 0:
                end_line -= 1
            lines = str(begin_line + 1) + ',' + str(end_line + 1)
            command.extend(('-L', lines))

        command.append(self.get_file_name())
        self.run_command(command, self.blame_done)

    def blame_done(self, result):
        self.scratch(result, title="Git Blame", syntax=plugin_file("Git Blame.tmLanguage"))


class GitLog:
    def run(self, edit=None):
        return self.run_log('--', self.get_file_name())

    def run_log(self, *args):
        # the ASCII bell (\a) is just a convenient character I'm pretty sure
        # won't ever come up in the subject of the commit (and if it does then
        # you positively deserve broken output...)
        # 9000 is a pretty arbitrarily chosen limit; picked entirely because
        # it's about the size of the largest repo I've tested this on... and
        # there's a definite hiccup when it's loading that
        command = ['git', 'log', '--pretty=%s\a%h %an <%aE>\a%ad (%ar)',
            '--date=local', '--max-count=9000']
        command.extend(args)
        self.run_command(
            command,
            self.log_done)

    def log_done(self, result):
        self.results = [r.split('\a', 2) for r in result.strip().split('\n')]
        self.quick_panel(self.results, self.log_panel_done)

    def log_panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        item = self.results[picked]
        # the commit hash is the first thing on the second line
        self.log_result(item[1].split(' ')[0])

    def log_result(self, ref):
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


class GitShow:
    def run(self, edit=None):
        # GitLog Copy-Past
        self.run_command(
            ['git', 'log', '--pretty=%s\a%h %an <%aE>\a%ad (%ar)',
            '--date=local', '--max-count=9000', '--', self.get_file_name()],
            self.show_done)

    def show_done(self, result):
        # GitLog Copy-Past
        self.results = [r.split('\a', 2) for r in result.strip().split('\n')]
        self.quick_panel(self.results, self.panel_done)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        item = self.results[picked]
        # the commit hash is the first thing on the second line
        ref = item[1].split(' ')[0]
        # Make full file name
        working_dir = self.get_working_dir()
        file_path = working_dir.replace(git_root(working_dir), '')[1:]
        file_name = os.path.join(file_path, self.get_file_name())
        self.run_command(
            ['git', 'show', '%s:%s' % (ref, file_name)],
            self.details_done,
            ref=ref)

    def details_done(self, result, ref):
        syntax = self.view.settings().get('syntax')
        self.scratch(result, title="%s:%s" % (ref, self.get_file_name()), syntax=syntax)


class GitShowCommand(GitShow, GitTextCommand):
    pass


class GitShowAllCommand(GitShow, GitWindowCommand):
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
        s = sublime.load_settings("Git.sublime-settings")
        if s.get('diff_panel'):
            view = self.panel(result)
        else:
            view = self.scratch(result, title="Git Diff")

        lines_inserted = view.find_all(r'^\+[^+]{2} ')
        lines_deleted = view.find_all(r'^-[^-]{2} ')

        view.add_regions("inserted", lines_inserted, "markup.inserted.diff", "dot", sublime.HIDDEN)
        view.add_regions("deleted", lines_deleted, "markup.deleted.diff", "dot", sublime.HIDDEN)


class GitDiffCommit (object):
    def run(self, edit=None):
        self.run_command(['git', 'diff', '--cached', '--no-color'],
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


class GitDiffCommitCommand(GitDiffCommit, GitWindowCommand):
    pass


class GitDiffTool(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'difftool'])


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
        self.run_command(['git', 'diff', '--staged'], self.diff_done)

    def diff_done(self, result):
        template = "\n".join([
            "",
            "# Please enter the commit message for your changes. Lines starting",
            "# with '#' and everything after the 'END' statement below will be ",
            "# ignored, and an empty message aborts the commit.",
            "# Just close the window to accept your message.",
            "# END--------------",
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
        lines = [line for line in message.split("\n# END---")[0].split("\n")
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
    may_change_files = True

    def run(self):
        self.run_command(['git', 'stash'])


class GitStashPopCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'stash', 'pop'])


class GitOpenFileCommand(GitLog, GitWindowCommand):
    def run(self):
        self.run_command(['git', 'branch', '-a', '--no-color'], self.branch_done)

    def branch_done(self, result):
        self.results = result.rstrip().split('\n')
        self.quick_panel(self.results, self.branch_panel_done,
            sublime.MONOSPACE_FONT)

    def branch_panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        self.branch = self.results[picked].split(' ')[-1]
        self.run_log(self.branch)

    def log_result(self, result_hash):
        # the commit hash is the first thing on the second line
        self.ref = result_hash
        self.run_command(
            ['git', 'ls-tree', '-r', '--full-tree', self.ref],
            self.ls_done)

    def ls_done(self, result):
        # Last two items are the ref and the file name
        # p.s. has to be a list of lists; tuples cause errors later
        self.results = [[match.group(2), match.group(1)] for match in re.finditer(r"\S+\s(\S+)\t(.+)", result)]

        self.quick_panel(self.results, self.ls_panel_done)

    def ls_panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        item = self.results[picked]

        self.filename = item[0]
        self.fileRef = item[1]

        self.run_command(
            ['git', 'show', self.fileRef],
            self.show_done)

    def show_done(self, result):
        self.scratch(result, title="%s:%s" % (self.fileRef, self.filename))


class GitBranchCommand(GitWindowCommand):
    may_change_files = True
    command_to_run_after_branch = 'checkout'

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
        self.run_command(['git', self.command_to_run_after_branch, picked_branch])


class GitMergeCommand(GitBranchCommand):
    command_to_run_after_branch = 'merge'


class GitNewBranchCommand(GitWindowCommand):
    def run(self):
        self.get_window().show_input_panel("Branch name", "",
            self.on_input, None, None)

    def on_input(self, branchname):
        if branchname.strip() == "":
            self.panel("No branch name provided")
            return
        self.run_command(['git', 'checkout', '-b', branchname])


class GitCheckoutCommand(GitTextCommand):
    may_change_files = True

    def run(self, edit):
        self.run_command(['git', 'checkout', self.get_file_name()])


class GitPullCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'pull'], callback=self.panel)


class GitPushCommand(GitWindowCommand):
    def run(self):
        self.run_command(['git', 'push'], callback=self.panel)


class GitCustomCommand(GitTextCommand):
    may_change_files = True

    def run(self, edit):
        self.get_window().show_input_panel("Git command", "",
            self.on_input, None, None)

    def on_input(self, command):
        command = str(command)  # avoiding unicode
        if command.strip() == "":
            self.panel("No git command provided")
            return
        import shlex
        command_splitted = ['git'] + shlex.split(command)
        print command_splitted
        self.run_command(command_splitted)


class GitResetHeadCommand(GitTextCommand):
    def run(self, edit):
        self.run_command(['git', 'reset', 'HEAD', self.get_file_name()])

    def generic_done(self, result):
        pass


class GitClearAnnotationCommand(GitTextCommand):
    def run(self, view):
        self.active_view().settings().set('live_git_annotations', False)
        self.view.erase_regions('git.changes.x')
        self.view.erase_regions('git.changes.+')
        self.view.erase_regions('git.changes.-')


class GitAnnotationListener(sublime_plugin.EventListener):
    def on_modified(self, view):
        if not view.settings().get('live_git_annotations'):
            return
        view.run_command('git_annotate')


class GitAnnotateCommand(GitTextCommand):
    # Unfortunately, git diff does not support text from stdin, making a *live* annotation
    # difficult. Therefore I had to resort to the system diff command. (Problems on win?)
    # This works as follows:
    # 1. When the command is run for the first time for this file, a temporary file with the
    #    current state of the HEAD is being pulled from git.
    # 2. All consecutive runs will pass the current buffer into diffs stdin. The resulting
    #    output is then parsed and regions are set accordingly.
    def run(self, view):
        # If the annotations are already running, we dont have to create a new tmpfile
        if self.active_view().settings().get('live_git_annotations'):
            self.compare_tmp(None)
            return
        self.tmp = tempfile.NamedTemporaryFile()
        self.active_view().settings().set('live_git_annotations', True)
        root = git_root(self.get_working_dir())
        repo_file = os.path.relpath(self.view.file_name(), root)
        self.run_command(['git', 'show', 'HEAD:{0}'.format(repo_file)], show_status=False, no_save=True, callback=self.compare_tmp, stdout=self.tmp)

    def compare_tmp(self, result, stdout=None):
        all_text = self.view.substr(sublime.Region(0, self.view.size()))
        self.run_command(['diff', '-u', self.tmp.name, '-'], stdin=all_text, no_save=True, show_status=False, callback=self.parse_diff)

    # This is where the magic happens. At the moment, only one chunk format is supported. While
    # the unified diff format theoritaclly supports more, I don't think git diff creates them.
    def parse_diff(self, result, stdin=None):
        lines = result.splitlines()
        matcher = re.compile('^@@ -([0-9]*),([0-9]*) \+([0-9]*),([0-9]*) @@')
        diff = []
        for line_index in range(0, len(lines)):
            line = lines[line_index]
            if not line.startswith('@'):
                continue
            match = matcher.match(line)
            if not match:
                continue
            line_before, len_before, line_after, len_after = [int(match.group(x)) for x in [1, 2, 3, 4]]
            chunk_index = line_index + 1
            tracked_line_index = line_after - 1
            deletion = False
            insertion = False
            while True:
                line = lines[chunk_index]
                if line.startswith('@'):
                    break
                elif line.startswith('-'):
                    if not line.strip() == '-':
                        deletion = True
                    tracked_line_index -= 1
                elif line.startswith('+'):
                    if deletion and not line.strip() == '+':
                        diff.append(['x', tracked_line_index])
                        insertion = True
                    elif not deletion:
                        insertion = True
                        diff.append(['+', tracked_line_index])
                else:
                    if not insertion and deletion:
                        diff.append(['-', tracked_line_index])
                    insertion = deletion = False
                tracked_line_index += 1
                chunk_index += 1
                if chunk_index >= len(lines):
                    break

        self.annotate(diff)

    # Once we got all lines with their specific change types (either x, +, or - for
    # modified, added, or removed) we can create our regions and do the actual annotation.
    def annotate(self, diff):
        self.view.erase_regions('git.changes.x')
        self.view.erase_regions('git.changes.+')
        self.view.erase_regions('git.changes.-')
        typed_diff = {'x': [], '+': [], '-': []}
        for change_type, line in diff:
            if change_type == '-':
                full_region = self.view.full_line(self.view.text_point(line - 1, 0))
                position = full_region.begin()
                for i in xrange(full_region.size()):
                    typed_diff[change_type].append(sublime.Region(position + i))
            else:
                point = self.view.text_point(line, 0)
                region = self.view.full_line(point)
                if change_type == '-':
                    region = sublime.Region(point, point + 5)
                typed_diff[change_type].append(region)

        for change in ['x', '+']:
            self.view.add_regions("git.changes.{0}".format(change), typed_diff[change], 'git.changes.{0}'.format(change), 'dot')

        self.view.add_regions("git.changes.-", typed_diff['-'], 'git.changes.-', 'dot', sublime.DRAW_EMPTY_AS_OVERWRITE)


class GitAddSelectedHunkCommand(GitTextCommand):
    def run(self, edit):
        self.run_command(['git', 'diff', '--no-color', self.get_file_name()], self.cull_diff)

    def cull_diff(self, result):
        selection = []
        for sel in self.view.sel():
            selection.append({
                "start": self.view.rowcol(sel.begin())[0] + 1,
                "end": self.view.rowcol(sel.end())[0] + 1,
            })

        hunks = [{"diff":""}]
        i = 0
        matcher = re.compile('^@@ -([0-9]*)(?:,([0-9]*))? \+([0-9]*)(?:,([0-9]*))? @@')
        for line in result.splitlines():
            if line.startswith('@@'):
                i += 1
                match = matcher.match(line)
                start = int(match.group(3))
                end = match.group(4)
                if end:
                    end = start + int(end)
                else:
                    end = start
                hunks.append({"diff": "", "start": start, "end": end})
            hunks[i]["diff"] += line + "\n"

        diffs = hunks[0]["diff"]
        hunks.pop(0)
        selection_is_hunky = False
        for hunk in hunks:
            for sel in selection:
                if sel["end"] < hunk["start"]:
                    continue
                if sel["start"] > hunk["end"]:
                    continue
                diffs += hunk["diff"]  # + "\n\nEND OF HUNK\n\n"
                selection_is_hunky = True

        if selection_is_hunky:
            self.run_command(['git', 'apply', '--cached'], stdin=diffs)
        else:
            sublime.status_message("No selected hunk")


class GitCommitSelectedHunk(GitAddSelectedHunkCommand):
    def run(self, edit):
        self.run_command(['git', 'diff', '--no-color', self.get_file_name()], self.cull_diff)
        self.get_window().run_command('git_commit')

