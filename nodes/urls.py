from django.contrib import admin
from django.urls import path

from nodes.views import NodesView, NodesDownloadView

urlpatterns = [
    path("", NodesView.as_view()),
    path("<int:node_id>/download", NodesDownloadView.as_view()),
]
