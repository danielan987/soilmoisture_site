from django.db import models

class LocationQuery(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    query_text = models.CharField(max_length=255)
    lat = models.FloatField()
    lon = models.FloatField()
    display_name = models.TextField()

    def __str__(self):
        return f"{self.query_text} -> ({self.lat:.4f}, {self.lon:.4f})"
