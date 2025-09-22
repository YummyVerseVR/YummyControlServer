import os
import json
from ollama import Client
from pydantic import BaseModel


class TopNames(BaseModel):
    first: str
    second: str
    third: str


class ResponseModel(BaseModel):
    status: str = ""
    chewiness: int = 5
    firmness: int = 5
    translated: str = ""
    best_name: str = ""
    top_names: TopNames = TopNames(first="", second="", third="")
    error: str = ""


class LLM:
    def __init__(self, config: dict, debug_mode: bool = False):
        self.__debug = debug_mode
        self.__endpoint = config.get("endpoints", {})
        self.__config = config.get("ollama", {})
        self.__client = self.__get_client()

    def __get_client(self) -> Client:
        ollama_endpoint = self.__endpoint.get("ollama", "http://localhost:11434")
        return Client(ollama_endpoint)

    def __extract_json_block(self, text: str) -> ResponseModel:
        """
        Extracts the first JSON block from the given text.

        Args:
            text (str): The input text containing a JSON block.

        Returns:
            ResponseModel: The parsed JSON block as a ResponseModel object.
        """
        try:
            # if text contains ```json ... ``` block, extract it
            json_block = ""
            if text.startswith("```json"):
                json_block = text[7:-3].strip()
            elif text.startswith("```"):
                json_block = text[3:-3].strip()
            else:
                raise ValueError("No JSON block found")

            data = json.loads(json_block)

            response = ResponseModel()
            response.status = data.get("status", "")
            response.chewiness = data.get("chewiness", 5)
            response.firmness = data.get("firmness", 5)
            response.translated = data.get("translated", "")

            if response.status == "ok":
                response.best_name = data.get("best_name", "")
            else:
                top_names = data.get("top_names", [])
                response.top_names = TopNames(
                    first=top_names[0] if len(top_names) > 0 else "",
                    second=top_names[1] if len(top_names) > 1 else "",
                    third=top_names[2] if len(top_names) > 2 else "",
                )

            response.error = "no error"
            return response

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # if JSON parsing fails, return an error response
            return ResponseModel(
                status="error",
                chewiness=5,
                firmness=5,
                translated="",
                best_name="",
                top_names=TopNames(first="", second="", third=""),
                error=f"Failed to parse JSON response: {str(e)}",
            )

    def choose_dish(self, user_request: str, candidates: list):
        ollama_model = self.__config.get("model", "gemma3:12b")
        prompt_path = self.__config.get("prompt", "")
        system_prompt = ""

        if not prompt_path or not os.path.exists(prompt_path):
            raise FileNotFoundError("System prompt file not found")

        with open(prompt_path, "rb") as f:
            system_prompt = f.read()

        temperature = float(self.__config.get("temperature", 0))
        num_predict = int(self.__config.get("num_predict", 500))

        user_input = {"query": user_request, "candidates": candidates}
        user_input_json = json.dumps(user_input, ensure_ascii=False)

        if self.__debug:
            print("[DEBUG] Debug mode is enabled, skipping LLM call")
            return self.__extract_json_block(
                """
                ```json
                {
                    "status": "ok",
                    "chewiness": 7,
                    "firmness": 6,
                    "translated": "Delicious sushi with fresh ingredients.",
                    "best_name": "Sushi Delight",
                    "top_names": ["Sushi Delight", "Ocean's Bounty", "Fresh Catch"]
                }
                ```
                """
            )

        response = self.__client.chat(
            model=ollama_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input_json},
            ],
            options={
                "temperature": temperature,
                "num_predict": num_predict,
            },
        )
        return self.__extract_json_block(response["message"]["content"].strip())
