from django.urls import path
from buckets.views import (
    BucketShareView,
    BucketView,
    ChunksView,
    NodesView,
    NodesDownloadView,
)

urlpatterns = [
    path(
        "",
        BucketView.as_view(),
    ),
    path(
        "<str:bucket_id>/",
        BucketView.as_view(),
    ),
    path(
        "<str:bucket_id>/share/",
        BucketShareView.as_view(),
    ),
    path(
        "<str:bucket_id>/nodes/",
        NodesView.as_view(),
    ),
    path(
        "<str:bucket_id>/nodes/<str:node_id>/",
        NodesView.as_view(),
    ),
    path(
        "<str:bucket_id>/nodes/<str:node_id>/chunks/<int:chunk_index>/",
        ChunksView.as_view(),
    ),
    path(
        "<str:bucket_id>/nodes/<str:node_id>/download/",
        NodesDownloadView.as_view(),
    ),
]
