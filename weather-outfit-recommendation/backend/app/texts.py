"""Text layer. The engine produces facts; this module turns them into friendly English text."""

ITEMS = {
    "thermal": "Thermal base layer", "down_jacket": "Down jacket", "winter_coat": "Winter coat",
    "warm_coat": "Warm jacket", "jacket": "Jacket", "light_jacket": "Light jacket",
    "wool_coat": "Wool coat", "blazer": "Blazer", "sweater": "Sweater",
    "long_sleeve": "Long-sleeve top", "tshirt": "T-shirt", "shorts": "Shorts",
    "hat": "Hat", "gloves": "Gloves", "scarf": "Scarf",
    "winter_boots": "Winter boots", "boots": "Boots", "sneakers": "Sneakers",
    "leather_shoes": "Dress shoes", "leather_boots": "Leather boots",
    "dress_shirt": "Dress shirt", "blouse": "Blouse", "flats": "Flats", "ankle_boots": "Ankle boots",
    "sundress": "Sundress", "tights": "Tights", "heels": "Heels",
    "rain_jacket": "Rain jacket", "umbrella": "Umbrella",
    "sunglasses": "Sunglasses", "sunscreen": "Sunscreen", "grip_shoes": "Ice grips",
    "layers": "Layers you can peel off", "water": "Water bottle",
    "white_shoes": "white shoes", "suede": "suede", "smooth_soles": "smooth soles",
}

SACRIFICE = {
    "umbrella_for_style": "Umbrella instead of a rain jacket keeps the look sharp, but your back may get wet.",
    "wind_vs_umbrella": "It is too windy for an umbrella, so the rain jacket takes over.",
}

# Fields: {event} {time} {rain_time} {temp} {wind} {bring} {avoid} {wear}
TEMPLATES = {
    "ice": "It's {temp}° and damp, so it may be slippery. Wear shoes with good grip.",
    "rain_dressy": "Rain from {rain_time} and you have {event} at {time}. Bring the umbrella and avoid {avoid}.",
    "rain": "Rain is expected from {rain_time}. Bring {bring} to stay dry.",
    "wind": "Winds up to {wind} m/s. Choose a windproof jacket.",
    "cold": "It feels like {temp}° out there. Dress warmly: {wear}.",
    "heat": "Warm today, up to {temp}°. Dress light and drink water.",
    "nice": "Nice weather: {temp}° and dry. {wear} is enough.",
}

LABELS = {"wear": "Wear", "bring": "Bring", "avoid": "Avoid", "sacrifice": "Trade-off"}
NO_EVENTS_NOTE = "No events added, so this is based on a typical commute."
