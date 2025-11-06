import os

from litellm import completion

from ..messages import SYSTEM_PROMPT


class AIManager:
    def __init__(self, api_key: str, model: str) -> None:
        provider = model.split("/")[0]
        provider_key = f"{provider}_API_KEY".upper()
        os.environ[provider_key] = api_key
        self.model = model

    def prompt(self, text: str) -> str:
        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content
