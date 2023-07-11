from django.core.management.base import BaseCommand
from django.db.models.aggregates import Max

from DjangoAnnotation.models import Top, Middle, Lower

from django.db.models import Case, Count, IntegerField, Sum, When, OuterRef, Subquery, Q
from django.db.models.functions import Coalesce
from django.db import connection

import sqlparse
from datetime import datetime, timedelta

def get_SQL(queryset, explain=False, pretty=True):
    '''
    A workaround for a bug in Django which is reported here (several times):
        https://code.djangoproject.com/ticket/30132
        https://code.djangoproject.com/ticket/25705
        https://code.djangoproject.com/ticket/25092
        https://code.djangoproject.com/ticket/24991
        https://code.djangoproject.com/ticket/17741

    that should be documented here:
        https://docs.djangoproject.com/en/2.1/faq/models/#how-can-i-see-the-raw-sql-queries-django-is-running
    but isn't.

    The work around was published by Zach Borboa here:
        https://code.djangoproject.com/ticket/17741#comment:4

    :param queryset: A Django QuerySet
    :param explain:  If True uses the server's EXPLAIN function. Not good for invalid SQL alas.
    :param pretty:   Format the SQL nicely
    '''
    if explain:
        sql, params = queryset.query.sql_with_params()
        cursor = connection.cursor()
        cursor.execute('EXPLAIN ' + sql, params)
        SQL = cursor.db.ops.last_executed_query(cursor, sql, params).replace("EXPLAIN ", "", 1)
    else:
        # We don't want to execute a query in this case but find the SQL reliablyf rom Django

        # We can get SQL and params from the query compiler
        sql, params = queryset.query.get_compiler(using=queryset.db).as_sql()

        # params is a dict of parameters.
        # DateTimes and TimeDeltas are alas converted to strings without the requiste
        # wrapping in single quotes. So we replace them by strign reps wrapped in single
        # quotes
        params = list(params)
        for i, p in enumerate(params):
            if isinstance(p, datetime):
                params[i] = "'" + str(p) + "'"
            elif isinstance(p, timedelta):
                params[i] = "INTERVAL '" + str(p) + "'"
        params = tuple(params)

        # And this is used when excuted as described here:
        #  https://docs.djangoproject.com/en/2.2/topics/db/sql/#passing-parameters-into-raw
        #
        # The key note being:
        #     params is a list or dictionary of parameters.
        #     You’ll use %s placeholders in the query string for a list,
        #     or %(key)s placeholders for a dictionary (where key is replaced
        #     by a dictionary key, of course)
        #
        # Which is precisely how Python2 standard % formating works.
        SQL = sql % params

    if pretty:
        return sqlparse.format(SQL, reindent=True, keyword_case='upper')
    else:
        return SQL


def print_SQL(queryset, explain=False, pretty=True):
    '''
    A trivial wrapper around get_SQL that simply prints the result. Useful primarily in a debugger say, to
    produce a SQL straing htat can be copied/ and pasted into a Query Tool. That is, it doesn't have quotes
    around it for example.

    :param queryset: A Django QuerySet
    :param explain:  If True uses the server's EXPLAIN function. Not good for invalid SQL alas.
    :param pretty:   Format the SQL nicely
    '''
    print(get_SQL(queryset, explain, pretty))


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Narrow scope:")

        expected = {}
        print("\tExpected Annotations (no klass):")
        for T in Top.objects.all():
            annos = [0, 0]
            for M in T.middles.all():
                annos[0] += 1
                for L in M.lowers.all():
                    annos[1] += 1
            print(f"\t\t{T.name}: {annos[0]}, {annos[1]}")
            expected[T.name] = tuple(annos)

        annotated = Top.objects.all().annotate(middle_count=Count('middles', distinct=True), lower_count=Count('middles__lowers', distinct=True))

        print("\tCreated Annotations (no klass):")
        for T in annotated:
            annos = (T.middle_count, T.lower_count)
            status = "PASS" if annos == expected[T.name] else "FAIL"
            print(f"\t{T.name}: {T.middle_count}, {T.lower_count}    {status}")

        klass = 1
        mfilter = Q(middles__klass=klass)
        expected = {}
        print(f"\tExpected Annotations (klass {klass}):")
        for T in Top.objects.all():
            annos = [0, 0]
            for M in T.middles.filter(klass=1):
                annos[0] += 1
                for L in M.lowers.all():
                    annos[1] += 1
            print(f"\t\t{T.name}: {annos[0]}, {annos[1]}")
            expected[T.name] = tuple(annos)

        annotated = Top.objects.annotate(
            middle_count=Count('middles', distinct=True, filter=mfilter),
            lower_count=Count('middles__lowers', distinct=True, filter=mfilter),
        )

        print(f"\tCreated Annotations (klass {klass}):")
        try:
            for T in annotated:
                annos = (T.middle_count, T.lower_count)
                status = "PASS" if annos == expected[T.name] else "FAIL"
                print(f"\t\t{T.name}: {T.middle_count}, {T.lower_count}    {status}")
        except Exception as E:
            print(E.args)

            print(f"\nSQL:")
            print_SQL(annotated)

        print("Broad scope:")

        def test_top(top, klass=None):
            l_filter = Q(reports_to__reports_to=top)
            if not klass is None:
                l_filter &= Q(reports_to__klass=klass)
            highest_ranks = Lower.objects.filter(l_filter).values('reports_to__reports_to', 'name').annotate(highest_rank=Max('rank')).values('highest_rank')
            sum_highest_ranks = highest_ranks.aggregate(total=Sum('highest_rank'))
            print(f"\t\tGot sum of {sum_highest_ranks}, for {top.name} from:")
            for r in highest_ranks:
                print(f"\t\t\t{r}")

        print("\tChecking each top individually (no klass)")
        for t in Top.objects.all():
            test_top(t)

        print("\tChecking each top individually (klass 2)")
        for t in Top.objects.all():
            test_top(t,2)

        def test_query(klass=None, top=None):
            if top is None:
                l_filter = Q(reports_to__reports_to=OuterRef('id'))
            else:
                l_filter = Q(reports_to__reports_to=top)
            if not klass is None:
                l_filter &= Q(reports_to__klass=klass)

            hr = Lower.objects.filter(l_filter).values('reports_to__reports_to', 'name').annotate(highest_rank=Max('rank')).values('highest_rank')

            if top:
                print(f"\t\t{top.name} drill down to highest ranks:")
                for l in hr:
                    print(f"\t\t\t{l}")
            else:
                Tops = Top.objects.annotate(high_rank_sums=Sum(Subquery(hr)))

                for t in Tops:
                    print(f"\t\t{t.name}, {t.high_rank_sums}")

        print("\tTrying a Queryset (no klass)")
        test_query()

        print("\tTrying a Queryset (klass 2)")
        test_query(2, Top.objects.get(name="Jill Tuley"))
        test_query(2)




