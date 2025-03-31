from chatbot import build_openmeteo_json, fetch_weather_data, print_weather_summary
import json

queries = [
    "What's the weather in Berlin in the last 2 days of march 2025?",
    "What's the weather in Jasanova 10, Plzen in the last day of march 2025"
]

if __name__ == '__main__':
    for query in queries:
        print("\n==============================")
        print(f" Query: {query}")
        final_json = build_openmeteo_json(query)

        print("\n Final JSON for OpenMeteo API call:")
        print(final_json)

        weather_data = fetch_weather_data(
            final_json["latitude"],
            final_json["longitude"],
            final_json["date_from"],
            final_json["date_to"]
        )

        print_weather_summary(weather_data) #every 12 hours formated output

        #raw json
        print("\n-- Full Raw Weather Data --")
        print(json.dumps(weather_data, indent=2, ensure_ascii=False))
