import requests
import msgpack

url = "http://localhost:18000"

data = {"method": "on_new_mail", "args": ["testing", "body"]}

headers = {"Content-Type": "application/msgpack"}

msg_data = msgpack.packb(data, use_bin_type=True)

r = requests.post(url, data=msg_data, headers=headers)

print(r)
