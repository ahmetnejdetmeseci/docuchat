
from django.db import models

class Document(models.Model):
    filename = models.CharField(max_length=255)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    index = models.IntegerField()
    page = models.IntegerField(null=True, blank=True, default=None) #daha iyi sonuc almak icin deneme
    text = models.TextField()
