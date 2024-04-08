import requests
from requests import HTTPError

PORT_API_DDB = 8001


def api_ddb_req(ep, time_out=1):
    url = f'http://0.0.0.0:{PORT_API_DDB}/ddb/{ep}'
    try:
        rsp = requests.get(url, timeout=time_out)
        rsp.raise_for_status()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except requests.exceptions.Timeout:
        # print('timeout')
        pass
    except (Exception, ):
        # print(f'Other error occurred: {err}')
        pass
    else:
        # success
        return rsp
