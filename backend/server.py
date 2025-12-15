from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
PDF_GENERATION_DISABLED = True  # Disable PDF generation due to dependency issues
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Generator, Dict
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
import asyncio

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

# =============================
# Encryption Utility (AES-256-GCM)
# =============================
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a key for demo purposes (store this in .env for production)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    logging.warning("No ENCRYPTION_KEY found in .env, using generated key (not persistent!)")

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_field(plain_text: str) -> str:
    """Encrypt sensitive field using Fernet (AES-128 CBC + HMAC)"""
    if not plain_text:
        return ""
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_field(encrypted_text: str) -> str:
    """Decrypt sensitive field"""
    if not encrypted_text:
        return ""
    try:
        return fernet.decrypt(encrypted_text.encode()).decode()
    except Exception:
        return ""

def hash_id_number(id_number: str, user_id: str) -> str:
    """Hash ID number with user-specific salt"""
    salt = f"{user_id}_wanderlite_salt"
    return hashlib.sha256(f"{id_number}{salt}".encode()).hexdigest()

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

# =============================
# WebSocket Connection Manager for Real-Time Notifications
# =============================
class ConnectionManager:
    def __init__(self):
        # Maps user_id to list of WebSocket connections (user can have multiple tabs)
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logging.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logging.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send notification to a specific user"""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logging.warning(f"Failed to send to user {user_id}: {e}")
                    disconnected.append(connection)
            # Clean up disconnected connections
            for conn in disconnected:
                self.active_connections[user_id].remove(conn)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast notification to all connected users"""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)
    
    def get_connected_users(self) -> List[str]:
        """Get list of connected user IDs"""
        return list(self.active_connections.keys())

notification_manager = ConnectionManager()

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
    # KYC & Payment flags
    is_kyc_completed = Column(Integer, default=0)
    payment_profile_completed = Column(Integer, default=0)


class KYCDetailsModel(Base):
    __tablename__ = "kyc_details"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    dob = Column(String(20), nullable=False)  # YYYY-MM-DD
    gender = Column(String(20), nullable=False)  # male / female / other
    nationality = Column(String(100), nullable=False)
    id_type = Column(String(50), nullable=False)  # aadhaar / passport / voterid
    id_number_hash = Column(String(255), nullable=False)  # hashed ID number
    id_proof_front_path = Column(String(500), nullable=True)
    id_proof_back_path = Column(String(500), nullable=True)
    selfie_path = Column(String(500), nullable=True)
    address_line = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    pincode = Column(String(20), nullable=False)
    verification_status = Column(String(20), default="pending")  # pending / verified / rejected
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)


class PaymentProfileModel(Base):
    __tablename__ = "payment_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, index=True, nullable=False)
    account_holder_name = Column(String(255), nullable=False)
    bank_name = Column(String(255), nullable=False)
    account_number_encrypted = Column(Text, nullable=False)  # AES-256-GCM encrypted
    ifsc_encrypted = Column(Text, nullable=False)
    upi_encrypted = Column(Text, nullable=True)  # optional
    default_method = Column(String(20), default="bank")  # bank / upi
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)


class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    booking_id = Column(String(36), index=True, nullable=True)  # reference to service_bookings
    service_type = Column(String(30), nullable=True)  # flight / hotel / restaurant
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    payment_method = Column(String(50), nullable=False)  # saved_bank / saved_upi / one_time_card / one_time_upi
    status = Column(String(20), default="success")  # success / failed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


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


# =============================
# Admin Panel Database Models
# =============================
class AdminModel(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), default="support")  # super_admin / support
    is_active = Column(Integer, default=1)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(36), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), default="info")  # info / warning / success / error
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DestinationModel(Base):
    __tablename__ = "destinations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # beach / hill / city / heritage / adventure
    country = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)


class PlatformSettingModel(Base):
    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# =============================
# Bus Booking Database Models
# =============================
class BusCityModel(Base):
    __tablename__ = "bus_cities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BusRouteModel(Base):
    __tablename__ = "bus_routes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_city_id = Column(Integer, ForeignKey("bus_cities.id"), nullable=False)
    to_city_id = Column(Integer, ForeignKey("bus_cities.id"), nullable=False)
    distance_km = Column(Float, nullable=True)
    estimated_duration_mins = Column(Integer, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BusOperatorModel(Base):
    __tablename__ = "bus_operators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    logo_url = Column(String(500), nullable=True)
    rating = Column(Float, default=4.0)
    total_reviews = Column(Integer, default=0)
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    cancellation_policy = Column(Text, nullable=True)
    amenities = Column(Text, nullable=True)  # JSON: wifi, charging, water, blanket, etc.
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BusModel(Base):
    __tablename__ = "buses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operator_id = Column(Integer, ForeignKey("bus_operators.id"), nullable=False)
    bus_number = Column(String(50), nullable=False)
    bus_type = Column(String(50), nullable=False)  # AC Sleeper, Non-AC Seater, AC Seater, etc.
    total_seats = Column(Integer, nullable=False)
    seat_layout = Column(String(20), default="2+2")  # 2+2, 2+1, sleeper
    has_upper_deck = Column(Integer, default=0)
    amenities = Column(Text, nullable=True)  # JSON array
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BusScheduleModel(Base):
    __tablename__ = "bus_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    route_id = Column(Integer, ForeignKey("bus_routes.id"), nullable=False)
    departure_time = Column(String(10), nullable=False)  # HH:MM format
    arrival_time = Column(String(10), nullable=False)    # HH:MM format
    duration_mins = Column(Integer, nullable=True)
    days_of_week = Column(String(50), default="0,1,2,3,4,5,6")  # 0=Monday, 6=Sunday
    base_price = Column(Float, nullable=False)
    is_night_bus = Column(Integer, default=0)
    next_day_arrival = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BusSeatModel(Base):
    __tablename__ = "bus_seats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    seat_number = Column(String(10), nullable=False)  # L1, L2, U1, U2, 1A, 1B, etc.
    seat_type = Column(String(20), default="seater")  # seater, sleeper, semi-sleeper
    deck = Column(String(10), default="lower")  # lower, upper
    row_number = Column(Integer, nullable=True)
    column_number = Column(Integer, nullable=True)
    position = Column(String(20), default="window")  # window, aisle, middle
    price_modifier = Column(Float, default=0)  # Extra charge for premium seats
    is_female_only = Column(Integer, default=0)
    is_active = Column(Integer, default=1)


class BusBoardingPointModel(Base):
    __tablename__ = "bus_boarding_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("bus_schedules.id"), nullable=False)
    city_id = Column(Integer, ForeignKey("bus_cities.id"), nullable=False)
    point_name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    time = Column(String(10), nullable=False)  # HH:MM
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    point_type = Column(String(20), default="boarding")  # boarding, dropping
    is_active = Column(Integer, default=1)


class BusBookingModel(Base):
    __tablename__ = "bus_bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    schedule_id = Column(Integer, ForeignKey("bus_schedules.id"), nullable=False)
    journey_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    pnr = Column(String(20), unique=True, nullable=False)
    booking_status = Column(String(30), default="pending")  # pending, confirmed, cancelled, completed
    total_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0)
    final_amount = Column(Float, nullable=False)
    payment_status = Column(String(30), default="pending")  # pending, paid, refunded
    payment_method = Column(String(30), nullable=True)
    transaction_id = Column(String(100), nullable=True)
    boarding_point_id = Column(Integer, ForeignKey("bus_boarding_points.id"), nullable=True)
    dropping_point_id = Column(Integer, ForeignKey("bus_boarding_points.id"), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    refund_amount = Column(Float, nullable=True)
    refund_status = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)


class BusPassengerModel(Base):
    __tablename__ = "bus_passengers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    booking_id = Column(String(36), ForeignKey("bus_bookings.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("bus_seats.id"), nullable=False)
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)  # male, female, other
    id_type = Column(String(50), nullable=True)  # aadhaar, passport, etc.
    id_number = Column(String(100), nullable=True)
    seat_price = Column(Float, nullable=False)


class BusSeatAvailabilityModel(Base):
    __tablename__ = "bus_seat_availability"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("bus_schedules.id"), nullable=False)
    seat_id = Column(Integer, ForeignKey("bus_seats.id"), nullable=False)
    journey_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    status = Column(String(20), default="available")  # available, booked, locked, blocked
    locked_by = Column(String(36), nullable=True)  # user_id who locked
    locked_until = Column(DateTime(timezone=True), nullable=True)
    booking_id = Column(String(36), ForeignKey("bus_bookings.id"), nullable=True)


class BusLiveTrackingModel(Base):
    __tablename__ = "bus_live_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("bus_schedules.id"), nullable=False)
    journey_date = Column(String(20), nullable=False)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    speed_kmph = Column(Float, nullable=True)
    status = Column(String(30), default="not_started")  # not_started, departed, en_route, arrived
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    eta_mins = Column(Integer, nullable=True)


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
    is_kyc_completed: Optional[int] = 0
    payment_profile_completed: Optional[int] = 0


class KYCSubmit(BaseModel):
    full_name: str
    dob: str  # YYYY-MM-DD
    gender: str  # male / female / other
    nationality: str
    id_type: str  # aadhaar / passport / voterid
    id_number: str  # will be hashed
    address_line: str
    city: str
    state: str
    country: str
    pincode: str
    # File URLs handled separately via multipart upload


class KYCStatus(BaseModel):
    is_completed: bool
    verification_status: Optional[str] = None  # pending / verified / rejected
    full_name: Optional[str] = None
    created_at: Optional[datetime] = None


class PaymentProfileSubmit(BaseModel):
    account_holder_name: str
    bank_name: str
    account_number: str  # will be encrypted
    ifsc: str  # will be encrypted
    upi: Optional[str] = None  # will be encrypted
    default_method: str = "bank"  # bank / upi


class PaymentProfileStatus(BaseModel):
    is_completed: bool
    is_payment_profile_completed: Optional[bool] = False
    account_holder_name: Optional[str] = None
    bank_name: Optional[str] = None
    account_last_4: Optional[str] = None  # masked
    default_method: Optional[str] = None
    created_at: Optional[datetime] = None


class TransactionRecord(BaseModel):
    id: str
    booking_id: Optional[str] = None
    service_type: Optional[str] = None
    amount: float
    currency: str


class MockPaymentRequest(BaseModel):
    booking_id: str
    service_type: Optional[str] = None
    amount: float
    currency: str = "INR"
    payment_method: Optional[str] = None


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


# =============================
# Admin Panel Pydantic Schemas
# =============================
class AdminLogin(BaseModel):
    email: str
    password: str


class AdminToken(BaseModel):
    access_token: str
    token_type: str
    admin: dict


class AdminPublic(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime


class AdminCreate(BaseModel):
    email: str
    username: str
    password: str
    role: str = "support"


class AdminPasswordChange(BaseModel):
    current_password: str
    new_password: str


class DashboardStats(BaseModel):
    total_users: int
    total_bookings: int
    total_revenue: float
    pending_kyc: int
    active_trips: int
    recent_bookings: List[dict] = []
    bookings_by_day: List[dict] = []
    revenue_by_month: List[dict] = []
    top_destinations: List[dict] = []


class UserListItem(BaseModel):
    id: str
    email: str
    username: str
    name: Optional[str] = None
    phone: Optional[str] = None
    is_kyc_completed: int
    is_blocked: Optional[int] = 0
    created_at: datetime


class UserDetail(BaseModel):
    id: str
    email: str
    username: str
    name: Optional[str] = None
    phone: Optional[str] = None
    is_kyc_completed: int
    payment_profile_completed: int
    is_blocked: Optional[int] = 0
    created_at: datetime
    kyc_details: Optional[dict] = None
    bookings: List[dict] = []
    transactions: List[dict] = []


class KYCReviewItem(BaseModel):
    id: int
    user_id: str
    user_email: str
    user_name: str
    full_name: str
    id_type: str
    verification_status: str
    submitted_at: Optional[datetime] = None
    created_at: datetime


class KYCReviewAction(BaseModel):
    action: str  # approve / reject
    reason: Optional[str] = None


class BookingListItem(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    service_type: str
    booking_ref: str
    total_price: float
    currency: str
    status: str
    created_at: datetime


class TransactionListItem(BaseModel):
    id: int
    user_id: str
    user_email: Optional[str] = None
    booking_id: Optional[str] = None
    service_type: Optional[str] = None
    amount: float
    currency: str
    payment_method: str
    status: str
    created_at: datetime


class DestinationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: int = 1


class DestinationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: Optional[int] = None


class NotificationCreate(BaseModel):
    user_id: Optional[str] = None  # None = all users
    title: str
    message: str
    notification_type: str = "info"


class PlatformSettingUpdate(BaseModel):
    maintenance_mode: Optional[bool] = None
    bookings_enabled: Optional[bool] = None
    new_user_registration: Optional[bool] = None


class AuditLogItem(BaseModel):
    id: int
    admin_id: Optional[int] = None
    admin_email: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime


# =============================
# Bus Booking Pydantic Schemas
# =============================
class BusCityCreate(BaseModel):
    name: str
    state: Optional[str] = None
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class BusCityResponse(BaseModel):
    id: int
    name: str
    state: Optional[str] = None
    country: str
    is_active: int


class BusOperatorCreate(BaseModel):
    name: str
    logo_url: Optional[str] = None
    rating: float = 4.0
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    cancellation_policy: Optional[str] = None
    amenities: Optional[str] = None  # JSON string


class BusRouteCreate(BaseModel):
    from_city_id: int
    to_city_id: int
    distance_km: Optional[float] = None
    estimated_duration_mins: Optional[int] = None


class BusCreate(BaseModel):
    operator_id: int
    bus_number: str
    bus_type: str
    total_seats: int
    seat_layout: str = "2+2"
    has_upper_deck: int = 0
    amenities: Optional[str] = None


class BusScheduleCreate(BaseModel):
    bus_id: int
    route_id: int
    departure_time: str
    arrival_time: str
    duration_mins: Optional[int] = None
    days_of_week: str = "0,1,2,3,4,5,6"
    base_price: float
    is_night_bus: int = 0
    next_day_arrival: int = 0


class BusBoardingPointCreate(BaseModel):
    schedule_id: int
    city_id: int
    point_name: str
    address: Optional[str] = None
    time: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    point_type: str = "boarding"


class BusSearchRequest(BaseModel):
    from_city_id: int
    to_city_id: int
    journey_date: str  # YYYY-MM-DD
    return_date: Optional[str] = None


class BusSeatSelection(BaseModel):
    seat_id: int
    schedule_id: int
    journey_date: str


class BusSeatLockRequest(BaseModel):
    schedule_id: int
    journey_date: str
    seat_ids: List[int]


class BusPassengerInfo(BaseModel):
    seat_id: int
    name: str
    age: int
    gender: str
    id_type: Optional[str] = None
    id_number: Optional[str] = None


class BusBookingCreate(BaseModel):
    schedule_id: int
    journey_date: str
    passengers: List[BusPassengerInfo]
    boarding_point_id: int
    dropping_point_id: int
    contact_name: str
    contact_email: str
    contact_phone: str
    payment_method: str = "mock"


class BusTicketResponse(BaseModel):
    id: str
    pnr: str
    booking_status: str
    journey_date: str
    total_amount: float
    final_amount: float
    payment_status: str
    operator_name: str
    bus_type: str
    bus_number: str
    from_city: str
    to_city: str
    departure_time: str
    arrival_time: str
    boarding_point: str
    boarding_time: str
    dropping_point: str
    dropping_time: str
    passengers: List[dict]
    amenities: List[str]
    cancellation_policy: str
    created_at: datetime


class BusCancellationRequest(BaseModel):
    booking_id: str
    reason: Optional[str] = None


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
            is_kyc_completed=row.is_kyc_completed,
            payment_profile_completed=row.payment_profile_completed,
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


# =============================
# KYC Endpoints
# =============================
@api_router.post("/kyc")
async def submit_kyc(
    full_name: str = Form(...),
    dob: str = Form(...),
    gender: str = Form(...),
    nationality: str = Form(...),
    id_type: str = Form(...),
    id_number: str = Form(...),
    address_line: str = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    country: str = Form(...),
    pincode: str = Form(...),
    id_proof_front: Optional[UploadFile] = File(None),
    id_proof_back: Optional[UploadFile] = File(None),
    selfie: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit KYC details with optional file uploads"""
    
    # Check if KYC already exists
    existing = db.query(KYCDetailsModel).filter(KYCDetailsModel.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="KYC already submitted")
    
    # Hash ID number with user-specific salt
    id_hash = hash_id_number(id_number, current_user.id)
    
    # Handle file uploads
    id_front_path = None
    id_back_path = None
    selfie_path_var = None
    
    uploads_dir = ROOT_DIR / "uploads" / "kyc" / str(current_user.id)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    if id_proof_front:
        front_path = uploads_dir / f"id_front_{uuid.uuid4().hex[:8]}.jpg"
        with open(front_path, "wb") as f:
            f.write(await id_proof_front.read())
        id_front_path = f"/uploads/kyc/{current_user.id}/{front_path.name}"
    
    if id_proof_back:
        back_path = uploads_dir / f"id_back_{uuid.uuid4().hex[:8]}.jpg"
        with open(back_path, "wb") as f:
            f.write(await id_proof_back.read())
        id_back_path = f"/uploads/kyc/{current_user.id}/{back_path.name}"
    
    if selfie:
        selfie_file = uploads_dir / f"selfie_{uuid.uuid4().hex[:8]}.jpg"
        with open(selfie_file, "wb") as f:
            f.write(await selfie.read())
        selfie_path_var = f"/uploads/kyc/{current_user.id}/{selfie_file.name}"
    
    # Create KYC record (pending admin verification)
    kyc_record = KYCDetailsModel(
        user_id=current_user.id,
        full_name=full_name,
        dob=dob,
        gender=gender,
        nationality=nationality,
        id_type=id_type,
        id_number_hash=id_hash,
        id_proof_front_path=id_front_path,
        id_proof_back_path=id_back_path,
        selfie_path=selfie_path_var,
        address_line=address_line,
        city=city,
        state=state,
        country=country,
        pincode=pincode,
        verification_status="pending",  # Requires admin verification
        submitted_at=datetime.now(timezone.utc),
        verified_at=None,  # Will be set when admin approves
        created_at=datetime.now(timezone.utc)
    )
    db.add(kyc_record)
    
    # Note: is_kyc_completed will be set to 1 only when admin approves
    
    db.commit()
    
    return {
        "message": "KYC submitted successfully. Pending admin verification.",
        "status": "pending",
        "is_kyc_completed": False
    }


@api_router.get("/kyc/status", response_model=KYCStatus)
async def get_kyc_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get KYC verification status"""
    kyc = db.query(KYCDetailsModel).filter(KYCDetailsModel.user_id == current_user.id).first()
    
    if not kyc:
        return KYCStatus(is_completed=False)
    
    return KYCStatus(
        is_completed=True,
        verification_status=kyc.verification_status,
        full_name=kyc.full_name,
        created_at=kyc.created_at
    )


# =============================
# Payment Profile Endpoints
# =============================
@api_router.post("/payment-profile")
async def submit_payment_profile(
    profile: PaymentProfileSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit payment profile with encrypted bank details"""
    
    # Check if profile already exists
    existing = db.query(PaymentProfileModel).filter(PaymentProfileModel.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Payment profile already exists")
    
    # Encrypt sensitive fields
    account_encrypted = encrypt_field(profile.account_number)
    ifsc_encrypted = encrypt_field(profile.ifsc)
    upi_encrypted = encrypt_field(profile.upi) if profile.upi else None
    
    # Create payment profile
    payment_profile = PaymentProfileModel(
        user_id=current_user.id,
        account_holder_name=profile.account_holder_name,
        bank_name=profile.bank_name,
        account_number_encrypted=account_encrypted,
        ifsc_encrypted=ifsc_encrypted,
        upi_encrypted=upi_encrypted,
        default_method=profile.default_method,
        created_at=datetime.now(timezone.utc)
    )
    db.add(payment_profile)
    
    # Update user payment profile flag
    user_row = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if user_row:
        user_row.payment_profile_completed = 1
    
    db.commit()
    
    return {
        "message": "Payment profile saved successfully",
        "is_payment_profile_completed": True
    }


@api_router.get("/payment-profile/status", response_model=PaymentProfileStatus)
async def get_payment_profile_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get payment profile status (never return decrypted data)"""
    profile = db.query(PaymentProfileModel).filter(PaymentProfileModel.user_id == current_user.id).first()
    
    if not profile:
        return PaymentProfileStatus(is_completed=False, is_payment_profile_completed=False)
    
    # Decrypt only to get last 4 digits for display
    account_number = decrypt_field(profile.account_number_encrypted)
    last_4 = account_number[-4:] if len(account_number) >= 4 else "****"
    
    return PaymentProfileStatus(
        is_completed=True,
        is_payment_profile_completed=True,
        account_holder_name=profile.account_holder_name,
        bank_name=profile.bank_name,
        account_last_4=last_4,
        default_method=profile.default_method,
        created_at=profile.created_at
    )


# =============================
# Mock Payment Endpoint
# =============================
@api_router.post("/payments/mock")
async def mock_payment(
    request: MockPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Simulate payment processing (always succeeds for demo)"""
    
    # Get booking details
    booking = db.query(ServiceBookingModel).filter(ServiceBookingModel.id == request.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Determine payment method
    payment_method = request.payment_method
    if not payment_method:
        # Check if user has payment profile
        profile = db.query(PaymentProfileModel).filter(PaymentProfileModel.user_id == current_user.id).first()
        if profile:
            payment_method = f"saved_{profile.default_method}"
        else:
            payment_method = "one_time_card"
    
    # Create transaction record
    transaction = TransactionModel(
        user_id=current_user.id,
        booking_id=request.booking_id,
        service_type=request.service_type or booking.service_type,
        amount=request.amount,
        currency=request.currency,
        payment_method=payment_method,
        status="success",
        created_at=datetime.now(timezone.utc)
    )
    db.add(transaction)
    
    # Update booking status to paid
    booking.status = "Paid"
    
    db.commit()
    
    return {
        "transaction_id": transaction.id,
        "status": "completed",
        "payment_method": payment_method,
        "amount": request.amount,
        "currency": request.currency
    }


# =============================
# Transactions History
# =============================
@api_router.get("/transactions", response_model=List[TransactionRecord])
async def get_transactions(
    service_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user transaction history with optional filtering"""
    query = db.query(TransactionModel).filter(TransactionModel.user_id == current_user.id)
    
    if service_type:
        query = query.filter(TransactionModel.service_type == service_type)
    
    transactions = query.order_by(TransactionModel.created_at.desc()).all()
    
    return [
        TransactionRecord(
            id=t.id,
            booking_id=t.booking_id,
            service_type=t.service_type,
            amount=t.amount,
            currency=t.currency,
            payment_method=t.payment_method,
            status=t.status,
            created_at=t.created_at
        )
        for t in transactions
    ]


# =============================
# User Notifications
# =============================
@api_router.get("/notifications")
async def get_user_notifications(
    page: int = 1,
    limit: int = 20,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notifications for the current user"""
    query = db.query(NotificationModel).filter(NotificationModel.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(NotificationModel.is_read == 0)
    
    total = query.count()
    notifications = query.order_by(NotificationModel.created_at.desc()).offset((page-1)*limit).limit(limit).all()
    
    return {
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.notification_type,
                "is_read": bool(n.is_read),
                "created_at": n.created_at.isoformat() if n.created_at else None
            } for n in notifications
        ],
        "total": total,
        "unread_count": db.query(NotificationModel).filter(
            NotificationModel.user_id == current_user.id,
            NotificationModel.is_read == 0
        ).count()
    }


@api_router.get("/notifications/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications"""
    count = db.query(NotificationModel).filter(
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_read == 0
    ).count()
    return {"unread_count": count}


@api_router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read"""
    notification = db.query(NotificationModel).filter(
        NotificationModel.id == notification_id,
        NotificationModel.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = 1
    db.commit()
    return {"message": "Notification marked as read"}


@api_router.post("/notifications/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    db.query(NotificationModel).filter(
        NotificationModel.user_id == current_user.id,
        NotificationModel.is_read == 0
    ).update({NotificationModel.is_read: 1})
    db.commit()
    return {"message": "All notifications marked as read"}


@api_router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a notification"""
    notification = db.query(NotificationModel).filter(
        NotificationModel.id == notification_id,
        NotificationModel.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    return {"message": "Notification deleted"}


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
            # Fetch city details from OpenTripMap with timeout (2 seconds)
            geoname_data = {}
            try:
                geoname_url = f"https://api.opentripmap.com/0.1/en/places/geoname?name={city['name']}"
                geoname_response = requests.get(geoname_url, timeout=2)
                geoname_data = geoname_response.json() if geoname_response.status_code == 200 else {}
            except (requests.Timeout, requests.ConnectionError):
                pass  # Skip external API on timeout, use defaults

            # Fetch nearby attractions with timeout (2 seconds)
            attractions = []
            try:
                radius_url = f"https://api.opentripmap.com/0.1/en/places/radius?radius=5000&lon={city['lon']}&lat={city['lat']}&kinds=museums,historical_places,natural,beaches,urban_environment&limit=5"
                radius_response = requests.get(radius_url, timeout=2)
                if radius_response.status_code == 200:
                    places_data = radius_response.json()
                    attractions = [feature["properties"]["name"] for feature in places_data.get("features", []) if "properties" in feature and "name" in feature["properties"]]
            except (requests.Timeout, requests.ConnectionError):
                pass  # Skip external API on timeout

            # Fetch real weather data with timeout (2 seconds)
            weather_api_key = os.environ.get('OPENWEATHER_API_KEY')
            weather = {"temp": 25, "condition": "Sunny", "humidity": 60}  # Default mock
            if weather_api_key:
                try:
                    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city['name']}&appid={weather_api_key}&units=metric"
                    weather_response = requests.get(weather_url, timeout=2)
                    if weather_response.status_code == 200:
                        weather_data = weather_response.json()
                        weather = {
                            "temp": weather_data["main"]["temp"],
                            "condition": weather_data["weather"][0]["description"],
                            "humidity": weather_data["main"]["humidity"]
                        }
                except (requests.Timeout, requests.ConnectionError):
                    pass  # Use default mock on timeout

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
    """Create a new service booking (flight/hotel/restaurant) with KYC check"""
    db: Session = next(get_db())
    
    # Check if KYC is completed
    user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not user or not user.is_kyc_completed:
        raise HTTPException(
            status_code=403,
            detail="Please complete KYC verification before booking"
        )
    
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
            # Add is_blocked column if missing
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0"))
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Schema migration checks failed: {e}")
    logger.info("Database tables created/verified successfully")


# =============================
# ADMIN PANEL API ROUTES
# =============================
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

ADMIN_SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'admin-super-secret-key-2025')


def create_admin_token(admin_id: int, email: str, role: str) -> str:
    """Create JWT token for admin"""
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    payload = {
        "sub": str(admin_id),
        "email": email,
        "role": role,
        "scope": "admin",
        "exp": expire
    }
    return jwt.encode(payload, ADMIN_SECRET_KEY, algorithm=ALGORITHM)


def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify admin JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, ADMIN_SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "admin":
            raise HTTPException(status_code=403, detail="Not an admin token")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")


async def get_current_admin(
    token_data: dict = Depends(verify_admin_token),
    db: Session = Depends(get_db)
) -> AdminModel:
    """Get current admin from token"""
    admin = db.query(AdminModel).filter(AdminModel.id == int(token_data["sub"])).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin not found or inactive")
    return admin


def log_admin_action(db: Session, admin_id: int, action: str, entity_type: str = None, 
                     entity_id: str = None, details: str = None, ip_address: str = None):
    """Log admin action for audit trail"""
    log = AuditLogModel(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address
    )
    db.add(log)
    db.commit()


# =============================
# Admin Authentication
# =============================
@admin_router.post("/login", response_model=AdminToken)
async def admin_login(credentials: AdminLogin, db: Session = Depends(get_db)):
    """Admin login - separate from user login"""
    admin = db.query(AdminModel).filter(AdminModel.email == credentials.email).first()
    
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not pwd_context.verify(credentials.password, admin.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Admin account is disabled")
    
    # Update last login
    admin.last_login = datetime.now(timezone.utc)
    db.commit()
    
    token = create_admin_token(admin.id, admin.email, admin.role)
    
    return AdminToken(
        access_token=token,
        token_type="bearer",
        admin={
            "id": admin.id,
            "email": admin.email,
            "username": admin.username,
            "role": admin.role
        }
    )


@admin_router.get("/me", response_model=AdminPublic)
async def get_admin_profile(admin: AdminModel = Depends(get_current_admin)):
    """Get current admin profile"""
    return AdminPublic(
        id=admin.id,
        email=admin.email,
        username=admin.username,
        role=admin.role,
        is_active=bool(admin.is_active),
        last_login=admin.last_login,
        created_at=admin.created_at
    )


@admin_router.post("/change-password")
async def admin_change_password(
    data: AdminPasswordChange,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Change admin password"""
    if not pwd_context.verify(data.current_password, admin.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    admin.hashed_password = pwd_context.hash(data.new_password)
    admin.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    log_admin_action(db, admin.id, "password_change", "admin", str(admin.id))
    
    return {"message": "Password changed successfully"}


# =============================
# Dashboard Statistics
# =============================
@admin_router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    # Total users
    total_users = db.query(UserModel).count()
    
    # Total bookings (service + regular)
    service_bookings = db.query(ServiceBookingModel).count()
    regular_bookings = db.query(BookingModel).count()
    total_bookings = service_bookings + regular_bookings
    
    # Total revenue (from transactions)
    total_revenue = db.query(TransactionModel).filter(
        TransactionModel.status == "success"
    ).with_entities(
        text("COALESCE(SUM(amount), 0)")
    ).scalar() or 0
    
    # Pending KYC
    pending_kyc = db.query(KYCDetailsModel).filter(
        KYCDetailsModel.verification_status == "pending"
    ).count()
    
    # Active trips
    active_trips = db.query(TripModel).count()
    
    # Recent bookings
    recent_bookings = db.query(ServiceBookingModel).order_by(
        ServiceBookingModel.created_at.desc()
    ).limit(5).all()
    
    recent_bookings_data = []
    for b in recent_bookings:
        user = db.query(UserModel).filter(UserModel.id == b.user_id).first()
        recent_bookings_data.append({
            "id": b.id,
            "booking_ref": b.booking_ref,
            "service_type": b.service_type,
            "total_price": b.total_price,
            "status": b.status,
            "user_email": user.email if user else "N/A",
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    
    # Bookings by day (last 7 days)
    # For SQLite compatibility
    bookings_by_day = []
    for i in range(7):
        from datetime import date as dt_date
        day = datetime.now(timezone.utc).date() - timedelta(days=6-i)
        count = db.query(ServiceBookingModel).filter(
            text(f"DATE(created_at) = '{day}'")
        ).count()
        bookings_by_day.append({
            "date": day.isoformat(),
            "count": count
        })
    
    # Top destinations
    top_destinations = []
    try:
        destinations = db.query(DestinationModel).filter(
            DestinationModel.is_active == 1
        ).limit(5).all()
        for d in destinations:
            top_destinations.append({
                "name": d.name,
                "category": d.category,
                "bookings": 0  # Would need to join with bookings
            })
    except:
        pass
    
    return DashboardStats(
        total_users=total_users,
        total_bookings=total_bookings,
        total_revenue=float(total_revenue),
        pending_kyc=pending_kyc,
        active_trips=active_trips,
        recent_bookings=recent_bookings_data,
        bookings_by_day=bookings_by_day,
        revenue_by_month=[],
        top_destinations=top_destinations
    )


# =============================
# User Management
# =============================
@admin_router.get("/users", response_model=List[UserListItem])
async def list_users(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    kyc_status: Optional[str] = None,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all users with filtering"""
    query = db.query(UserModel)
    
    if search:
        query = query.filter(
            (UserModel.email.contains(search)) | 
            (UserModel.username.contains(search)) |
            (UserModel.name.contains(search))
        )
    
    if kyc_status == "completed":
        query = query.filter(UserModel.is_kyc_completed == 1)
    elif kyc_status == "pending":
        query = query.filter(UserModel.is_kyc_completed == 0)
    
    users = query.order_by(UserModel.created_at.desc()).offset((page-1)*limit).limit(limit).all()
    
    return [
        UserListItem(
            id=u.id,
            email=u.email,
            username=u.username,
            name=u.name,
            phone=u.phone,
            is_kyc_completed=u.is_kyc_completed or 0,
            is_blocked=getattr(u, 'is_blocked', 0) or 0,
            created_at=u.created_at
        ) for u in users
    ]


@admin_router.get("/users/{user_id}", response_model=UserDetail)
async def get_user_detail(
    user_id: str,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed user information"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get KYC details
    kyc = db.query(KYCDetailsModel).filter(KYCDetailsModel.user_id == user_id).first()
    kyc_data = None
    if kyc:
        kyc_data = {
            "id": kyc.id,
            "full_name": kyc.full_name,
            "dob": kyc.dob,
            "gender": kyc.gender,
            "nationality": kyc.nationality,
            "id_type": kyc.id_type,
            "address": f"{kyc.address_line}, {kyc.city}, {kyc.state}, {kyc.country} - {kyc.pincode}",
            "verification_status": kyc.verification_status,
            "submitted_at": kyc.submitted_at.isoformat() if kyc.submitted_at else None,
            "id_proof_front": kyc.id_proof_front_path,
            "id_proof_back": kyc.id_proof_back_path,
            "selfie": kyc.selfie_path
        }
    
    # Get bookings
    bookings = db.query(ServiceBookingModel).filter(
        ServiceBookingModel.user_id == user_id
    ).order_by(ServiceBookingModel.created_at.desc()).limit(10).all()
    
    bookings_data = [
        {
            "id": b.id,
            "booking_ref": b.booking_ref,
            "service_type": b.service_type,
            "total_price": b.total_price,
            "status": b.status,
            "created_at": b.created_at.isoformat() if b.created_at else None
        } for b in bookings
    ]
    
    # Get transactions
    transactions = db.query(TransactionModel).filter(
        TransactionModel.user_id == user_id
    ).order_by(TransactionModel.created_at.desc()).limit(10).all()
    
    transactions_data = [
        {
            "id": t.id,
            "amount": t.amount,
            "currency": t.currency,
            "payment_method": t.payment_method,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None
        } for t in transactions
    ]
    
    return UserDetail(
        id=user.id,
        email=user.email,
        username=user.username,
        name=user.name,
        phone=user.phone,
        is_kyc_completed=user.is_kyc_completed or 0,
        payment_profile_completed=user.payment_profile_completed or 0,
        is_blocked=getattr(user, 'is_blocked', 0) or 0,
        created_at=user.created_at,
        kyc_details=kyc_data,
        bookings=bookings_data,
        transactions=transactions_data
    )


@admin_router.post("/users/{user_id}/block")
async def block_user(
    user_id: str,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Block a user"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Use raw SQL for SQLite compatibility
    db.execute(text(f"UPDATE users SET is_blocked = 1 WHERE id = '{user_id}'"))
    db.commit()
    
    log_admin_action(db, admin.id, "block_user", "user", user_id, f"Blocked user {user.email}")
    
    return {"message": f"User {user.email} has been blocked"}


@admin_router.post("/users/{user_id}/unblock")
async def unblock_user(
    user_id: str,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Unblock a user"""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.execute(text(f"UPDATE users SET is_blocked = 0 WHERE id = '{user_id}'"))
    db.commit()
    
    log_admin_action(db, admin.id, "unblock_user", "user", user_id, f"Unblocked user {user.email}")
    
    return {"message": f"User {user.email} has been unblocked"}


# =============================
# KYC Verification Management
# =============================
@admin_router.get("/kyc/counts")
async def get_kyc_counts(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get counts of KYC requests by status"""
    pending_count = db.query(KYCDetailsModel).filter(KYCDetailsModel.verification_status == "pending").count()
    verified_count = db.query(KYCDetailsModel).filter(KYCDetailsModel.verification_status == "verified").count()
    rejected_count = db.query(KYCDetailsModel).filter(KYCDetailsModel.verification_status == "rejected").count()
    
    return {
        "pending": pending_count,
        "verified": verified_count,
        "rejected": rejected_count
    }


@admin_router.get("/kyc", response_model=List[KYCReviewItem])
async def list_kyc_requests(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List KYC verification requests"""
    query = db.query(KYCDetailsModel)
    
    if status:
        query = query.filter(KYCDetailsModel.verification_status == status)
    
    kyc_list = query.order_by(KYCDetailsModel.created_at.desc()).offset((page-1)*limit).limit(limit).all()
    
    result = []
    for kyc in kyc_list:
        user = db.query(UserModel).filter(UserModel.id == kyc.user_id).first()
        result.append(KYCReviewItem(
            id=kyc.id,
            user_id=kyc.user_id,
            user_email=user.email if user else "N/A",
            user_name=user.username if user else "N/A",
            full_name=kyc.full_name,
            id_type=kyc.id_type,
            verification_status=kyc.verification_status,
            submitted_at=kyc.submitted_at,
            created_at=kyc.created_at
        ))
    
    return result


@admin_router.get("/kyc/{kyc_id}")
async def get_kyc_detail(
    kyc_id: int,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed KYC information for review"""
    kyc = db.query(KYCDetailsModel).filter(KYCDetailsModel.id == kyc_id).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")
    
    user = db.query(UserModel).filter(UserModel.id == kyc.user_id).first()
    
    return {
        "id": kyc.id,
        "user_id": kyc.user_id,
        "user_email": user.email if user else "N/A",
        "user_name": user.username if user else "N/A",
        "full_name": kyc.full_name,
        "dob": kyc.dob,
        "gender": kyc.gender,
        "nationality": kyc.nationality,
        "id_type": kyc.id_type,
        "address_line": kyc.address_line,
        "city": kyc.city,
        "state": kyc.state,
        "country": kyc.country,
        "pincode": kyc.pincode,
        "verification_status": kyc.verification_status,
        "id_proof_front_path": kyc.id_proof_front_path,
        "id_proof_back_path": kyc.id_proof_back_path,
        "selfie_path": kyc.selfie_path,
        "submitted_at": kyc.submitted_at.isoformat() if kyc.submitted_at else None,
        "verified_at": kyc.verified_at.isoformat() if kyc.verified_at else None,
        "created_at": kyc.created_at.isoformat() if kyc.created_at else None
    }


@admin_router.post("/kyc/{kyc_id}/review")
async def review_kyc(
    kyc_id: int,
    action: KYCReviewAction,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Approve or reject KYC"""
    kyc = db.query(KYCDetailsModel).filter(KYCDetailsModel.id == kyc_id).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")
    
    if action.action == "approve":
        kyc.verification_status = "verified"
        kyc.verified_at = datetime.now(timezone.utc)
        
        # Update user KYC status
        user = db.query(UserModel).filter(UserModel.id == kyc.user_id).first()
        if user:
            user.is_kyc_completed = 1
        
        log_admin_action(db, admin.id, "approve_kyc", "kyc", str(kyc_id), f"Approved KYC for user {kyc.user_id}")
        
    elif action.action == "reject":
        kyc.verification_status = "rejected"
        log_admin_action(db, admin.id, "reject_kyc", "kyc", str(kyc_id), f"Rejected KYC for user {kyc.user_id}: {action.reason}")
    
    kyc.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": f"KYC {action.action}d successfully"}


# =============================
# Booking Management
# =============================
@admin_router.get("/bookings", response_model=List[BookingListItem])
async def list_bookings(
    service_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all bookings"""
    query = db.query(ServiceBookingModel)
    
    if service_type:
        query = query.filter(ServiceBookingModel.service_type == service_type)
    if status:
        query = query.filter(ServiceBookingModel.status == status)
    
    bookings = query.order_by(ServiceBookingModel.created_at.desc()).offset((page-1)*limit).limit(limit).all()
    
    result = []
    for b in bookings:
        user = db.query(UserModel).filter(UserModel.id == b.user_id).first() if b.user_id else None
        result.append(BookingListItem(
            id=b.id,
            user_id=b.user_id,
            user_email=user.email if user else "Guest",
            service_type=b.service_type,
            booking_ref=b.booking_ref,
            total_price=b.total_price,
            currency=b.currency,
            status=b.status,
            created_at=b.created_at
        ))
    
    return result


@admin_router.get("/bookings/{booking_id}")
async def get_booking_detail(
    booking_id: str,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed booking information"""
    booking = db.query(ServiceBookingModel).filter(ServiceBookingModel.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    user = db.query(UserModel).filter(UserModel.id == booking.user_id).first() if booking.user_id else None
    
    # Parse service JSON
    service_details = {}
    try:
        service_details = json.loads(booking.service_json)
    except:
        pass
    
    # Get related receipt
    receipt = db.query(PaymentReceiptModel).filter(
        PaymentReceiptModel.booking_ref == booking.booking_ref
    ).first()
    
    return {
        "id": booking.id,
        "user_id": booking.user_id,
        "user_email": user.email if user else "Guest",
        "service_type": booking.service_type,
        "booking_ref": booking.booking_ref,
        "total_price": booking.total_price,
        "currency": booking.currency,
        "status": booking.status,
        "service_details": service_details,
        "receipt_url": receipt.receipt_url if receipt else None,
        "created_at": booking.created_at.isoformat() if booking.created_at else None
    }


@admin_router.post("/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status: str,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update booking status"""
    booking = db.query(ServiceBookingModel).filter(ServiceBookingModel.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    old_status = booking.status
    booking.status = status
    db.commit()
    
    log_admin_action(db, admin.id, "update_booking_status", "booking", booking_id, 
                     f"Changed status from {old_status} to {status}")
    
    return {"message": f"Booking status updated to {status}"}


@admin_router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: str,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cancel a booking"""
    booking = db.query(ServiceBookingModel).filter(ServiceBookingModel.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking.status = "Cancelled"
    db.commit()
    
    log_admin_action(db, admin.id, "cancel_booking", "booking", booking_id, 
                     f"Cancelled booking {booking.booking_ref}")
    
    return {"message": "Booking cancelled successfully"}


# =============================
# Transaction Management
# =============================
@admin_router.get("/transactions", response_model=List[TransactionListItem])
async def list_transactions(
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all transactions"""
    query = db.query(TransactionModel)
    
    if status:
        query = query.filter(TransactionModel.status == status)
    if payment_method:
        query = query.filter(TransactionModel.payment_method.contains(payment_method))
    
    transactions = query.order_by(TransactionModel.created_at.desc()).offset((page-1)*limit).limit(limit).all()
    
    result = []
    for t in transactions:
        user = db.query(UserModel).filter(UserModel.id == t.user_id).first()
        result.append(TransactionListItem(
            id=t.id,
            user_id=t.user_id,
            user_email=user.email if user else "N/A",
            booking_id=t.booking_id,
            service_type=t.service_type,
            amount=t.amount,
            currency=t.currency,
            payment_method=t.payment_method,
            status=t.status,
            created_at=t.created_at
        ))
    
    return result


# =============================
# Destination Management (CRUD)
# =============================
@admin_router.get("/destinations")
async def list_destinations(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all destinations"""
    destinations = db.query(DestinationModel).order_by(DestinationModel.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "category": d.category,
            "country": d.country,
            "state": d.state,
            "city": d.city,
            "image_url": d.image_url,
            "is_active": d.is_active,
            "created_at": d.created_at.isoformat() if d.created_at else None
        } for d in destinations
    ]


@admin_router.post("/destinations")
async def create_destination(
    data: DestinationCreate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new destination"""
    destination = DestinationModel(
        name=data.name,
        description=data.description,
        category=data.category,
        country=data.country,
        state=data.state,
        city=data.city,
        image_url=data.image_url,
        latitude=data.latitude,
        longitude=data.longitude,
        is_active=data.is_active
    )
    db.add(destination)
    db.commit()
    db.refresh(destination)
    
    log_admin_action(db, admin.id, "create_destination", "destination", str(destination.id), 
                     f"Created destination: {data.name}")
    
    return {"message": "Destination created", "id": destination.id}


@admin_router.put("/destinations/{dest_id}")
async def update_destination(
    dest_id: int,
    data: DestinationUpdate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a destination"""
    destination = db.query(DestinationModel).filter(DestinationModel.id == dest_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if data.name is not None:
        destination.name = data.name
    if data.description is not None:
        destination.description = data.description
    if data.category is not None:
        destination.category = data.category
    if data.country is not None:
        destination.country = data.country
    if data.state is not None:
        destination.state = data.state
    if data.city is not None:
        destination.city = data.city
    if data.image_url is not None:
        destination.image_url = data.image_url
    if data.latitude is not None:
        destination.latitude = data.latitude
    if data.longitude is not None:
        destination.longitude = data.longitude
    if data.is_active is not None:
        destination.is_active = data.is_active
    
    destination.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    log_admin_action(db, admin.id, "update_destination", "destination", str(dest_id), 
                     f"Updated destination: {destination.name}")
    
    return {"message": "Destination updated"}


@admin_router.delete("/destinations/{dest_id}")
async def delete_destination(
    dest_id: int,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a destination"""
    destination = db.query(DestinationModel).filter(DestinationModel.id == dest_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    name = destination.name
    db.delete(destination)
    db.commit()
    
    log_admin_action(db, admin.id, "delete_destination", "destination", str(dest_id), 
                     f"Deleted destination: {name}")
    
    return {"message": "Destination deleted"}


# =============================
# Notifications Management
# =============================
@admin_router.post("/notifications")
async def send_notification(
    data: NotificationCreate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Send notification to users"""
    notification_data = {
        "type": "notification",
        "title": data.title,
        "message": data.message,
        "notification_type": data.notification_type,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if data.user_id:
        # Send to specific user
        notification = NotificationModel(
            user_id=data.user_id,
            admin_id=admin.id,
            title=data.title,
            message=data.message,
            notification_type=data.notification_type
        )
        db.add(notification)
        db.commit()
        
        # Send real-time notification via WebSocket
        notification_data["id"] = notification.id
        await notification_manager.send_to_user(data.user_id, notification_data)
        count = 1
    else:
        # Send to all users
        users = db.query(UserModel).all()
        count = 0
        user_ids = []
        for user in users:
            notification = NotificationModel(
                user_id=user.id,
                admin_id=admin.id,
                title=data.title,
                message=data.message,
                notification_type=data.notification_type
            )
            db.add(notification)
            user_ids.append(user.id)
            count += 1
        
        db.commit()
        
        # Broadcast to all connected users
        await notification_manager.broadcast_to_all(notification_data)
    
    log_admin_action(db, admin.id, "send_notification", "notification", None, 
                     f"Sent notification to {count} user(s): {data.title}")
    
    return {"message": f"Notification sent to {count} user(s)"}


@admin_router.get("/notifications")
async def list_notifications(
    page: int = 1,
    limit: int = 50,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List sent notifications"""
    notifications = db.query(NotificationModel).order_by(
        NotificationModel.created_at.desc()
    ).offset((page-1)*limit).limit(limit).all()
    
    return [
        {
            "id": n.id,
            "user_id": n.user_id,
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        } for n in notifications
    ]


# =============================
# Reports & Logs
# =============================
@admin_router.get("/reports/bookings")
async def booking_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get booking report"""
    query = db.query(ServiceBookingModel)
    
    if start_date:
        query = query.filter(ServiceBookingModel.created_at >= start_date)
    if end_date:
        query = query.filter(ServiceBookingModel.created_at <= end_date)
    
    total = query.count()
    by_type = {}
    by_status = {}
    total_revenue = 0
    
    bookings = query.all()
    for b in bookings:
        by_type[b.service_type] = by_type.get(b.service_type, 0) + 1
        by_status[b.status] = by_status.get(b.status, 0) + 1
        if b.status in ["Confirmed", "Paid", "Completed"]:
            total_revenue += b.total_price
    
    return {
        "total_bookings": total,
        "by_service_type": by_type,
        "by_status": by_status,
        "total_revenue": total_revenue
    }


@admin_router.get("/reports/users")
async def user_report(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get user growth report"""
    total_users = db.query(UserModel).count()
    kyc_completed = db.query(UserModel).filter(UserModel.is_kyc_completed == 1).count()
    
    # Users by month (last 6 months)
    users_by_month = []
    for i in range(6):
        month_start = datetime.now(timezone.utc).replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)
        count = db.query(UserModel).filter(
            UserModel.created_at >= month_start,
            UserModel.created_at < month_end
        ).count()
        users_by_month.append({
            "month": month_start.strftime("%Y-%m"),
            "count": count
        })
    
    return {
        "total_users": total_users,
        "kyc_completed": kyc_completed,
        "kyc_pending": total_users - kyc_completed,
        "users_by_month": list(reversed(users_by_month))
    }


@admin_router.get("/audit-logs", response_model=List[AuditLogItem])
async def get_audit_logs(
    page: int = 1,
    limit: int = 50,
    action: Optional[str] = None,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get admin audit logs"""
    query = db.query(AuditLogModel)
    
    if action:
        query = query.filter(AuditLogModel.action.contains(action))
    
    logs = query.order_by(AuditLogModel.created_at.desc()).offset((page-1)*limit).limit(limit).all()
    
    result = []
    for log in logs:
        admin_user = db.query(AdminModel).filter(AdminModel.id == log.admin_id).first() if log.admin_id else None
        result.append(AuditLogItem(
            id=log.id,
            admin_id=log.admin_id,
            admin_email=admin_user.email if admin_user else "System",
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at
        ))
    
    return result


# =============================
# Platform Settings
# =============================
@admin_router.get("/settings")
async def get_platform_settings(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get platform settings"""
    settings = db.query(PlatformSettingModel).all()
    return {s.setting_key: s.setting_value for s in settings}


@admin_router.put("/settings")
async def update_platform_settings(
    data: PlatformSettingUpdate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update platform settings"""
    if data.maintenance_mode is not None:
        setting = db.query(PlatformSettingModel).filter(
            PlatformSettingModel.setting_key == "maintenance_mode"
        ).first()
        if setting:
            setting.setting_value = str(data.maintenance_mode).lower()
            setting.updated_by = admin.id
            setting.updated_at = datetime.now(timezone.utc)
    
    if data.bookings_enabled is not None:
        setting = db.query(PlatformSettingModel).filter(
            PlatformSettingModel.setting_key == "bookings_enabled"
        ).first()
        if setting:
            setting.setting_value = str(data.bookings_enabled).lower()
            setting.updated_by = admin.id
            setting.updated_at = datetime.now(timezone.utc)
    
    if data.new_user_registration is not None:
        setting = db.query(PlatformSettingModel).filter(
            PlatformSettingModel.setting_key == "new_user_registration"
        ).first()
        if setting:
            setting.setting_value = str(data.new_user_registration).lower()
            setting.updated_by = admin.id
            setting.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    log_admin_action(db, admin.id, "update_settings", "settings", None, "Updated platform settings")
    
    return {"message": "Settings updated"}


# =============================
# Receipts & Tickets
# =============================
@admin_router.get("/receipts")
async def list_receipts(
    page: int = 1,
    limit: int = 20,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all payment receipts"""
    receipts = db.query(PaymentReceiptModel).order_by(
        PaymentReceiptModel.created_at.desc()
    ).offset((page-1)*limit).limit(limit).all()
    
    return [
        {
            "id": r.id,
            "booking_ref": r.booking_ref,
            "full_name": r.full_name,
            "email": r.email,
            "amount": r.amount,
            "payment_method": r.payment_method,
            "receipt_url": r.receipt_url,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in receipts
    ]


# =============================
# Bus Booking API Router
# =============================
bus_router = APIRouter(prefix="/api/bus", tags=["bus"])


def generate_pnr():
    """Generate a unique PNR number"""
    import random
    import string
    prefix = "WL"
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}{chars}"


# Cities endpoints
@bus_router.get("/cities")
async def get_bus_cities(
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of bus cities"""
    query = db.query(BusCityModel).filter(BusCityModel.is_active == 1)
    if search:
        query = query.filter(BusCityModel.name.ilike(f"%{search}%"))
    cities = query.order_by(BusCityModel.name).all()
    return [{"id": c.id, "name": c.name, "state": c.state} for c in cities]


# Search buses
@bus_router.post("/search")
async def search_buses(
    request: BusSearchRequest,
    db: Session = Depends(get_db)
):
    """Search available buses for a route and date"""
    # Find the route
    route = db.query(BusRouteModel).filter(
        BusRouteModel.from_city_id == request.from_city_id,
        BusRouteModel.to_city_id == request.to_city_id,
        BusRouteModel.is_active == 1
    ).first()
    
    if not route:
        return {"buses": [], "message": "No routes found"}
    
    # Get day of week (0=Monday, 6=Sunday) for Python, but also check 1-7 format
    from datetime import datetime as dt
    journey_dt = dt.strptime(request.journey_date, "%Y-%m-%d")
    day_of_week = journey_dt.weekday()  # 0-6
    day_of_week_1based = day_of_week + 1  # 1-7 format
    
    # Find schedules for this route on the selected day (check both formats)
    schedules = db.query(BusScheduleModel).filter(
        BusScheduleModel.route_id == route.id,
        BusScheduleModel.is_active == 1
    ).filter(
        (BusScheduleModel.days_of_week.contains(str(day_of_week))) | 
        (BusScheduleModel.days_of_week.contains(str(day_of_week_1based)))
    ).all()
    
    results = []
    from_city = db.query(BusCityModel).filter(BusCityModel.id == request.from_city_id).first()
    to_city = db.query(BusCityModel).filter(BusCityModel.id == request.to_city_id).first()
    
    for schedule in schedules:
        bus = db.query(BusModel).filter(BusModel.id == schedule.bus_id).first()
        operator = db.query(BusOperatorModel).filter(BusOperatorModel.id == bus.operator_id).first()
        
        # Count available seats
        total_seats = db.query(BusSeatModel).filter(BusSeatModel.bus_id == bus.id, BusSeatModel.is_active == 1).count()
        booked_seats = db.query(BusSeatAvailabilityModel).filter(
            BusSeatAvailabilityModel.schedule_id == schedule.id,
            BusSeatAvailabilityModel.journey_date == request.journey_date,
            BusSeatAvailabilityModel.status.in_(["booked", "locked"])
        ).count()
        available_seats = total_seats - booked_seats
        
        # Get boarding points
        boarding_points = db.query(BusBoardingPointModel).filter(
            BusBoardingPointModel.schedule_id == schedule.id,
            BusBoardingPointModel.point_type == "boarding",
            BusBoardingPointModel.is_active == 1
        ).all()
        
        dropping_points = db.query(BusBoardingPointModel).filter(
            BusBoardingPointModel.schedule_id == schedule.id,
            BusBoardingPointModel.point_type == "dropping",
            BusBoardingPointModel.is_active == 1
        ).all()
        
        results.append({
            "schedule_id": schedule.id,
            "bus_id": bus.id,
            "operator_name": operator.name,
            "operator_logo": operator.logo_url,
            "operator_rating": operator.rating,
            "bus_type": bus.bus_type,
            "bus_number": bus.bus_number,
            "seat_layout": bus.seat_layout,
            "has_upper_deck": bus.has_upper_deck,
            "departure_time": schedule.departure_time,
            "arrival_time": schedule.arrival_time,
            "duration_mins": schedule.duration_mins,
            "is_night_bus": schedule.is_night_bus,
            "next_day_arrival": schedule.next_day_arrival,
            "base_price": schedule.base_price,
            "available_seats": available_seats,
            "total_seats": total_seats,
            "amenities": json.loads(bus.amenities) if bus.amenities else [],
            "cancellation_policy": operator.cancellation_policy,
            "boarding_points": [{"id": bp.id, "name": bp.point_name, "time": bp.time, "address": bp.address} for bp in boarding_points],
            "dropping_points": [{"id": dp.id, "name": dp.point_name, "time": dp.time, "address": dp.address} for dp in dropping_points],
            "from_city": from_city.name if from_city else "",
            "to_city": to_city.name if to_city else ""
        })
    
    return {"buses": results, "total": len(results)}


# Get seat layout for a bus
@bus_router.get("/seats/{schedule_id}/{journey_date}")
async def get_seat_layout(
    schedule_id: int,
    journey_date: str,
    db: Session = Depends(get_db)
):
    """Get seat layout and availability for a schedule"""
    try:
        schedule = db.query(BusScheduleModel).filter(BusScheduleModel.id == schedule_id).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        bus = db.query(BusModel).filter(BusModel.id == schedule.bus_id).first()
        if not bus:
            raise HTTPException(status_code=404, detail="Bus not found")
            
        seats = db.query(BusSeatModel).filter(BusSeatModel.bus_id == bus.id, BusSeatModel.is_active == 1).all()
        
        seat_data = []
        for seat in seats:
            # Check availability
            availability = db.query(BusSeatAvailabilityModel).filter(
                BusSeatAvailabilityModel.schedule_id == schedule_id,
                BusSeatAvailabilityModel.seat_id == seat.id,
                BusSeatAvailabilityModel.journey_date == journey_date
            ).first()
            
            status = "available"
            if availability:
                if availability.status == "booked":
                    status = "booked"
                elif availability.status == "locked":
                    # Check if lock expired
                    if availability.locked_until:
                        # Handle both naive and aware datetimes
                        lock_time = availability.locked_until
                        now = datetime.now()
                        if lock_time.tzinfo is not None:
                            now = datetime.now(timezone.utc)
                        if lock_time > now:
                            status = "locked"
                        else:
                            status = "available"
                    else:
                        status = "available"
                elif availability.status == "blocked":
                    status = "blocked"
            
            seat_data.append({
                "id": seat.id,
                "seat_number": seat.seat_number,
                "seat_type": seat.seat_type,
                "deck": seat.deck,
                "row": seat.row_number,
                "column": seat.column_number,
                "position": seat.position,
                "price_modifier": float(seat.price_modifier) if seat.price_modifier else 0.0,
                "is_female_only": seat.is_female_only,
                "status": status,
                "price": float(schedule.base_price) + (float(seat.price_modifier) if seat.price_modifier else 0.0)
            })
        
        return {
            "bus_type": bus.bus_type,
            "seat_layout": bus.seat_layout,
            "has_upper_deck": bus.has_upper_deck,
            "total_seats": len(seats),
            "base_price": float(schedule.base_price),
            "seats": seat_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_seat_layout: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Lock seats temporarily
@bus_router.post("/seats/lock")
async def lock_seats(
    request: BusSeatLockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Temporarily lock selected seats for 5 minutes"""
    locked_seats = []
    lock_until = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    for seat_id in request.seat_ids:
        # Check if seat is available
        existing = db.query(BusSeatAvailabilityModel).filter(
            BusSeatAvailabilityModel.schedule_id == request.schedule_id,
            BusSeatAvailabilityModel.seat_id == seat_id,
            BusSeatAvailabilityModel.journey_date == request.journey_date
        ).first()
        
        if existing:
            if existing.status == "booked":
                raise HTTPException(status_code=400, detail=f"Seat already booked")
            elif existing.status == "locked" and existing.locked_until > datetime.now(timezone.utc):
                if existing.locked_by != current_user.id:
                    raise HTTPException(status_code=400, detail=f"Seat is temporarily unavailable")
            # Update lock
            existing.status = "locked"
            existing.locked_by = current_user.id
            existing.locked_until = lock_until
        else:
            # Create new lock
            availability = BusSeatAvailabilityModel(
                schedule_id=request.schedule_id,
                seat_id=seat_id,
                journey_date=request.journey_date,
                status="locked",
                locked_by=current_user.id,
                locked_until=lock_until
            )
            db.add(availability)
        
        locked_seats.append(seat_id)
    
    db.commit()
    return {"locked_seats": locked_seats, "expires_at": lock_until.isoformat()}


# Create booking
@bus_router.post("/book")
async def create_bus_booking(
    booking: BusBookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a bus booking"""
    schedule = db.query(BusScheduleModel).filter(BusScheduleModel.id == booking.schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    bus = db.query(BusModel).filter(BusModel.id == schedule.bus_id).first()
    operator = db.query(BusOperatorModel).filter(BusOperatorModel.id == bus.operator_id).first()
    route = db.query(BusRouteModel).filter(BusRouteModel.id == schedule.route_id).first()
    
    # Calculate total amount
    total_amount = 0
    for passenger in booking.passengers:
        seat = db.query(BusSeatModel).filter(BusSeatModel.id == passenger.seat_id).first()
        if not seat:
            raise HTTPException(status_code=400, detail=f"Invalid seat ID: {passenger.seat_id}")
        seat_price = schedule.base_price + seat.price_modifier
        total_amount += seat_price
    
    # Generate PNR
    pnr = generate_pnr()
    
    # Create booking
    new_booking = BusBookingModel(
        user_id=current_user.id,
        schedule_id=booking.schedule_id,
        journey_date=booking.journey_date,
        pnr=pnr,
        booking_status="confirmed",
        total_amount=total_amount,
        discount_amount=0,
        final_amount=total_amount,
        payment_status="paid",  # Mock payment
        payment_method=booking.payment_method,
        transaction_id=f"TXN{uuid.uuid4().hex[:12].upper()}",
        boarding_point_id=booking.boarding_point_id,
        dropping_point_id=booking.dropping_point_id,
        contact_name=booking.contact_name,
        contact_email=booking.contact_email,
        contact_phone=booking.contact_phone
    )
    db.add(new_booking)
    db.flush()
    
    # Create passengers and mark seats as booked
    for passenger in booking.passengers:
        seat = db.query(BusSeatModel).filter(BusSeatModel.id == passenger.seat_id).first()
        seat_price = schedule.base_price + seat.price_modifier
        
        # Create passenger record
        new_passenger = BusPassengerModel(
            booking_id=new_booking.id,
            seat_id=passenger.seat_id,
            name=passenger.name,
            age=passenger.age,
            gender=passenger.gender,
            id_type=passenger.id_type,
            id_number=passenger.id_number,
            seat_price=seat_price
        )
        db.add(new_passenger)
        
        # Update seat availability
        availability = db.query(BusSeatAvailabilityModel).filter(
            BusSeatAvailabilityModel.schedule_id == booking.schedule_id,
            BusSeatAvailabilityModel.seat_id == passenger.seat_id,
            BusSeatAvailabilityModel.journey_date == booking.journey_date
        ).first()
        
        if availability:
            availability.status = "booked"
            availability.booking_id = new_booking.id
            availability.locked_by = None
            availability.locked_until = None
        else:
            new_availability = BusSeatAvailabilityModel(
                schedule_id=booking.schedule_id,
                seat_id=passenger.seat_id,
                journey_date=booking.journey_date,
                status="booked",
                booking_id=new_booking.id
            )
            db.add(new_availability)
    
    db.commit()
    
    return {"booking_id": new_booking.id, "pnr": pnr, "message": "Booking confirmed"}


# Get booking details / ticket
@bus_router.get("/booking/{booking_id}")
async def get_bus_booking(
    booking_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get bus booking details"""
    booking = db.query(BusBookingModel).filter(
        BusBookingModel.id == booking_id,
        BusBookingModel.user_id == current_user.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    schedule = db.query(BusScheduleModel).filter(BusScheduleModel.id == booking.schedule_id).first()
    bus = db.query(BusModel).filter(BusModel.id == schedule.bus_id).first()
    operator = db.query(BusOperatorModel).filter(BusOperatorModel.id == bus.operator_id).first()
    route = db.query(BusRouteModel).filter(BusRouteModel.id == schedule.route_id).first()
    from_city = db.query(BusCityModel).filter(BusCityModel.id == route.from_city_id).first()
    to_city = db.query(BusCityModel).filter(BusCityModel.id == route.to_city_id).first()
    
    boarding_point = db.query(BusBoardingPointModel).filter(BusBoardingPointModel.id == booking.boarding_point_id).first()
    dropping_point = db.query(BusBoardingPointModel).filter(BusBoardingPointModel.id == booking.dropping_point_id).first()
    
    passengers = db.query(BusPassengerModel).filter(BusPassengerModel.booking_id == booking.id).all()
    passenger_list = []
    for p in passengers:
        seat = db.query(BusSeatModel).filter(BusSeatModel.id == p.seat_id).first()
        passenger_list.append({
            "name": p.name,
            "age": p.age,
            "gender": p.gender,
            "seat_number": seat.seat_number if seat else "",
            "seat_type": seat.seat_type if seat else "",
            "seat_price": p.seat_price
        })
    
    return {
        "id": booking.id,
        "pnr": booking.pnr,
        "booking_status": booking.booking_status,
        "journey_date": booking.journey_date,
        "total_amount": booking.total_amount,
        "discount_amount": booking.discount_amount,
        "final_amount": booking.final_amount,
        "payment_status": booking.payment_status,
        "payment_method": booking.payment_method,
        "transaction_id": booking.transaction_id,
        "operator_name": operator.name,
        "operator_logo": operator.logo_url,
        "operator_rating": operator.rating,
        "bus_type": bus.bus_type,
        "bus_number": bus.bus_number,
        "from_city": from_city.name,
        "to_city": to_city.name,
        "departure_time": schedule.departure_time,
        "arrival_time": schedule.arrival_time,
        "duration_mins": schedule.duration_mins,
        "is_night_bus": schedule.is_night_bus,
        "next_day_arrival": schedule.next_day_arrival,
        "boarding_point": boarding_point.point_name if boarding_point else "",
        "boarding_time": boarding_point.time if boarding_point else "",
        "boarding_address": boarding_point.address if boarding_point else "",
        "dropping_point": dropping_point.point_name if dropping_point else "",
        "dropping_time": dropping_point.time if dropping_point else "",
        "dropping_address": dropping_point.address if dropping_point else "",
        "passengers": passenger_list,
        "contact_name": booking.contact_name,
        "contact_email": booking.contact_email,
        "contact_phone": booking.contact_phone,
        "amenities": json.loads(bus.amenities) if bus.amenities else [],
        "cancellation_policy": operator.cancellation_policy,
        "created_at": booking.created_at.isoformat() if booking.created_at else None
    }


# Get user's bus bookings
@bus_router.get("/my-bookings")
async def get_my_bus_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bus bookings for current user"""
    bookings = db.query(BusBookingModel).filter(
        BusBookingModel.user_id == current_user.id
    ).order_by(BusBookingModel.created_at.desc()).all()
    
    results = []
    for booking in bookings:
        schedule = db.query(BusScheduleModel).filter(BusScheduleModel.id == booking.schedule_id).first()
        bus = db.query(BusModel).filter(BusModel.id == schedule.bus_id).first()
        operator = db.query(BusOperatorModel).filter(BusOperatorModel.id == bus.operator_id).first()
        route = db.query(BusRouteModel).filter(BusRouteModel.id == schedule.route_id).first()
        from_city = db.query(BusCityModel).filter(BusCityModel.id == route.from_city_id).first()
        to_city = db.query(BusCityModel).filter(BusCityModel.id == route.to_city_id).first()
        
        passengers = db.query(BusPassengerModel).filter(BusPassengerModel.booking_id == booking.id).all()
        
        results.append({
            "id": booking.id,
            "pnr": booking.pnr,
            "booking_status": booking.booking_status,
            "journey_date": booking.journey_date,
            "final_amount": booking.final_amount,
            "operator_name": operator.name,
            "bus_type": bus.bus_type,
            "from_city": from_city.name,
            "to_city": to_city.name,
            "departure_time": schedule.departure_time,
            "passenger_count": len(passengers),
            "created_at": booking.created_at.isoformat() if booking.created_at else None
        })
    
    return results


# Cancel booking
@bus_router.post("/cancel")
async def cancel_bus_booking(
    request: BusCancellationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a bus booking"""
    booking = db.query(BusBookingModel).filter(
        BusBookingModel.id == request.booking_id,
        BusBookingModel.user_id == current_user.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.booking_status == "cancelled":
        raise HTTPException(status_code=400, detail="Booking already cancelled")
    
    if booking.booking_status == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel completed journey")
    
    schedule = db.query(BusScheduleModel).filter(BusScheduleModel.id == booking.schedule_id).first()
    
    # Calculate refund based on time before departure
    from datetime import datetime as dt
    journey_dt = dt.strptime(f"{booking.journey_date} {schedule.departure_time}", "%Y-%m-%d %H:%M")
    now = dt.now()
    hours_before = (journey_dt - now).total_seconds() / 3600
    
    refund_percentage = 0
    if hours_before > 24:
        refund_percentage = 90
    elif hours_before > 12:
        refund_percentage = 50
    elif hours_before > 6:
        refund_percentage = 25
    # No refund if less than 6 hours
    
    refund_amount = (booking.final_amount * refund_percentage) / 100
    
    # Update booking
    booking.booking_status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.refund_amount = refund_amount
    booking.refund_status = "processed" if refund_amount > 0 else "no_refund"
    
    # Release seats
    passengers = db.query(BusPassengerModel).filter(BusPassengerModel.booking_id == booking.id).all()
    for passenger in passengers:
        availability = db.query(BusSeatAvailabilityModel).filter(
            BusSeatAvailabilityModel.booking_id == booking.id,
            BusSeatAvailabilityModel.seat_id == passenger.seat_id
        ).first()
        if availability:
            db.delete(availability)
    
    db.commit()
    
    return {
        "message": "Booking cancelled",
        "refund_percentage": refund_percentage,
        "refund_amount": refund_amount,
        "refund_status": booking.refund_status
    }


# Get live tracking
@bus_router.get("/tracking/{booking_id}")
async def get_bus_tracking(
    booking_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get live tracking for a booked bus"""
    booking = db.query(BusBookingModel).filter(
        BusBookingModel.id == booking_id,
        BusBookingModel.user_id == current_user.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.booking_status != "confirmed":
        raise HTTPException(status_code=400, detail="Tracking only available for confirmed bookings")
    
    tracking = db.query(BusLiveTrackingModel).filter(
        BusLiveTrackingModel.schedule_id == booking.schedule_id,
        BusLiveTrackingModel.journey_date == booking.journey_date
    ).first()
    
    if not tracking:
        return {
            "status": "not_started",
            "message": "Bus tracking will be available once the journey starts"
        }
    
    return {
        "status": tracking.status,
        "latitude": tracking.current_latitude,
        "longitude": tracking.current_longitude,
        "speed_kmph": tracking.speed_kmph,
        "eta_mins": tracking.eta_mins,
        "last_updated": tracking.last_updated.isoformat() if tracking.last_updated else None
    }


# Register bus router
app.include_router(bus_router)


# =============================
# Admin Bus Management Endpoints
# =============================
@admin_router.get("/bus/cities")
async def admin_get_cities(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all bus cities"""
    cities = db.query(BusCityModel).order_by(BusCityModel.name).all()
    return [{"id": c.id, "name": c.name, "state": c.state, "is_active": c.is_active} for c in cities]


@admin_router.post("/bus/cities")
async def admin_create_city(
    city: BusCityCreate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new bus city"""
    new_city = BusCityModel(
        name=city.name,
        state=city.state,
        country=city.country,
        latitude=city.latitude,
        longitude=city.longitude
    )
    db.add(new_city)
    db.commit()
    return {"id": new_city.id, "message": "City created"}


@admin_router.get("/bus/operators")
async def admin_get_operators(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all bus operators"""
    operators = db.query(BusOperatorModel).order_by(BusOperatorModel.name).all()
    return [{
        "id": o.id,
        "name": o.name,
        "rating": o.rating,
        "is_active": o.is_active,
        "contact_phone": o.contact_phone,
        "contact_email": o.contact_email
    } for o in operators]


@admin_router.post("/bus/operators")
async def admin_create_operator(
    operator: BusOperatorCreate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new bus operator"""
    new_operator = BusOperatorModel(
        name=operator.name,
        logo_url=operator.logo_url,
        rating=operator.rating,
        contact_phone=operator.contact_phone,
        contact_email=operator.contact_email,
        cancellation_policy=operator.cancellation_policy,
        amenities=operator.amenities
    )
    db.add(new_operator)
    db.commit()
    return {"id": new_operator.id, "message": "Operator created"}


@admin_router.get("/bus/routes")
async def admin_get_routes(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all bus routes"""
    routes = db.query(BusRouteModel).all()
    result = []
    for r in routes:
        from_city = db.query(BusCityModel).filter(BusCityModel.id == r.from_city_id).first()
        to_city = db.query(BusCityModel).filter(BusCityModel.id == r.to_city_id).first()
        result.append({
            "id": r.id,
            "from_city_id": r.from_city_id,
            "from_city": from_city.name if from_city else "",
            "to_city_id": r.to_city_id,
            "to_city": to_city.name if to_city else "",
            "distance_km": r.distance_km,
            "is_active": r.is_active
        })
    return result


@admin_router.post("/bus/routes")
async def admin_create_route(
    route: BusRouteCreate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new bus route"""
    new_route = BusRouteModel(
        from_city_id=route.from_city_id,
        to_city_id=route.to_city_id,
        distance_km=route.distance_km,
        estimated_duration_mins=route.estimated_duration_mins
    )
    db.add(new_route)
    db.commit()
    return {"id": new_route.id, "message": "Route created"}


@admin_router.get("/bus/buses")
async def admin_get_buses(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all buses"""
    buses = db.query(BusModel).all()
    result = []
    for b in buses:
        operator = db.query(BusOperatorModel).filter(BusOperatorModel.id == b.operator_id).first()
        result.append({
            "id": b.id,
            "operator_id": b.operator_id,
            "operator_name": operator.name if operator else "",
            "bus_number": b.bus_number,
            "bus_type": b.bus_type,
            "total_seats": b.total_seats,
            "seat_layout": b.seat_layout,
            "is_active": b.is_active
        })
    return result


@admin_router.post("/bus/buses")
async def admin_create_bus(
    bus: BusCreate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new bus with seat layout"""
    new_bus = BusModel(
        operator_id=bus.operator_id,
        bus_number=bus.bus_number,
        bus_type=bus.bus_type,
        total_seats=bus.total_seats,
        seat_layout=bus.seat_layout,
        has_upper_deck=bus.has_upper_deck,
        amenities=bus.amenities
    )
    db.add(new_bus)
    db.flush()
    
    # Generate seats based on layout
    if bus.seat_layout == "2+2":
        # Standard seater bus
        rows = (bus.total_seats + 3) // 4
        seat_num = 1
        for row in range(1, rows + 1):
            for col in range(1, 5):
                if seat_num > bus.total_seats:
                    break
                position = "window" if col in [1, 4] else "aisle"
                seat = BusSeatModel(
                    bus_id=new_bus.id,
                    seat_number=f"{row}{chr(64+col)}",
                    seat_type="seater",
                    deck="lower",
                    row_number=row,
                    column_number=col,
                    position=position
                )
                db.add(seat)
                seat_num += 1
    elif bus.seat_layout == "sleeper":
        # Sleeper bus with upper and lower deck
        lower_seats = bus.total_seats // 2
        upper_seats = bus.total_seats - lower_seats
        
        # Lower deck
        rows = (lower_seats + 1) // 2
        for row in range(1, rows + 1):
            for col in [1, 2]:
                seat = BusSeatModel(
                    bus_id=new_bus.id,
                    seat_number=f"L{row}{col}",
                    seat_type="sleeper",
                    deck="lower",
                    row_number=row,
                    column_number=col,
                    position="window" if col == 1 else "aisle"
                )
                db.add(seat)
        
        # Upper deck
        rows = (upper_seats + 1) // 2
        for row in range(1, rows + 1):
            for col in [1, 2]:
                seat = BusSeatModel(
                    bus_id=new_bus.id,
                    seat_number=f"U{row}{col}",
                    seat_type="sleeper",
                    deck="upper",
                    row_number=row,
                    column_number=col,
                    position="window" if col == 1 else "aisle",
                    price_modifier=50  # Upper deck slightly cheaper
                )
                db.add(seat)
    else:
        # Default 2+1 layout
        rows = (bus.total_seats + 2) // 3
        seat_num = 1
        for row in range(1, rows + 1):
            for col in range(1, 4):
                if seat_num > bus.total_seats:
                    break
                position = "window" if col in [1, 3] else "aisle"
                seat = BusSeatModel(
                    bus_id=new_bus.id,
                    seat_number=f"{row}{chr(64+col)}",
                    seat_type="seater",
                    deck="lower",
                    row_number=row,
                    column_number=col,
                    position=position
                )
                db.add(seat)
                seat_num += 1
    
    db.commit()
    return {"id": new_bus.id, "message": "Bus created with seats"}


@admin_router.get("/bus/schedules")
async def admin_get_schedules(
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all bus schedules"""
    schedules = db.query(BusScheduleModel).all()
    result = []
    for s in schedules:
        bus = db.query(BusModel).filter(BusModel.id == s.bus_id).first()
        route = db.query(BusRouteModel).filter(BusRouteModel.id == s.route_id).first()
        from_city = db.query(BusCityModel).filter(BusCityModel.id == route.from_city_id).first() if route else None
        to_city = db.query(BusCityModel).filter(BusCityModel.id == route.to_city_id).first() if route else None
        operator = db.query(BusOperatorModel).filter(BusOperatorModel.id == bus.operator_id).first() if bus else None
        
        result.append({
            "id": s.id,
            "bus_id": s.bus_id,
            "bus_number": bus.bus_number if bus else "",
            "operator_name": operator.name if operator else "",
            "route_id": s.route_id,
            "from_city": from_city.name if from_city else "",
            "to_city": to_city.name if to_city else "",
            "departure_time": s.departure_time,
            "arrival_time": s.arrival_time,
            "base_price": s.base_price,
            "is_night_bus": s.is_night_bus,
            "is_active": s.is_active
        })
    return result


@admin_router.post("/bus/schedules")
async def admin_create_schedule(
    schedule: BusScheduleCreate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new bus schedule"""
    new_schedule = BusScheduleModel(
        bus_id=schedule.bus_id,
        route_id=schedule.route_id,
        departure_time=schedule.departure_time,
        arrival_time=schedule.arrival_time,
        duration_mins=schedule.duration_mins,
        days_of_week=schedule.days_of_week,
        base_price=schedule.base_price,
        is_night_bus=schedule.is_night_bus,
        next_day_arrival=schedule.next_day_arrival
    )
    db.add(new_schedule)
    db.commit()
    return {"id": new_schedule.id, "message": "Schedule created"}


@admin_router.post("/bus/boarding-points")
async def admin_create_boarding_point(
    point: BusBoardingPointCreate,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a boarding/dropping point"""
    new_point = BusBoardingPointModel(
        schedule_id=point.schedule_id,
        city_id=point.city_id,
        point_name=point.point_name,
        address=point.address,
        time=point.time,
        latitude=point.latitude,
        longitude=point.longitude,
        point_type=point.point_type
    )
    db.add(new_point)
    db.commit()
    return {"id": new_point.id, "message": "Boarding point created"}


@admin_router.get("/bus/bookings")
async def admin_get_bus_bookings(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all bus bookings"""
    query = db.query(BusBookingModel)
    if status:
        query = query.filter(BusBookingModel.booking_status == status)
    
    bookings = query.order_by(BusBookingModel.created_at.desc()).offset((page-1)*limit).limit(limit).all()
    
    result = []
    for b in bookings:
        schedule = db.query(BusScheduleModel).filter(BusScheduleModel.id == b.schedule_id).first()
        bus = db.query(BusModel).filter(BusModel.id == schedule.bus_id).first() if schedule else None
        operator = db.query(BusOperatorModel).filter(BusOperatorModel.id == bus.operator_id).first() if bus else None
        passengers = db.query(BusPassengerModel).filter(BusPassengerModel.booking_id == b.id).count()
        
        result.append({
            "id": b.id,
            "pnr": b.pnr,
            "user_id": b.user_id,
            "journey_date": b.journey_date,
            "operator_name": operator.name if operator else "",
            "final_amount": b.final_amount,
            "booking_status": b.booking_status,
            "payment_status": b.payment_status,
            "passengers": passengers,
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    
    return result


# Register admin router
app.include_router(admin_router)


# =============================
# WebSocket Endpoint for Real-Time Notifications
# =============================
@app.websocket("/ws/notifications/{token}")
async def websocket_notification_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time notifications"""
    # Validate token and get user
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except JWTError as e:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Connect the WebSocket
    await notification_manager.connect(websocket, user_id)
    
    try:
        # Send initial unread count
        db = SessionLocal()
        try:
            unread_count = db.query(NotificationModel).filter(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read == 0
            ).count()
            await websocket.send_json({
                "type": "init",
                "unread_count": unread_count
            })
        finally:
            db.close()
        
        # Keep connection alive and listen for pings
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Handle ping/pong to keep connection alive
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except:
                    break
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket, user_id)
    except Exception as e:
        logging.error(f"WebSocket error for user {user_id}: {e}")
        notification_manager.disconnect(websocket, user_id)


# =============================
# Bus Data Seed Endpoint
# =============================
@app.post("/api/bus/seed", tags=["bus"])
async def seed_bus_data(db: Session = Depends(get_db)):
    """Seed initial bus data for demo purposes"""
    
    # Check if data already exists
    existing_cities = db.query(BusCityModel).count()
    if existing_cities > 0:
        return {"message": "Bus data already seeded", "cities": existing_cities}
    
    # Indian Cities with coordinates
    cities_data = [
        {"name": "Chennai", "state": "Tamil Nadu", "country": "India", "latitude": 13.0827, "longitude": 80.2707},
        {"name": "Bangalore", "state": "Karnataka", "country": "India", "latitude": 12.9716, "longitude": 77.5946},
        {"name": "Mumbai", "state": "Maharashtra", "country": "India", "latitude": 19.0760, "longitude": 72.8777},
        {"name": "Delhi", "state": "Delhi", "country": "India", "latitude": 28.7041, "longitude": 77.1025},
        {"name": "Hyderabad", "state": "Telangana", "country": "India", "latitude": 17.3850, "longitude": 78.4867},
        {"name": "Pune", "state": "Maharashtra", "country": "India", "latitude": 18.5204, "longitude": 73.8567},
        {"name": "Coimbatore", "state": "Tamil Nadu", "country": "India", "latitude": 11.0168, "longitude": 76.9558},
        {"name": "Madurai", "state": "Tamil Nadu", "country": "India", "latitude": 9.9252, "longitude": 78.1198},
        {"name": "Mysore", "state": "Karnataka", "country": "India", "latitude": 12.2958, "longitude": 76.6394},
        {"name": "Trichy", "state": "Tamil Nadu", "country": "India", "latitude": 10.7905, "longitude": 78.7047},
        {"name": "Salem", "state": "Tamil Nadu", "country": "India", "latitude": 11.6643, "longitude": 78.1460},
        {"name": "Vijayawada", "state": "Andhra Pradesh", "country": "India", "latitude": 16.5062, "longitude": 80.6480},
        {"name": "Tirupati", "state": "Andhra Pradesh", "country": "India", "latitude": 13.6288, "longitude": 79.4192},
        {"name": "Kochi", "state": "Kerala", "country": "India", "latitude": 9.9312, "longitude": 76.2673},
        {"name": "Trivandrum", "state": "Kerala", "country": "India", "latitude": 8.5241, "longitude": 76.9366},
    ]
    
    # Create cities
    city_map = {}
    for city_data in cities_data:
        city = BusCityModel(**city_data)
        db.add(city)
        db.flush()
        city_map[city_data["name"]] = city.id
    
    # Bus Operators
    operators_data = [
        {
            "name": "SRS Travels",
            "logo_url": "/images/srs-logo.png",
            "rating": 4.2,
            "cancellation_policy": "Free cancellation up to 24 hours before departure. 50% refund within 12-24 hours.",
            "amenities": "WiFi,Charging Point,Water Bottle,Blanket,Snacks"
        },
        {
            "name": "VRL Travels",
            "logo_url": "/images/vrl-logo.png",
            "rating": 4.5,
            "cancellation_policy": "90% refund if cancelled 48 hours before. 50% refund within 24-48 hours.",
            "amenities": "WiFi,Charging Point,Water Bottle,Blanket,GPS Tracking"
        },
        {
            "name": "KPN Travels",
            "logo_url": "/images/kpn-logo.png",
            "rating": 4.3,
            "cancellation_policy": "Free cancellation up to 6 hours before departure.",
            "amenities": "Charging Point,Water Bottle,Reading Light,Emergency Exit"
        },
        {
            "name": "Orange Travels",
            "logo_url": "/images/orange-logo.png",
            "rating": 4.0,
            "cancellation_policy": "75% refund up to 24 hours before departure.",
            "amenities": "WiFi,Charging Point,Blanket,TV,Snacks"
        },
        {
            "name": "KSRTC",
            "logo_url": "/images/ksrtc-logo.png",
            "rating": 3.8,
            "cancellation_policy": "No refunds for government buses.",
            "amenities": "Charging Point,Reading Light"
        },
        {
            "name": "Parveen Travels",
            "logo_url": "/images/parveen-logo.png",
            "rating": 4.4,
            "cancellation_policy": "85% refund up to 12 hours before departure.",
            "amenities": "WiFi,Charging Point,Water Bottle,Blanket,Pillow"
        }
    ]
    
    operator_map = {}
    for op_data in operators_data:
        operator = BusOperatorModel(**op_data)
        db.add(operator)
        db.flush()
        operator_map[op_data["name"]] = operator.id
    
    # Routes (one-way distances in km and time in minutes)
    routes_data = [
        {"from": "Chennai", "to": "Bangalore", "distance": 350, "duration": 360},
        {"from": "Chennai", "to": "Coimbatore", "distance": 500, "duration": 480},
        {"from": "Chennai", "to": "Madurai", "distance": 460, "duration": 450},
        {"from": "Chennai", "to": "Trichy", "distance": 320, "duration": 300},
        {"from": "Chennai", "to": "Hyderabad", "distance": 630, "duration": 600},
        {"from": "Chennai", "to": "Tirupati", "distance": 135, "duration": 180},
        {"from": "Bangalore", "to": "Chennai", "distance": 350, "duration": 360},
        {"from": "Bangalore", "to": "Mysore", "distance": 150, "duration": 180},
        {"from": "Bangalore", "to": "Hyderabad", "distance": 570, "duration": 540},
        {"from": "Bangalore", "to": "Mumbai", "distance": 980, "duration": 900},
        {"from": "Bangalore", "to": "Coimbatore", "distance": 360, "duration": 360},
        {"from": "Bangalore", "to": "Kochi", "distance": 560, "duration": 540},
        {"from": "Mumbai", "to": "Pune", "distance": 150, "duration": 180},
        {"from": "Mumbai", "to": "Bangalore", "distance": 980, "duration": 900},
        {"from": "Mumbai", "to": "Hyderabad", "distance": 710, "duration": 660},
        {"from": "Delhi", "to": "Mumbai", "distance": 1400, "duration": 1200},
        {"from": "Hyderabad", "to": "Bangalore", "distance": 570, "duration": 540},
        {"from": "Hyderabad", "to": "Vijayawada", "distance": 275, "duration": 300},
        {"from": "Coimbatore", "to": "Chennai", "distance": 500, "duration": 480},
        {"from": "Coimbatore", "to": "Kochi", "distance": 195, "duration": 240},
        {"from": "Kochi", "to": "Trivandrum", "distance": 200, "duration": 240},
    ]
    
    route_map = {}
    for route_data in routes_data:
        route = BusRouteModel(
            from_city_id=city_map[route_data["from"]],
            to_city_id=city_map[route_data["to"]],
            distance_km=route_data["distance"],
            estimated_duration_mins=route_data["duration"]
        )
        db.add(route)
        db.flush()
        route_key = f"{route_data['from']}-{route_data['to']}"
        route_map[route_key] = route.id
    
    # Buses and their seat configurations
    buses_data = [
        {"operator": "SRS Travels", "number": "TN01AB1234", "type": "Sleeper", "seats": 30, "layout": "2+1", "upper_deck": True},
        {"operator": "SRS Travels", "number": "TN01AB1235", "type": "AC Seater", "seats": 44, "layout": "2+2", "upper_deck": False},
        {"operator": "VRL Travels", "number": "KA01CD5678", "type": "AC Sleeper", "seats": 36, "layout": "2+1", "upper_deck": True},
        {"operator": "VRL Travels", "number": "KA01CD5679", "type": "Multi-Axle Volvo", "seats": 40, "layout": "2+2", "upper_deck": False},
        {"operator": "KPN Travels", "number": "TN02EF9012", "type": "Semi Sleeper", "seats": 38, "layout": "2+2", "upper_deck": False},
        {"operator": "KPN Travels", "number": "TN02EF9013", "type": "AC Sleeper", "seats": 30, "layout": "2+1", "upper_deck": True},
        {"operator": "Orange Travels", "number": "AP03GH3456", "type": "Volvo AC", "seats": 44, "layout": "2+2", "upper_deck": False},
        {"operator": "Orange Travels", "number": "AP03GH3457", "type": "Sleeper", "seats": 36, "layout": "2+1", "upper_deck": True},
        {"operator": "KSRTC", "number": "KA04IJ7890", "type": "Non AC Seater", "seats": 52, "layout": "2+3", "upper_deck": False},
        {"operator": "KSRTC", "number": "KA04IJ7891", "type": "AC Seater", "seats": 44, "layout": "2+2", "upper_deck": False},
        {"operator": "Parveen Travels", "number": "TN05KL1122", "type": "Multi-Axle AC Sleeper", "seats": 30, "layout": "2+1", "upper_deck": True},
        {"operator": "Parveen Travels", "number": "TN05KL1123", "type": "Volvo B11R", "seats": 40, "layout": "2+2", "upper_deck": False},
    ]
    
    # Helper function to generate seat layouts
    def create_bus_seats(db_session, bus_id, layout, total_seats, has_upper_deck):
        """Generate seats for a bus based on layout"""
        seats_per_row = sum(int(x) for x in layout.split('+'))
        decks = ["lower", "upper"] if has_upper_deck else ["lower"]
        seats_per_deck = total_seats // len(decks)
        rows_per_deck = max(1, seats_per_deck // seats_per_row)
        
        seat_num = 1
        for deck in decks:
            for row in range(1, rows_per_deck + 1):
                col = 1
                for section in layout.split('+'):
                    for _ in range(int(section)):
                        position = "window" if col == 1 or col == seats_per_row else "aisle"
                        
                        seat = BusSeatModel(
                            bus_id=bus_id,
                            seat_number=f"{deck[0].upper()}{seat_num}",
                            seat_type="sleeper" if has_upper_deck else "seater",
                            deck=deck,
                            row_number=row,
                            column_number=col,
                            position=position,
                            price_modifier=1.1 if position == "window" else 1.0,
                            is_female_only=row == rows_per_deck and col == 1
                        )
                        db_session.add(seat)
                        seat_num += 1
                        col += 1
    
    bus_map = {}
    for bus_data in buses_data:
        bus = BusModel(
            operator_id=operator_map[bus_data["operator"]],
            bus_number=bus_data["number"],
            bus_type=bus_data["type"],
            total_seats=bus_data["seats"],
            seat_layout=bus_data["layout"],
            has_upper_deck=bus_data["upper_deck"]
        )
        db.add(bus)
        db.flush()
        bus_map[bus_data["number"]] = bus.id
        
        # Generate seats for this bus
        create_bus_seats(db, bus.id, bus_data["layout"], bus_data["seats"], bus_data["upper_deck"])
    
    # Schedules with departure times
    schedules_data = [
        # Chennai - Bangalore (Multiple timings)
        {"bus": "TN01AB1234", "route": "Chennai-Bangalore", "dep": "21:00", "arr": "05:00", "days": "1,2,3,4,5,6,7", "price": 850, "night": True, "next_day": True},
        {"bus": "TN01AB1235", "route": "Chennai-Bangalore", "dep": "06:00", "arr": "12:00", "days": "1,2,3,4,5,6,7", "price": 650, "night": False, "next_day": False},
        {"bus": "KA01CD5678", "route": "Chennai-Bangalore", "dep": "22:30", "arr": "06:30", "days": "1,2,3,4,5,6,7", "price": 1100, "night": True, "next_day": True},
        {"bus": "KA01CD5679", "route": "Chennai-Bangalore", "dep": "08:00", "arr": "14:00", "days": "1,2,3,4,5,6,7", "price": 900, "night": False, "next_day": False},
        # Chennai - Coimbatore
        {"bus": "TN02EF9012", "route": "Chennai-Coimbatore", "dep": "21:30", "arr": "06:30", "days": "1,2,3,4,5,6,7", "price": 750, "night": True, "next_day": True},
        {"bus": "TN02EF9013", "route": "Chennai-Coimbatore", "dep": "22:00", "arr": "07:00", "days": "1,2,3,4,5,6,7", "price": 950, "night": True, "next_day": True},
        # Chennai - Hyderabad
        {"bus": "AP03GH3456", "route": "Chennai-Hyderabad", "dep": "18:00", "arr": "06:00", "days": "1,2,3,4,5,6,7", "price": 1200, "night": True, "next_day": True},
        {"bus": "AP03GH3457", "route": "Chennai-Hyderabad", "dep": "20:00", "arr": "08:00", "days": "1,2,3,4,5,6,7", "price": 1050, "night": True, "next_day": True},
        # Bangalore - Chennai
        {"bus": "TN01AB1234", "route": "Bangalore-Chennai", "dep": "21:00", "arr": "05:00", "days": "1,2,3,4,5,6,7", "price": 850, "night": True, "next_day": True},
        {"bus": "KA01CD5679", "route": "Bangalore-Chennai", "dep": "07:00", "arr": "13:00", "days": "1,2,3,4,5,6,7", "price": 900, "night": False, "next_day": False},
        # Bangalore - Mysore
        {"bus": "KA04IJ7890", "route": "Bangalore-Mysore", "dep": "06:00", "arr": "09:00", "days": "1,2,3,4,5,6,7", "price": 350, "night": False, "next_day": False},
        {"bus": "KA04IJ7891", "route": "Bangalore-Mysore", "dep": "08:00", "arr": "11:00", "days": "1,2,3,4,5,6,7", "price": 450, "night": False, "next_day": False},
        # Bangalore - Hyderabad
        {"bus": "KA01CD5678", "route": "Bangalore-Hyderabad", "dep": "20:00", "arr": "05:00", "days": "1,2,3,4,5,6,7", "price": 1100, "night": True, "next_day": True},
        # Bangalore - Kochi
        {"bus": "TN05KL1122", "route": "Bangalore-Kochi", "dep": "21:30", "arr": "06:30", "days": "1,2,3,4,5,6,7", "price": 950, "night": True, "next_day": True},
        # Mumbai - Pune
        {"bus": "TN05KL1123", "route": "Mumbai-Pune", "dep": "06:00", "arr": "09:00", "days": "1,2,3,4,5,6,7", "price": 450, "night": False, "next_day": False},
        {"bus": "AP03GH3456", "route": "Mumbai-Pune", "dep": "18:00", "arr": "21:00", "days": "1,2,3,4,5,6,7", "price": 500, "night": False, "next_day": False},
        # Hyderabad - Vijayawada
        {"bus": "AP03GH3457", "route": "Hyderabad-Vijayawada", "dep": "06:00", "arr": "11:00", "days": "1,2,3,4,5,6,7", "price": 450, "night": False, "next_day": False},
        # Coimbatore - Kochi
        {"bus": "TN02EF9012", "route": "Coimbatore-Kochi", "dep": "07:00", "arr": "11:00", "days": "1,2,3,4,5,6,7", "price": 400, "night": False, "next_day": False},
    ]
    
    schedule_map = {}
    for sched_data in schedules_data:
        if sched_data["route"] not in route_map:
            continue
        schedule = BusScheduleModel(
            bus_id=bus_map[sched_data["bus"]],
            route_id=route_map[sched_data["route"]],
            departure_time=sched_data["dep"],
            arrival_time=sched_data["arr"],
            duration_mins=int(sched_data["arr"].split(':')[0]) * 60 - int(sched_data["dep"].split(':')[0]) * 60 if not sched_data["next_day"] else 480,
            days_of_week=sched_data["days"],
            base_price=sched_data["price"],
            is_night_bus=sched_data["night"],
            next_day_arrival=sched_data["next_day"]
        )
        db.add(schedule)
        db.flush()
        schedule_map[f"{sched_data['bus']}-{sched_data['route']}"] = schedule.id
        
        # Add boarding and dropping points for each schedule
        route_cities = sched_data["route"].split("-")
        from_city = route_cities[0]
        to_city = route_cities[1]
        
        # Boarding points (from city)
        boarding_points = [
            {"city": from_city, "name": f"{from_city} Central Bus Stand", "address": f"Central Bus Station, {from_city}", "time": sched_data["dep"], "type": "boarding"},
            {"city": from_city, "name": f"{from_city} Koyambedu" if from_city == "Chennai" else f"{from_city} Main Terminal", "address": f"Main Terminal, {from_city}", "time": add_minutes_to_time(sched_data["dep"], 15), "type": "boarding"},
        ]
        
        # Dropping points (to city)
        dropping_points = [
            {"city": to_city, "name": f"{to_city} Central Bus Stand", "address": f"Central Bus Station, {to_city}", "time": sched_data["arr"], "type": "dropping"},
            {"city": to_city, "name": f"{to_city} Railway Station", "address": f"Near Railway Station, {to_city}", "time": add_minutes_to_time(sched_data["arr"], -15), "type": "dropping"},
        ]
        
        for bp in boarding_points:
            point = BusBoardingPointModel(
                schedule_id=schedule.id,
                city_id=city_map[bp["city"]],
                point_name=bp["name"],
                address=bp["address"],
                time=bp["time"],
                point_type=bp["type"]
            )
            db.add(point)
        
        for dp in dropping_points:
            point = BusBoardingPointModel(
                schedule_id=schedule.id,
                city_id=city_map[dp["city"]],
                point_name=dp["name"],
                address=dp["address"],
                time=dp["time"],
                point_type=dp["type"]
            )
            db.add(point)
    
    db.commit()
    
    return {
        "message": "Bus data seeded successfully",
        "cities": len(cities_data),
        "operators": len(operators_data),
        "routes": len(routes_data),
        "buses": len(buses_data),
        "schedules": len(schedule_map)
    }


def add_minutes_to_time(time_str: str, minutes: int) -> str:
    """Add minutes to a time string (HH:MM)"""
    hours, mins = map(int, time_str.split(':'))
    total_mins = hours * 60 + mins + minutes
    new_hours = (total_mins // 60) % 24
    new_mins = total_mins % 60
    return f"{new_hours:02d}:{new_mins:02d}"


if __name__ == "__main__":
    import uvicorn
    # Get port and host from environment
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

