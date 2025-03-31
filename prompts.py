from langchain.prompts import PromptTemplate

prompt_template = """
You are an assistant that converts natural language weather queries into JSON.
Extract the location and date from the following query.
Output a JSON exactly in this format (keys in double quotes):

{{
  "location": "<location>",
  "date": "<date>",
  "latitude": null,
  "longitude": null
}}

Query: {query}
"""

weather_prompt = PromptTemplate(input_variables=["query"], template=prompt_template)