from fastapi import FastAPI, Request
from pymongo import MongoClient
import os

app = FastAPI()

# Connect to your MongoDB database using an environment variable
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["makaan24"]
properties_collection = db["properties"]

@app.post("/search-properties")
async def search_properties(request: Request):
    payload = await request.json()
    args = payload.get("args", {})

    city = args.get("city")
    max_price = args.get("max_price")
    bhk = args.get("bhk")

    query = {}
    if city:
        query["city"] = {"$regex": city, "$options": "i"}
    if max_price:
        query["price"] = {"$lte": int(max_price)}
    if bhk:
        query["bhk"] = int(bhk)

    results = list(properties_collection.find(query, {"_id": 0}).limit(3))

    if not results:
        return {"properties": [], "message": "No matching properties found on makaan24.com."}

    return {"properties": results}
