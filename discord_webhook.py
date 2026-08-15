import requests
from config import loadConfig

def fireMessage(die_value):
    cfg =  loadConfig()
    server_url = cfg["webhook_url"]
    if int(die_value) == 20:
        requests.post(
            url=server_url,
            json={"content": f":fire: {die_value} :fire:"},
            timeout=5,
            )
    elif int(die_value) == 1:
        requests.post(
            url=server_url,
            json={"content": f":skull: {die_value} :skull:"},
            timeout=5,
            )
    else:
        requests.post(
            url=server_url,
            json={"content": die_value},
            timeout=5,
            )
