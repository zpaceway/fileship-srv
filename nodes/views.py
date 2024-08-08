import requests
import json
import os
import uuid
import concurrent.futures
from django.conf import settings
import zipfile
from nodes.forms import NodeForm
from nodes.models import Node
from rest_framework import views
import rest_framework.permissions
from django.http.response import JsonResponse, FileResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
import shlex
import shutil
from nodes.utils import get_response_from_callback_or_retry_on_error


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

    def get(self, request, node_id: str):
        node = Node.objects.get(id=node_id)
        content = json.loads(node.data)
        chunks = content["chunks"]
        compressed = content["compressed"]

        temp_dir = os.path.join(settings.BASE_DIR, f"tmp/{uuid.uuid4()}")
        result_dir = os.path.join(temp_dir, "result")
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(result_dir, exist_ok=True)

        def process_indexed_url(file_name, url):
            local_filename = os.path.join(temp_dir, file_name)
            local_files.append(local_filename)
            response = get_response_from_callback_or_retry_on_error(
                lambda: requests.get(url)
            )
            print(f"Success {url}")
            with open(local_filename, "wb") as f:
                f.write(response.content)

        # Download the split files and save them locally
        local_files = []
        master_zip_file_name: str = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            for chunk in chunks:
                file_name = chunk["name"]
                if not compressed or "001" == file_name[-3::]:
                    master_zip_file_name = file_name
                file_url = chunk["url"]
                executor.submit(process_indexed_url, file_name, file_url)

        part_files = list(map(lambda path: f"{temp_dir}/{path}", os.listdir(temp_dir)))
        part_files.sort()
        if compressed:
            zip_fullname = shlex.quote(f"{temp_dir}/{master_zip_file_name}")
            unzip_command = f"7z x {zip_fullname} -o{result_dir}"
            os.system(unzip_command)
            result_file = os.listdir(result_dir)[0]
            result_file = f"{result_dir}/{result_file}"

        else:
            result_file = f"{temp_dir}/{os.listdir(temp_dir)[0]}"

        # Create a response containing the extracted file
        response = FileResponse(open(result_file, "rb"), as_attachment=True)
        response["Content-Disposition"] = f'attachment; filename="{node.name}"'

        shutil.rmtree(temp_dir)

        return response
