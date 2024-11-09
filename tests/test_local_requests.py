import requests


def test_local_requests():
    url = 'https://127.0.0.1:5000/'
    response = requests.get(url, verify=False)  # 禁用 SSL 验证
    # response = requests.get(url)
    assert response.status_code == 200
    print(response.text)
    print("local requests test passed")


if __name__ == '__main__':
    test_local_requests()
