import requests


def test_local_requests():
    url = 'http://localhost:8888/'
    response = requests.get(url)
    assert response.status_code == 200


if __name__ == '__main__':
    test_local_requests()
