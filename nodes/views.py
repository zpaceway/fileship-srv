import requests
import json
import os
import uuid
import concurrent.futures
from django.conf import settings
import zipfile
from nodes.models import Node
from django import views
from django.http.response import JsonResponse, FileResponse


class NodesView(views.View):
    def get(self, request):
        return JsonResponse(
            {
                "result": Node.tree(),
            }
        )


class NodesDownloadView(views.View):
    def get(self, request, node_id: str):
        urls = json.loads(Node.objects.get(id=node_id).urls)

        temp_dir = os.path.join(settings.BASE_DIR, f"tmp/{uuid.uuid4()}")
        os.makedirs(temp_dir, exist_ok=True)

        def process_indexed_url(file_name, url):
            local_filename = os.path.join(temp_dir, file_name)
            local_files.append(local_filename)
            with requests.get(url) as r:
                print(f"Success {url}")
                with open(local_filename, "wb") as f:
                    f.write(r.content)

        # Download the split files and save them locally
        local_files = []
        master_zip_file = None
        result_name = os.path.join(temp_dir, "result.zip")
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            for url_obj in urls:
                file_name = url_obj["name"]
                if ".zip" == file_name[-4::]:
                    master_zip_file = os.path.join(temp_dir, file_name)
                file_url = url_obj["url"]
                executor.submit(process_indexed_url, file_name, file_url)

        rezip_command = f"zip -s0 '{master_zip_file}' --out '{result_name}'"
        unzip_command = f"unzip {result_name} -d {temp_dir}"
        os.system(rezip_command)
        os.system(unzip_command)

        result_file = os.listdir(f"{temp_dir}/tmp")[0]

        # Create a response containing the extracted file
        response = FileResponse(
            open(f"{temp_dir}/tmp/{result_file}", "rb"), as_attachment=True
        )
        response["Content-Disposition"] = 'attachment; filename="extracted_file"'

        return response
