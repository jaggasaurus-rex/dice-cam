import requests

server_url = "https://discord.com/api/webhooks/1529286260877692978/ZGf1Pbso23D8JSfa4UK7h-1BKJkEZ68qEbQ1xRNGtzhW0DgYhD5L58qcPmwyMiU5ttms"

def fireMessage(pip_count): 
    r = requests.post(
        url=server_url,
        json={"content": pip_count},
        timeout=5)
    print(r.status_code, r.text)
