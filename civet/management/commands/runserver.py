from django.contrib.staticfiles.management.commands import runserver

from civet.asset_precompiler import precompile_and_watch_coffee_and_sass_assets     # nopep8


class Command(runserver.Command):

    def get_handler(self, *args, **options):
        precompile_and_watch_coffee_and_sass_assets()
        return super(Command, self).get_handler(*args, **options)
