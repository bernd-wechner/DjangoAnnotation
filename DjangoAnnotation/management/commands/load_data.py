import names
import random

from django.core.management.base import BaseCommand
from django.db import connection

from DjangoAnnotation.models import Top, Middle, Lower


class Command(BaseCommand):

    def handle(self, *args, **options):
        # define the tree
        tops = 5
        middles = (2, 10)
        lowers = (2, 10)

        # define the lower uniqueness
        ulowers = 10
        nlowers = tops * sum(middles)//2 * sum(lowers)//2 // ulowers
        lower_names = [names.get_full_name() for _ in range(nlowers)]

        # Start with a clean database
        Top.objects.all().delete()
        Middle.objects.all().delete()
        Lower.objects.all().delete()

        # Ensure ID sequences are reset
        with connection.cursor() as cursor:
            def reset_sequence(model):
                tbl = model._meta.db_table
                sql = f"DELETE FROM `sqlite_sequence` WHERE `name` = '{tbl}';"
                cursor.execute(sql)
            reset_sequence(Top)
            reset_sequence(Middle)
            reset_sequence(Lower)

        print("Adding this data:")
        for t in range(tops):  # @UnusedVariable
            T = Top(name=names.get_full_name())
            T.save()
            print(f"\t{T.name}:")
            for m in range(middles[0], random.randint(middles[0]+1, middles[1]+1)):  # @UnusedVariable
                M = Middle(name=names.get_full_name())
                M.reports_to = T
                M.klass = random.randint(1, 2)
                M.save()
                print(f"\t\t{M.name}, {M.klass}:")
                used = set()
                for l in range(lowers[0], random.randint(lowers[0]+1, lowers[1]+1)):  # @UnusedVariable
                    name = random.choice(lower_names)
                    while name in used:
                        name = random.choice(lower_names)
                    L = Lower(name=name)
                    L.rank = Lower.objects.filter(name=L.name).count() + 1
                    L.reports_to = M
                    L.save()
                    used.add(name)
                    print(f"\t\t\t{L.name}, {L.rank}")
