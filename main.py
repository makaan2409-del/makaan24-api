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
        
        args = (
            payload.get("args") or 
            payload.get("parameters") or 
            payload.get("call", {}).get("args") or 
            payload
        )

        city = args.get("city") or args.get("location")
        max_price = args.get("max_price") or args.get("budget")
        bhk = args.get("bhk") or args.get("bedrooms")

        query = {"isTrashed": {"$ne": True}}

        # 1. Location Filter
        if city and str(city).strip():
            city_str = str(city).strip()
            query["$or"] = [
                {"cityText": {"$regex": city_str, "$options": "i"}},
                {"areaText": {"$regex": city_str, "$options": "i"}},
                {"address": {"$regex": city_str, "$options": "i"}},
                {"title": {"$regex": city_str, "$options": "i"}}
            ]

        # 2. BHK Filter (Handle both string "2" and int 2)
        if bhk is not None:
            try:
                query["bedrooms"] = int(bhk)
            except (ValueError, TypeError):
                pass

        # 3. Budget Filter (Handle both string "20000000" and float/int)
        if max_price is not None:
            try:
                price_val = float(max_price)
                if price_val > 1000000:
                    query["price"] = {"$gte": 500000, "$lte": price_val}
                else:
                    query["price"] = {"$lte": price_val}
            except (ValueError, TypeError):
                pass

        # Search MongoDB
        results = list(properties_collection.find(query).sort("createdAt", -1).limit(5))

        # Safe BSON to JSON Conversion
        cleaned_results = json.loads(json_util.dumps(results))

        return JSONResponse(status_code=200, content={"properties": cleaned_results})

    except Exception as e:
        return JSONResponse(status_code=200, content={"properties": [], "error": str(e)})
