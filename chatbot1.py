import os
import json
from dotenv import load_dotenv
from geo import get_coordinates
from prompts import weather_prompt
from langchain_openai import ChatOpenAI
from os import getenv
from langchain.chains import LLMChain

load_dotenv()

from langchain.globals import set_debug
set_debug(True)




#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


llm = ChatOpenAI(
    openai_api_key=getenv("OPENAI_API_KEY"),
    openai_api_base=getenv("OPENAI_API_BASE"),
    model_name="deepseek/deepseek-v3-base:free",
    temperature=0.7
)

llm_chain = LLMChain(prompt=weather_prompt, llm=llm)




def transform_query_to_json(query: str) -> dict:
    # Run the chain with the query; this returns a JSON-formatted string
    result = llm_chain.invoke({"query": query})
    return json.loads(result)


def build_openmeteo_json(query: str) -> dict:
    base_json = transform_query_to_json(query)
    location = base_json.get("location")
    lat, lon = get_coordinates(location)
    base_json["latitude"] = lat
    base_json["longitude"] = lon
    return base_json


