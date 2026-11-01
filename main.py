from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from bson import json_util
import json
import os
from datetime import datetime

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

# ==========================================
# NEW ENDPOINT: Caller Leads Save Karne Ke Liye
# ==========================================
leads_collection = db["caller_leads"]  # Mongo database mein naya collection banega

@app.post("/save-lead")
async def save_lead(request: Request):
    try:
        payload = await request.json()
        
        args = (
            payload.get("args") or 
            payload.get("parameters") or 
            payload.get("call", {}).get("args") or 
            payload
        )
        
        # Retell Call Object se auto-caller number fetch karein
        call_obj = payload.get("call", {})
        caller_phone = call_obj.get("from_number") or args.get("phone_number")
        caller_name = args.get("name") or "Unknown Customer"

        if caller_phone or caller_name:
            lead_data = {
                "name": caller_name,
                "phone": caller_phone,
                "city_interest": args.get("city"),
                "bhk_interest": args.get("bhk"),
                "created_at": datetime.utcnow()
            }
            leads_collection.insert_one(lead_data)
            return JSONResponse(status_code=200, content={"status": "success", "message": "Lead saved successfully!"})
        
        return JSONResponse(status_code=200, content={"status": "failed", "message": "No caller info provided."})
        
    except Exception as e:
        return JSONResponse(status_code=200, content={"status": "error", "message": str(e)})
