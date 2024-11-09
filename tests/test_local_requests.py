import requests


def test_local_requests():
    url = 'https://127.0.0.1:5000/'
    response = requests.get(url)
    assert response.status_code == 200


if __name__ == '__main__':
    test_local_requests()
