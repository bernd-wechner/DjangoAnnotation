from django.db import models

class Top(models.Model):
    name = models.CharField(max_length=70)

class Middle(models.Model):
    name = models.CharField(max_length=70)
    klass = models.IntegerField(default=1)
    reports_to = models.ForeignKey(Top, related_name='middles', on_delete=models.CASCADE)

class Lower(models.Model):
    name = models.CharField(max_length=70)
    rank = models.IntegerField(default=1)
    reports_to = models.ForeignKey(Middle, related_name='lowers', on_delete=models.CASCADE)

