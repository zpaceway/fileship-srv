import os
import requests


def send_email(to: str, body: str):
    mailjet_url = "https://api.mailjet.com/v3.1/send"

    auth = (os.environ.get("MJ_APIKEY_PUBLIC"), os.environ.get("MJ_APIKEY_PRIVATE"))

    data = {
        "Messages": [
            {
                "From": {
                    "Email": os.environ.get("EMAIL_SENDER"),
                    "Name": "OTP Service",
                },
                "To": [
                    {
                        "Email": to,
                    }
                ],
                "Subject": "Your OTP Code",
                "HTMLPart": body,
            }
        ]
    }

    requests.post(mailjet_url, auth=auth, json=data)
