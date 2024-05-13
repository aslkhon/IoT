from datetime import datetime
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

load_dotenv()

DB_URI = os.getenv("DB_URI")
client = MongoClient(DB_URI)
db = client.get_database("iot")

app = FastAPI()
security = HTTPBasic()

# Authenticate the user


def get_user_id(credentials: HTTPBasicCredentials = Depends(security)):
    user_collection = db.users
    user = user_collection.find_one({"username": credentials.username})
    if user and user["password"] == credentials.password:
        return user["_id"]
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )


def get_sensor_id(credentials: HTTPBasicCredentials = Depends(security)):
    sensor_collection = db.sensors
    sensor = sensor_collection.find_one({"_id": ObjectId(credentials.username)})
    if sensor and sensor["password"] == credentials.password:
        return sensor["_id"]
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )


# Get the current user's information


class UserResponseModel(BaseModel):
    name: str
    username: str
    email: str


@app.get(
    "/me",
    tags=["app"],
    response_model=UserResponseModel,
    responses={404: {"description": "User not found"}},
)
def read_current_user(user_id: ObjectId = Depends(get_user_id)):
    user_collection = db.users
    user = user_collection.find_one({"_id": user_id})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponseModel(
        name=user["name"], username=user["username"], email=user["email"]
    )


# Get the list of sensors


class SensorResponseModel(BaseModel):
    name: str
    status: str
    location: str


@app.get(
    "/sensors",
    tags=["app"],
    response_model=list[SensorResponseModel],
    responses={404: {"description": "Sensors not found"}},
)
def read_sensors(user_id: ObjectId = Depends(get_user_id)):
    sensor_collection = db.sensors
    sensors = sensor_collection.find({"owner_id": user_id})

    if not sensors:
        raise HTTPException(status_code=404, detail="Sensors not found")

    return [
        SensorResponseModel(
            name=sensor["name"], status=sensor["status"], location=sensor["location"]
        )
        for sensor in sensors
    ]


# Get sensor details


class SensorRecordModel(BaseModel):
    is_triggered: bool
    created_at: datetime


class SensorDetailResponseModel(BaseModel):
    name: str
    status: str
    updated_at: datetime
    location: str
    records: list[SensorRecordModel]


@app.get(
    "/sensors/{sensor_id}",
    tags=["app"],
    response_model=SensorDetailResponseModel,
    responses={404: {"description": "Sensor not found"}},
)
def read_sensor(
    sensor_id: str, records_limit: int = 10, user_id: ObjectId = Depends(get_user_id)
):
    sensor_collection = db.sensors
    sensor = sensor_collection.find_one({"_id": ObjectId(sensor_id)})

    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")

    if sensor["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Sensor not owned by the user")

    records_collection = db.records
    records = (
        records_collection.find({"sensor_id": ObjectId(sensor_id)})
        .sort("created_at", -1)
        .limit(records_limit)
    )
    return SensorDetailResponseModel(
        name=sensor["name"],
        status=sensor["status"],
        updated_at=sensor["updated_at"],
        location=sensor["location"],
        records=[
            SensorRecordModel(
                is_triggered=record["is_triggered"], created_at=record["created_at"]
            )
            for record in records
        ],
    )


# Reset sensor status


@app.put("/sensors/{sensor_id}/reset", tags=["app"])
def reset_sensor_status(sensor_id: str, user_id: ObjectId = Depends(get_user_id)):
    sensor_collection = db.sensors
    sensor = sensor_collection.find_one({"_id": ObjectId(sensor_id)})

    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")

    if sensor["owner_id"] != user_id:
        raise HTTPException(status_code=403, detail="Sensor not owned by the user")

    sensor_collection.update_one(
        {"_id": ObjectId(sensor_id)},
        {"$set": {"status": "CALM", "updated_at": datetime.now()}},
    )

    return {"message": "Sensor status reset successfully"}


# Receive sensor data


class SensorRecordRequestModel(BaseModel):
    is_triggered: bool


class SensorRecordRequestModel(BaseModel):
    is_triggered: bool

    @app.post("/record", tags=["sensor"], status_code=201)
    def create_sensor_record(
        record: SensorRecordRequestModel,
        sensor_id: ObjectId = Depends(get_sensor_id),
    ):
        sensor_collection = db.sensors
        sensor = sensor_collection.find_one({"_id": sensor_id})

        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor not found")

        if record.is_triggered:
            if sensor["status"] == "CALM":
                sensor_collection.update_one(
                    {"_id": sensor_id},
                    {"$set": {"status": "WARNING", "updated_at": datetime.now()}},
                )
            elif sensor["status"] == "WARNING":
                sensor_collection.update_one(
                    {"_id": sensor_id},
                    {"$set": {"status": "ALERT", "updated_at": datetime.now()}},
                )

        record_data = {
            "sensor_id": sensor_id,
            "is_triggered": record.is_triggered,
            "created_at": datetime.now(),
        }
        records_collection = db.records
        records_collection.insert_one(record_data)

        return {"message": "Record created"}
