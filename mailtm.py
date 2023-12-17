import requests
import time
import json
from datetime import datetime
from dataclasses import dataclass

from typing import Dict

# from mailtm import MailTM


BASE_API_URL = "https://api.mail.tm"
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpYXQiOjE3MDI3OTQ3NjMsInJvbGVzIjpbIlJPTEVfVVNFUiJdLCJhZGRyZXNzIjoidGVzdGluZ2FjY291bnRAd2lyZWNvbm5lY3RlZC5jb20iLCJpZCI6IjY1N2U5M2Q2NzhlYmNjYjU0YjA2YmU2NiIsIm1lcmN1cmUiOnsic3Vic2NyaWJlIjpbIi9hY2NvdW50cy82NTdlOTNkNjc4ZWJjY2I1NGIwNmJlNjYiXX19.BpYoLhPKl1kVrCGD232diYIgyA0zekNAeVWKBzyL8qlhP7iHqHERMhhYjQLu7fPaJPZ_cSR7sL96e-3N-lP0rA"

MAILTM_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


class MailTmError(Exception):
    pass


def _make_mailtm_request(request_fn, timeout=600):
    tstart = time.monotonic()
    error = None
    status_code = None
    while time.monotonic() - tstart < timeout:
        try:
            r = request_fn()
            status_code = r.status_code
            if status_code == 200 or status_code == 201:
                return r.json()
            if status_code != 429:
                break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            error = e
        time.sleep(1.0)

    if error is not None:
        raise MailTmError(error) from error
    if status_code is not None:
        raise MailTmError(f"Status code: {status_code}")
    if time.monotonic() - tstart >= timeout:
        raise MailTmError("timeout")
    raise MailTmError("unknown error")


def get_mailtm_domains():
    def _domain_req():
        return requests.get("https://api.mail.tm/domains", headers=MAILTM_HEADERS)

    r = _make_mailtm_request(_domain_req)

    return [x["domain"] for x in r]


def create_mailtm_account(address, password):
    account = json.dumps({"address": address, "password": password})

    def _acc_req():
        return requests.post(
            "https://api.mail.tm/accounts", data=account, headers=MAILTM_HEADERS
        )

    r = _make_mailtm_request(_acc_req)
    assert len(r["id"]) > 0


@dataclass
class Message:
    id_: str
    from_: Dict
    to: Dict
    subject: str
    intro: str
    text: str
    html: str
    data: Dict


def get_email_headers():
    header_list = []
    email_request = requests.get(
        f"{BASE_API_URL}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )

    jsonified_emails = json.loads(email_request.text)

    print(jsonified_emails)

    emails = jsonified_emails["hydra:member"]

    for email in emails:
        append_data = {
            "from": email["from"],
            "to": email["to"],
            "subject": email["subject"],
            "sent_at": email["createdAt"],
            "body": email["intro"],
        }

        header_list.append(append_data)

    return header_list


def get_existing_messages_id():
    old_messages = get_messages()
    return list(map(lambda m: m.id_, old_messages))


def get_messages():
    r = requests.get(
        "{}/messages".format(BASE_API_URL),
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    messages = []
    for message_data in r.json()["hydra:member"]:
        time.sleep(2)
        r = requests.get(
            f"{BASE_API_URL}/messages/{message_data['id']}",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

        full_message_json = r.json()
        text = full_message_json["text"]
        html = full_message_json["html"]

        messages.append(
            Message(
                message_data["id"],
                message_data["from"],
                message_data["to"],
                message_data["subject"],
                message_data["intro"],
                text,
                html,
                message_data,
            )
        )

    return messages


def wait_for_message():
    old_messages_id = get_existing_messages_id()

    while True:
        time.sleep(1)
        try:
            new_messages = list(
                filter(lambda m: m.id_ not in old_messages_id, get_messages())
            )
            if new_messages:
                return new_messages[0]
        except Exception as e:
            print(e)
            print("Cannot get messages.")


def read_email(id: str):
    response = requests.patch(
        f"{BASE_API_URL}/messages/{id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/merge-patch+json",
        },
    )

    print(response.text)
    if response.ok:
        print(f"Message with ID {id} marked as read.")

    else:
        print("Failure to read the message!")
