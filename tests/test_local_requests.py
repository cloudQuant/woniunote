import requests
import sys


def test_local_requests(params=None):
    result = False
    if params is None:
        url = 'https://127.0.0.1:8888/'
        print(f"begin to request {url}")
        response = requests.get(url, verify=False)  # 禁用 SSL 验证
        # response = requests.get(url)
        if response.status_code == 200:
            result = True
    if params is not None:
        url = f'https://{params}/'
        print(f"begin to request {url}")
        response = requests.get(url, verify=False, params=params)  # 禁用 SSL 验证
        if response.status_code == 200:
            result = True
    assert result is True
    print("local requests test passed")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        test_local_requests()
    local_url = sys.argv[1]
    test_local_requests(params=local_url)
