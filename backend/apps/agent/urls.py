from django.urls import path
from .views import create_task, get_task, view_report

urlpatterns = [
    path("agent/tasks", create_task),
    path("agent/tasks/<int:task_id>", get_task),
    path("agent/tasks/<int:task_id>/report", view_report),  # rapor sayfası
]