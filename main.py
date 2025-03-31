from chatbot import build_openmeteo_json



if __name__=='__main__':

    sample_query = "What's the weather in Berlin on 2025-04-01?"
    final_json = build_openmeteo_json(sample_query)
    print("Final JSON for OpenMeteo API call:")
    print(final_json)

