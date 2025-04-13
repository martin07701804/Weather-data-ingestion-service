from langchain.prompts import PromptTemplate

# Define roles in alligment with MCP standards
ROLE_SYSTEM = "system"
ROLE_USER = "user"
SYSTEM_PROMPT = """You are an assistant that converts natural language weather queries into JSON.
You must extract the location, the date or date range, and granularity from the user's query.
Always return both "date_from" and "date_to" fields in YYYY-MM-DD format.
Granularity represents the desired time interval in minutes (e.g., "each 15 min" is 15, "hourly" is 60, "every 2 hours" is 120, "daily" is 1440). Convert hours and days to minutes.
If granularity is not specified or unclear in the query, YOU MUST default the granularity value to 60.
The fields "latitude" and "longitude" must always be present and set to null.
Return *only* the JSON object, without any introductory text or explanation.
The required JSON format is:

{
  "location": "<location>",
  "date_from": "<date in YYYY-MM-DD>",
  "date_to": "<date in YYYY-MM-DD>",
  "granularity": <integer in minutes>,
  "latitude": null,
  "longitude": null
}"""

USER_PROMPT_TEMPLATE = """
User Query: {query}
"""

weather_user_prompt = PromptTemplate(input_variables=["query"], template=USER_PROMPT_TEMPLATE)

