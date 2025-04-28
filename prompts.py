
from langchain.prompts import PromptTemplate

ROLE_SYSTEM = "system"
ROLE_USER = "user"


SYSTEM_PROMPT = """Directly convert the user's weather query into a single JSON object.

**Instructions:**
1.  Extract: location, date range (start/end), and granularity (interval in minutes).
2.  Format Dates: Output "date_from" and "date_to" as YYYY-MM-DD.
3.  Granularity: Convert textual descriptions (hourly, daily, every X hours) to minutes (60, 1440, X*60). Default to 60 if unspecified.
4.  Coordinates: Always include "latitude": null and "longitude": null.
5.  Context: Use the current date "{current_date}" to resolve relative terms like 'today', 'tomorrow', 'yesterday'.

**Output Format:**
{{
  "location": "<location>",
  "date_from": "<YYYY-MM-DD>",
  "date_to": "<YYYY-MM-DD>",
  "granularity": <integer_minutes>,
  "latitude": null,
  "longitude": null
}}

**CRITICAL: Respond with ONLY the JSON object described above. Do NOT include any other text, explanations, greetings, apologies, or examples.**"""

USER_PROMPT_TEMPLATE = """
User Query: {query}
"""

weather_user_prompt = PromptTemplate(input_variables=["query"], template=USER_PROMPT_TEMPLATE)

