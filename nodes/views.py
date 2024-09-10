from django.http import HttpResponse
import requests
import json
import os
import uuid
import concurrent.futures
from django.conf import settings
from django.http.request import HttpRequest
from nodes.connectors import TelegramConnector
from nodes.forms import ChunkForm, NodeForm
from nodes.models import Chunk, Node
from rest_framework import views
import rest_framework.permissions
from django.http.response import JsonResponse
import shutil
from core.utils import auto_retry
import mimetypes
from cachetools import TTLCache


browser_mime_types = [
    "text/html",
    "text/plain",
    "text/css",
    "text/javascript",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "application/javascript",
    "application/json",
    "application/pdf",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "video/mp4",
    "video/webm",
    "video/ogg",
    "application/xml",
    "application/xhtml+xml",
]

MAX_CACHE_SIZE = 5 * 1024 * 1024 * 1024
TTL = 6 * 60 * 60
cache = TTLCache(maxsize=MAX_CACHE_SIZE, ttl=TTL)


@auto_retry
def get_url_data_content(url) -> bytes:
    response = requests.get(url)
    response.raise_for_status()

    return response.content


def get_file_data_from_node_id(node_id: str):
    if node_id in cache:
        return cache[node_id]

    node = Node.objects.get(id=node_id)

    temp_dir_path = os.path.join(settings.BASE_DIR, "tmp", uuid.uuid4().__str__())
    os.makedirs(temp_dir_path, exist_ok=True)

    telegram_connector = TelegramConnector()

    data_chunks = []

    for chunk in node.chunks.all().order_by("index"):
        telegram_file_id = json.loads(chunk.data)["telegram_file_id"]
        url = telegram_connector.get_file_url(telegram_file_id)
        chunk_data = get_url_data_content(url)
        data_chunks.append(chunk_data)

    data = b"".join(data_chunks)
    result_file_path = os.path.join(temp_dir_path, "result")

    with open(result_file_path, "wb") as file:
        file.write(data)

    mime_type, _ = mimetypes.guess_type(result_file_path) or "application/octet-stream"
    shutil.rmtree(temp_dir_path)
    result = [data, mime_type, node.name]
    cache[node_id] = result

    return result


class NodesView(views.APIView):
    permission_classes = (rest_framework.permissions.AllowAny,)
    authentication_classes = ()
    # permission_classes = (rest_framework.permissions.IsAuthenticated,)
    # authentication_classes = (JWTAuthentication,)

    serializer_class = None

    def get(self, _, *args):
        return JsonResponse(
            {
                "result": Node.tree(),
            }
        )

    def post(self, request: HttpRequest, *args):
        chunks: int = request.POST.get("chunks")

        node_form = NodeForm(data=request.POST, files=request.FILES)

        instance: Node = node_form.save(commit=False)
        instance.save()

        for index in range(chunks):
            Chunk.objects.get_or_create(
                index=index,
                node=instance,
            )

        return JsonResponse(
            {
                "result": instance.representation(),
            }
        )

    def patch(self, request, node_id):
        node = Node.objects.get(id=node_id)
        node.name = request.POST.get("name")
        node.save()

        return JsonResponse(
            {
                "result": node.representation(),
            }
        )

    def delete(self, request, node_id):
        node = Node.objects.get(id=node_id)
        node.delete()

        return JsonResponse(
            {
                "status": "success",
            }
        )


class ChunksView(views.APIView):
    permission_classes = (rest_framework.permissions.AllowAny,)
    authentication_classes = ()
    # permission_classes = (rest_framework.permissions.IsAuthenticated,)
    # authentication_classes = (JWTAuthentication,)

    serializer_class = None

    def get(
        self,
        _,
        node_id,
        chunk_index,
    ):
        chunk = Chunk.objects.get(
            node_id=node_id,
            index=chunk_index,
        )
        return JsonResponse(
            {
                "result": chunk.representation(),
            }
        )

    def post(
        self,
        request: HttpRequest,
        node_id,
        chunk_index,
    ):
        chunk = Chunk.objects.get(
            node_id=node_id,
            index=chunk_index,
        )
        node_form = ChunkForm(
            data=request.POST,
            files=request.FILES,
            instance=chunk,
        )

        instance: Chunk = node_form.save(commit=False)
        instance.save()

        return JsonResponse(
            {
                "result": instance.representation(),
            }
        )


class NodesDownloadView(views.APIView):
    permission_classes = (rest_framework.permissions.AllowAny,)
    authentication_classes = ()

    serializer_class = None

    def get(self, _, node_id: str):
        result = get_file_data_from_node_id(node_id)

        data, mime_type, filename = result

        response = HttpResponse(
            data,
        )

        response["Content-Disposition"] = (
            f'{"inline" if mime_type in browser_mime_types else "attachment"}; filename="{filename}"'
        )
        response["Content-Type"] = mime_type

        return response
