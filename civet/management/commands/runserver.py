from django.contrib.staticfiles.management.commands import runserver

from civet.asset_precompiler import precompile_and_watch_assets


class Command(runserver.Command):

    def get_handler(self, *args, **options):
        precompile_and_watch_assets()
        return super(Command, self).get_handler(*args, **options)
