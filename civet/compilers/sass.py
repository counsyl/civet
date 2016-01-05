from __future__ import print_function
import atexit
import os
import re
import subprocess
import sys

from distutils.spawn import find_executable
from django.conf import settings

from civet.compilers.base_compiler import Compiler
from civet.util import collect_src_dst_dir_mappings
from civet.util import get_shortest_topmost_directories
from civet.util import raise_error_or_kill


# The regex to find Sass if Bundler is used (see CIVET_BUNDLE_GEMFILE below)
BUNDLE_LIST_SASS_FINDER = re.compile(r'^.+?sass \(\d+\.\d+.+?\)', re.MULTILINE)

# If given, Bundler (http://bundler.io/) will be used to invoke Sass
# (via `bundle exec sass`) with the designated Gemfile.
bundle_gemfile = getattr(
    settings, 'CIVET_BUNDLE_GEMFILE', None)

# Location of Bundler's `bundle`. This is used if settings.CIVET_BUNDLE_GEMFILE
# is given.
bundle_bin = getattr(
    settings, 'CIVET_BUNDLE_BIN', 'bundle')

# Default Sass arguments. If you use Compass, you will want to add
# `CIVET_SASS_ARGUMENTS = ('--compass',)` in your `settings.py`.
sass_arguments = getattr(
    settings, 'CIVET_SASS_ARGUMENTS', ())


class SassCompiler(Compiler):
    name = "Sass"
    executable_setting = 'CIVET_SASS_BIN'
    executable_name = 'sass'

    def __init__(self, precompiled_assets_dir, kill_on_error):
        # Make sure that CIVET_SASS_BIN and CIVET_BUNDLE_GEMFILE are not both
        # set in settings.
        if (getattr(settings, 'CIVET_SASS_BIN', None) and
                getattr(settings, 'CIVET_BUNDLE_GEMFILE', None)):
            print(
                'CIVET_BUNDLE_GEMFILE and CIVET_SASS_BIN must not be set '
                'at the same time in settings.', file=sys.stderr)
            raise_error_or_kill(kill_on_error)

        if bundle_gemfile:
            if not find_executable(bundle_bin):
                print(
                    'Your project uses Sass and you have specified a Gemfile '
                    'to be used with Bundler, but "bundle" is not found in '
                    'your PATH.', file=sys.stderr)
                raise_error_or_kill(kill_on_error)

            # Now, look for the gem `sass`.
            args = (bundle_bin, 'list')
            env = os.environ.copy()
            env['BUNDLE_GEMFILE'] = bundle_gemfile
            process = subprocess.Popen(args, stdout=subprocess.PIPE, env=env)
            stdout, _ = process.communicate()

            if process.returncode != 0:
                lines = stdout.split('\n')
                messages = '\n'.join("    %s" % ln for ln in lines)
                print(
                    '"bundle list" failed, exit code = %d, messages:\n%s' % (
                        process.returncode, messages), file=sys.stderr)
                raise_error_or_kill(kill_on_error)

            match = BUNDLE_LIST_SASS_FINDER.search(stdout)
            if not match:
                print(
                    'You have specified to use Bundler to run Sass, but '
                    '"sass" is not included in your bundle.', file=sys.stderr)
                raise_error_or_kill(kill_on_error)
            self.args = [bundle_bin, 'exec', 'sass']
            self.env = env

        super(SassCompiler, self).__init__(precompiled_assets_dir,
                                           kill_on_error)

        if not hasattr(self, 'args'):
            self.args = [self.executable]
            self.env = None
        self.args.extend(sass_arguments)

    def matches(self, base, ext):
        return ext == '.sass' or ext == '.scss'

    def get_dest_path(self, base, ext):
        return os.path.join(self.precompiled_assets_dir, base + '.css')

    def _get_dir_pairs(self, sass_files):
        # Collect the directories we want to watch
        dir_map = collect_src_dst_dir_mappings(sass_files)

        # sass watch directories recursively, so we can remove children dirs.
        topmost_dirs = get_shortest_topmost_directories(dir_map)
        dir_map = {k: dir_map[k] for k in topmost_dirs}

        # sass can update and monitor multiple directories with the arguments
        # in the form of <src_dir_1>:<dst_dir_1> <src_dir_2>:<dst_dir_2> ...
        return [':'.join(item) for item in dir_map.items()]

    def compile_all(self, sass_files):
        """Pre-compile Sass source files and watch for changes."""
        # Block and compile non-existent or newer files first
        print('Start precompiling Sass files')
        args = list(self.args)
        args.append('--update')
        args.extend(self._get_dir_pairs(sass_files))
        process = subprocess.Popen(args, env=self.env)
        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(args[0], process.returncode)
        print('End precompiling Sass files')

    def watch(self, files, observer):
        # Start watching with a separate process
        args = list(self.args)
        args.append('--watch')
        args.extend(self._get_dir_pairs(files))
        process = subprocess.Popen(args, env=self.env, close_fds=True)

        # Django's autoreload calls sys.exit() before reloading, and we want to
        # kill the Sass process we've spawned at that point.
        def cleanup():
            process.kill()

        atexit.register(cleanup)
        print("Watching for Sass changes")
