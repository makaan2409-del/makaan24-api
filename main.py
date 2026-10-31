from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from bson import json_util
import json
import os

app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["makaan_latest_db"]
properties_collection = db["properties"]

@app.post("/search-properties")
async def search_properties(request: Request):
    try:
        payload = await request.json()
        args = payload.get("args", {}) or payload.get("parameters", {}) or payload.get("call", {}).get("args", {})

        city = args.get("city")
        max_price = args.get("max_price")
        bhk = args.get("bhk")

        query = {"isTrashed": {"$ne": True}}

        # Match cityText, areaText, title, or address
        if city:
            city_str = str(city).strip()
            query["$or"] = [
                {"cityText": {"$regex": city_str, "$options": "i"}},
                {"areaText": {"$regex": city_str, "$options": "i"}},
                {"address": {"$regex": city_str, "$options": "i"}},
                {"title": {"$regex": city_str, "$options": "i"}}
            ]

        # Match exact bedrooms (BHK)
        if bhk:
            try:
                query["bedrooms"] = int(bhk)
            except (ValueError, TypeError):
                pass

        # Match Price Budget
        if max_price:
            try:
                price_val = float(max_price)
                # Avoid returning monthly rent properties when user asks for buying budget (> 10 Lakhs)
                if price_val > 1000000:
                    query["price"] = {"$gte": 500000, "$lte": price_val}
                else:
                    query["price"] = {"$lte": price_val}
            except (ValueError, TypeError):
                pass

        # Search MongoDB database across ALL matching listings
        results = list(properties_collection.find(query).sort("createdAt", -1).limit(5))

        # Secondary Fallback: Try searching only by location if exact BHK+Price match was empty
        if not results and city:
            location_only_query = {
                "$or": [
                    {"cityText": {"$regex": str(city), "$options": "i"}},
                    {"areaText": {"$regex": str(city), "$options": "i"}},
                    {"address": {"$regex": str(city), "$options": "i"}}
                ]
            }
            results = list(properties_collection.find(location_only_query).sort("createdAt", -1).limit(3))

        # Safely convert BSON (ObjectIds, Dates) into standard JSON format
        cleaned_results = json.loads(json_util.dumps(results))

        return JSONResponse(status_code=200, content={"properties": cleaned_results})

    except Exception as e:
        return JSONResponse(status_code=200, content={"properties": [], "error": str(e)})
