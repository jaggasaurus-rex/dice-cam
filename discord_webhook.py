import requests

def fireMessage(pip_count, server_url): 
    if pip_count == 20:
        requests.post(
            url=server_url,
            json={"content": f":fire: {pip_count} :fire:"},
            timeout=5,
            )
    elif pip_count == 1:
        requests.post(
            url=server_url,
            json={"content": f":skull: {pip_count} :skull:"},
            timeout=5,
            )
    else:
        requests.post(
            url=server_url,
            json={"content": pip_count},
            timeout=5,
            )
