from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
PDF_GENERATION_DISABLED = True  # Disable PDF generation due to dependency issues
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
# from fpdf import FPDF  # Commenting out to avoid numpy issues
# import qrcode
from io import BytesIO
import base64

# Placeholder variables to avoid Pylance undefined variable warnings
FPDF = None
qrcode = None
import hashlib
from cryptography.fernet import Fernet
import httpx

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

# Initialize FastAPI app
app = FastAPI(title="Wanderlite API")

# Basic CORS to allow frontend dev origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Minimal auth router to satisfy frontend login calls
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

@auth_router.post("/login")
def auth_login(req: LoginRequest):
    # Development mode: accept any valid credentials without DB check
    # For production, validate against UserModel in database
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    
    token = jwt.encode({"sub": req.email, "scope": "user"}, "dev-secret", algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "user": {"email": req.email}}

app.include_router(auth_router)

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

# Only attempt MySQL database creation for MySQL URLs
try:
    if parsed_url.get_backend_name().startswith("mysql"):
        tmp_engine = create_engine(server_url, pool_pre_ping=True)
        with tmp_engine.connect() as conn:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(
                text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            )
        tmp_engine.dispose()
except Exception as e:
    # Log but continue; startup will fail later with clearer error
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
HF_API_KEY = os.environ.get('HUGGINGFACE_API_KEY')

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
    """Generate a realistic flight ticket PDF with boarding pass layout - PLACEHOLDER VERSION."""
    # PDF generation temporarily disabled due to dependency issues
    # This function would normally generate a PDF ticket
    tickets_dir = upload_dir / 'tickets'
    tickets_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a simple text file as placeholder
    filename = f"flight_ticket_{booking_ref}.txt"
    file_path = tickets_dir / filename
    
    # Create a simple text-based ticket
    ticket_content = f"""
FLIGHT TICKET - {booking_ref}
================================

Passenger: {passenger_info.get('name', 'N/A')}
Flight: {service_data.get('airline', 'N/A')} {service_data.get('flight_number', 'N/A')}
From: {service_data.get('origin', 'N/A')}
To: {service_data.get('destination', 'N/A')}
Date: {service_data.get('departure_time', 'N/A')}
Seat: {passenger_info.get('seat', 'N/A')}

Booking Reference: {booking_ref}
Status: CONFIRMED

Note: PDF generation is temporarily unavailable.
This is a text-based ticket for demonstration purposes.
"""
    
    with open(file_path, 'w') as f:
        f.write(ticket_content)
    
    return str(file_path)
    
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
    pdf.cell(50, 10, '->', 0, 0, 'C')
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
    qr = None  # qrcode disabled
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
    
    return f"/uploads/{str(file_path.relative_to(upload_dir))}"


def _generate_hotel_voucher_pdf(service_data: dict, booking_ref: str, guest_info: dict, upload_dir: Path) -> str:
    """Generate a hotel booking voucher PDF - PLACEHOLDER VERSION."""
    tickets_dir = upload_dir / 'tickets'
    tickets_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"hotel_voucher_{booking_ref}.txt"
    file_path = tickets_dir / filename
    
    # Create a simple text-based voucher
    voucher_content = f"""
HOTEL VOUCHER - {booking_ref}
================================

Guest: {guest_info.get('name', 'N/A')}
Hotel: {service_data.get('name', 'N/A')}
Location: {service_data.get('location', 'N/A')}
Check-in: {service_data.get('check_in', 'N/A')}
Check-out: {service_data.get('check_out', 'N/A')}
Guests: {service_data.get('guests', 1)}

Booking Reference: {booking_ref}
Status: CONFIRMED

Note: PDF generation is temporarily unavailable.
This is a text-based voucher for demonstration purposes.
"""
    
    with open(file_path, 'w') as f:
        f.write(voucher_content)
    
    return f"/uploads/{str(file_path.relative_to(upload_dir))}"
    
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
    pdf.set_font('Arial', '', 12)
    pdf.set_xy(10, y + 10)
    pdf.cell(0, 6, f"Rating: {rating}/5", 0, 1)
    
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
        qr = None  # qrcode disabled
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
    return f"/uploads/{str(file_path.relative_to(upload_dir))}"


def _generate_restaurant_reservation_pdf(service_data: dict, booking_ref: str, guest_info: dict, upload_dir: Path) -> str:
    """Generate a restaurant reservation confirmation PDF."""
    tickets_dir = upload_dir / 'tickets'
    tickets_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"restaurant_reservation_{booking_ref}.pdf"
    file_path = tickets_dir / filename
    
    pdf = None  # FPDF disabled
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
    pdf.set_xy(10, y + 18)
    pdf.cell(0, 6, f"Rating: {rating}/5", 0, 1)
    
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
        qr = None  # qrcode disabled
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
    return f"/uploads/{str(file_path.relative_to(upload_dir))}"


def _generate_receipt_pdf(payload: PaymentRequest, upload_dir: Path) -> str:
    """Generate a simple payment receipt PDF and return the relative file path under uploads."""
    if PDF_GENERATION_DISABLED:
        # Return a placeholder receipt URL when PDF generation is disabled
        booking_ref = payload.booking_ref or f"WL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        return f"/uploads/receipts/receipt_{booking_ref}.pdf"
    
    receipts_dir = upload_dir / 'receipts'
    receipts_dir.mkdir(parents=True, exist_ok=True)

    booking_ref = payload.booking_ref or f"WL-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    filename = f"receipt_{booking_ref}.pdf"
    file_path = receipts_dir / filename

    from fpdf import FPDF
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
    row('Amount Paid:', f"INR {(payload.amount or 0):,.2f}")
    row('Status:', 'SUCCESS')

    pdf.ln(6)
    pdf.set_text_color(100, 100, 100)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, 'This is a system-generated receipt for a simulated payment. For assistance contact support@wanderlite.com')

    pdf.output(str(file_path))
    return f"/uploads/receipts/{filename}"

def _generate_hotel_receipt_pdf(service_data: dict, booking_ref: str, guest_info: dict, amount: float, currency: str, upload_dir: Path) -> str:
    """Generate a rich, branded hotel stay receipt PDF. Returns an absolute '/uploads/receipts/..' URL path."""
    receipts_dir = upload_dir / 'receipts'
    receipts_dir.mkdir(parents=True, exist_ok=True)

    filename = f"hotel_receipt_{booking_ref}.pdf"
    file_path = receipts_dir / filename

    pdf = None  # FPDF disabled
    pdf.add_page()

    # Header branding
    pdf.set_fill_color(102, 51, 153)  # Purple brand for hotel
    pdf.rect(0, 0, 210, 28, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, 'WanderLite - Hotel Receipt', 0, 1, 'L')

    # Receipt meta
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 11)
    y = 40
    pdf.set_xy(10, y)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 7, 'Receipt Details', 0, 1)
    pdf.set_font('Arial', '', 11)
    def row(lbl: str, val: str):
        nonlocal y
        pdf.set_xy(10, y)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(45, 7, lbl)
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 7, val, 0, 1)
        y += 7

    issue_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    row('Receipt No.:', booking_ref)
    row('Issue Date:', issue_date)

    # Guest & Booker
    y += 3
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'Guest & Booker', 0, 1)
    y += 12
    row('Name:', str(guest_info.get('full_name') or guest_info.get('fullName') or 'N/A'))
    row('Email:', str(guest_info.get('email') or 'N/A'))
    row('Phone:', str(guest_info.get('phone') or 'N/A'))

    # Hotel & Stay details
    y += 3
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'Hotel & Stay', 0, 1)
    y += 12
    hotel_name = service_data.get('name') or service_data.get('hotel_name') or 'Hotel'
    location = service_data.get('location') or service_data.get('destination') or 'N/A'
    rating = service_data.get('rating') or service_data.get('stars') or ''
    check_in = service_data.get('check_in') or service_data.get('checkIn') or ''
    check_out = service_data.get('check_out') or service_data.get('checkOut') or ''
    nights = service_data.get('nights') or service_data.get('nights_count') or ''
    guests = service_data.get('guests') or 1
    room_type = service_data.get('room_type') or service_data.get('roomType') or 'Standard'

    row('Hotel:', f"{hotel_name}")
    row('Location:', f"{location}")
    if rating:
        row('Rating:', f"{rating}/5")
    row('Check-in:', str(check_in))
    row('Check-out:', str(check_out))
    row('Nights:', str(nights))
    row('Guests:', str(guests))
    row('Room Type:', str(room_type))

    # Price breakdown
    y += 3
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'Price Breakdown', 0, 1)
    y += 10
    pdf.set_font('Arial', '', 11)
    price_per_night = float(service_data.get('price_per_night') or 0)
    nights_val = int(nights or 1)
    subtotal = price_per_night * nights_val
    taxes = round(subtotal * 0.10, 2)  # 10% illustrative taxes
    fees = round(subtotal * 0.05, 2)   # 5% service fee
    computed_total = round(subtotal + taxes + fees, 2)
    # Prefer provided amount if present
    total_amount = float(amount or computed_total)
    cur = currency or service_data.get('currency') or 'INR'

    def money(v: float) -> str:
        try:
            return f"INR {v:,.2f}" if cur.upper() == 'INR' else f"{cur} {v:,.2f}"
        except Exception:
            return str(v)

    # 2-column breakdown
    pdf.set_xy(12, y)
    pdf.cell(90, 7, f"Room ({nights_val} night(s))", 0, 0)
    pdf.cell(0, 7, money(subtotal), 0, 1, 'R')
    y += 7
    pdf.set_xy(12, y)
    pdf.cell(90, 7, "Taxes (10%)", 0, 0)
    pdf.cell(0, 7, money(taxes), 0, 1, 'R')
    y += 7
    pdf.set_xy(12, y)
    pdf.cell(90, 7, "Service Fee (5%)", 0, 0)
    pdf.cell(0, 7, money(fees), 0, 1, 'R')
    y += 7
    pdf.set_font('Arial', 'B', 12)
    pdf.set_xy(12, y)
    pdf.cell(90, 8, "Total Paid", 0, 0)
    pdf.cell(0, 8, money(total_amount), 0, 1, 'R')
    y += 10

    # Payment details
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'Payment', 0, 1)
    y += 12
    method = guest_info.get('method') or 'Card'
    credential = guest_info.get('credential') or ''
    masked = _mask_credential(method, credential)
    row('Method:', method)
    row('Credential:', masked)

    # QR verification
    try:
        verify_url = _build_qr_verification_url(booking_ref, 'hotel')
        qr = None  # qrcode disabled
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_temp_path = receipts_dir / f"qr_{booking_ref}.png"
        qr_img.save(str(qr_temp_path))
        pdf.image(str(qr_temp_path), x=165, y=10, w=30, h=30)
        try:
            qr_temp_path.unlink()
        except Exception:
            pass
    except Exception:
        pass

    # Footer note
    y = max(y + 6, 250)
    pdf.set_xy(10, y)
    pdf.set_text_color(100, 100, 100)
    pdf.set_font('Arial', 'I', 9)
    pdf.multi_cell(0, 5, '* This is an electronically generated receipt. For queries, contact support@wanderlite.com')

    pdf.output(str(file_path))
    return f"/uploads/receipts/{filename}"

def _generate_restaurant_receipt_pdf(service_data: dict, booking_ref: str, guest_info: dict, amount: float, currency: str, upload_dir: Path) -> str:
    """Generate a branded restaurant reservation receipt PDF. Returns an absolute '/uploads/receipts/..' URL path."""
    receipts_dir = upload_dir / 'receipts'
    receipts_dir.mkdir(parents=True, exist_ok=True)

    filename = f"restaurant_receipt_{booking_ref}.pdf"
    file_path = receipts_dir / filename

    pdf = None  # FPDF disabled
    pdf.add_page()

    # Header
    pdf.set_fill_color(230, 126, 34)  # Orange
    pdf.rect(0, 0, 210, 28, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 16)
    pdf.set_xy(10, 8)
    pdf.cell(0, 10, 'WanderLite - Dining Receipt', 0, 1, 'L')

    pdf.set_text_color(0, 0, 0)
    y = 40
    def row(lbl: str, val: str):
        nonlocal y
        pdf.set_xy(10, y)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(45, 7, lbl)
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 7, val, 0, 1)
        y += 7

    row('Receipt No.:', booking_ref)
    row('Issue Date:', datetime.now().strftime('%Y-%m-%d %H:%M'))
    row('Guest:', str(guest_info.get('full_name') or 'N/A'))
    row('Email:', str(guest_info.get('email') or 'N/A'))
    row('Phone:', str(guest_info.get('phone') or 'N/A'))

    # Restaurant details
    y += 3
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'Reservation', 0, 1)
    y += 12
    name = service_data.get('name', 'Restaurant')
    cuisine = service_data.get('cuisine', '')
    reservation_time = service_data.get('reservation_time') or service_data.get('reservationDate') or service_data.get('timeSlot') or 'TBA'
    guests = service_data.get('guests') or 2
    row('Restaurant:', name)
    if cuisine:
        row('Cuisine:', cuisine)
    row('Guests:', str(guests))
    row('Date & Time:', str(reservation_time))

    # Payment summary
    y += 3
    pdf.set_xy(10, y)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, y, 190, 8, 'F')
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'Payment', 0, 1)
    y += 12
    method = guest_info.get('method') or 'Card'
    credential = guest_info.get('credential') or ''
    masked = _mask_credential(method, credential)
    cur = currency or service_data.get('currency') or 'INR'
    def money(v: float) -> str:
        try:
            return f"INR {v:,.2f}" if cur.upper() == 'INR' else f"{cur} {v:,.2f}"
        except Exception:
            return str(v)
    row('Amount Paid:', money(float(amount or 0)))
    row('Method:', method)
    row('Credential:', masked)

    # QR
    try:
        verify_url = _build_qr_verification_url(booking_ref, 'restaurant')
        qr = None  # qrcode disabled
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_temp_path = receipts_dir / f"qr_{booking_ref}.png"
        qr_img.save(str(qr_temp_path))
        pdf.image(str(qr_temp_path), x=165, y=10, w=30, h=30)
        try:
            qr_temp_path.unlink()
        except Exception:
            pass
    except Exception:
        pass

    # Footer
    y = max(y + 6, 250)
    pdf.set_xy(10, y)
    pdf.set_text_color(100, 100, 100)
    pdf.set_font('Arial', 'I', 9)
    pdf.multi_cell(0, 5, '* Reservation policies may apply. Contact the restaurant for changes.')

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
        receipt_url: Optional[str] = None
        try:
            if service_booking:
                import json
                service_data = json.loads(service_booking.service_json)
                guest_info = {
                    'full_name': payload.full_name,
                    'email': payload.email,
                    'phone': payload.phone,
                    'method': payload.method,
                    'credential': payload.credential,
                }
                
                if service_booking.service_type == 'flight':
                    ticket_url = _generate_flight_ticket_pdf(service_data, booking_ref, guest_info, upload_dir)
                    # For flights we keep the generic payment receipt as well
                elif service_booking.service_type == 'hotel':
                    # Generate a rich hotel receipt and also provide a hotel voucher PDF as e-ticket
                    receipt_url = _generate_hotel_receipt_pdf(service_data, booking_ref, guest_info, payload.amount, payload.__dict__.get('currency', 'INR'), upload_dir)
                    ticket_url = _generate_hotel_voucher_pdf(service_data, booking_ref, guest_info, upload_dir)
                elif service_booking.service_type == 'restaurant':
                    # Generate a branded dining receipt
                    receipt_url = _generate_restaurant_receipt_pdf(service_data, booking_ref, guest_info, payload.amount, payload.__dict__.get('currency', 'INR'), upload_dir)
                
                # Update service booking status to Confirmed
                service_booking.status = 'Confirmed'
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to generate specialized receipt/ticket: {e}")
            # Continue with generic receipt generation
        
        # Generate a generic payment receipt only if not already generated a specialized one
        if not receipt_url:
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
        raise HTTPException(status_code=500, detail=f"Failed to confirm payment: {str(e)}")


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

# Auth Login - Development mode endpoint
@api_router.post("/auth/login")
def login_dev(req: LoginRequest):
    # Development mode: accept any valid credentials and create user if needed
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    
    # Get database session
    db = next(get_db())
    
    # Check if user exists, if not create them
    user = db.query(UserModel).filter(UserModel.email == req.email).first()
    if not user:
        # Create new user for development
        user = UserModel(
            id=str(uuid.uuid4()),
            email=req.email,
            username=req.email.split('@')[0],
            hashed_password=get_password_hash(req.password),
            created_at=datetime.now(timezone.utc)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create JWT token using the same SECRET_KEY
    to_encode = {"sub": user.email}
    access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"access_token": access_token, "token_type": "bearer", "user": {"email": user.email}}

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


# =============================
# AI Assistant Endpoint
# =============================
# OLD AI Chat Endpoint - DISABLED (using new Gemini proxy instead)
# =============================

# class ChatMessage(BaseModel):
#     role: str
#     content: str

# class ChatRequest(BaseModel):
#     messages: List[ChatMessage]

# def _summarize_flights(origin: str, destination: str, db_data: List[dict]) -> str:
#     lines = [f"Here are sample flights from {origin} to {destination}:"]
#     for f in db_data[:3]:
#         lines.append(f"- {f['airline']} {f['flight_number']} {f['departure_time'][11:16]}->{f['arrival_time'][11:16]} | {f['duration']} | INR {f['price']}")
#     return "\n".join(lines)

# @api_router.post("/ai/chat")
# async def ai_chat_old(req: ChatRequest):
#     user_msg = next((m.content for m in reversed(req.messages) if m.role == 'user'), '')
#     user_lower = user_msg.lower()

#     # Heuristic: if user asks for flights/hotels/restaurants, use our mock search to build an answer
#     try:
#         if 'flight' in user_lower and (' from ' in user_lower or ' to ' in user_lower):
#             # naive parse: "flights from X to Y"
#             origin = 'Delhi'
#             destination = 'Goa'
#             try:
#                 parts = user_lower.replace('flights', '').replace('flight', '')
#                 if 'from' in parts and 'to' in parts:
#                     origin = parts.split('from')[1].split('to')[0].strip().title()
#                     destination = parts.split('to')[1].strip().title()
#             except Exception:
#                 pass
#             flights = _generate_mock_flights(origin, destination, None, 1)
#             return { 'answer': _summarize_flights(origin, destination, flights) }

#         if 'hotel' in user_lower:
#             dest = 'Goa'
#             try:
#                 # pick last word as destination rudimentarily
#                 dest = user_msg.strip().split()[-1]
#             except Exception:
#                 pass
#             hotels = _generate_mock_hotels(dest, None, None, 2, None, None)
#             top = hotels[:3]
#             ans = "Top hotels in {d}:\n".format(d=dest)
#             ans += "\n".join([f"- {h['name']} ({h['rating']}/5) INR {h['price_per_night']}/night" for h in top])
#             return { 'answer': ans }

#         if 'restaurant' in user_lower or 'dining' in user_lower:
#             dest = 'Goa'
#             restaurants = _generate_mock_restaurants(dest, None, None)
#             top = restaurants[:3]
#             ans = "Popular restaurants in {d}:\n".format(d=dest)
#             ans += "\n".join([f"- {r['name']} ({r['cuisine']}) avg INR {r['average_cost']}" for r in top])
#             return { 'answer': ans }
#     except Exception:
#         pass

#     # Fallback to Hugging Face Inference API if configured
#     if HF_API_KEY:
#         try:
#             prompt = "You are a helpful travel assistant. Answer concisely.\n" + user_msg
#             async with httpx.AsyncClient(timeout=30) as client:
#                 resp = await client.post(
#                     'https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3',
#                     headers={ 'Authorization': f'Bearer {HF_API_KEY}' },
#                     json={ 'inputs': prompt, 'parameters': { 'max_new_tokens': 200, 'temperature': 0.7 } }
#                 )
#             data = resp.json()
#             if isinstance(data, list) and data and 'generated_text' in data[0]:
#                 return { 'answer': data[0]['generated_text'][-600:] }
#             if isinstance(data, dict) and 'generated_text' in data:
#                 return { 'answer': data['generated_text'] }
#         except Exception as e:
#             logger.warning(f"HF inference failed: {e}")

#     # Final fallback
#     return { 'answer': "I can help with destinations, flights, hotels, and restaurants. Ask me for flights from City A to City B, or hotels in a city." }


@api_router.post("/service/bookings")
@api_router.post("/bookings/service")  # Alias for frontend compatibility
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

# ===============================================
# AI Assistant Endpoints - Data for Recommendations
# ===============================================

class AIDataRequest(BaseModel):
    data_type: str  # 'hotels', 'flights', 'restaurants'
    location: Optional[str] = None
    limit: Optional[int] = 10

@app.get("/api/ai/data/hotels")
async def get_hotels_for_ai(location: Optional[str] = None, limit: int = 10):
    """
    Get sample hotel data for AI recommendations
    """
    # In a real app, this would query your hotel database
    # For now, return structured sample data
    hotels = [
        {
            "name": "Paradise Inn",
            "location": location or "Goa",
            "price_per_night": 3500,
            "rating": 4.5,
            "amenities": ["Pool", "WiFi", "Breakfast", "Beach Access"],
            "type": "Beach Resort",
            "best_for": "Couples, Families"
        },
        {
            "name": "Mountain View Lodge",
            "location": location or "Manali",
            "price_per_night": 4200,
            "rating": 4.7,
            "amenities": ["Mountain View", "WiFi", "Parking", "Restaurant"],
            "type": "Mountain Resort",
            "best_for": "Adventure, Solo Travelers"
        },
        {
            "name": "City Comfort Hotel",
            "location": location or "Mumbai",
            "price_per_night": 5500,
            "rating": 4.3,
            "amenities": ["WiFi", "Gym", "Business Center", "Airport Shuttle"],
            "type": "Business Hotel",
            "best_for": "Business Travelers"
        },
        {
            "name": "Heritage Palace",
            "location": location or "Jaipur",
            "price_per_night": 6800,
            "rating": 4.8,
            "amenities": ["Pool", "Spa", "Restaurant", "Cultural Tours"],
            "type": "Heritage Hotel",
            "best_for": "Couples, Luxury Travelers"
        },
        {
            "name": "Backpacker's Haven",
            "location": location or "Delhi",
            "price_per_night": 1200,
            "rating": 4.0,
            "amenities": ["WiFi", "Common Kitchen", "Lounge", "Tours"],
            "type": "Hostel",
            "best_for": "Solo Travelers, Budget"
        }
    ]
    return {"hotels": hotels[:limit], "count": len(hotels[:limit])}

@app.get("/api/ai/data/flights")
async def get_flights_for_ai(origin: Optional[str] = None, destination: Optional[str] = None, limit: int = 10):
    """
    Get sample flight data for AI recommendations
    """
    flights = [
        {
            "airline": "IndiGo",
            "flight_number": "6E-123",
            "origin": origin or "Delhi",
            "destination": destination or "Mumbai",
            "price": 4500,
            "duration": "2h 15m",
            "class": "Economy",
            "stops": 0
        },
        {
            "airline": "Air India",
            "flight_number": "AI-456",
            "origin": origin or "Delhi",
            "destination": destination or "Mumbai",
            "price": 6200,
            "duration": "2h 10m",
            "class": "Business",
            "stops": 0
        },
        {
            "airline": "SpiceJet",
            "flight_number": "SG-789",
            "origin": origin or "Delhi",
            "destination": destination or "Mumbai",
            "price": 3800,
            "duration": "2h 30m",
            "class": "Economy",
            "stops": 0
        },
        {
            "airline": "Vistara",
            "flight_number": "UK-234",
            "origin": origin or "Delhi",
            "destination": destination or "Mumbai",
            "price": 5500,
            "duration": "2h 20m",
            "class": "Premium Economy",
            "stops": 0
        }
    ]
    return {"flights": flights[:limit], "count": len(flights[:limit])}

@app.get("/api/ai/data/restaurants")
async def get_restaurants_for_ai(location: Optional[str] = None, cuisine: Optional[str] = None, limit: int = 10):
    """
    Get sample restaurant data for AI recommendations
    """
    restaurants = [
        {
            "name": "Spice Garden",
            "location": location or "Delhi",
            "cuisine": cuisine or "Indian",
            "price_range": "INR 800-1500",
            "rating": 4.6,
            "specialties": ["Butter Chicken", "Dal Makhani", "Naan"],
            "best_for": "Families, Traditional Dining"
        },
        {
            "name": "Coastal Breeze",
            "location": location or "Goa",
            "cuisine": cuisine or "Seafood",
            "price_range": "INR 1200-2000",
            "rating": 4.7,
            "specialties": ["Goan Fish Curry", "Prawns", "Calamari"],
            "best_for": "Seafood Lovers, Beach Dining"
        },
        {
            "name": "Taj Mahal Restaurant",
            "location": location or "Agra",
            "cuisine": cuisine or "Mughlai",
            "price_range": "INR 600-1200",
            "rating": 4.5,
            "specialties": ["Biryani", "Kebabs", "Korma"],
            "best_for": "Traditional Food, Groups"
        },
        {
            "name": "Green Leaf Cafe",
            "location": location or "Bangalore",
            "cuisine": cuisine or "Vegetarian",
            "price_range": "INR 400-800",
            "rating": 4.4,
            "specialties": ["South Indian", "Dosa", "Idli"],
            "best_for": "Vegetarians, Healthy Eating"
        }
    ]
    return {"restaurants": restaurants[:limit], "count": len(restaurants[:limit])}

@app.get("/api/ai/policies")
async def get_policies():
    """
    Get booking and refund policies for AI to explain
    """
    policies = {
        "booking": {
            "hotels": "Book hotels with ease! Pay online or at the property. Most bookings are confirmed instantly. You'll receive a voucher via email.",
            "flights": "Flight tickets are confirmed immediately after payment. E-tickets will be sent to your email. Please check baggage allowance.",
            "restaurants": "Restaurant reservations are confirmed based on availability. You'll receive a confirmation via email and SMS."
        },
        "cancellation": {
            "hotels": "Free cancellation up to 24 hours before check-in for most hotels. Some may have different policies - check booking details.",
            "flights": "Cancellation fees depend on airline and fare type. Refunds processed in 7-14 business days. Check fare rules before booking.",
            "restaurants": "Cancel up to 2 hours before reservation time for full refund. Late cancellations may incur charges."
        },
        "refund": {
            "general": "Refunds are processed within 7-14 business days to the original payment method. Cancellation fees (if any) will be deducted."
        }
    }
    return policies


# ===============================================
# AI Chat Proxy - Calls Google Gemini server-side
# ===============================================

class AIChatRequest(BaseModel):
    message: str
    context: Optional[dict] = {}
    
    model_config = ConfigDict(extra='allow')

_AI_SYSTEM_CONTEXT = (
    "You are WanderLite AI — an advanced, friendly, and knowledgeable travel assistant integrated into a travel "
    "planning website.\n\n"
    "Your role:\n"
    "- Help users find destinations, hotels, flights, and restaurants based on their preferences.\n"
    "- Provide personalized suggestions based on location, budget, and travel type (solo, family, group, romantic).\n"
    "- Explain booking and refund policies in simple terms.\n"
    "- Handle trip planning, itinerary creation, and group coordination.\n"
    "- Keep tone: friendly, clear, and human-like — never robotic.\n"
    "- Format answers neatly with bullet points, emojis, and short paragraphs.\n\n"
    "Rules:\n"
    "- Stay within travel, hotels, restaurants, and flights context.\n"
    "- Never provide fake payment or transaction details.\n"
    "- If unrelated questions arise, politely redirect to travel assistance.\n"
    "- If you need data (like hotel list or flight options), say: \"Would you like me to show WanderLite's latest results?\"\n"
    "- Ask clarifying questions before giving recommendations when needed.\n\n"
    "System Context:\n- App name: WanderLite\n- Developer: Bro\n"
)

@app.post("/api/ai/chat")
async def ai_chat(req: AIChatRequest):
    logger.info(f"AI Chat Request: message={req.message[:50]}..., context={req.context}")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured on server")

    # Build prompt with system context and optional user context
    ctx_parts = []
    if req.context:
        try:
            ctx_parts.append("Context: " + json.dumps(req.context, ensure_ascii=False))
        except Exception:
            pass
    full_prompt = _AI_SYSTEM_CONTEXT + ("\n\n" + "\n".join(ctx_parts) if ctx_parts else "") + "\n\n" + req.message

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ],
    }

    # First, try to get the list of available models
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            list_resp = await client.get(list_url)
        
        if list_resp.status_code == 200:
            models_data = list_resp.json()
            available_models = []
            
            # Extract model names that support generateContent
            for model in models_data.get("models", []):
                model_name = model.get("name", "").replace("models/", "")
                supported_methods = model.get("supportedGenerationMethods", [])
                if "generateContent" in supported_methods:
                    available_models.append(model_name)
            
            logger.info(f"Available Gemini models: {available_models}")
            
            # Prioritize older/stable models that are less likely to have quota issues
            priority_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro", "gemini-1.0-pro"]
            ordered_models = [m for m in priority_models if m in available_models]
            # Add remaining available models
            ordered_models.extend([m for m in available_models if m not in ordered_models])
            
            # Try each available model
            for model_name in ordered_models[:5]:  # Try first 5 models
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    logger.info(f"Trying available model: {model_name}")
                    
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.post(url, json=payload)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = (
                            (data.get("candidates") or [{}])[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text")
                        )
                        if answer:
                            logger.info(f"✅ Success with available model: {model_name}")
                            return {"answer": answer}
                    elif resp.status_code == 429:
                        detail = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                        logger.warning(f"⏳ {model_name}: Quota exceeded - trying next model")
                        continue
                    else:
                        detail = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                        logger.warning(f"❌ Available model {model_name} failed: {resp.status_code} {detail}")
                        continue
                        
                except Exception as e:
                    logger.warning(f"Available model {model_name} error: {str(e)}")
                    continue
    
    except Exception as e:
        logger.warning(f"Could not list available models: {str(e)}")
    
    # If listing models failed, try hardcoded stable models
    fallback_models = [
        "gemini-1.5-flash",
        "gemini-1.5-pro", 
        "gemini-pro",
        "gemini-1.0-pro",
        "gemini-1.5-flash-8b-001",
        "gemini-1.5-flash-002", 
        "gemini-1.5-pro-002",
        "gemini-1.0-pro-002",
    ]
    
    for model_name in fallback_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            logger.info(f"Trying fallback model: {model_name}")
            
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)
            
            if resp.status_code == 200:
                data = resp.json()
                answer = (
                    (data.get("candidates") or [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text")
                )
                if answer:
                    logger.info(f"✅ Success with fallback model: {model_name}")
                    return {"answer": answer}
            elif resp.status_code == 429:
                detail = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                logger.warning(f"⏳ Fallback {model_name}: Quota exceeded - trying next model")
                continue
            else:
                detail = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                logger.warning(f"❌ Fallback model {model_name} failed: {resp.status_code} {detail}")
                continue
                
        except Exception as e:
            logger.warning(f"Fallback model {model_name} error: {str(e)}")
            continue
    
    # If all models failed due to quota, return helpful message
    logger.error("All Gemini models failed - likely quota exceeded")
    return {"answer": "I'm currently experiencing high demand and have temporarily reached my response limits. Please try again in a few minutes! In the meantime, feel free to explore our destinations, hotels, and flights. How can I help you plan your perfect trip? 🌍✈️"}


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
    # Get port and host from environment
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

