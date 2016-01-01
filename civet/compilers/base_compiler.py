from __future__ import print_function
import atexit
from distutils.spawn import find_executable
import os
import subprocess
import sys

from django.conf import settings
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from civet.util import collect_src_dst_dir_mappings
from civet.util import raise_error_or_kill


class CompilerObserver(Observer):
    """Watch source files and compile them on change.

    We have to roll our own watchdog-based solution because:

    1. Unlike sass, coffee does not allow watching multiple directories. This
       leaves us with only one option: Watch the entire project root
       directory. That is not viable because we use a different directory
       layout for the compiled assets (think how collectstatic works).
    2. coffee can't handle the number of source files we have! This is caused
       by the combination of node.js's FS watcher implementation and OS X's
       default limit on the number of open files. This can be mitigated by
       asking all our devs to remember to dial up the limit manually, but then
       again 1. makes it hard to work with. For details, see
       https://github.com/joyent/node/issues/2479
    """

    def start(self):
        super(CompilerObserver, self).start()

        # Stop the observer when Django's autoreload calls sys.exit() before
        # reloading
        def cleanup():
            self.stop()

        atexit.register(cleanup)


class CompilerFSEventHandler(FileSystemEventHandler):
    """A watchdog FS event handler for watching file changes and compiling.

    We don't handle directory creation events anywhere in our source dir. We
    rarely add new directories, and when that happens, we can always re-start
    the runserver command. Handling directory events correctly will require
    more code than is practical.
    """

    def __init__(self, compiler, src_dst_dir_map):
        self.compiler = compiler
        super(FileSystemEventHandler, self).__init__()
        self.src_dst_dir_map = src_dst_dir_map

    def get_dst_path(self, src_path):
        src_dir, src_filename = os.path.split(src_path)
        dst_dir = self.src_dst_dir_map.get(src_dir)
        if not dst_dir:
            return None
        dst_filename = self.compiler.get_dest_path(
            *os.path.splitext(src_filename))
        dst_path = os.path.join(dst_dir, dst_filename)
        return dst_path

    def compile(self, src_path):
        dst_path = self.get_dst_path(src_path)
        if not dst_path:
            print(
                'Warning: No matching destination found for source {0}, and '
                'the source is not compiled'.format(src_path), file=sys.stderr)
        else:
            try:
                self.compiler.compile(src_path, dst_path)
            except subprocess.CalledProcessError:
                # coffee already reported the actual error to stderr
                pass

    def on_created(self, event):
        if event.is_directory:
            print(
                'Warning: New directory %s created but not watched' %
                event.src_path, file=sys.stderr)
        elif self.compiler.matches(*os.path.splitext(event.src_path)):
            self.compile(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            print(
                'Warning: Directory %s deleted' % event.src_path,
                file=sys.stderr)
        elif self.compiler.matches(*os.path.splitext(event.src_path)):
            print('Warning: File %s deleted' % event.src_path, file=sys.stderr)

    def on_modified(self, event):
        if (not event.is_directory
                and self.compiler.matches(*os.path.splitext(event.src_path))):
            self.compile(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            print(
                'Warning: Directory %s deleted' % event.src_path,
                file=sys.stderr)
        elif (self.compiler.matches(*os.path.splitext(event.src_path))
              and self.compiler.matches(*os.path.splitext(event.dest_path))):
            print(
                'Warning: File renamed {0} -> {1}'.format(
                    event.src_path, event.dest_path), file=sys.stderr)
            self.compile(event.dest_path)


class Compiler(object):
    def __init__(self, precompiled_assets_dir, kill_on_error):
        self.precompiled_assets_dir = precompiled_assets_dir
        if not hasattr(self, 'executable'):
            bin = getattr(
                settings, self.executable_setting, self.executable_name)
            self.executable = find_executable(bin)
        if not self.executable:
            if getattr(settings, self.executable_setting, None):
                print(
                    'Your project uses {name}, but "{bin_path}" specified in '
                    'settings.{settings_name} is not found.'
                    .format(
                        name=self.name,
                        bin_path=bin,
                        settings_name=self.executable_setting
                    ), file=sys.stderr)
            else:
                print(
                    'Your project uses {name}, but "{executable_name}" is not '
                    'found in your PATH.'
                    .format(
                        name=self.name,
                        executable_name=self.executable_name
                    ), file=sys.stderr)
            raise_error_or_kill(kill_on_error)

    @property
    def name(self):
        """Human visible name for this kind of compiler (eg "CoffeeScript").
        """
        raise NotImplementedError("Subclasses must implement name.")

    @property
    def executable_name(self):
        """Bare name of compiler executable (eg `coffee`).
        """
        raise NotImplementedError("Subclasses must implement executable_name.")

    @property
    def executable_setting(self):
        """Django settings name for executable path.
        """
        raise NotImplementedError(
            "Subclasses must implement executable_setting.")

    def matches(self, base, ext):
        """Return true if given base path and file extension is handled by this
        compiler.
        """
        raise NotImplementedError("Subclasses must implement matches()")

    def get_dest_path(self, base, ext):
        """Return destination path for given filename base and ext (previously
        accepted by matches().
        """
        raise NotImplementedError("Subclasses must implement get_dest_path()")

    def get_command_with_arguments(self, src_path, dst_path):
        """Return compiler executable and arguments needed to compile src_path
        to dst_path.
        """
        raise NotImplementedError("Subclasses must implement get_arguments()")

    def compile(self, src_path, dst_path):
        """Invoke the appropriate compiler to compile src_path to dst_path.

        Upon any compiler error, dst will be deleted if it exists. This
        prevents stale asset files from being served.
        """
        if os.path.exists(dst_path):
            if os.path.getmtime(dst_path) >= os.path.getmtime(src_path):
                return
            else:
                os.remove(dst_path)

        print('Compiling %s' % src_path)
        args = self.get_command_with_arguments(src_path, dst_path)
        subprocess.check_call(args)

    def compile_all(self, src_dest_tuples):
        """Pre-compile given (src, dest) file path tuples.
        """
        # Block and compile non-existent or newer files first
        print('Start precompiling {} files'.format(self.name))
        for src, dst in src_dest_tuples:
            self.compile(src, dst)
        print('End precompiling {} files'.format(self.name))

    def watch(self, files, observer):
        # Watch for changes in directories containing source files.
        src_dst_dir_map = collect_src_dst_dir_mappings(files)
        event_handler = CompilerFSEventHandler(self, src_dst_dir_map)

        for src_dir in src_dst_dir_map:
            observer.schedule(event_handler, src_dir, recursive=False)

        # The observer will start its own thread. We don't care about cleaning
        # it up since it goes down with the server's process. See
        # django.utils.autoreload.python_reloader
        print('Watching for {} changes'.format(self.name))
