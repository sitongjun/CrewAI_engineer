"""Small client for the FastAPI endpoint."""

import requests


URL = "http://127.0.0.1:8012/v1/chat/completions"


def main() -> None:
    response = requests.post(
        URL,
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "张三九最近的头痛与之前的体检记录是否有关？",
                }
            ],
            "stream": False,
        },
        timeout=180,
    )
    response.raise_for_status()
    print(response.json()["choices"][0]["message"]["content"])


if __name__ == "__main__":
    main()
