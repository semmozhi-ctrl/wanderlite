from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import timedelta
import requests
import json
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

# SQLAlchemy (MySQL via XAMPP)
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    DateTime,
    Float,
    Text,
    ForeignKey,
    text,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.engine import url as sa_url


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# =============================
# Database setup (MySQL / XAMPP)
# =============================
DATABASE_URL = os.environ.get(
    "MYSQL_URL", "mysql+pymysql://root:@localhost:3306/wanderlite"
)

# Ensure database exists (for XAMPP first-time setup)
parsed_url = sa_url.make_url(DATABASE_URL)
db_name = parsed_url.database
server_url = parsed_url.set(database=None)

try:
    # Create database if it doesn't exist
    tmp_engine = create_engine(server_url, pool_pre_ping=True)
    with tmp_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(
            text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        )
    tmp_engine.dispose()
except Exception as e:
    # Log but continue; startup will fail later with clearer error if MySQL isn't running
    logging.getLogger(__name__).warning(f"Could not ensure database exists: {e}")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Profile fields
    name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    profile_image = Column(String(500), nullable=True)
    favorite_travel_type = Column(String(50), nullable=True)
    preferred_budget_range = Column(String(50), nullable=True)
    climate_preference = Column(String(50), nullable=True)
    food_preference = Column(String(50), nullable=True)
    language_preference = Column(String(50), nullable=True)
    notifications_enabled = Column(Integer, default=1)


class TripModel(Base):
    __tablename__ = "trips"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    destination = Column(String(255), nullable=False)
    days = Column(Integer, nullable=False)
    budget = Column(String(20), nullable=False)
    currency = Column(String(10), nullable=False)
    total_cost = Column(Float, default=0)
    itinerary_json = Column(Text, nullable=False, default="[]")
    images_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)


class StatusCheckModel(Base):
    __tablename__ = "status_checks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_name = Column(String(255), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Authentication setup
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    username: str
    hashed_password: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    profile_image: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


class UserPublic(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime
    name: Optional[str] = None
    phone: Optional[str] = None
    profile_image: Optional[str] = None
    favorite_travel_type: Optional[str] = None
    preferred_budget_range: Optional[str] = None
    climate_preference: Optional[str] = None
    food_preference: Optional[str] = None
    language_preference: Optional[str] = None
    notifications_enabled: Optional[int] = 1


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    favorite_travel_type: Optional[str] = None
    preferred_budget_range: Optional[str] = None
    climate_preference: Optional[str] = None
    food_preference: Optional[str] = None
    language_preference: Optional[str] = None
    notifications_enabled: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class Trip(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    destination: str
    days: int
    budget: str
    currency: str
    total_cost: float
    itinerary: List[dict]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    images: List[str] = []

class TripCreate(BaseModel):
    destination: str
    days: int
    budget: str
    currency: str
    itinerary: List[dict]

class Destination(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    image: str
    short_description: str
    description: str
    best_time: str
    weather: dict
    attractions: List[str]
    activities: List[str]

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate, db: Session = Depends(get_db)):
    obj = StatusCheckModel(client_name=input.client_name)
    db.add(obj)
    db.commit()
    return StatusCheck(id=obj.id, client_name=obj.client_name, timestamp=obj.timestamp)

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks(db: Session = Depends(get_db)):
    rows = db.query(StatusCheckModel).order_by(StatusCheckModel.timestamp.desc()).all()
    return [StatusCheck(id=r.id, client_name=r.client_name, timestamp=r.timestamp) for r in rows]

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Lookup user in MySQL
    with SessionLocal() as dbs:
        user_row = dbs.query(UserModel).filter(UserModel.email == email).first()
    if user_row is None:
        raise credentials_exception
    return User(
        id=user_row.id,
        email=user_row.email,
        username=user_row.username,
        hashed_password=None,
        created_at=user_row.created_at,
        profile_image=None,
    )


@api_router.get("/auth/me", response_model=UserPublic)
async def auth_me(current_user: User = Depends(get_current_user)):
    # Load fresh row to include all profile fields
    with SessionLocal() as dbs:
        row = dbs.query(UserModel).filter(UserModel.id == current_user.id).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return UserPublic(
            id=row.id,
            email=row.email,
            username=row.username,
            created_at=row.created_at,
            name=row.name,
            phone=row.phone,
            profile_image=row.profile_image,
            favorite_travel_type=row.favorite_travel_type,
            preferred_budget_range=row.preferred_budget_range,
            climate_preference=row.climate_preference,
            food_preference=row.food_preference,
            language_preference=row.language_preference,
            notifications_enabled=row.notifications_enabled,
        )


@api_router.put("/profile", response_model=UserPublic)
async def update_profile(payload: ProfileUpdate, current_user: User = Depends(get_current_user)):
    with SessionLocal() as dbs:
        row = dbs.query(UserModel).filter(UserModel.id == current_user.id).first()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        if payload.name is not None:
            row.name = payload.name
        if payload.username is not None and payload.username.strip():
            row.username = payload.username.strip()
        if payload.phone is not None:
            row.phone = payload.phone
        if payload.favorite_travel_type is not None:
            row.favorite_travel_type = payload.favorite_travel_type
        if payload.preferred_budget_range is not None:
            row.preferred_budget_range = payload.preferred_budget_range
        if payload.climate_preference is not None:
            row.climate_preference = payload.climate_preference
        if payload.food_preference is not None:
            row.food_preference = payload.food_preference
        if payload.language_preference is not None:
            row.language_preference = payload.language_preference
        if payload.notifications_enabled is not None:
            row.notifications_enabled = 1 if payload.notifications_enabled else 0
        dbs.commit()
        dbs.refresh(row)
        return UserPublic(
            id=row.id,
            email=row.email,
            username=row.username,
            created_at=row.created_at,
            name=row.name,
            phone=row.phone,
            profile_image=row.profile_image,
            favorite_travel_type=row.favorite_travel_type,
            preferred_budget_range=row.preferred_budget_range,
            climate_preference=row.climate_preference,
            food_preference=row.food_preference,
            language_preference=row.language_preference,
            notifications_enabled=row.notifications_enabled,
        )


@api_router.post("/profile/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    file_extension = Path(file.filename).suffix
    file_name = f"avatar_{current_user.id}{file_extension}"
    file_path = upload_dir / file_name
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    # Save URL to DB
    url = f"/uploads/{file_name}"
    with SessionLocal() as dbs:
        row = dbs.query(UserModel).filter(UserModel.id == current_user.id).first()
        if row:
            row.profile_image = url
            dbs.commit()
    return {"image_url": url}


@api_router.put("/auth/password")
async def change_password(payload: PasswordChange, current_user: User = Depends(get_current_user)):
    with SessionLocal() as dbs:
        row = dbs.query(UserModel).filter(UserModel.id == current_user.id).first()
        if not row or not verify_password(payload.current_password, row.hashed_password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        row.hashed_password = get_password_hash(payload.new_password)
        dbs.commit()
    return {"message": "Password updated"}


@api_router.delete("/auth/account")
async def delete_account(current_user: User = Depends(get_current_user)):
    with SessionLocal() as dbs:
        # Delete trips first (FK safe)
        dbs.query(TripModel).filter(TripModel.user_id == current_user.id).delete()
        dbs.query(UserModel).filter(UserModel.id == current_user.id).delete()
        dbs.commit()
    return {"message": "Account deleted"}

# Authentication endpoints
@api_router.post("/auth/signup", response_model=Token)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(user.password)
    new_user = UserModel(email=user.email, username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()

    # Issue access token on signup
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@api_router.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == user_credentials.email).first()
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

# Trip endpoints
@api_router.post("/trips", response_model=Trip)
async def create_trip(trip: TripCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_trip = TripModel(
        user_id=current_user.id,
        destination=trip.destination,
        days=trip.days,
        budget=trip.budget,
        currency=trip.currency,
        total_cost=0,
        itinerary_json=json.dumps(trip.itinerary),
        images_json=json.dumps([]),
    )
    db.add(new_trip)
    db.commit()
    return Trip(
        id=new_trip.id,
        user_id=new_trip.user_id,
        destination=new_trip.destination,
        days=new_trip.days,
        budget=new_trip.budget,
        currency=new_trip.currency,
        total_cost=new_trip.total_cost,
        itinerary=json.loads(new_trip.itinerary_json),
        created_at=new_trip.created_at,
        images=json.loads(new_trip.images_json),
    )

@api_router.get("/trips", response_model=List[Trip])
async def get_user_trips(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(TripModel).filter(TripModel.user_id == current_user.id).order_by(TripModel.created_at.desc()).all()
    return [
        Trip(
            id=r.id,
            user_id=r.user_id,
            destination=r.destination,
            days=r.days,
            budget=r.budget,
            currency=r.currency,
            total_cost=r.total_cost,
            itinerary=json.loads(r.itinerary_json or "[]"),
            created_at=r.created_at,
            images=json.loads(r.images_json or "[]"),
        ) for r in rows
    ]

@api_router.get("/trips/{trip_id}", response_model=Trip)
async def get_trip(trip_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(TripModel).filter(TripModel.id == trip_id, TripModel.user_id == current_user.id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Trip not found")
    return Trip(
        id=r.id,
        user_id=r.user_id,
        destination=r.destination,
        days=r.days,
        budget=r.budget,
        currency=r.currency,
        total_cost=r.total_cost,
        itinerary=json.loads(r.itinerary_json or "[]"),
        created_at=r.created_at,
        images=json.loads(r.images_json or "[]"),
    )

class TripUpdate(BaseModel):
    destination: Optional[str] = None
    days: Optional[int] = None
    budget: Optional[str] = None
    currency: Optional[str] = None
    itinerary: Optional[List[dict]] = None
    images: Optional[List[str]] = None


@api_router.put("/trips/{trip_id}", response_model=Trip)
async def update_trip(trip_id: str, trip_update: TripUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(TripModel).filter(TripModel.id == trip_id, TripModel.user_id == current_user.id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip_update.destination is not None:
        r.destination = trip_update.destination
    if trip_update.days is not None:
        r.days = trip_update.days
    if trip_update.budget is not None:
        r.budget = trip_update.budget
    if trip_update.currency is not None:
        r.currency = trip_update.currency
    if trip_update.itinerary is not None:
        r.itinerary_json = json.dumps(trip_update.itinerary)
    if trip_update.images is not None:
        r.images_json = json.dumps(trip_update.images)
    r.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(r)
    return Trip(
        id=r.id,
        user_id=r.user_id,
        destination=r.destination,
        days=r.days,
        budget=r.budget,
        currency=r.currency,
        total_cost=r.total_cost,
        itinerary=json.loads(r.itinerary_json or "[]"),
        created_at=r.created_at,
        images=json.loads(r.images_json or "[]"),
    )

@api_router.delete("/trips/{trip_id}")
async def delete_trip(trip_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(TripModel).filter(TripModel.id == trip_id, TripModel.user_id == current_user.id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Trip not found")
    db.delete(r)
    db.commit()
    return {"message": "Trip deleted successfully"}

# Destinations endpoint with real API integration using OpenTripMap
@api_router.get("/destinations", response_model=List[Destination])
async def get_destinations(category: Optional[str] = None, search: Optional[str] = None):
    # Define popular destinations with coordinates and categories
    cities = [
        {"name": "Goa", "lat": 15.2993, "lon": 74.1240, "category": "Beach"},
        {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "category": "Heritage"},
        {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503, "category": "Urban"},
        {"name": "Bali", "lat": -8.3405, "lon": 115.0920, "category": "Beach"},
        {"name": "Rome", "lat": 41.9028, "lon": 12.4964, "category": "Heritage"},
    ]

    destinations = []

    for city in cities:
        if category and city["category"].lower() != category.lower():
            continue
        if search and search.lower() not in city["name"].lower():
            continue

        try:
            # Fetch city details from OpenTripMap
            geoname_url = f"https://api.opentripmap.com/0.1/en/places/geoname?name={city['name']}"
            geoname_response = requests.get(geoname_url)
            geoname_data = geoname_response.json() if geoname_response.status_code == 200 else {}

            # Fetch nearby attractions
            radius_url = f"https://api.opentripmap.com/0.1/en/places/radius?radius=5000&lon={city['lon']}&lat={city['lat']}&kinds=museums,historical_places,natural,beaches,urban_environment&limit=5"
            radius_response = requests.get(radius_url)
            attractions = []
            if radius_response.status_code == 200:
                places_data = radius_response.json()
                attractions = [feature["properties"]["name"] for feature in places_data.get("features", []) if "properties" in feature and "name" in feature["properties"]]

            # Fetch real weather data
            weather_api_key = os.environ.get('OPENWEATHER_API_KEY')
            weather = {"temp": 25, "condition": "Sunny", "humidity": 60}  # Default mock
            if weather_api_key:
                try:
                    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city['name']}&appid={weather_api_key}&units=metric"
                    weather_response = requests.get(weather_url)
                    if weather_response.status_code == 200:
                        weather_data = weather_response.json()
                        weather = {
                            "temp": weather_data["main"]["temp"],
                            "condition": weather_data["weather"][0]["description"],
                            "humidity": weather_data["main"]["humidity"]
                        }
                except:
                    pass  # Use default mock

            # Map to Destination model
            dest = {
                "id": geoname_data.get("xid", str(uuid.uuid4())),
                "name": geoname_data.get("name", city["name"]),
                "category": city["category"],
                "image": geoname_data.get("image", "https://via.placeholder.com/800x600"),
                "short_description": geoname_data.get("wikipedia_extracts", {}).get("text", f"Explore the wonders of {city['name']}").split('.')[0] + ".",
                "description": geoname_data.get("wikipedia_extracts", {}).get("text", f"A beautiful destination in {city['name']} with rich culture and attractions."),
                "best_time": "Varies by season",  # Could be enhanced with real data
                "weather": weather,
                "attractions": attractions,
                "activities": ["Sightseeing", "Local cuisine", "Cultural experiences"]  # Generic activities
            }
            destinations.append(Destination(**dest))
        except Exception as e:
            logger.error(f"Error fetching data for {city['name']}: {e}")
            continue

    return destinations

# Weather API endpoint
@api_router.get("/weather/{location}")
async def get_weather(location: str):
    # Using OpenWeatherMap API (free tier)
    api_key = os.environ.get('OPENWEATHER_API_KEY')
    if not api_key:
        # Return mock data if no API key
        return {"temp": 25, "condition": "Sunny", "humidity": 60}

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
        response = requests.get(url)
        data = response.json()

        return {
            "temp": data["main"]["temp"],
            "condition": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"]
        }
    except:
        return {"temp": 25, "condition": "Sunny", "humidity": 60}

# Currency conversion endpoint
@api_router.get("/currency/convert")
async def convert_currency(amount: float, from_currency: str, to_currency: str):
    # Using free currency API (CurrencyAPI)
    api_key = os.environ.get('CURRENCY_API_KEY')
    if not api_key:
        # Mock conversion rates
        rates = {"USD": 1, "EUR": 0.92, "GBP": 0.79, "INR": 83.12, "JPY": 149.50, "AED": 3.67}
        if from_currency in rates and to_currency in rates:
            return {"converted_amount": amount * (rates[to_currency] / rates[from_currency])}
        return {"converted_amount": amount}

    try:
        url = f"https://api.currencyapi.com/v3/latest?apikey={api_key}&base_currency={from_currency}&currencies={to_currency}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            rate = data["data"][to_currency]["value"]
            return {"converted_amount": amount * rate}
        else:
            # Fallback to mock rates if API fails
            rates = {"USD": 1, "EUR": 0.92, "GBP": 0.79, "INR": 83.12, "JPY": 149.50, "AED": 3.67}
            if from_currency in rates and to_currency in rates:
                return {"converted_amount": amount * (rates[to_currency] / rates[from_currency])}
            return {"converted_amount": amount}
    except Exception as e:
        logger.error(f"Currency conversion error: {e}")
        # Fallback to mock rates
        rates = {"USD": 1, "EUR": 0.92, "GBP": 0.79, "INR": 83.12, "JPY": 149.50, "AED": 3.67}
        if from_currency in rates and to_currency in rates:
            return {"converted_amount": amount * (rates[to_currency] / rates[from_currency])}
        return {"converted_amount": amount}

# Image upload endpoint
@api_router.post("/upload/image")
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    # For now, save to local directory - in production use cloud storage
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    file_extension = Path(file.filename).suffix
    file_name = f"{current_user.id}_{uuid.uuid4()}{file_extension}"
    file_path = upload_dir / file_name

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Return the file URL (in production, this would be cloud storage URL)
    return {"image_url": f"/uploads/{file_name}"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files statically in development
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
def on_startup():
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    # Best-effort add columns for users (in case table existed before)
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS name VARCHAR(255) NULL,
                ADD COLUMN IF NOT EXISTS phone VARCHAR(50) NULL,
                ADD COLUMN IF NOT EXISTS profile_image VARCHAR(500) NULL,
                ADD COLUMN IF NOT EXISTS favorite_travel_type VARCHAR(50) NULL,
                ADD COLUMN IF NOT EXISTS preferred_budget_range VARCHAR(50) NULL,
                ADD COLUMN IF NOT EXISTS climate_preference VARCHAR(50) NULL,
                ADD COLUMN IF NOT EXISTS food_preference VARCHAR(50) NULL,
                ADD COLUMN IF NOT EXISTS language_preference VARCHAR(50) NULL,
                ADD COLUMN IF NOT EXISTS notifications_enabled TINYINT DEFAULT 1
            """))
    except Exception as e:
        logger.warning(f"Could not ensure user columns exist: {e}")


