from django.http import HttpResponse
import requests
import json
import os
import uuid
import concurrent.futures
from django.conf import settings
from nodes.connectors import TelegramConnector
from nodes.forms import NodeForm
from nodes.models import Node
from rest_framework import views
import rest_framework.permissions
from django.http.response import JsonResponse, FileResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
import shlex
import shutil
from core.utils import auto_retry
import mimetypes
from cachetools import TTLCache


def download_file_chunk(chunk_name, chunk_object, temp_dir_path):
    chunk_url = chunk_object.get("url")
    if not chunk_url and chunk_object.get("telegram_file_id"):
        telegram_connector = TelegramConnector()
        chunk_url = telegram_connector.get_file_url(chunk_object["telegram_file_id"])

    @auto_retry
    def get_request_url_response():
        response = requests.get(chunk_url)
        response.raise_for_status()

        return response.content

    print(f"Downloading chunk {chunk_name} from {chunk_url}")
    content = get_request_url_response()

    chunk_path = os.path.join(temp_dir_path, chunk_name)
    with open(chunk_path, "wb") as f:
        print(f"Saving chunk {chunk_name} on {chunk_path}")
        f.write(content)


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


def get_file_data_from_node_id(node_id: str):
    if node_id in cache:
        return cache[node_id]

    node = Node.objects.get(id=node_id)
    content = json.loads(node.data)
    chunk_objects = content["chunks"]
    compressed = content["compressed"]

    temp_dir_path = os.path.join(settings.BASE_DIR, "tmp", uuid.uuid4().__str__())
    os.makedirs(temp_dir_path, exist_ok=True)

    master_chunk_name: str = None

    with concurrent.futures.ProcessPoolExecutor(max_workers=16) as executor:
        futures = []
        for chunk_object in chunk_objects:
            chunk_name = chunk_object["name"]
            if not compressed or "001" == chunk_name[-3::]:
                master_chunk_name = chunk_name

            futures.append(
                executor.submit(
                    download_file_chunk, chunk_name, chunk_object, temp_dir_path
                )
            )

        for future in futures:
            future.result()

    if compressed:
        unzip_result_dir_path = os.path.join(temp_dir_path, "result")
        master_zip_path = shlex.quote(os.path.join(temp_dir_path, master_chunk_name))

        os.makedirs(unzip_result_dir_path, exist_ok=True)

        unzip_command = f"7z x {master_zip_path} -o{unzip_result_dir_path}"
        os.system(unzip_command)

        result_file_name = os.listdir(unzip_result_dir_path)[0]
        result_file_path = os.path.join(unzip_result_dir_path, result_file_name)

    else:
        result_file_path = os.path.join(temp_dir_path, os.listdir(temp_dir_path)[0])

    mime_type, _ = mimetypes.guess_type(result_file_path) or "application/octet-stream"
    data = None

    with open(result_file_path, "rb") as f:
        data = f.read()

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

    def get(self, request, *args):
        return JsonResponse(
            {
                "result": Node.tree(),
            }
        )

    def post(self, request, *args):
        node_form = NodeForm(data=request.POST, files=request.FILES)
        instance = node_form.save(commit=False)
        instance.save()

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
