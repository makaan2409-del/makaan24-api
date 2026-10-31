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

        query = {}

        # Search cityText, areaText, or address
        if city:
            query["$or"] = [
                {"cityText": {"$regex": str(city), "$options": "i"}},
                {"areaText": {"$regex": str(city), "$options": "i"}},
                {"address": {"$regex": str(city), "$options": "i"}},
                {"title": {"$regex": str(city), "$options": "i"}}
            ]

        # Search bedrooms (BHK)
        if bhk:
            try:
                query["bedrooms"] = int(bhk)
            except (ValueError, TypeError):
                pass

        # Search budget price
        if max_price:
            try:
                query["price"] = {"$lte": float(max_price)}
            except (ValueError, TypeError):
                pass

        # Fetch matching records
        results = list(properties_collection.find(query).limit(3))

        # Fallback: If no match, return latest 3 properties
        if not results:
            results = list(properties_collection.find({}).limit(3))

        # Safely convert BSON (ObjectIds, Dates) into standard JSON format
        cleaned_results = json.loads(json_util.dumps(results))

        return JSONResponse(status_code=200, content={"properties": cleaned_results})

    except Exception as e:
        # Prevent 500 crashes and return readable error message
        return JSONResponse(status_code=200, content={"properties": [], "error": str(e)})
