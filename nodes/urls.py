from django.contrib import admin
from django.urls import path

from nodes.views import ChunksView, NodesView, NodesDownloadView

urlpatterns = [
    path("", NodesView.as_view()),
    path("<str:node_id>/", NodesView.as_view()),
    path("<str:node_id>/chunks/<int:chunk_index>", ChunksView.as_view()),
    path("<str:node_id>/download", NodesDownloadView.as_view()),
]
