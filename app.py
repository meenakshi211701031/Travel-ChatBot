from flask import Flask, render_template, request, jsonify
import json
import wikipedia
from serpapi import GoogleSearch
import threading

app = Flask(__name__)

# Load travel data from JSON
with open("data.json", "r") as file:
    travel_data = json.load(file)

# Google Search API Key (Replace with your SerpAPI key)
SERPAPI_KEY = "75757076e395b11a41e518687b0d2956ff6d22409addba9583c884bb890d7ebc"

# Cache for Wikipedia results
wiki_cache = {}


# Fetch Wikipedia summary
def fetch_wikipedia_summary(destination):
    if destination in wiki_cache:
        return wiki_cache[destination]

    try:
        summary = wikipedia.summary(destination, sentences=3, auto_suggest=True)
        wiki_cache[destination] = summary  # Store in cache
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Multiple results found: {e.options[:3]}"
    except wikipedia.exceptions.PageError:
        return "No Wikipedia page found."


# Fetch Google search results using SerpAPI
def fetch_google_summary(destination, category, results_dict):
    params = {
        "q": f"best {category} in {destination}",
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()

    if "organic_results" in results:
        top_result = results["organic_results"][0]
        results_dict[category] = top_result.get("snippet", "No specific details found.")
    else:
        results_dict[category] = "No data available."


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_input = request.json.get("message")

    if not user_input:
        return jsonify({"response": "Please enter a valid destination."})

    destination = user_input.strip().title()  # Format the destination properly

    # If destination exists in JSON, retrieve data fast
    if destination in travel_data:
        response_text = f"🌍 **Travel Guide for {destination}**:\n\n"

        for intent in ["places_to_visit", "restaurants", "famous_foods", "hotels"]:
            response_data = travel_data[destination].get(intent, [])
            response_text += f"🔹 **{intent.replace('_', ' ').title()}**:\n"

            if response_data:
                for item in response_data:
                    details = f"- {item['name']}: {item.get('description', '')}"
                    if "cuisine" in item:
                        details += f" (Cuisine: {item['cuisine']}, Price: {item['price_range']})"
                    if "rating" in item:
                        details += f" (Rating: {item['rating']}/5, Price: {item['price_range']})"
                    response_text += details + "\n"
            else:
                response_text += "No data available.\n"

            response_text += "\n"

        return jsonify({"response": response_text.strip()})

    # If destination is NOT in JSON, fetch data from Wikipedia & Google
    response_text = f"🌍 **Travel Guide for {destination}**:\n\n"

    # Start Wikipedia fetching in a separate thread
    wiki_summary = fetch_wikipedia_summary(destination)
    response_text += f"📖 **Wikipedia Summary:**\n{wiki_summary}\n\n"

    # Dictionary to store Google search results
    google_results = {}

    # Start Google fetching in separate threads
    google_threads = []
    for category in ["places to visit", "restaurants", "famous foods", "hotels"]:
        thread = threading.Thread(target=fetch_google_summary, args=(destination, category, google_results))
        google_threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in google_threads:
        thread.join()

    # Add Google search results to response
    for category, summary in google_results.items():
        response_text += f"🔹 **{category.title()}**:\n{summary}\n\n"

    return jsonify({"response": response_text.strip()})


if __name__ == "__main__":
    app.run(debug=True)
