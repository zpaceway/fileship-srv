import os
from mailjet_rest import Client


def send_email(to: str, body: str):
    mailjet = Client(
        auth=(
            os.environ.get("MJ_APIKEY_PUBLIC"),
            os.environ.get("MJ_APIKEY_PRIVATE"),
        ),
        version="v3.1",
    )

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

    mailjet.send.create(data=data)
