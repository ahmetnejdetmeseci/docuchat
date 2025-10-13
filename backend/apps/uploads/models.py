from django.db import models

class Tenant(models.Model):
    name = models.CharField(max_length=150, unique=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Document(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='documents')
    filename = models.CharField(max_length=255)
    text = models.TextField(blank=True, default="")
    size = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} ({self.tenant.name})"

class Chunk(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='chunks')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    index = models.IntegerField()
    page = models.IntegerField(null=True, blank=True, default=None)
    text = models.TextField()

    class Meta:
        indexes = [models.Index(fields=['tenant','document','index'])]

class Report(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=255)
    content_md = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

class Task(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='tasks')
    topic = models.CharField(max_length=255)
    status = models.CharField(max_length=50, default="queued")
    group = models.CharField(max_length=255)  # ws group name
    steps = models.JSONField(default=list, blank=True)
    report = models.ForeignKey(Report, null=True, blank=True, on_delete=models.SET_NULL, related_name='task')
    created_at = models.DateTimeField(auto_now_add=True)
