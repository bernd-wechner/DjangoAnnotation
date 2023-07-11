# DjangoAnnotation

Minimal Django app for experimenting with complex annotations.

At present set up in support of this question:

https://stackoverflow.com/questions/76660098/annotating-a-django-queryset-with-the-sum-of-the-max-of-a-subquery

There are only three models, and there is a sample database included. It was generated using the management command [load_data](https://github.com/bernd-wechner/DjangoAnnotation/blob/main/DjangoAnnotation/management/commands/load_data.py).

`python manage.py load_data`

The data can be inspected for manual verification of expectations using the management command [list_data](https://github.com/bernd-wechner/DjangoAnnotation/blob/main/DjangoAnnotation/management/commands/list_data.py).

`python manage.py list_data`

The annotations are tested in the management command [annotate](https://github.com/bernd-wechner/DjangoAnnotation/blob/main/DjangoAnnotation/management/commands/annotate.py).

`python manage.py annotate`

Requirements are in [requirements.txt](https://github.com/bernd-wechner/DjangoAnnotation/blob/main/requirements.txt). Typically you'd gets started by installing that in a [venv](https://docs.python.org/3/library/venv.html), something like this (on a *nix system, slightly different on Windows):

```
$ python -m venv my_venv_dir
$ source my_venv_dir/bin/activate
(my_venv_dir) $ pip install -r requirments.txt
(my_venv_dir) $ python manage.py annotate  # To try it out
```

