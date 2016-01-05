from __future__ import print_function
import json
import os

from django.conf import settings

from civet.compilers.base_compiler import Compiler


class CoffeescriptCompiler(Compiler):
    name = "CoffeeScript"
    executable_name = 'coffee'
    executable_setting = 'CIVET_COFFEE_BIN'

    def __init__(self, precompiled_assets_dir, kill_on_error):
        super(CoffeescriptCompiler, self).__init__(precompiled_assets_dir,
                                                   kill_on_error)
        self.args = getattr(
            settings, 'CIVET_COFFEE_SCRIPT_ARGUMENTS', ('--compile', '--map'))

    def matches(self, base, ext):
        return ext == '.coffee'

    def get_dest_path(self, base, ext):
        return os.path.join(self.precompiled_assets_dir, base + '.js')

    def get_command_with_arguments(self, src_path, dst_path):
        dst_dir, dst_basename = os.path.split(dst_path)

        # coffee is smart enough to do mkdir -p for us
        args = [self.executable, '-o', dst_dir]
        args.extend(self.args)
        args.append(src_path)
        return args

    def compile(self, src_path, dst_path):
        super(CoffeescriptCompiler, self).compile(src_path, dst_path)

        # check_call raises an exception if the exit status is not 0, so the
        # fact that we reach here means we can safely massage the map file.
        #
        # The reason we need to massage the map is that when `coffee -o` is
        # used, the sourceRoot and sources keys in the map become relative path
        # references, which are not valid paths from Django static file
        # finder's point of view.
        #
        # For example, if the JS file is at
        #
        #     /static/myapp/js/foo.js
        #
        # And the actual coffee source lives in
        #
        #     <source root>/myapp/static/myapp/js/foo.coffee
        #
        # Without the massaging, sourceRoot and sources in the map are:
        #
        #     {
        #         "sourceRoot": "../../..",
        #         "sources": ["myapp/static/myapp/js/foo.coffee"]
        #     }
        #
        # Which would make the browser want to fetch this:
        #
        #     /myapp/static/myapp/js/foo.coffee
        #
        # Which we know is wrong.
        #
        # By removing the relative references, the browser will correctly fetch
        #
        #     /static_files/myapp/js/foo.coffee
        #
        # Which will be found by Django's static finder correctly.
        dst_dir, dst_basename = os.path.split(dst_path)
        map_filename = os.path.splitext(dst_basename)[0] + '.map'
        map_path = os.path.join(dst_dir, map_filename)

        if os.path.exists(map_path):
            map_data = None
            with open(map_path) as f:
                map_data = json.load(f)
                map_data['sourceRoot'] = ''
                map_data['sources'] = [os.path.basename(src_path)]

            with open(map_path, 'w') as f:
                json.dump(map_data, f)
