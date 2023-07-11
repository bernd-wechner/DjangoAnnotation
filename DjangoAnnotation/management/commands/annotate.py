from django.core.management.base import BaseCommand
from django.db.models.aggregates import Max

from DjangoAnnotation.models import Top, Middle, Lower

from django.db.models import Case, Count, IntegerField, Sum, When, OuterRef, Subquery, Q, F, Window
from django.db.models.functions import RowNumber
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

        expected = {}
        def test_top(top, klass=None):
            l_filter = Q(reports_to__reports_to=top)
            if not klass is None:
                l_filter &= Q(reports_to__klass=klass)
            highest_ranks = Lower.objects.filter(l_filter).values('reports_to__reports_to', 'name').annotate(highest_rank=Max('rank')).values('highest_rank')
            sum_highest_ranks = highest_ranks.aggregate(total=Sum('highest_rank'))
            if not top.name in expected: expected[top.name] = {}
            expected[top.name][klass] = sum_highest_ranks['total']
            print(f"\t\tGot sum of {sum_highest_ranks['total']}, for {top.name} from:")
            for r in highest_ranks:
                print(f"\t\t\t{r}")

        print("\tChecking each top individually (no klass)")
        for t in Top.objects.all():
            test_top(t)

        print("\tChecking each top individually (klass 2)")
        for t in Top.objects.all():
            test_top(t,2)

        def test_query(klass=None, top=None, method=1):
            if method == 1:
                # This gets the FIRST of the MAX for some reason even though we ask for the SUM
                # Explored here: https://stackoverflow.com/questions/76660098/annotating-a-django-queryset-with-the-sum-of-the-max-of-a-subquery
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

            elif method == 2:
                # This works, but aaargh, Raw SQL!
                where_klass = "" if klass is None else f'WHERE M."klass"={klass}\n'
                query = f"""
                    SELECT id, name, SUM(max) AS high_rank_sums
                    FROM
                        (SELECT T."id" AS id, T."name" AS name, MAX(L."rank") AS max
                         FROM "DjangoAnnotation_top" T
                         INNER JOIN "DjangoAnnotation_middle" M ON M.reports_to_id = T.id
                         INNER JOIN "DjangoAnnotation_lower" L ON L.reports_to_id = M.id
                         {where_klass}GROUP BY T."id",T."name", L."name")
                    GROUP BY id, name
                """

                Tops = Top.objects.raw(query)

            elif method == 3:
                # This crashes with: django.core.exceptions.FieldError: Cannot compute Sum('max_rank'): 'max_rank' is an aggregate
                Tops = Top.objects.annotate(max_rank=Max('middles__lowers__rank')).values('name').annotate(high_rank_sums=Sum('max_rank'))

            elif method == 4:
                # Appears to generate valid SQL that should work, but doesn't ... Odd.
                subquery = Lower.objects.filter(reports_to__reports_to_id=OuterRef('id')).values('reports_to__id').annotate(
                    max_rank=Max('rank')
                ).values('max_rank')

                Tops = Top.objects.annotate(high_rank_sums=Sum(Subquery(subquery)))

            elif method == 5:
                # Appears to return arbitrary values from the list of MAXs ... odd
                subquery = Lower.objects.filter(reports_to__reports_to_id=OuterRef('id')).values('reports_to__id').annotate(
                    max_rank=Max('rank')
                ).values('max_rank')

                Tops = Top.objects.annotate(
                    max_rank=Subquery(subquery),
                    high_rank_sums=Sum(
                        Case(
                            When(max_rank__isnull=False, then=F('max_rank')),
                            default=0,
                            output_field=IntegerField(),
                        )
                    )
                )

            elif method == 6:
                # Bombs with: django.core.exceptions.FieldError: Cannot compute Sum('max_rank'): 'max_rank' is an aggregate
                middle_subquery = Middle.objects.filter(reports_to=OuterRef('id')).values('id')

                top_subquery = Middle.objects.filter(reports_to__in=Subquery(middle_subquery)).values('reports_to')

                Tops = Top.objects.annotate(
                    max_rank=Max('middles__lowers__rank'),
                ).annotate(
                    high_rank_sums=Sum('max_rank', filter=Subquery(top_subquery))
                )

            elif method == 7:
                # Bombs on django.core.exceptions.FieldError: Unsupported lookup 'reports_to_id' for ForeignKey or join on the field not permitted.
                middle_subquery = Middle.objects.filter(reports_to__reports_to_id=OuterRef('id')).values('reports_to__id')

                Tops = Top.objects.annotate(
                    max_rank=Max('middles__lowers__rank'),
                    row_number=Window(
                        expression=RowNumber(),
                        partition_by=[F('id')],
                        order_by=F('id').asc()
                    )
                ).annotate(
                    high_rank_sums=Sum('max_rank', filter=Subquery(
                        middle_subquery.annotate(
                            row_number=Window(expression=RowNumber(), order_by=F('max_rank').desc())
                        ).filter(row_number=1).values('max_rank')
                    ))
                )

            # print(f"\t\tExpecting:")
            # for t in Tops:
            #     print(f"\t\t\t{t.name}, {expected[t.name][klass]}")

            print(f"\t\tProduced:")
            for t in Tops:
                status = "PASS" if  t.high_rank_sums == expected[t.name][klass] else "FAIL"
                print(f"\t\t\t{t.name}, {t.high_rank_sums} expected {expected[t.name][klass]}    {status}")


        method = 2
        print("\tTrying a Queryset (no klass)")
        test_query( method=method)

        print("\tTrying a Queryset (klass 2)")
        #test_query(2, Top.objects.get(name="Jill Tuley"))
        test_query(2, method=method)
