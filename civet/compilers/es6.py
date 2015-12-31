import errno
import os

from civet.compilers.base_compiler import Compiler


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class ES6Compiler(Compiler):
    """Civet compiler for Ecmascript 6 using Babel.
    """
    def __init__(self, precompiled_assets_dir, kill_on_error):
        super(ES6Compiler, self).__init__(precompiled_assets_dir,
                                          kill_on_error)
        self.args = [('--compile', '--map')]

    @property
    def name(self):
        return "Ecmascript 6"

    @property
    def executable_name(self):
        return 'babel'

    @property
    def executable_setting(self):
        return 'CIVET_BABEL_BIN'

    def matches(self, base, ext):
        return ext == '.es6'

    def get_dest_path(self, base, ext):
        return os.path.join(self.precompiled_assets_dir, base + '.js')

    def get_arguments(self, src_path, dst_path):
        return [
            self.executable,
            '--source-maps true',
            '-o',
            dst_path,
            src_path,
        ]

    def compile(self, src_path, dst_path):
        dst_dir, dst_basename = os.path.split(dst_path)
        mkdir_p(dst_dir)
        super(ES6Compiler, self).compile(src_path, dst_path)

        # TODO: handle sourcemap rewriting or use correct babel arguments.
