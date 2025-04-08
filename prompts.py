from langchain.prompts import PromptTemplate

prompt_template = """
You are an assistant that converts natural language weather queries into JSON.
Extract the location, the date or date range, and granularity from the following query.
Always return both "date_from" and "date_to" fields.
Granularity stands for the time detail of the data (for example: "each 15 min" means the value should be 15). 
Notice that you have to convert hours and days into minutes for the granularity field.
Do not change the fields "latitude" and "longitude" — they must remain null.
Return exactly the JSON in the following format (keys in double quotes):

{{
  "location": "<location>",
  "date_from": "<date in YYYY-MM-DD>",
  "date_to": "<date in YYYY-MM-DD>",
  "granularity": "<In minutes>",
  "latitude": null,
  "longitude": null
}}

If granularity is not identifiable in the query, do not invent values; leave the field as 60.



Query: {query}
"""


weather_prompt = PromptTemplate(input_variables=["query"], template=prompt_template)
