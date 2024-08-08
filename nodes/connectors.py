import concurrent.futures
import abc
import os
import requests
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings


class AbstractConnector(abc.ABC):

    @abc.abstractmethod
    def upload(self, file: InMemoryUploadedFile):
        raise NotImplementedError()


class TelegramConnector(AbstractConnector):
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")
    MAX_CHUNK_SIZE_IN_MB = 10
    CHUNK_SIZE = 1024 * 1024 * MAX_CHUNK_SIZE_IN_MB

    def upload(self, uploaded_file: InMemoryUploadedFile):
        file_size = uploaded_file.size

        if file_size <= self.CHUNK_SIZE:
            return [
                {
                    "url": self.upload_chunk(uploaded_file, uploaded_file.name),
                    "name": uploaded_file.name,
                }
            ]
        else:
            return self.upload_large_file(uploaded_file)

    def get_file_path(self, file_id):
        url = f"https://api.telegram.org/bot{self.TELEGRAM_BOT_TOKEN}/getFile"
        params = {"file_id": file_id}

        response = requests.get(url, params=params)
        result = response.json()

        if result["ok"]:
            return result["result"]["file_path"]
        else:
            raise Exception(f"Failed to get file path: {result['description']}")

    def upload_chunk(self, file: InMemoryUploadedFile, filename):
        url = f"https://api.telegram.org/bot{self.TELEGRAM_BOT_TOKEN}/sendDocument"
        files = {"document": (filename, file.read())}  # Reading the content as bytes
        data = {"chat_id": self.TELEGRAM_ADMIN_CHAT_ID}

        response = requests.post(url, files=files, data=data)
        result = response.json()

        if result["ok"]:
            file_id = result["result"]["document"]["file_id"]
            file_url = f"https://api.telegram.org/file/bot{self.TELEGRAM_BOT_TOKEN}/{self.get_file_path(file_id)}"
            return file_url
        else:
            raise Exception(f"Failed to upload file: {result['description']}")

    def upload_large_file(self, uploaded_file: InMemoryUploadedFile):
        # Split the file into chunks and compress
        file_name = uploaded_file.name
        file_urls = []

        folder = f"./tmp/{file_name}"

        os.makedirs(folder, exist_ok=True)
        split_command = f"zip -s {self.MAX_CHUNK_SIZE_IN_MB}m '{folder}/{file_name}.zip' '{uploaded_file.temporary_file_path()}'"
        os.system(split_command)

        def process_split_file(split_file_name: str):
            split_file_path = f"{folder}/{split_file_name}"
            with open(split_file_path, "rb") as f:
                file_url = self.upload_chunk(
                    f, split_file_name
                )  # Open and pass the file directly
                file_urls.append({"url": file_url, "name": split_file_name})

        # Upload each split file
        split_files = [f for f in os.listdir(folder)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for split_file_name in split_files:
                executor.submit(process_split_file, split_file_name)

        return file_urls


class LocalConnector(AbstractConnector):
    def upload(self, file: InMemoryUploadedFile):
        file_path = f"{settings.BASE_DIR}/media/{file.name}"
        with open(file_path, "wb") as f:
            f.write(file.read())

        return [f"{os.getenv('APP_URL')}/media/{file.name}"]
