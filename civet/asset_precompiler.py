from __future__ import print_function
from collections import defaultdict
import os
import subprocess
import sys

from django.conf import settings
from django.contrib.staticfiles import finders

from civet.compilers.base_compiler import CompilerObserver
from civet.compilers.coffeescript import CoffeescriptCompiler
from civet.compilers.es6 import ES6Compiler
from civet.compilers.sass import SassCompiler
from civet.util import raise_error_or_kill


try:
    from django.utils.six.moves import _thread as thread
except ImportError:
    from django.utils.six.moves import _dummy_thread as thread

if not hasattr(settings, 'CIVET_PRECOMPILED_ASSET_DIR'):
    raise AssertionError(
        'Must specify CIVET_PRECOMPILED_ASSET_DIR in settings')


# Directory to put the compiled JavaScript and CSS files.
precompiled_assets_dir = settings.CIVET_PRECOMPILED_ASSET_DIR

additional_ignore_patterns = getattr(
    settings, 'CIVET_IGNORE_PATTERNS', None)

ignore_dirs = getattr(
    settings, 'CIVET_IGNORE_DIRS', [])

compiler_classes = getattr(
    settings, 'CIVET_COMPILER_CLASSES', [
        CoffeescriptCompiler,
        ES6Compiler,
        SassCompiler]
)


def precompile_and_watch_assets():
    thread.start_new_thread(
        precompile_assets, (), {
            'watch': True,
            'kill_on_error': True
        })


def precompile_assets(watch=False, kill_on_error=False):
    """Precompile and watch assets for all configured Compilers.

    This function has the side effect of adding precompiled_assets_dir to
    settings.STATICFILES_DIRS. Django's staticfiles library uses that list
    to serve static assets.

    Args:
        watch: If True, the method will continue watching for Sass and
            CoffeeScript source changes in the background.
        kill_on_error: If True, the method will trigger a signal before
            calling `sys.exit()`. If you call this method from the Django
            `runserver` management command, you need to use this so that you
            can correctly stop the command's loader thread.
    """
    if not os.path.exists(precompiled_assets_dir):
        print('Directory created for saving precompiled assets: %s' % (
            precompiled_assets_dir))
        os.makedirs(precompiled_assets_dir)

    if precompiled_assets_dir not in settings.STATICFILES_DIRS:
        settings.STATICFILES_DIRS += (precompiled_assets_dir,)

    if watch:
        observer = CompilerObserver()

    # Create compilers, also checks if executables exist.
    compilers = []
    for compiler_class in compiler_classes:
        compilers.append(compiler_class(precompiled_assets_dir, kill_on_error))

    src_dest_tuples_by_compiler = collect_files(compilers)

    try:
        for compiler in compilers:
            if src_dest_tuples_by_compiler[compiler]:
                compiler.compile_all(src_dest_tuples_by_compiler[compiler])
    except subprocess.CalledProcessError:
        print(
            'Incomplete asset precompilation, server not started.',
            file=sys.stderr)
        raise_error_or_kill(kill_on_error)

    if watch:
        for compiler in compilers:
            compiler.watch(src_dest_tuples_by_compiler[compiler], observer)
        observer.start()


def collect_files(compilers):
    """Collect files for given compilers across the project.

    Given list of compilers to collect files for, returns a dictionary mapping
    compiler to list of tuples (src_path, dest_path).

    This is a mini implementation of the "collectstatic" management command.
    """

    # This common ignore pattern is defined inline in
    # django.contrib.staticfiles.management.commands.collectstatic, and we
    # just repeat it here verbatim
    ignore_patterns = ['CVS', '.*', '*~']

    if additional_ignore_patterns:
        ignore_patterns.extend(additional_ignore_patterns)

    output = defaultdict(list)

    # staticfiles has two default finders, one for the STATICFILES_DIRS and
    # one for the /static directories of the apps listed in INSTALLED_APPS.
    # This allows us to discover all the files we are interested in across
    # the entire project, including the libraries it uses.

    for finder in finders.get_finders():
        for partial_path, storage in finder.list(ignore_patterns):
            # Get the actual path of the asset
            full_path = storage.path(partial_path)

            # Resolve symbolic links
            src_path = os.path.realpath(full_path)

            base, ext = os.path.splitext(partial_path)

            if not any(dirs in full_path for dirs in ignore_dirs):
                for compiler in compilers:
                    if compiler.matches(base, ext):
                        output[compiler].append(
                            (src_path, compiler.get_dest_path(base, ext)))
    return output
