from typing import List
from django import views
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
from django.http.response import JsonResponse, StreamingHttpResponse
from core.utils import auto_retry
import mimetypes
from cachetools import TTLCache


browser_mime_types = set(
    [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
        # Videos
        "video/mp4",
        "video/webm",
        "video/ogg",
        # Audio
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/webm",
        # PDFs
        "application/pdf",
        # Text
        "text/html",
        "text/css",
        "text/plain",
        "text/javascript",
        # XML and JSON
        "application/xml",
        "application/json",
        "application/xhtml+xml",
    ]
)


MAX_CACHE_SIZE = 5 * 1024 * 1024 * 1024
TTL = 6 * 60 * 60
cache = TTLCache(maxsize=MAX_CACHE_SIZE, ttl=TTL)


@auto_retry
def get_url_data_content(url: str) -> bytes:
    if url.startswith("http://") or url.startswith("https://"):
        response = requests.get(url)
        response.raise_for_status()

        return response.content

    with open(os.path.join(settings.BASE_DIR, url), "rb") as f:
        return f.read()


def get_chunk_data(chunk: Chunk):
    if result := cache.get(chunk.id):
        return result

    chunk_data_dict: dict = json.loads(chunk.data)
    url = chunk_data_dict.get("url") or TelegramConnector.get_file_url(
        chunk_data_dict["telegram_file_id"]
    )
    chunk_data = get_url_data_content(url)
    cache[chunk.id] = chunk_data

    return chunk_data


def get_file_data_in_chunks_from_node(node: Node):
    yield b""

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures: List[concurrent.futures.Future[bytes]] = []
        for chunk in node.chunks.all().order_by("index"):
            future = executor.submit(get_chunk_data, chunk)
            futures.append(future)

        for future in futures:
            yield future.result()


class NodesView(views.View):
    serializer_class = None

    def get(self, _, node_id=None):
        return JsonResponse(
            {
                "result": Node.tree(node_id=node_id, order_by=["name"]),
            }
        )

    def post(self, request: HttpRequest, *args):
        chunks: int = int(request.POST.get("chunks"))
        name = request.POST.get("name")
        parent_id = request.POST.get("parent")

        node = None
        try:
            node = Node.objects.get(
                name=name,
                parent_id=parent_id,
            )
            return JsonResponse(
                {
                    "result": node.representation(),
                }
            )
        except Node.DoesNotExist:
            pass

        node_form = NodeForm(data=request.POST, files=request.FILES)
        instance: Node = node_form.save(commit=False)
        instance.save()

        for index in range(chunks):
            chunk_id = uuid.uuid4().hex[0:8]
            Chunk.objects.get_or_create(
                index=index,
                node=instance,
                defaults={
                    "id": chunk_id,
                },
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


class ChunksView(views.View):
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


class NodesDownloadView(views.View):
    def get(self, request: HttpRequest, node_id: str):
        preview = request.GET.get("preview") in set(["1", "true", "True"])
        node = Node.objects.get(id=node_id)

        response = StreamingHttpResponse(
            get_file_data_in_chunks_from_node(node),
        )

        content_type = mimetypes.guess_type(node.name)[0] or "application/octet-stream"
        response["Content-Disposition"] = (
            f'{"inline" if content_type in browser_mime_types and preview else "attachment"}; filename="{node.name}"'
        )
        response["Content-Type"] = content_type
        response["Content-Length"] = node.size

        return response
