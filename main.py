from chatbot import build_openmeteo_json, fetch_weather_data, filter_data_by_granularity
import json



# Using placeholder values, to be replaced

API_COSTS = {
    "llm": 0.005,
    "geocoding": 0.00,
    "meteo_archive": 0.02,
    "meteo_forecast": 0.02
}
COST_CURRENCY = "CZK"


queries = [
    "The weather in Pilsen from yesterday to tomorrow",
    "What's the weather in Berlin tomorrow?",
    "How was the weather in Prague from 2024-05-01 to 2024-05-03?",
    "What's the weather like in London today measured every 3 hours?",
    "Weather forecast for New York for the next 3 days, 15 minute intervals",
    "Nonexistent City weather today",
    "Weather for Paris yesterday"
]

if __name__ == '__main__':
    total_cost_all_queries = 0.0
    total_counts_all_queries = {key: 0 for key in API_COSTS}

    for i, query in enumerate(queries):
        print(f"\n==============================")
        print(f" Processing Query {i+1}/{len(queries)}")
        print(f" Query: {query}")
        print(f"==============================")

        current_api_counts = {
            "llm": 0,
            "geocoding": 0,
            "meteo_archive": 0,
            "meteo_forecast": 0
        }
        current_query_cost = 0.0
        final_json = None
        raw_weather_data = None
        filtered_weather_data = None

        try:

            final_json = build_openmeteo_json(query, current_api_counts)

            print("\n Final JSON for API call preparation:")
            print(json.dumps(final_json, indent=2))


            raw_weather_data = fetch_weather_data(
                final_json["latitude"],
                final_json["longitude"],
                final_json["date_from"],
                final_json["date_to"],
                final_json["granularity"],
                current_api_counts
            )


            filtered_weather_data = filter_data_by_granularity(
                raw_weather_data,
                final_json["granularity"]
            )

            print("\n-- Filtered Weather Data (Matching User Request) --")

            print(json.dumps(filtered_weather_data, indent=2, ensure_ascii=False))



        except Exception as e:
            print(f"\n--- ERROR PROCESSING QUERY ---")
            print(f"An error occurred: {e}")

            print("Processing stopped for this query.")

            if final_json:
                 print(f"  (Occurred after initial JSON build: {json.dumps(final_json)})")


        print("\n--- API Call Counts & Cost for this Query ---")
        for api_name, count in current_api_counts.items():
            cost_per_call = API_COSTS.get(api_name, 0)
            cost_for_api = count * cost_per_call
            print(f"  {api_name.capitalize()} Calls: {count} (@ {cost_per_call:.5f} {COST_CURRENCY}/call) = {cost_for_api:.5f} {COST_CURRENCY}")
            current_query_cost += cost_for_api


        print(f"---------------------------------------------")
        print(f"  Total Estimated Cost for this Query: {current_query_cost:.5f} {COST_CURRENCY}")
        print(f"==============================\n")

        for api_name, count in current_api_counts.items():
             total_counts_all_queries[api_name] += count
        total_cost_all_queries += current_query_cost


    print("\n##############################")
    print(" Overall Summary for All Queries")
    print("##############################")
    print("Total API Calls:")
    for api_name, count in total_counts_all_queries.items():
         print(f"  {api_name.capitalize()}: {count}")
    print("------------------------------")
    print(f"Total Estimated Cost for All Queries: {total_cost_all_queries:.5f} {COST_CURRENCY}")
    print("##############################")