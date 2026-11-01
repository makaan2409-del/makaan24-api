from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from bson import json_util
import json
import os
from datetime import datetime, timezone, timedelta

app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["makaan_latest_db"]
properties_collection = db["properties"]
leads_collection = db["caller_leads"]

IST = timezone(timedelta(hours=5, minutes=30))

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

        raw_city = args.get("city") or args.get("location") or ""
        max_price = args.get("max_price") or args.get("budget")
        bhk = args.get("bhk") or args.get("bedrooms")
        purpose = args.get("purpose") or args.get("listing_type") or args.get("intent")
        prop_type = args.get("property_type") or args.get("type") # Builder Floor / Flat / Plot

        query = {
            "isTrashed": {"$ne": True},
            "status": "published"
        }

        # 1. Location Filter
        if raw_city and str(raw_city).strip():
            city_clean = str(raw_city).split(',')[0].strip()
            query["$or"] = [
                {"areaText": {"$regex": city_clean, "$options": "i"}},
                {"address": {"$regex": city_clean, "$options": "i"}},
                {"cityText": {"$regex": city_clean, "$options": "i"}},
                {"title": {"$regex": city_clean, "$options": "i"}}
            ]

        # 2. BHK Filter
        if bhk is not None:
            try:
                bhk_num = int(bhk)
                query["$and"] = query.get("$and", [])
                query["$and"].append({
                    "$or": [
                        {"bedrooms": bhk_num},
                        {"bedrooms": str(bhk_num)}
                    ]
                })
            except (ValueError, TypeError):
                pass

        # 3. Purpose Filter (Sale vs Rent)
        if purpose and str(purpose).strip():
            p_str = str(purpose).lower()
            if "rent" in p_str:
                query["statusType"] = "for-rent"
            elif "sale" in p_str or "buy" in p_str or "kharid" in p_str:
                query["statusType"] = "for-sale"

        # 4. Property Type Filter (Floor / Flat / Plot)
        if prop_type and str(prop_type).strip():
            type_str = str(prop_type).strip()
            query["$or"] = query.get("$or", [])
            query["$or"].extend([
                {"title": {"$regex": type_str, "$options": "i"}},
                {"slug": {"$regex": type_str, "$options": "i"}}
            ])

        # 5. Budget Filter
        if max_price is not None:
            try:
                price_val = float(max_price)
                query["price"] = {"$lte": price_val}
            except (ValueError, TypeError):
                pass

        # Projection to remove heavy HTML fields
        projection = {
            "content": 0,
            "seo": 0,
            "mediaGalleryAlt": 0
        }

        results = list(properties_collection.find(query, projection).sort("createdAt", -1).limit(20))
        cleaned_results = json.loads(json_util.dumps(results))

        return JSONResponse(status_code=200, content={"properties": cleaned_results})

    except Exception as e:
        return JSONResponse(status_code=200, content={"properties": [], "error": str(e)})


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
        
        call_obj = payload.get("call", {})
        caller_phone = call_obj.get("from_number") or args.get("phone_number") or args.get("phone")
        caller_name = args.get("name") or "Unknown Customer"

        if caller_phone or caller_name:
            lead_data = {
                "name": caller_name,
                "phone": caller_phone,
                "city_interest": args.get("city"),
                "bhk_interest": args.get("bhk"),
                "created_at": datetime.now(IST)
            }
            
            if caller_phone:
                leads_collection.update_one(
                    {"phone": caller_phone},
                    {"$set": lead_data},
                    upsert=True
                )
            else:
                leads_collection.insert_one(lead_data)
                
            return JSONResponse(status_code=200, content={"status": "success", "message": "Lead saved successfully!"})
        
        return JSONResponse(status_code=200, content={"status": "failed", "message": "No caller info provided."})
        
    except Exception as e:
        return JSONResponse(status_code=200, content={"status": "error", "message": str(e)})
