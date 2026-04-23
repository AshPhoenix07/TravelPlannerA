import os
from mistralai import Mistral
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.after_request
def add_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

def enrich_prompt_context(data):
    """Member 5 — vibe logic, input validation, destination hints"""
    hints = []

    budget = data.get('budget', '')
    scope = data.get('scope', '')
    transport = data.get('transport', '')
    dest_type = data.get('dest_type', '')
    vibe = data.get('vibe', '')
    season = data.get('season', '')
    kids = data.get('kids', 'no')
    seniors = data.get('seniors', 'no')
    duration = data.get('duration', '')
    origin = data.get('origin', '')
    max_hours = data.get('max_hours', '')
    avoid = data.get('avoid', '')
    must_haves = data.get('must_haves', '')

    # Budget vs scope mismatch warning
    if 'emergency' in budget.lower() and scope == 'international':
        hints.append("IMPORTANT: User has an emergency/very low budget but selected international travel. Suggest realistic budget-friendly international options like Mexico or Canada if near the border, or strongly recommend domestic alternatives.")

    if 'low' in budget.lower() and scope == 'international':
        hints.append("Budget is low for international travel. Focus on nearby international destinations like Mexico, Canada, or Caribbean that are affordable.")

    # Vibe mapping
    vibe_lower = vibe.lower()
    if any(w in vibe_lower for w in ['relax', 'chill', 'peaceful', 'quiet', 'calm']):
        hints.append("User wants a relaxing, low-key trip. Avoid suggesting busy tourist hotspots. Prioritize quiet towns, nature retreats, and slow-paced destinations.")
    if any(w in vibe_lower for w in ['adventure', 'active', 'thrill', 'excit']):
        hints.append("User wants adventure and activity. Prioritize destinations with outdoor activities, hiking, water sports, or unique experiences.")
    if any(w in vibe_lower for w in ['romantic', 'couple', 'anniversary', 'honeymoon']):
        hints.append("This is a romantic trip. Suggest intimate settings, scenic spots, candlelit dining, and private accommodation options.")
    if any(w in vibe_lower for w in ['cultural', 'history', 'art', 'museum']):
        hints.append("User is interested in culture and history. Prioritize destinations with museums, historical sites, local art scenes, and cultural events.")
    if any(w in vibe_lower for w in ['party', 'nightlife', 'festival', 'fun']):
        hints.append("User wants nightlife and fun. Suggest destinations known for their entertainment, festivals, or vibrant social scenes.")

    # Destination type mapping
    dest_lower = dest_type.lower()
    if 'snow' in dest_lower or 'ski' in dest_lower:
        hints.append("User wants snow/ski destination. Focus on mountain destinations with winter activities like skiing, snowboarding, or snowshoeing.")
    if 'beach' in dest_lower:
        hints.append("User wants a beach destination. Prioritize coastal towns with good beaches, warm weather (if summer), and water activities.")
    if 'mountain' in dest_lower:
        hints.append("User wants mountains. Suggest destinations with scenic mountain views, hiking trails, and fresh air.")
    if 'city' in dest_lower:
        hints.append("User wants a city trip. Focus on urban destinations with good food scenes, walkability, and cultural attractions.")
    if 'surprise' in dest_lower:
        hints.append("User wants to be surprised. Pick 3 creative, unexpected destinations they probably haven't considered.")

    # Transport mapping
    transport_lower = transport.lower()
    if 'road trip' in transport_lower:
        hints.append("This is a road trip. Suggest destinations with scenic drives, and include road trip tips like good stopping points along the way.")
    if 'flight' in transport_lower and max_hours:
        hints.append(f"User is flying. Keep total travel time under {max_hours}. Factor in airport travel time, not just flight duration.")
    if 'train' in transport_lower:
        hints.append("User prefers train travel. Suggest destinations accessible by Amtrak or regional rail from their origin city.")
    if 'public transport' in transport_lower:
        hints.append("User wants public transport only. Suggest walkable, transit-friendly cities with good bus/metro systems.")

    # Season mapping
    season_lower = season.lower()
    if 'summer' in season_lower:
        hints.append("Traveling in summer. Warn about peak crowds and heat. Suggest destinations that are good in summer specifically.")
    if 'winter' in season_lower:
        hints.append("Traveling in winter. Note which activities are seasonal. Suggest destinations that shine in winter, not ones that are dead in the off-season.")
    if 'spring' in season_lower:
        hints.append("Traveling in spring. Highlight wildflowers, mild weather, and fewer crowds compared to summer.")
    if 'fall' in season_lower:
        hints.append("Traveling in fall. Highlight foliage, harvest festivals, and pleasant temperatures.")

    # Kids and seniors
    if kids == 'yes':
        hints.append("Traveling with kids. All suggestions must be family-friendly. Include kid-friendly activities, accommodation, and restaurants. Avoid anything unsafe or inappropriate for children.")
    if seniors == 'yes':
        hints.append("Traveling with seniors. Prioritize accessibility, comfortable accommodation, easy walking distances, and avoid strenuous activities unless requested.")
    if kids == 'yes' and seniors == 'yes':
        hints.append("Multi-generational trip with both kids and seniors. Find activities that work for all ages.")

    # Duration mapping
    duration_lower = duration.lower()
    if 'day trip' in duration_lower:
        hints.append("This is a day trip — no overnight stay. Keep all suggestions within realistic driving distance for a same-day return.")
    if 'overnight' in duration_lower:
        hints.append("Just one night. Keep it simple — one main activity area, easy check-in, no complex logistics.")
    if 'week' in duration_lower or '7' in duration_lower:
        hints.append("This is a longer trip. Suggest destinations with enough variety to fill a full week without getting bored.")

    # Must-haves
    if must_haves:
        hints.append(f"User absolutely requires: {must_haves}. Make sure every suggested destination can realistically provide these.")

    # Things to avoid
    if avoid:
        hints.append(f"User wants to avoid: {avoid}. Filter out any destinations or activities that involve these.")

    return hints


def ask_mistral(prompt: str) -> str:
    client = Mistral(
        api_key=os.getenv("MISTRAL_API_KEY"),
    )
    res = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {
                "role": "system",
                "content": """You are an expert travel planner AI.
When given travel preferences, suggest exactly 3 destinations.
Format your response EXACTLY like this for each destination, with no variation:

DESTINATION 1
Name: [destination name]
Trip Name: [creative trip name]
Why it fits: [2-3 sentences explaining why]
---DAYS---
Day 1 | [day title]
Morning: [what to do]
Afternoon: [what to do]
Evening: [what to do]
Day 2 | [day title]
Morning: [what to do]
Afternoon: [what to do]
Evening: [what to do]
Day 3 | [day title]
Morning: [what to do]
Afternoon: [what to do]
Evening: [what to do]
---COSTS---
Transport: [estimated cost]
Hotel: [cost per night]
Food: [cost per day]
Total: [total range]
---PACKING---
[item1], [item2], [item3], [item4], [item5], [item6]
---SEASONS---
Busy: [busy months]
Quiet: [quiet months]
---WEATHER---
[expected weather for their travel season]

DESTINATION 2
[exact same format]

DESTINATION 3
[exact same format]

Use this format exactly. Do not use markdown, hashtags, or asterisks."""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return res.choices[0].message.content


def build_prompt(data):
    hints = enrich_prompt_context(data)
    hints_text = '\n'.join(f"- {h}" for h in hints) if hints else "None"

    return f"""
Plan a trip for me based on these preferences:

Budget: {data.get('budget', 'not specified')}
Transport type: {data.get('transport', 'not specified')}
Trip vibe: {data.get('vibe', 'not specified')}
Traveling from: {data.get('origin', 'not specified')}
Trip length: {data.get('duration', 'not specified')}
Max travel time to destination: {data.get('max_hours', 'not specified')} hours
Trip scope: {data.get('scope', 'not specified')}
Season: {data.get('season', 'not specified')}
Destination type: {data.get('dest_type', 'not specified')}
Accommodation: {data.get('accommodation', 'not specified')}
Activities: {data.get('activities', 'not specified')}
Food preference: {data.get('food', 'not specified')}
Favorite foods / must-eat: {data.get('fav_food', 'not specified')}
Dietary restrictions: {data.get('dietary', 'none')}
Group type: {data.get('group_type', 'not specified')}
Traveling with kids: {data.get('kids', 'no')}
Traveling with seniors: {data.get('seniors', 'no')}
Group size: {data.get('group_size', 'not specified')}
Must-haves: {data.get('must_haves', 'none')}
Things to avoid: {data.get('avoid', 'none')}

Smart planning notes (use these to refine suggestions):
{hints_text}

Suggest 3 destinations ranked by best fit. Follow the format exactly.
"""


@app.route("/")
def home():
    return render_template("front.html")


@app.route("/api/trip", methods=["POST"])
def trip():
    data = request.get_json()
    prompt = build_prompt(data)
    reply = ask_mistral(prompt)
    return jsonify({"reply": reply})


@app.route("/api/regenerate", methods=["POST"])
def regenerate():
    data = request.get_json()
    prompt = build_prompt(data)
    # Add instruction to give different results
    prompt += "\n\nIMPORTANT: Suggest 3 COMPLETELY DIFFERENT destinations from any previous suggestions. Be creative and think outside the box."
    reply = ask_mistral(prompt)
    return jsonify({"reply": reply})


@app.route("/api/deep-dive", methods=["POST"])
def deep_dive():
    data = request.get_json()
    destination = data.get('destination', '')
    original_prefs = data.get('preferences', {})

    prompt = f"""
The user has chosen: {destination}

Their preferences:
Budget: {original_prefs.get('budget', 'not specified')}
Transport: {original_prefs.get('transport', 'not specified')}
Group: {original_prefs.get('group_type', 'not specified')} of {original_prefs.get('group_size', 'not specified')}
Food: {original_prefs.get('food', 'not specified')}, dietary: {original_prefs.get('dietary', 'none')}
Favorite foods: {original_prefs.get('fav_food', 'none')}
Must-haves: {original_prefs.get('must_haves', 'none')}
Avoid: {original_prefs.get('avoid', 'none')}
Kids: {original_prefs.get('kids', 'no')}, Seniors: {original_prefs.get('seniors', 'no')}

Give a DETAILED trip plan for {destination} only. Include:

DEEP DIVE: {destination}
---FULLDAYS---
Day 1 | [title]
Morning: [detailed activity with specific place names]
Afternoon: [detailed activity with specific place names]
Evening: [detailed activity with specific restaurant/bar names]
Day 2 | [title]
Morning: [detailed]
Afternoon: [detailed]
Evening: [detailed]
Day 3 | [title]
Morning: [detailed]
Afternoon: [detailed]
Evening: [detailed]
---RESTAURANTS---
[restaurant1 name]: [description and must-order dish]
[restaurant2 name]: [description and must-order dish]
[restaurant3 name]: [description and must-order dish]
---HOTELS---
[option1 name]: [description and price range]
[option2 name]: [description and price range]
---TIPS---
[local tip 1]
[local tip 2]
[local tip 3]
---FULLPACKING---
[item1], [item2], [item3], [item4], [item5], [item6], [item7], [item8]

Use this format exactly. No markdown, no asterisks."""

    client = Mistral(
        api_key=os.getenv("MISTRAL_API_KEY"),
    )
    res = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": "You are an expert travel planner. Give very specific, detailed, practical travel advice with real place names."},
            {"role": "user", "content": prompt}
        ]
    )
    return jsonify({"reply": res.choices[0].message.content})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
