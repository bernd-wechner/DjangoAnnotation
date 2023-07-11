import names
import random

from django.core.management.base import BaseCommand
from django.db import connection

from DjangoAnnotation.models import Top, Middle, Lower


class Command(BaseCommand):

    def handle(self, *args, **options):
        for t in Top.objects.all():  # @UnusedVariable
            print(f"{t.name}:")
            for m in t.middles.all():  # @UnusedVariable
                print(f"\t{m.name}, {m.klass}:")
                for l in m.lowers.all():  # @UnusedVariable
                    print(f"\t\t{l.name}, {l.rank}")
