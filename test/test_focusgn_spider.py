import requests

def test_focusgn_spider():
    # Send a GET request to the FocusGN API
    response = requests.get('https://focusgn.com/category/sportsbetting-news')

    # Check if the request was successful
    # assert response.status_code == 200
    print(response.status_code)

if __name__ == '__main__':
    test_focusgn_spider()