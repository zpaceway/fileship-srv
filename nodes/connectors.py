import concurrent.futures
import abc
import os
from typing import Dict, List, Literal, Union
import requests
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.conf import settings
from core.utils import auto_retry
import shlex
import uuid
from django.conf import settings
import shutil


class AbstractConnector(abc.ABC):

    name: str

    @classmethod
    @abc.abstractmethod
    def upload(
        self, file: InMemoryUploadedFile
    ) -> List[Dict[Union[Literal["name"], Literal["url"]], str]]:
        raise NotImplementedError()


class TelegramConnector(AbstractConnector):
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

    name = "Telegram Connector"

    @classmethod
    def upload(
        cls, uploaded_file: InMemoryUploadedFile
    ) -> List[Dict[Union[Literal["name"], Literal["url"]], str]]:
        filename = uploaded_file.name

        print(f"Uplaoding chunk {filename}")
        url = f"https://api.telegram.org/bot{cls.TELEGRAM_BOT_TOKEN}/sendDocument"
        files = {"document": (filename, uploaded_file.read())}
        data = {"chat_id": cls.TELEGRAM_ADMIN_CHAT_ID}

        @auto_retry
        def get_send_document_response():
            response = requests.get(url, files=files, data=data)
            response.raise_for_status()

            return response.json()

        result = get_send_document_response()

        print(f"Chunk {filename} result {result}")

        if not result["ok"]:
            raise Exception(f"Failed to upload file: {result['description']}")

        file_id = result["result"].get("document", {}).get("file_id")
        file_id = file_id or result["result"].get("video", {}).get("file_id")
        file_id = file_id or result["result"].get("audio", {}).get("file_id")
        file_id = file_id or result["result"].get("image", {}).get("file_id")
        file_id = file_id or result["result"].get("music", {}).get("file_id")

        return {
            "telegram_file_id": file_id,
        }

    @classmethod
    def get_file_path(cls, file_id):
        print(f"Getting file path for file {file_id}")
        url = f"https://api.telegram.org/bot{cls.TELEGRAM_BOT_TOKEN}/getFile"
        params = {"file_id": file_id}

        @auto_retry
        def get_file_path_response():
            response = requests.get(url, params=params)
            response.raise_for_status()

            return response.json()

        result = get_file_path_response()

        print(f"File path result for {file_id} is {result}")

        if result["ok"]:
            return result["result"]["file_path"]
        else:
            raise Exception(f"Failed to get file path: {result['description']}")

    @classmethod
    def get_file_url(cls, file_id: str):
        return f"https://api.telegram.org/file/bot{cls.TELEGRAM_BOT_TOKEN}/{cls.get_file_path(file_id)}"


class LocalConnector(AbstractConnector):
    name = "Local Connector"

    @classmethod
    def upload(cls, uploaded_file: InMemoryUploadedFile):
        file_path = f"{settings.BASE_DIR}/media/{uploaded_file.name}"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())

        return {
            "url": os.path.join("media", uploaded_file.name),
        }


class DiscordConnector(AbstractConnector):
    name = "Discord Connector"

    @classmethod
    def upload(cls, uploaded_file: InMemoryUploadedFile):
        url = f"https://discord.com/api/v10/channels/{os.getenv('DISCORD_CHANNEL_ID')}/messages"
        headers = {"Authorization": f"Bot {os.getenv('DISCORD_BOT_TOKEN')}"}
        files = {"file": (uploaded_file.name, uploaded_file.read())}

        @auto_retry
        def get_file_url_response():
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            url = response.json()["attachments"][0]["url"]

            return url

        url = get_file_url_response()

        return {
            "url": url,
        }
