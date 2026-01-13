import requests

url = "https://hok3cqu9h4.execute-api.eu-west-3.amazonaws.com/prod/predict"
data = {
    "fecha":"2025-10-25",
    "hora":"12:00",
    "atraccion":"Batman Gotham City Escape",
    "zona":"DC Super Heroes World",
    "temperatura":22,
    "humedad":60,
    "codigo_clima":3
}

response = requests.post(url, json=data)
print("Status:", response.status_code)
print("Response:", response.json())
