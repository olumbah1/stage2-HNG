from django.db import models
from django.utils import timezone

class Country(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    capital = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    population = models.BigIntegerField()
    currency_code = models.CharField(max_length=3, null=True, blank=True, db_index=True)
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True)
    estimated_gdp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    flag_url = models.URLField(null=True, blank=True)
    last_refreshed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-estimated_gdp']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['region']),
            models.Index(fields=['currency_code']),
        ]

    def __str__(self):
        return self.name