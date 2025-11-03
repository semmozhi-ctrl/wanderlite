from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Generator
import uuid
from datetime import datetime, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import timedelta
import requests
import json
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF
import qrcode
from io import BytesIO
import base64
import hashlib
from cryptography.fernet import Fernet

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
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    travelers = Column(Integer, nullable=True)
    itinerary_json = Column(Text, nullable=False, default="[]")
    images_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)

class BookingModel(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True, nullable=False)  # Removed ForeignKey constraint
    trip_id = Column(String(36), index=True, nullable=True)  # Removed ForeignKey constraint
    destination = Column(String(255), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    travelers = Column(Integer, default=1)
    package_type = Column(String(50), nullable=True)
    hotel_name = Column(String(255), nullable=True)
    flight_number = Column(String(50), nullable=True)
    total_price = Column(Float, default=0)
    currency = Column(String(10), default="INR")
    booking_ref = Column(String(50), unique=True, index=True, nullable=False)
    status = Column(String(20), default="Confirmed")  # Confirmed / Cancelled / Completed
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class GalleryPostModel(Base):
    __tablename__ = "gallery_posts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    image_url = Column(String(500), nullable=False)
    caption = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    tags_json = Column(Text, nullable=False, default="[]")
    likes = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PaymentReceiptModel(Base):
    __tablename__ = "payment_receipts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True, nullable=True)  # nullable for guest payments
    booking_ref = Column(String(50), index=True, nullable=False)
    destination = Column(String(255), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    travelers = Column(Integer, nullable=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    payment_method = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    receipt_url = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ChecklistItemModel(Base):
    __tablename__ = "checklist_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True, nullable=True)
    booking_id = Column(String(36), index=True, nullable=True)
    trip_id = Column(String(36), index=True, nullable=True)
    item_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)  # e.g., Clothing, Documents, Toiletries, etc.
    is_packed = Column(Integer, default=0)  # 0 = not packed, 1 = packed
    is_auto_generated = Column(Integer, default=0)  # 0 = user added, 1 = auto-suggested
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ServiceBookingModel(Base):
    __tablename__ = "service_bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True, nullable=True)
    service_type = Column(String(30), nullable=False)  # flight / hotel / restaurant
    service_json = Column(Text, nullable=False)
    total_price = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), default="INR")
    booking_ref = Column(String(80), unique=True, index=True, nullable=False)
    status = Column(String(20), default="Pending")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class StatusCheckModel(Base):
    __tablename__ = "status_checks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_name = Column(String(255), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def get_db() -> Generator[Session, None, None]:
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
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', 'http://127.0.0.1:8001')

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
    total_cost: float = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    travelers: Optional[int] = None
    itinerary: List[dict]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    images: List[str] = []

class TripCreate(BaseModel):
    destination: str
    days: int
    budget: str
    currency: str
    total_cost: Optional[float] = 0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    travelers: Optional[int] = None
    itinerary: List[dict]

class Booking(BaseModel):
    id: str
    destination: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    travelers: int
    package_type: Optional[str] = None
    hotel_name: Optional[str] = None
    flight_number: Optional[str] = None
    total_price: float
    currency: str
    booking_ref: str
    status: str = "Confirmed"
    created_at: datetime

class BookingCreate(BaseModel):
    trip_id: Optional[str] = None
    destination: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    travelers: int = 1
    package_type: Optional[str] = None
    hotel_name: Optional[str] = None
    flight_number: Optional[str] = None
    total_price: float
    currency: str = "INR"

class GalleryPost(BaseModel):
    id: str
    image_url: str
    caption: Optional[str] = None
    location: Optional[str] = None
    tags: List[str] = []
    likes: int
    created_at: datetime

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

# Payment models
class PaymentRequest(BaseModel):
    booking_ref: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    travelers: Optional[int] = None

    full_name: str
    email: str
    phone: str
    method: str  # Card / UPI / Wallet
    credential: str  # Card Number / UPI ID / Wallet ID
    amount: float

class PaymentResponse(BaseModel):
    status: str
    booking_ref: str
    receipt_url: str
    ticket_url: Optional[str] = None  # For service-specific tickets (flight/hotel/restaurant)


class ReceiptRecord(BaseModel):
    id: str
    booking_ref: str
    destination: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    travelers: Optional[int] = None
    full_name: str
    email: str
    phone: str
    payment_method: str
    amount: float
    receipt_url: str
    created_at: datetime

class ChecklistItem(BaseModel):
    id: str
    booking_id: Optional[str] = None
    trip_id: Optional[str] = None
    item_name: str
    category: Optional[str] = None
    is_packed: bool
    is_auto_generated: bool
    created_at: datetime

class ChecklistItemCreate(BaseModel):
    booking_id: Optional[str] = None
    trip_id: Optional[str] = None
    item_name: str
    category: Optional[str] = None

class BookingStatusUpdate(BaseModel):
    status: str  # Confirmed / Cancelled / Completed


# Service Booking Models
class ServiceBookingCreate(BaseModel):
    service_type: str  # flight / hotel / restaurant
    service_json: str  # JSON string of service details
    total_price: float
    currency: str = "INR"


class ServiceBookingResponse(BaseModel):
    id: str
    user_id: str
    service_type: str
    service_json: str
    total_price: float
    currency: str
    booking_ref: str
    status: str
    created_at: datetime


# Search Query Models
class FlightSearchQuery(BaseModel):
    origin: str
    destination: str
    date: Optional[str] = None
    travelers: int = 1


class HotelSearchQuery(BaseModel):
    destination: str
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    guests: int = 1
    min_rating: Optional[float] = None
    max_price: Optional[float] = None


class RestaurantSearchQuery(BaseModel):
    destination: str
    cuisine: Optional[str] = None
    budget: Optional[str] = None  # budget / mid-range / fine-dining


# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

# Smart packing checklist templates
PACKING_TEMPLATES = {
    "Beach": {
        "Clothing": ["Swimwear", "Beach cover-up", "Shorts", "T-shirts", "Sandals", "Sun hat", "Sunglasses"],
        "Toiletries": ["Sunscreen SPF 50+", "After-sun lotion", "Lip balm with SPF", "Waterproof phone case"],
        "Accessories": ["Beach towel", "Beach bag", "Snorkeling gear", "Flip flops"],
        "Essentials": ["Passport", "Tickets", "Hotel booking", "Travel insurance", "Cash/Cards"]
    },
    "Mountain": {
        "Clothing": ["Warm jacket", "Thermal wear", "Gloves", "Woolen cap", "Hiking boots", "Thick socks", "Waterproof pants"],
        "Toiletries": ["Moisturizer", "Lip balm", "Hand cream", "Sunscreen", "First aid kit"],
        "Accessories": ["Backpack", "Trekking pole", "Water bottle", "Flashlight", "Power bank"],
        "Essentials": ["Passport", "Tickets", "Hotel booking", "Travel insurance", "Cash/Cards", "Emergency contacts"]
    },
    "Heritage": {
        "Clothing": ["Comfortable walking shoes", "Light jacket", "Modest clothing", "Scarf/shawl", "Sun hat"],
        "Toiletries": ["Sunscreen", "Hand sanitizer", "Wet wipes", "Basic medicines"],
        "Accessories": ["Camera", "Guidebook", "Daypack", "Water bottle", "Notebook"],
        "Essentials": ["Passport", "Tickets", "Hotel booking", "Travel insurance", "Cash/Cards", "Museum passes"]
    },
    "Adventure": {
        "Clothing": ["Quick-dry clothes", "Sports shoes", "Cap", "Sunglasses", "Rain jacket", "Extra socks"],
        "Toiletries": ["Sunscreen", "Insect repellent", "First aid kit", "Energy bars", "Electrolyte powder"],
        "Accessories": ["GoPro/Action camera", "Headlamp", "Multi-tool", "Dry bag", "Portable charger"],
        "Essentials": ["Passport", "Tickets", "Activity bookings", "Travel insurance", "Emergency contact", "Maps"]
    },
    "Urban": {
        "Clothing": ["Casual wear", "Comfortable shoes", "Light jacket", "Accessories for photos"],
        "Toiletries": ["Travel-size toiletries", "Hand sanitizer", "Wet wipes", "Basic medicines"],
        "Accessories": ["Phone charger", "Power bank", "Camera", "Day bag", "Reusable water bottle"],
        "Essentials": ["Passport", "Tickets", "Hotel booking", "Travel card/pass", "City map/app"]
    },
    "Default": {
        "Clothing": ["Comfortable clothes", "Shoes", "Light jacket", "Undergarments", "Socks"],
        "Toiletries": ["Toothbrush", "Toothpaste", "Soap", "Shampoo", "Deodorant", "Sunscreen"],
        "Accessories": ["Phone charger", "Power bank", "Headphones", "Books/e-reader"],
        "Essentials": ["Passport", "Tickets", "Hotel booking", "Travel insurance", "Cash", "Credit cards"]
    }
}

def _detect_destination_category(destination: str) -> str:
    """Detect category from destination name or return Default."""
    dest_lower = destination.lower()
    # Beach destinations
    if any(word in dest_lower for word in ['goa', 'beach', 'maldives', 'bali', 'phuket', 'coast', 'island']):
        return "Beach"
    # Mountain destinations
    if any(word in dest_lower for word in ['kashmir', 'mountain', 'himalaya', 'nepal', 'manali', 'shimla', 'ladakh', 'ski']):
        return "Mountain"
    # Heritage destinations
    if any(word in dest_lower for word in ['rome', 'paris', 'egypt', 'petra', 'heritage', 'delhi', 'agra', 'jaipur', 'rajasthan']):
        return "Heritage"
    # Adventure destinations
    if any(word in dest_lower for word in ['adventure', 'safari', 'jungle', 'rishikesh', 'queenstown', 'interlaken']):
        return "Adventure"
    # Urban destinations
    if any(word in dest_lower for word in ['tokyo', 'new york', 'london', 'dubai', 'singapore', 'city', 'urban', 'mumbai']):
        return "Urban"
    return "Default"

def _generate_checklist_for_booking(booking_id: str, destination: str, db: Session) -> List[str]:
    """Auto-generate smart packing checklist items based on destination."""
    category = _detect_destination_category(destination)
    template = PACKING_TEMPLATES.get(category, PACKING_TEMPLATES["Default"])
    
    item_ids = []
    for cat, items in template.items():
        for item_name in items:
            item = ChecklistItemModel(
                user_id=None,  # TODO: associate with current user
                booking_id=booking_id,
                item_name=item_name,
                category=cat,
                is_auto_generated=1
            )
            db.add(item)
            db.flush()
            item_ids.append(item.id)
    db.commit()
    return item_ids

def _mask_credential(method: str, credential: str) -> str:
    try:
        m = method.lower()
        if m == 'card':
            digits = ''.join(filter(str.isdigit, credential))
            if len(digits) <= 4:
                return digits
            return f"{'*' * (len(digits) - 4)}{digits[-4:]}"
        if m in ('upi', 'wallet'):
            parts = credential.split('@', 1)
            if len(parts) == 2:
                user, domain = parts
                return f"{user[:2]}***@{domain}"
            return credential[:2] + '***' if len(credential) > 2 else credential
    except Exception:
        pass
    return credential

def _get_fernet() -> Fernet:
    # Derive a stable Fernet key from SECRET_KEY (SHA-256 then urlsafe base64)
    digest = hashlib.sha256(SECRET_KEY.encode('utf-8')).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)

def _qr_encrypt(payload: dict) -> str:
    token = _get_fernet().encrypt(json.dumps(payload).encode('utf-8'))
    return token.decode('utf-8')

def _qr_decrypt(token: str) -> dict:
    data = _get_fernet().decrypt(token.encode('utf-8'))
    return json.loads(data.decode('utf-8'))

def _build_qr_verification_url(booking_ref: str, service_type: str) -> str:
    payload = {
        'br': booking_ref,
        'stype': service_type,
        'iat': datetime.now(timezone.utc).isoformat()
    }
    token = _qr_encrypt(payload)
    base = PUBLIC_BASE_URL.rstrip('/')
    return f"{base}/ticket/verify?token={token}"

def _generate_flight_ticket_pdf(service_data: dict, booking_ref: str, passenger_info: dict, upload_dir: Path) -> str:
    """Generate a realistic flight ticket PDF with boarding pass layout."""
    tickets_dir = upload_dir / 'tickets'
    tickets_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"flight_ticket_{booking_ref}.pdf"
    file_path = tickets_dir / filename
    
    pdf = FPDF()
    pdf.add_page()
    
    # Header - Airline branding
    pdf.set_fill_color(0, 51, 102)  # Dark blue
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 24)
    pdf.set_xy(10, 10)
    pdf.cell(0, 10, service_data.get('airline', 'Airline'), 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.set_xy(10, 22)
    pdf.cell(0, 5, 'BOARDING PASS / E-TICKET', 0, 1)
    
    # PNR and E-Ticket Number
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(150, 10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 5, f'PNR: {booking_ref}', 0, 1)
    pdf.set_xy(150, 17)
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 5, f"E-Ticket: {booking_ref[:6].upper()}", 0, 1)
    pdf.set_xy(150, 24)
    pdf.cell(0, 5, f"Date: {datetime.now().strftime('%d %b %Y')}", 0, 1)
    
    # Passenger Details Section
    y = 50
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'PASSENGER DETAILS', 0, 1)
    
    y += 12
    pdf.set_font('Arial', '', 10)
    pdf.set_xy(10, y)
    pdf.cell(95, 6, f"Name: {passenger_info.get('fullName', passenger_info.get('full_name', 'N/A'))}", 0, 0)
    pdf.cell(95, 6, f"Gender: {passenger_info.get('gender', 'N/A').capitalize()}", 0, 1)
    
    y += 8
    pdf.set_xy(10, y)
    pdf.cell(95, 6, f"Date of Birth: {passenger_info.get('dateOfBirth', passenger_info.get('date_of_birth', 'N/A'))}", 0, 0)
    pdf.cell(95, 6, f"Nationality: {passenger_info.get('nationality', 'N/A')}", 0, 1)
    
    y += 8
    pdf.set_xy(10, y)
    pdf.cell(95, 6, f"Email: {passenger_info.get('email', 'N/A')}", 0, 0)
    pdf.cell(95, 6, f"Mobile: {passenger_info.get('mobile', 'N/A')}", 0, 1)
    
    y += 8
    pdf.set_xy(10, y)
    passport_num = passenger_info.get('passportNumber', passenger_info.get('passport_number', 'N/A'))
    pdf.cell(0, 6, f"Passport / ID: {passport_num}", 0, 1)
    
    # Flight Details Section with Boarding Pass Layout
    y += 15
    pdf.set_xy(10, y)
    pdf.set_fill_color(0, 102, 204)  # Blue
    pdf.rect(10, y, 190, 10, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_xy(10, y + 2)
    pdf.cell(0, 6, 'FLIGHT INFORMATION', 0, 1, 'C')
    
    # Flight Number and Class
    y += 15
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(95, 8, f"Flight: {service_data.get('flight_number', 'N/A')}", 0, 0)
    pdf.cell(95, 8, f"Class: {service_data.get('class', 'Economy').upper()}", 0, 1)
    
    # Route with large font
    y += 15
    pdf.set_font('Arial', 'B', 18)
    pdf.set_xy(10, y)
    origin = service_data.get('origin', 'N/A')
    destination = service_data.get('destination', 'N/A')
    pdf.cell(70, 10, origin, 0, 0, 'C')
    pdf.set_font('Arial', '', 16)
    pdf.cell(50, 10, '✈', 0, 0, 'C')
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(70, 10, destination, 0, 1, 'C')
    
    # Departure and Arrival Times
    y += 15
    pdf.set_font('Arial', '', 10)
    departure_time = service_data.get('departure_time', '')
    arrival_time = service_data.get('arrival_time', '')
    departure_date = service_data.get('departureDate', '')
    
    try:
        if departure_time:
            dep_dt = datetime.fromisoformat(departure_time.replace('Z', '+00:00'))
            dep_str = dep_dt.strftime('%H:%M')
            dep_date = dep_dt.strftime('%d %b %Y')
        elif departure_date:
            dep_str = 'TBA'
            dep_date = departure_date
        else:
            dep_str = 'TBA'
            dep_date = 'TBA'
            
        if arrival_time:
            arr_dt = datetime.fromisoformat(arrival_time.replace('Z', '+00:00'))
            arr_str = arr_dt.strftime('%H:%M')
            arr_date = arr_dt.strftime('%d %b %Y')
        else:
            arr_str = 'TBA'
            arr_date = dep_date
    except:
        dep_str = departure_time[:5] if departure_time else 'TBA'
        arr_str = arrival_time[:5] if arrival_time else 'TBA'
        dep_date = departure_date if departure_date else 'TBA'
        arr_date = dep_date
    
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(70, 6, 'DEPARTURE', 0, 0, 'C')
    pdf.cell(50, 6, 'DURATION', 0, 0, 'C')
    pdf.cell(70, 6, 'ARRIVAL', 0, 1, 'C')
    
    y += 8
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(70, 6, dep_str, 0, 0, 'C')
    pdf.set_font('Arial', '', 11)
    pdf.cell(50, 6, service_data.get('duration', 'N/A'), 0, 0, 'C')
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(70, 6, arr_str, 0, 1, 'C')
    
    y += 8
    pdf.set_xy(10, y)
    pdf.set_font('Arial', '', 9)
    pdf.cell(70, 5, dep_date, 0, 0, 'C')
    pdf.cell(50, 5, '', 0, 0, 'C')
    pdf.cell(70, 5, arr_date, 0, 1, 'C')
    
    # Boarding Pass Section
    y += 15
    pdf.set_xy(10, y)
    pdf.set_fill_color(255, 215, 0)  # Gold
    pdf.rect(10, y, 190, 45, 'F')
    pdf.set_fill_color(0, 0, 0)
    pdf.rect(10, y, 190, 10, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_xy(10, y + 2)
    pdf.cell(0, 6, 'BOARDING INFORMATION', 0, 1, 'C')
    
    y += 15
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_xy(15, y)
    pdf.cell(45, 6, 'GATE', 0, 0)
    pdf.cell(45, 6, 'SEAT', 0, 0)
    pdf.cell(45, 6, 'BOARDING TIME', 0, 0)
    pdf.cell(45, 6, 'DATE', 0, 1)
    
    y += 8
    pdf.set_font('Arial', 'B', 16)
    pdf.set_xy(15, y)
    gate = service_data.get('gate', 'TBA')
    seat = passenger_info.get('seatNumber', passenger_info.get('seat_number', 'N/A'))
    boarding_time = service_data.get('boardingTime', 'TBA')
    
    pdf.cell(45, 8, str(gate), 0, 0)
    pdf.cell(45, 8, seat, 0, 0)
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(45, 8, boarding_time, 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(45, 8, dep_date, 0, 1)
    
    # Additional Information
    y += 15
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 6, 'Baggage Allowance:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, service_data.get('baggage', 'Check-in: 20kg, Cabin: 7kg'), 0, 1)
    
    y += 8
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 6, 'Booking Status:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 128, 0)
    pdf.cell(0, 6, 'CONFIRMED', 0, 1)
    
    # Generate QR Code
    y += 15
    pdf.set_text_color(0, 0, 0)
    
    # QR Code now encodes a secure verification URL
    qr_data = _build_qr_verification_url(booking_ref, 'flight')
    
    # Create QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to temporary file
    qr_temp_path = tickets_dir / f"qr_{booking_ref}.png"
    qr_img.save(str(qr_temp_path))
    
    # Add QR code to PDF (right side)
    pdf.image(str(qr_temp_path), x=155, y=y, w=40, h=40)
    
    # Add barcode on left side
    pdf.set_xy(10, y)
    pdf.set_fill_color(0, 0, 0)
    for i in range(35):
        if i % 2 == 0:
            pdf.rect(10 + i * 3, y, 2, 15, 'F')
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(10, y + 18)
    pdf.set_font('Arial', '', 8)
    pdf.cell(105, 4, f'*{booking_ref}*', 0, 0, 'C')
    
    # QR Code label
    pdf.set_xy(155, y + 42)
    pdf.set_font('Arial', '', 7)
    pdf.cell(40, 3, 'Scan for Details', 0, 0, 'C')
    
    # Footer
    y += 50
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, '* Please arrive at the airport at least 2-3 hours before departure for international flights.', 0, 1)
    y += 5
    pdf.set_xy(10, y)
    pdf.cell(0, 5, '* Carry a valid government-issued photo ID and passport for verification.', 0, 1)
    y += 5
    pdf.set_xy(10, y)
    pdf.cell(0, 5, f"* Boarding closes 30 minutes before departure. For queries: support@wanderlite.com | PNR: {booking_ref}", 0, 1)
    
    pdf.output(str(file_path))
    
    # Clean up QR code temp file
    try:
        qr_temp_path.unlink()
    except:
        pass
    
    return str(file_path.relative_to(upload_dir))


def _generate_hotel_voucher_pdf(service_data: dict, booking_ref: str, guest_info: dict, upload_dir: Path) -> str:
    """Generate a hotel booking voucher PDF."""
    tickets_dir = upload_dir / 'tickets'
    tickets_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"hotel_voucher_{booking_ref}.pdf"
    file_path = tickets_dir / filename
    
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(102, 51, 153)  # Purple
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 20)
    pdf.set_xy(10, 10)
    pdf.cell(0, 10, 'HOTEL BOOKING VOUCHER', 0, 1)
    
    pdf.set_xy(150, 12)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, f'Voucher: {booking_ref}', 0, 1)
    
    # Hotel Name
    y = 45
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_xy(10, y)
    pdf.cell(0, 10, service_data.get('name', 'Hotel Name'), 0, 1)
    
    # Rating
    rating = service_data.get('rating', 0)
    stars = '★' * int(rating) + '☆' * (5 - int(rating))
    pdf.set_font('Arial', '', 12)
    pdf.set_xy(10, y + 10)
    pdf.cell(0, 6, f"{stars} ({rating}/5)", 0, 1)
    
    # Location
    pdf.set_xy(10, y + 18)
    pdf.cell(0, 6, f"Location: {service_data.get('location', 'N/A')}", 0, 1)
    
    # Guest Details
    y += 35
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'GUEST DETAILS', 0, 1)
    
    y += 12
    pdf.set_font('Arial', '', 10)
    pdf.set_xy(10, y)
    pdf.cell(0, 6, f"Name: {guest_info.get('full_name', 'N/A')}", 0, 1)
    pdf.set_xy(10, y + 6)
    pdf.cell(0, 6, f"Email: {guest_info.get('email', 'N/A')}", 0, 1)
    pdf.set_xy(10, y + 12)
    pdf.cell(0, 6, f"Phone: {guest_info.get('phone', 'N/A')}", 0, 1)
    pdf.set_xy(10, y + 18)
    pdf.cell(0, 6, f"Guests: {service_data.get('guests', 1)} person(s)", 0, 1)
    
    # Booking Details
    y += 35
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'BOOKING DETAILS', 0, 1)
    
    y += 12
    pdf.set_font('Arial', '', 10)
    pdf.set_xy(10, y)
    pdf.cell(95, 6, f"Check-in: {service_data.get('check_in', 'N/A')}", 0, 0)
    pdf.cell(95, 6, f"Check-out: {service_data.get('check_out', 'N/A')}", 0, 1)
    
    pdf.set_xy(10, y + 8)
    pdf.cell(95, 6, f"Nights: {service_data.get('nights', 1)} night(s)", 0, 0)
    pdf.cell(95, 6, f"Room Type: {service_data.get('room_type', 'Standard')}", 0, 1)
    
    # Amenities
    y += 25
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, 'Amenities:', 0, 1)
    pdf.set_font('Arial', '', 9)
    amenities = service_data.get('amenities', [])
    amenities_text = ', '.join(amenities) if amenities else 'Contact hotel for details'
    pdf.set_xy(10, y + 6)
    pdf.multi_cell(190, 5, amenities_text)
    
    # Footer
    y = 250
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, '* Please present this voucher at the hotel reception during check-in.', 0, 1)
    pdf.cell(0, 5, '* Carry a valid government-issued ID for verification.', 0, 1)
    pdf.cell(0, 5, f"* For any queries, contact: support@wanderlite.com | Booking Ref: {booking_ref}", 0, 1)
    
    # Add QR with verification URL
    try:
        verify_url = _build_qr_verification_url(booking_ref, 'hotel')
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_temp_path = tickets_dir / f"qr_{booking_ref}.png"
        qr_img.save(str(qr_temp_path))
        pdf.image(str(qr_temp_path), x=170, y=10, w=30, h=30)
        try:
            qr_temp_path.unlink()
        except:
            pass
    except Exception:
        pass

    pdf.output(str(file_path))
    return str(file_path.relative_to(upload_dir))


def _generate_restaurant_reservation_pdf(service_data: dict, booking_ref: str, guest_info: dict, upload_dir: Path) -> str:
    """Generate a restaurant reservation confirmation PDF."""
    tickets_dir = upload_dir / 'tickets'
    tickets_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"restaurant_reservation_{booking_ref}.pdf"
    file_path = tickets_dir / filename
    
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(230, 126, 34)  # Orange
    pdf.rect(0, 0, 210, 35, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 20)
    pdf.set_xy(10, 10)
    pdf.cell(0, 10, 'RESTAURANT RESERVATION', 0, 1)
    
    pdf.set_xy(150, 12)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 5, f'Ref: {booking_ref}', 0, 1)
    
    # Restaurant Name
    y = 45
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 18)
    pdf.set_xy(10, y)
    pdf.cell(0, 10, service_data.get('name', 'Restaurant Name'), 0, 1)
    
    # Cuisine & Rating
    pdf.set_font('Arial', '', 11)
    pdf.set_xy(10, y + 12)
    pdf.cell(0, 6, f"Cuisine: {service_data.get('cuisine', 'Multi-cuisine')}", 0, 1)
    
    rating = service_data.get('rating', 0)
    stars = '★' * int(rating) + '☆' * (5 - int(rating))
    pdf.set_xy(10, y + 18)
    pdf.cell(0, 6, f"Rating: {stars} ({rating}/5)", 0, 1)
    
    # Guest Details
    y += 35
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'RESERVATION DETAILS', 0, 1)
    
    y += 12
    pdf.set_font('Arial', '', 10)
    pdf.set_xy(10, y)
    pdf.cell(0, 6, f"Name: {guest_info.get('full_name', 'N/A')}", 0, 1)
    pdf.set_xy(10, y + 6)
    pdf.cell(0, 6, f"Phone: {guest_info.get('phone', 'N/A')}", 0, 1)
    pdf.set_xy(10, y + 12)
    pdf.cell(0, 6, f"Email: {guest_info.get('email', 'N/A')}", 0, 1)
    
    # Reservation Info
    y += 28
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 6, 'Date & Time:', 0, 0)
    pdf.set_font('Arial', '', 10)
    reservation_time = service_data.get('reservation_time', datetime.now().strftime('%d %b %Y, %H:%M'))
    pdf.cell(0, 6, reservation_time, 0, 1)
    
    pdf.set_xy(10, y + 8)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 6, 'Number of Guests:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f"{service_data.get('guests', 2)} person(s)", 0, 1)
    
    pdf.set_xy(10, y + 16)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 6, 'Table Preference:', 0, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, service_data.get('table_preference', 'Standard seating'), 0, 1)
    
    # Specialty Dish
    y += 35
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, 'Recommended Specialty:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.set_xy(10, y + 6)
    pdf.cell(0, 6, service_data.get('specialty_dish', 'Ask for chef recommendations'), 0, 1)
    
    # Location
    y += 20
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 6, 'Address:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.set_xy(10, y + 6)
    pdf.multi_cell(190, 5, f"{service_data.get('location', 'N/A')}\nDistance: {service_data.get('distance', 'N/A')}")
    
    # Footer
    y = 250
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, '* Please arrive on time or call to inform if delayed.', 0, 1)
    pdf.cell(0, 5, '* Reservation may be cancelled if you are more than 15 minutes late without notice.', 0, 1)
    pdf.cell(0, 5, f"* For cancellation or changes, contact: {guest_info.get('phone', 'N/A')} | Ref: {booking_ref}", 0, 1)
    
    # Add QR with verification URL
    try:
        verify_url = _build_qr_verification_url(booking_ref, 'restaurant')
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_temp_path = tickets_dir / f"qr_{booking_ref}.png"
        qr_img.save(str(qr_temp_path))
        pdf.image(str(qr_temp_path), x=170, y=10, w=30, h=30)
        try:
            qr_temp_path.unlink()
        except:
            pass
    except Exception:
        pass

    pdf.output(str(file_path))
    return str(file_path.relative_to(upload_dir))


def _generate_receipt_pdf(payload: PaymentRequest, upload_dir: Path) -> str:
    """Generate a simple payment receipt PDF and return the relative file path under uploads."""
    receipts_dir = upload_dir / 'receipts'
    receipts_dir.mkdir(parents=True, exist_ok=True)

    booking_ref = payload.booking_ref or f"WL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    filename = f"receipt_{booking_ref}.pdf"
    file_path = receipts_dir / filename

    pdf = FPDF()
    pdf.add_page()

    # Header
    pdf.set_fill_color(0, 119, 182)  # WanderLite blue
    pdf.rect(0, 0, 210, 25, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, 'WanderLite - Payment Receipt', 0, 1, 'L')

    # Body
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 12)
    pdf.ln(10)

    def row(label: str, value: str):
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(55, 8, label)
        pdf.set_font('Arial', '', 12)
        pdf.multi_cell(0, 8, value)

    row('Receipt No.:', booking_ref)
    row('Date:', datetime.now().strftime('%Y-%m-%d %H:%M'))
    row('Destination:', payload.destination or '-')
    sdate = payload.start_date.astimezone(timezone.utc).strftime('%Y-%m-%d') if payload.start_date else '-'
    edate = payload.end_date.astimezone(timezone.utc).strftime('%Y-%m-%d') if payload.end_date else '-'
    row('Travel Dates:', f"{sdate} to {edate}")
    row('Travelers:', str(payload.travelers or '-'))
    row('Name:', payload.full_name)
    row('Email:', payload.email)
    row('Phone:', payload.phone)
    row('Payment Method:', payload.method)
    row('Credential:', _mask_credential(payload.method, payload.credential))
    row('Amount Paid:', f"₹{(payload.amount or 0):,.2f}")
    row('Status:', 'SUCCESS')

    pdf.ln(6)
    pdf.set_text_color(100, 100, 100)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, 'This is a system-generated receipt for a simulated payment. For assistance contact support@wanderlite.com')

    pdf.output(str(file_path))
    return f"/uploads/receipts/{filename}"

@api_router.post("/payment/confirm", response_model=PaymentResponse)
async def confirm_payment(payload: PaymentRequest, db: Session = Depends(get_db)):
    try:
        upload_dir = Path('uploads')
        upload_dir.mkdir(exist_ok=True)
        
        booking_ref = payload.booking_ref or f"WL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Check if this is a service booking (flight/hotel/restaurant)
        service_booking = None
        if payload.booking_ref:
            service_booking = db.query(ServiceBookingModel).filter(
                ServiceBookingModel.booking_ref == payload.booking_ref
            ).first()
        
        # Generate appropriate ticket/voucher based on service type
        ticket_url = None
        if service_booking:
            import json
            service_data = json.loads(service_booking.service_json)
            guest_info = {
                'full_name': payload.full_name,
                'email': payload.email,
                'phone': payload.phone
            }
            
            if service_booking.service_type == 'flight':
                ticket_url = _generate_flight_ticket_pdf(service_data, booking_ref, guest_info, upload_dir)
            elif service_booking.service_type == 'hotel':
                ticket_url = _generate_hotel_voucher_pdf(service_data, booking_ref, guest_info, upload_dir)
            elif service_booking.service_type == 'restaurant':
                ticket_url = _generate_restaurant_reservation_pdf(service_data, booking_ref, guest_info, upload_dir)
            
            # Update service booking status to Confirmed
            service_booking.status = 'Confirmed'
            db.commit()
        
        # Always generate payment receipt
        receipt_url = _generate_receipt_pdf(payload, upload_dir)
        
        # Save receipt record to database
        receipt_record = PaymentReceiptModel(
            user_id=None,  # TODO: link to current user if authenticated
            booking_ref=booking_ref,
            destination=payload.destination,
            start_date=payload.start_date,
            end_date=payload.end_date,
            travelers=payload.travelers,
            full_name=payload.full_name,
            email=payload.email,
            phone=payload.phone,
            payment_method=payload.method,
            amount=payload.amount,
            receipt_url=receipt_url,
        )
        db.add(receipt_record)
        db.commit()
        
        # Return both receipt and ticket (if applicable)
        response_data = {
            'status': 'success',
            'booking_ref': booking_ref,
            'receipt_url': receipt_url
        }
        
        if ticket_url:
            response_data['ticket_url'] = ticket_url
        
        return PaymentResponse(**response_data)
    except Exception as e:
        logger.exception("Payment confirmation failed")
        raise HTTPException(status_code=500, detail=f"Failed to generate receipt: {e}")


@api_router.get("/tickets/verify")
async def verify_ticket(token: str, db: Session = Depends(get_db)):
    """Decrypt QR token and return real-time booking details for verification."""
    try:
        data = _qr_decrypt(token)
        booking_ref = data.get('br')
        service_type = data.get('stype')
        if not booking_ref:
            raise HTTPException(status_code=400, detail="Invalid token")

        # Try service booking by booking_ref
        service_booking = db.query(ServiceBookingModel).filter(
            ServiceBookingModel.booking_ref == booking_ref
        ).first()
        service_json = None
        if service_booking:
            try:
                service_json = json.loads(service_booking.service_json)
            except Exception:
                service_json = None

        # Try receipt by booking_ref for payer details
        receipt = db.query(PaymentReceiptModel).filter(
            PaymentReceiptModel.booking_ref == booking_ref
        ).order_by(PaymentReceiptModel.created_at.desc()).first()

        return {
            'status': 'valid',
            'booking_ref': booking_ref,
            'service_type': service_type,
            'service': service_json,
            'receipt': {
                'full_name': receipt.full_name if receipt else None,
                'email': receipt.email if receipt else None,
                'phone': receipt.phone if receipt else None,
                'amount': receipt.amount if receipt else None,
                'destination': receipt.destination if receipt else None,
                'start_date': receipt.start_date if receipt else None,
                'end_date': receipt.end_date if receipt else None,
                'travelers': receipt.travelers if receipt else None,
            } if receipt else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Ticket verification failed")
        raise HTTPException(status_code=400, detail=f"Invalid or expired token: {e}")


@api_router.get("/receipts", response_model=List[ReceiptRecord])
async def list_receipts(db: Session = Depends(get_db)):
    """List all payment receipts (for now returns all; TODO: filter by user_id)."""
    rows = db.query(PaymentReceiptModel).order_by(PaymentReceiptModel.created_at.desc()).all()
    return [
        ReceiptRecord(
            id=r.id,
            booking_ref=r.booking_ref,
            destination=r.destination,
            start_date=r.start_date,
            end_date=r.end_date,
            travelers=r.travelers,
            full_name=r.full_name,
            email=r.email,
            phone=r.phone,
            payment_method=r.payment_method,
            amount=r.amount,
            receipt_url=r.receipt_url,
            created_at=r.created_at,
        ) for r in rows
    ]

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
        total_cost=trip.total_cost or 0,
        start_date=trip.start_date,
        end_date=trip.end_date,
        travelers=trip.travelers,
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
        start_date=new_trip.start_date,
        end_date=new_trip.end_date,
        travelers=new_trip.travelers,
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
            start_date=r.start_date,
            end_date=r.end_date,
            travelers=r.travelers,
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
        start_date=r.start_date,
        end_date=r.end_date,
        travelers=r.travelers,
        itinerary=json.loads(r.itinerary_json or "[]"),
        created_at=r.created_at,
        images=json.loads(r.images_json or "[]"),
    )

class TripUpdate(BaseModel):
    destination: Optional[str] = None
    days: Optional[int] = None
    budget: Optional[str] = None
    currency: Optional[str] = None
    total_cost: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    travelers: Optional[int] = None
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
    if trip_update.total_cost is not None:
        r.total_cost = trip_update.total_cost
    if trip_update.start_date is not None:
        r.start_date = trip_update.start_date
    if trip_update.end_date is not None:
        r.end_date = trip_update.end_date
    if trip_update.travelers is not None:
        r.travelers = trip_update.travelers
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
        start_date=r.start_date,
        end_date=r.end_date,
        travelers=r.travelers,
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

# Bookings endpoints
@api_router.post("/bookings", response_model=Booking)
async def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    booking_ref = f"WL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    booking = BookingModel(
        user_id="guest",  # Default user for bookings without authentication
        trip_id=payload.trip_id,
        destination=payload.destination,
        start_date=payload.start_date,
        end_date=payload.end_date,
        travelers=payload.travelers,
        package_type=payload.package_type,
        hotel_name=payload.hotel_name,
        flight_number=payload.flight_number,
        total_price=payload.total_price,
        currency=payload.currency,
        booking_ref=booking_ref,
        status="Confirmed",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    
    # Auto-generate smart packing checklist
    try:
        _generate_checklist_for_booking(booking.id, booking.destination, db)
    except Exception as e:
        logger.warning(f"Failed to generate checklist for booking {booking.id}: {e}")
    
    return Booking(
        id=booking.id,
        destination=booking.destination,
        start_date=booking.start_date,
        end_date=booking.end_date,
        travelers=booking.travelers,
        package_type=booking.package_type,
        hotel_name=booking.hotel_name,
        flight_number=booking.flight_number,
        total_price=booking.total_price,
        currency=booking.currency,
        booking_ref=booking.booking_ref,
        status=booking.status,
        created_at=booking.created_at,
    )

@api_router.get("/bookings", response_model=List[Booking])
async def list_bookings(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(BookingModel)
    if status:
        query = query.filter(BookingModel.status == status)
    rows = query.order_by(BookingModel.created_at.desc()).all()
    return [
        Booking(
            id=r.id,
            destination=r.destination,
            start_date=r.start_date,
            end_date=r.end_date,
            travelers=r.travelers,
            package_type=r.package_type,
            hotel_name=r.hotel_name,
            flight_number=r.flight_number,
            total_price=r.total_price,
            currency=r.currency,
            booking_ref=r.booking_ref,
            status=r.status,
            created_at=r.created_at,
        ) for r in rows
    ]

@api_router.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str, db: Session = Depends(get_db)):
    r = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(r)
    db.commit()
    return {"message": "Booking deleted"}

@api_router.put("/bookings/{booking_id}/status", response_model=Booking)
async def update_booking_status(booking_id: str, payload: BookingStatusUpdate, db: Session = Depends(get_db)):
    r = db.query(BookingModel).filter(BookingModel.id == booking_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if payload.status not in ["Confirmed", "Cancelled", "Completed"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be Confirmed, Cancelled, or Completed.")
    
    r.status = payload.status
    if payload.status == "Cancelled":
        r.cancelled_at = datetime.now(timezone.utc)
    elif payload.status == "Completed":
        r.completed_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(r)
    
    return Booking(
        id=r.id,
        destination=r.destination,
        start_date=r.start_date,
        end_date=r.end_date,
        travelers=r.travelers,
        package_type=r.package_type,
        hotel_name=r.hotel_name,
        flight_number=r.flight_number,
        total_price=r.total_price,
        currency=r.currency,
        booking_ref=r.booking_ref,
        status=r.status,
        created_at=r.created_at,
    )

# Checklist endpoints
@api_router.post("/checklist/items", response_model=ChecklistItem)
async def create_checklist_item(payload: ChecklistItemCreate, db: Session = Depends(get_db)):
    item = ChecklistItemModel(
        user_id=None,  # TODO: associate with current user
        booking_id=payload.booking_id,
        trip_id=payload.trip_id,
        item_name=payload.item_name,
        category=payload.category,
        is_auto_generated=0
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ChecklistItem(
        id=item.id,
        booking_id=item.booking_id,
        trip_id=item.trip_id,
        item_name=item.item_name,
        category=item.category,
        is_packed=bool(item.is_packed),
        is_auto_generated=bool(item.is_auto_generated),
        created_at=item.created_at,
    )

@api_router.get("/checklist/items", response_model=List[ChecklistItem])
async def list_checklist_items(booking_id: Optional[str] = None, trip_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(ChecklistItemModel)
    if booking_id:
        query = query.filter(ChecklistItemModel.booking_id == booking_id)
    if trip_id:
        query = query.filter(ChecklistItemModel.trip_id == trip_id)
    rows = query.order_by(ChecklistItemModel.category, ChecklistItemModel.item_name).all()
    return [
        ChecklistItem(
            id=r.id,
            booking_id=r.booking_id,
            trip_id=r.trip_id,
            item_name=r.item_name,
            category=r.category,
            is_packed=bool(r.is_packed),
            is_auto_generated=bool(r.is_auto_generated),
            created_at=r.created_at,
        ) for r in rows
    ]

@api_router.put("/checklist/items/{item_id}")
async def toggle_checklist_item(item_id: str, db: Session = Depends(get_db)):
    r = db.query(ChecklistItemModel).filter(ChecklistItemModel.id == item_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    r.is_packed = 1 if r.is_packed == 0 else 0
    db.commit()
    return {"id": r.id, "is_packed": bool(r.is_packed)}

@api_router.delete("/checklist/items/{item_id}")
async def delete_checklist_item(item_id: str, db: Session = Depends(get_db)):
    r = db.query(ChecklistItemModel).filter(ChecklistItemModel.id == item_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    db.delete(r)
    db.commit()
    return {"message": "Checklist item deleted"}

# Gallery endpoints
@api_router.post("/gallery", response_model=GalleryPost)
async def create_gallery_post(
    caption: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON-encoded list of strings
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    file_ext = Path(file.filename).suffix
    file_name = f"gallery_{current_user.id}_{uuid.uuid4()}{file_ext}"
    file_path = upload_dir / file_name
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    image_url = f"/uploads/{file_name}"

    tags_list = []
    try:
        if tags:
            tags_list = json.loads(tags)
            if not isinstance(tags_list, list):
                tags_list = []
    except Exception:
        tags_list = []

    row = GalleryPostModel(
        user_id=current_user.id,
        image_url=image_url,
        caption=caption,
        location=location,
        tags_json=json.dumps(tags_list),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return GalleryPost(
        id=row.id,
        image_url=row.image_url,
        caption=row.caption,
        location=row.location,
        tags=json.loads(row.tags_json or "[]"),
        likes=row.likes,
        created_at=row.created_at,
    )

@api_router.get("/gallery", response_model=List[GalleryPost])
async def list_gallery_posts(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(GalleryPostModel).order_by(GalleryPostModel.created_at.desc()).limit(limit).all()
    return [
        GalleryPost(
            id=r.id,
            image_url=r.image_url,
            caption=r.caption,
            location=r.location,
            tags=json.loads(r.tags_json or "[]"),
            likes=r.likes,
            created_at=r.created_at,
        ) for r in rows
    ]

@api_router.post("/gallery/{post_id}/like")
async def like_gallery_post(post_id: str, db: Session = Depends(get_db)):
    r = db.query(GalleryPostModel).filter(GalleryPostModel.id == post_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Post not found")
    r.likes = (r.likes or 0) + 1
    db.commit()
    return {"likes": r.likes}

@api_router.delete("/gallery/{post_id}")
async def delete_gallery_post(post_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(GalleryPostModel).filter(GalleryPostModel.id == post_id, GalleryPostModel.user_id == current_user.id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Post not found or not owned by user")
    db.delete(r)
    db.commit()
    return {"message": "Post deleted"}

# Analytics endpoint
class AnalyticsSummary(BaseModel):
    total_trips: int
    total_spend: float
    avg_days: float
    top_destinations: List[dict]

@api_router.get("/analytics/summary", response_model=AnalyticsSummary)
async def analytics_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    trips = db.query(TripModel).filter(TripModel.user_id == current_user.id).all()
    total_trips = len(trips)
    total_spend = sum([t.total_cost or 0 for t in trips])
    avg_days = (sum([t.days or 0 for t in trips]) / total_trips) if total_trips > 0 else 0
    # Top destinations
    dest_counts = {}
    for t in trips:
        dest_counts[t.destination] = dest_counts.get(t.destination, 0) + 1
    top_destinations = sorted([
        {"destination": d, "count": c} for d, c in dest_counts.items()
    ], key=lambda x: x["count"], reverse=True)[:5]
    return AnalyticsSummary(
        total_trips=total_trips,
        total_spend=total_spend,
        avg_days=avg_days,
        top_destinations=top_destinations,
    )

# Destinations endpoint with real API integration using OpenTripMap
@api_router.get("/destinations", response_model=List[Destination])
async def get_destinations(category: Optional[str] = None, search: Optional[str] = None):
    # Define popular destinations with coordinates, categories, and images (matching mock.js format)
    cities = [
        {"name": "Goa, India", "lat": 15.2993, "lon": 74.1240, "category": "Beach", "image": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800&q=80", "shortDescription": "Sun, sand, and endless beaches"},
        {"name": "Paris, France", "lat": 48.8566, "lon": 2.3522, "category": "Heritage", "image": "https://images.unsplash.com/photo-1431274172761-fca41d930114?w=800&q=80", "shortDescription": "The city of lights and love"},
        {"name": "Tokyo, Japan", "lat": 35.6762, "lon": 139.6503, "category": "Adventure", "image": "https://images.unsplash.com/photo-1526481280693-3bfa7568e0f3?w=800&q=80", "shortDescription": "Where tradition meets technology"},
        {"name": "Bali, Indonesia", "lat": -8.3405, "lon": 115.0920, "category": "Beach", "image": "https://images.pexels.com/photos/3601425/pexels-photo-3601425.jpeg?w=800&q=80", "shortDescription": "Island of the Gods"},
        {"name": "Santorini, Greece", "lat": 36.3932, "lon": 25.4615, "category": "Heritage", "image": "https://images.unsplash.com/photo-1613395877344-13d4a8e0d49e?w=800&q=80", "shortDescription": "Whitewashed beauty of the Aegean"},
        {"name": "Dubai, UAE", "lat": 25.2048, "lon": 55.2708, "category": "Adventure", "image": "https://images.unsplash.com/photo-1605130284535-11dd9eedc58a?w=800&q=80", "shortDescription": "Futuristic luxury in the desert"},
        {"name": "Maldives", "lat": 3.2028, "lon": 73.2207, "category": "Beach", "image": "https://images.unsplash.com/photo-1637576308588-6647bf80944d?w=800&q=80", "shortDescription": "Tropical paradise with crystal waters"},
        {"name": "Kashmir, India", "lat": 34.0837, "lon": 74.7973, "category": "Mountain", "image": "https://images.unsplash.com/photo-1694084086064-9cdd1ef07d71?w=800&q=80", "shortDescription": "Paradise on Earth"},
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
                "name": city["name"],  # Use full name with country
                "category": city["category"],
                "image": city.get("image", "https://via.placeholder.com/800x600"),
                "short_description": city.get("shortDescription", f"Explore the wonders of {city['name']}"),
                "description": geoname_data.get("wikipedia_extracts", {}).get("text", f"A beautiful destination with rich culture and attractions. {city['name']} offers unforgettable experiences for every traveler."),
                "best_time": "Varies by season",
                "weather": weather,
                "attractions": attractions if attractions else ["Historic Sites", "Cultural Landmarks", "Natural Beauty"],
                "activities": ["Sightseeing", "Local cuisine", "Cultural experiences", "Photography"]
            }
            destinations.append(Destination(**dest))
        except Exception as e:
            logger.error(f"Error fetching data for {city['name']}: {e}")
            continue

    return destinations


# =============================
# Service Booking Endpoints (Flights, Hotels, Restaurants)
# =============================

def _generate_mock_flights(origin: str, destination: str, date: Optional[str], travelers: int):
    """Generate mock flight data"""
    airlines = [
        {"name": "IndiGo", "code": "6E"},
        {"name": "Air India", "code": "AI"},
        {"name": "SpiceJet", "code": "SG"},
        {"name": "Vistara", "code": "UK"},
        {"name": "GoAir", "code": "G8"}
    ]
    
    flights = []
    base_date = datetime.now() if not date else datetime.strptime(date, "%Y-%m-%d")
    
    for i, airline in enumerate(airlines):
        dep_hour = 6 + (i * 3)
        arr_hour = dep_hour + 2 + (i % 3)
        
        flight = {
            "id": f"FL{uuid.uuid4().hex[:8].upper()}",
            "airline": airline["name"],
            "flight_number": f"{airline['code']}{1000 + i}",
            "origin": origin,
            "destination": destination,
            "departure_time": base_date.replace(hour=dep_hour, minute=0).isoformat(),
            "arrival_time": base_date.replace(hour=arr_hour, minute=30).isoformat(),
            "duration": f"{arr_hour - dep_hour}h 30m",
            "price": 3500 + (i * 800),
            "currency": "INR",
            "seats_available": 45 - (i * 5),
            "refund_policy": "Free cancellation up to 24 hours" if i % 2 == 0 else "Non-refundable",
            "baggage": "15kg check-in, 7kg cabin"
        }
        flights.append(flight)
    
    return flights


def _generate_mock_hotels(destination: str, check_in: Optional[str], check_out: Optional[str], 
                          guests: int, min_rating: Optional[float], max_price: Optional[float]):
    """Generate mock hotel data"""
    hotels_db = [
        {
            "name": "Grand Palace Hotel",
            "location": f"Central {destination}",
            "rating": 4.5,
            "price_per_night": 3500,
            "amenities": ["Free WiFi", "Pool", "Spa", "Restaurant", "Gym"],
            "image_url": "https://via.placeholder.com/400x300/3498db/ffffff?text=Grand+Palace"
        },
        {
            "name": "Comfort Inn & Suites",
            "location": f"Near Airport, {destination}",
            "rating": 4.0,
            "price_per_night": 2200,
            "amenities": ["Free WiFi", "Breakfast", "Parking", "Airport Shuttle"],
            "image_url": "https://via.placeholder.com/400x300/2ecc71/ffffff?text=Comfort+Inn"
        },
        {
            "name": "Luxury Resort & Spa",
            "location": f"Beachfront, {destination}",
            "rating": 5.0,
            "price_per_night": 8500,
            "amenities": ["Private Beach", "Infinity Pool", "Fine Dining", "Spa", "Concierge"],
            "image_url": "https://via.placeholder.com/400x300/e74c3c/ffffff?text=Luxury+Resort"
        },
        {
            "name": "Budget Stay Hotel",
            "location": f"Downtown {destination}",
            "rating": 3.5,
            "price_per_night": 1200,
            "amenities": ["Free WiFi", "AC", "24/7 Reception"],
            "image_url": "https://via.placeholder.com/400x300/f39c12/ffffff?text=Budget+Stay"
        },
        {
            "name": "Heritage Boutique Hotel",
            "location": f"Old City, {destination}",
            "rating": 4.8,
            "price_per_night": 4500,
            "amenities": ["Cultural Tours", "Rooftop Restaurant", "Free WiFi", "Heritage Architecture"],
            "image_url": "https://via.placeholder.com/400x300/9b59b6/ffffff?text=Heritage+Boutique"
        }
    ]
    
    # Filter by rating and price
    filtered = []
    for hotel in hotels_db:
        if min_rating and hotel["rating"] < min_rating:
            continue
        if max_price and hotel["price_per_night"] > max_price:
            continue
        
        hotel_copy = hotel.copy()
        hotel_copy["id"] = f"HT{uuid.uuid4().hex[:8].upper()}"
        hotel_copy["destination"] = destination
        hotel_copy["currency"] = "INR"
        hotel_copy["rooms_available"] = 12
        filtered.append(hotel_copy)
    
    return filtered if filtered else hotels_db[:3]  # Return at least 3 hotels


def _generate_mock_restaurants(destination: str, cuisine: Optional[str], budget: Optional[str]):
    """Generate mock restaurant data"""
    restaurants_db = [
        {
            "name": "Spice Junction",
            "cuisine": "Indian",
            "specialty_dish": "Butter Chicken with Naan",
            "timings": "11:00 AM - 11:00 PM",
            "average_cost": 800,
            "budget_category": "mid-range",
            "rating": 4.3,
            "distance": "1.2 km",
            "image_url": "https://via.placeholder.com/400x300/e67e22/ffffff?text=Spice+Junction"
        },
        {
            "name": "Ocean Breeze Seafood",
            "cuisine": "Seafood",
            "specialty_dish": "Grilled Lobster",
            "timings": "12:00 PM - 10:00 PM",
            "average_cost": 2500,
            "budget_category": "fine-dining",
            "rating": 4.7,
            "distance": "3.5 km",
            "image_url": "https://via.placeholder.com/400x300/3498db/ffffff?text=Ocean+Breeze"
        },
        {
            "name": "Quick Bites Cafe",
            "cuisine": "Continental",
            "specialty_dish": "Club Sandwich",
            "timings": "8:00 AM - 8:00 PM",
            "average_cost": 350,
            "budget_category": "budget",
            "rating": 3.9,
            "distance": "0.5 km",
            "image_url": "https://via.placeholder.com/400x300/95a5a6/ffffff?text=Quick+Bites"
        },
        {
            "name": "Maharaja's Kitchen",
            "cuisine": "Indian",
            "specialty_dish": "Royal Thali",
            "timings": "12:00 PM - 11:00 PM",
            "average_cost": 1200,
            "budget_category": "mid-range",
            "rating": 4.5,
            "distance": "2.0 km",
            "image_url": "https://via.placeholder.com/400x300/c0392b/ffffff?text=Maharaja+Kitchen"
        },
        {
            "name": "Pasta Paradise",
            "cuisine": "Italian",
            "specialty_dish": "Truffle Pasta",
            "timings": "11:00 AM - 10:00 PM",
            "average_cost": 1800,
            "budget_category": "fine-dining",
            "rating": 4.6,
            "distance": "4.0 km",
            "image_url": "https://via.placeholder.com/400x300/27ae60/ffffff?text=Pasta+Paradise"
        }
    ]
    
    # Filter by cuisine and budget
    filtered = []
    for restaurant in restaurants_db:
        if cuisine and restaurant["cuisine"].lower() != cuisine.lower():
            continue
        if budget and restaurant["budget_category"] != budget:
            continue
        
        restaurant_copy = restaurant.copy()
        restaurant_copy["id"] = f"RS{uuid.uuid4().hex[:8].upper()}"
        restaurant_copy["destination"] = destination
        restaurant_copy["currency"] = "INR"
        filtered.append(restaurant_copy)
    
    return filtered if filtered else restaurants_db[:4]


@api_router.post("/search/flights")
async def search_flights(query: FlightSearchQuery):
    """Search for available flights"""
    flights = _generate_mock_flights(query.origin, query.destination, query.date, query.travelers)
    return {"flights": flights, "count": len(flights)}


@api_router.post("/search/hotels")
async def search_hotels(query: HotelSearchQuery):
    """Search for available hotels"""
    hotels = _generate_mock_hotels(
        query.destination, 
        query.check_in, 
        query.check_out, 
        query.guests,
        query.min_rating,
        query.max_price
    )
    return {"hotels": hotels, "count": len(hotels)}


@api_router.post("/search/restaurants")
async def search_restaurants(query: RestaurantSearchQuery):
    """Search for restaurants"""
    restaurants = _generate_mock_restaurants(query.destination, query.cuisine, query.budget)
    return {"restaurants": restaurants, "count": len(restaurants)}


@api_router.post("/service/bookings")
async def create_service_booking(
    booking: ServiceBookingCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new service booking (flight/hotel/restaurant)"""
    db: Session = next(get_db())
    
    booking_ref = f"{booking.service_type[:2].upper()}{uuid.uuid4().hex[:8].upper()}"
    
    db_booking = ServiceBookingModel(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        service_type=booking.service_type,
        service_json=booking.service_json,
        total_price=booking.total_price,
        currency=booking.currency,
        booking_ref=booking_ref,
        status="Pending",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    return ServiceBookingResponse(
        id=db_booking.id,
        user_id=db_booking.user_id,
        service_type=db_booking.service_type,
        service_json=db_booking.service_json,
        total_price=db_booking.total_price,
        currency=db_booking.currency,
        booking_ref=db_booking.booking_ref,
        status=db_booking.status,
        created_at=db_booking.created_at
    )


@api_router.get("/service/bookings")
async def get_service_bookings(current_user: User = Depends(get_current_user)):
    """Get all service bookings for the current user"""
    db: Session = next(get_db())
    
    bookings = db.query(ServiceBookingModel).filter(
        ServiceBookingModel.user_id == current_user.id
    ).order_by(ServiceBookingModel.created_at.desc()).all()
    
    return {
        "bookings": [
            ServiceBookingResponse(
                id=b.id,
                user_id=b.user_id,
                service_type=b.service_type,
                service_json=b.service_json,
                total_price=b.total_price,
                currency=b.currency,
                booking_ref=b.booking_ref,
                status=b.status,
                created_at=b.created_at
            )
            for b in bookings
        ]
    }


# Weather API endpoint
@api_router.get("/weather/{location}")
async def get_weather(location: str):
    # Using OpenWeatherMap API (free tier)
    api_key = os.environ.get('OPENWEATHER_API_KEY')
    if not api_key:
        # Return mock data if no API key
        return {"temp": 25, "condition": "Sunny", "humidity": 60}

# Geolocation reverse lookup -> city name
@api_router.get("/geolocate")
async def reverse_geolocate(lat: float, lon: float):
    api_key = os.environ.get('OPENWEATHER_API_KEY')
    if not api_key:
        return {"city": None}
    try:
        url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and data:
                item = data[0]
                return {"city": item.get("name"), "country": item.get("country")}
    except Exception:
        pass
    return {"city": None}

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
    # Best-effort schema migrations for added columns
    try:
        with engine.connect() as conn:
            # Add status column if missing
            try:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN status VARCHAR(20) DEFAULT 'Confirmed'"))
            except Exception:
                pass
            # Add cancelled_at column if missing
            try:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN cancelled_at DATETIME NULL"))
            except Exception:
                pass
            # Add completed_at column if missing
            try:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN completed_at DATETIME NULL"))
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Schema migration checks failed: {e}")
    logger.info("Database tables created/verified successfully")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

