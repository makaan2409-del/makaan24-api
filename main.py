from fastapi import FastAPI, Request
from pymongo import MongoClient
import os

app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["makaan_latest_db"]
properties_collection = db["properties"]

@app.post("/search-properties")
async def search_properties(request: Request):
    payload = await request.json()
    args = payload.get("args", {}) or payload.get("parameters", {})

    city = args.get("city")
    max_price = args.get("max_price")
    bhk = args.get("bhk")

    query = {}

    # Match cityText, areaText, or address using the user's input
    if city:
        query["$or"] = [
            {"cityText": {"$regex": str(city), "$options": "i"}},
            {"areaText": {"$regex": str(city), "$options": "i"}},
            {"address": {"$regex": str(city), "$options": "i"}},
            {"title": {"$regex": str(city), "$options": "i"}}
        ]

    # Match bedrooms (BHK)
    if bhk:
        try:
            query["bedrooms"] = int(bhk)
        except:
            pass

    # Match price budget
    if max_price:
        try:
            query["price"] = {"$lte": float(max_price)}
        except:
            pass

    # Search MongoDB and fetch top 3 matching properties
    results = list(properties_collection.find(query, {"_id": 0}).limit(3))

    # Fallback: if no strict filter matches, return latest 3 properties so voice agent has data
    if not results:
        results = list(properties_collection.find({}, {"_id": 0}).limit(3))

    return {"properties": results}
