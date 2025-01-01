from typing import List, Optional
from rest_framework import views
import requests
import json
import os
import concurrent.futures
from django.conf import settings
from rest_framework.request import Request
from core.models import FileshipUser
from django.core.files.uploadedfile import UploadedFile
from django.core.files.base import ContentFile
from buckets.connectors import TelegramConnector
from buckets.forms import BucketForm, ChunkForm, NodeForm
from buckets.models import Bucket, Chunk, Node
from rest_framework.permissions import AllowAny
from rest_framework.views import Response
from django.http.response import StreamingHttpResponse
from fileship.utils import auto_retry
import mimetypes

from buckets.utils import generate_random_uuid


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


@auto_retry
def get_url_data_content(url: str) -> bytes:
    if url.startswith("http://") or url.startswith("https://"):
        response = requests.get(url)
        response.raise_for_status()

        return response.content

    with open(os.path.join(settings.BASE_DIR, url), "rb") as f:
        return f.read()


def get_chunk_data(chunk: Chunk):
    chunk_data_dict: dict = json.loads(chunk.data)
    url = chunk_data_dict.get("url") or TelegramConnector.get_file_url(
        chunk_data_dict["telegram_file_id"]
    )
    chunk_data = get_url_data_content(url)

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


class BucketView(views.APIView):
    def get(self, request: Request):
        return Response(
            {
                "result": [
                    bucket.representation()
                    for bucket in Bucket.objects.filter(
                        users__in=[request.user],
                    ).order_by("name")
                ],
            }
        )

    def post(self, request: Request):
        name = request.data["name"]
        bucket_form = BucketForm(
            data={
                "id": generate_random_uuid(),
                "name": name,
            }
        )
        bucket = bucket_form.save(commit=False)
        bucket.save()
        bucket.users.add(request.user)

        return Response(
            {
                "result": bucket.representation(),
            }
        )

    def delete(self, request: Request, bucket_id: str):
        bucket = Bucket.objects.get(
            id=bucket_id,
            users__in=[request.user],
        )
        bucket.delete()

        return Response(
            {
                "status": "success",
            }
        )

    def patch(self, request: Request, bucket_id: str):
        bucket = Bucket.objects.get(
            id=bucket_id,
            users__in=[request.user],
        )
        bucket.name = request.data["name"]
        bucket.save()

        return Response(
            {
                "status": "success",
            }
        )


class BucketShareView(views.APIView):
    def post(self, request: Request, bucket_id: str):
        bucket = Bucket.objects.get(
            id=bucket_id,
            users__in=[request.user],
        )
        fuser = FileshipUser.get_from_email(request.data["email"])
        bucket.users.add(fuser.user)

        return Response(
            {
                "result": bucket.representation(),
            }
        )


class NodesView(views.APIView):
    def get(
        self,
        request: Request,
        bucket_id,
        node_id: Optional[str] = None,
    ) -> Response:
        bucket = Bucket.objects.get(id=bucket_id)
        return Response(
            {
                "result": bucket.tree(
                    parent_node_id=node_id,
                    order_by=["name"],
                ),
            }
        )

    def post(
        self,
        request: Request,
        bucket_id: str,
        *args,
    ) -> Response:
        id = request.POST.get("id")
        name = request.POST.get("name")
        parent_id = request.POST.get("parent")
        size = int(request.POST.get("size", "0"))
        chunks = int(request.POST.get("chunks", "0"))

        file = request.FILES.get("file")
        connector = request.POST.get("connector")

        node = None
        try:
            node = Node.objects.get(
                name=name,
                parent_id=parent_id,
                bucket_id=bucket_id,
            )
            return Response(
                {
                    "result": node.representation(),
                }
            )
        except Node.DoesNotExist:
            pass

        chunk_data_files: List[ContentFile] = []
        if file and connector:
            file: UploadedFile = file
            data = file.read()
            chunk_size = 20 * 1024 * 1024

            for part_index, data_offset in enumerate(range(0, len(data), chunk_size)):
                chunk_data = data[data_offset : data_offset + chunk_size]
                chunk_file = ContentFile(chunk_data)
                chunk_file.name = f"{file.name}.part{part_index + 1}"
                chunk_data_files.append(chunk_file)

            id = id or generate_random_uuid()
            size = file.size
            chunks = len(chunk_data_files)

        if len(id) < 64:
            raise ValueError("NodeId must have at least 64 characters")

        new_node_data = {
            "id": id,
            "name": name,
            "parent": parent_id,
            "bucket": bucket_id,
            "size": size,
        }

        node_form = NodeForm(data=new_node_data)
        instance: Node = node_form.save(commit=False)
        instance.save()

        def save_chunk(index: int) -> None:
            chunk_id = generate_random_uuid()
            chunk, _ = Chunk.objects.get_or_create(
                index=index,
                node=instance,
                defaults={
                    "id": chunk_id,
                },
            )
            if chunk_data_files and chunk.data is None:
                chunk_data_file = chunk_data_files[index]
                chunk_form = ChunkForm(
                    data={
                        "id": chunk_id,
                        "node": instance.id,
                        "index": index,
                        "connector": connector,
                    },
                    files={
                        "file": chunk_data_file,
                    },
                    instance=chunk,
                )
                chunk_form.save(commit=False).save()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures: List[concurrent.futures.Future[None]] = []

            for index in range(chunks):
                future = executor.submit(save_chunk, index)
                futures.append(future)

            for future in futures:
                future.result()

        return Response(
            {
                "result": instance.representation(),
            }
        )

    def patch(
        self,
        request: Request,
        bucket_id: str,
        node_id: str,
    ) -> Response:
        node = Node.objects.get(id=node_id, bucket_id=bucket_id)
        node.name = request.data["name"]

        node.save()

        return Response(
            {
                "result": node.representation(),
            }
        )

    def delete(
        self,
        request: Request,
        bucket_id: str,
        node_id: str,
    ) -> Response:
        node = Node.objects.get(id=node_id, bucket_id=bucket_id)
        user_trash_bucket_id = f"{self.request.user.id}-trash-bucket"
        if node.bucket.id == user_trash_bucket_id:
            trash_bucket, _ = Bucket.objects.get_or_create(
                id="global-trash-bucket",
                defaults={
                    "name": ".Trash",
                },
            )
        else:
            trash_bucket, new = Bucket.objects.get_or_create(
                id=user_trash_bucket_id,
                defaults={
                    "name": ".Trash",
                },
            )
            if new:
                trash_bucket.users.add(self.request.user)

        node.update_bucket(trash_bucket.id)
        node.save()

        return Response(
            {
                "status": "success",
            }
        )


class ChunksView(views.APIView):
    def get(
        self,
        _,
        bucket_id,
        node_id,
        chunk_index,
    ):
        chunk = Chunk.objects.get(
            node__bucket_id=bucket_id,
            node_id=node_id,
            index=chunk_index,
        )
        return Response(
            {
                "result": chunk.representation(),
            }
        )

    def post(
        self,
        request: Request,
        bucket_id,
        node_id,
        chunk_index,
    ):
        chunk = Chunk.objects.get(
            node__bucket_id=bucket_id,
            node_id=node_id,
            index=chunk_index,
        )

        chunk_form = ChunkForm(
            data=request.POST,
            files=request.FILES,
            instance=chunk,
        )

        instance: Chunk = chunk_form.save(commit=False)
        instance.save()

        return Response(
            {
                "result": instance.representation(),
            }
        )


class NodesDownloadView(views.APIView):
    permission_classes = [AllowAny]

    def get(
        self,
        request: Request,
        bucket_id: str,
        node_id: str,
    ):
        node = Node.objects.get(bucket_id=bucket_id, id=node_id)

        response = StreamingHttpResponse(
            get_file_data_in_chunks_from_node(node),
        )

        content_type = mimetypes.guess_type(node.name)[0] or "application/octet-stream"
        inline_or_attachment = (
            "inline" if content_type in browser_mime_types else "attachment"
        )
        content_disposition = f'{inline_or_attachment}; filename="{node.name}"'
        response["Content-Disposition"] = content_disposition
        response["Content-Type"] = content_type
        response["Content-Length"] = node.size

        return response
