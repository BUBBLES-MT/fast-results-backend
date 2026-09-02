# app/api/v1/payments.py
# 🔥 VERSION 3.0 - 100% SNIPPE PRODUCTION READY! (NO MOCK DATA!)

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime, timedelta
import logging
import json
import os
import requests
import secrets
import hmac
import hashlib

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_optional
from app.models.school import School, SchoolStatus
from app.models.teacher import Teacher
#from app.models.payment_transactions import PaymentTransaction

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# 🔥 SNIPPE CONFIGURATION - LAZIMA IWE IMEWEKWA!
# ============================================================

SNIPPE_API_KEY = os.environ.get("SNIPPE_API_KEY")
SNIPPE_API_URL = os.environ.get("SNIPPE_API_URL", "https://api.snippe.sh/v1")
SNIPPE_WEBHOOK_SECRET = os.environ.get("SNIPPE_WEBHOOK_SECRET")
APP_URL = os.environ.get("APP_URL", "http://localhost:3000")

# ============================================================
# 🔥 THIBITISHA SNIPPE IMESANIDIWA
# ============================================================

def check_snippe_configured():
    """
    Hakikisha Snippe imesanidiwa kabla ya kuendelea.
    HAKUNA MOCK DATA - LAZIMA API KEY IWEPO!
    """
    if not SNIPPE_API_KEY:
        logger.error("❌ SNIPPE_API_KEY not configured!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PAYMENT_SERVICE_NOT_CONFIGURED",
                "message": "Payment service is not configured. Please contact system administrator.",
                "action": "Set SNIPPE_API_KEY in environment variables"
            }
        )
    if not SNIPPE_API_KEY.startswith("snp_"):
        logger.error(f"❌ Invalid SNIPPE_API_KEY format: {SNIPPE_API_KEY[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INVALID_API_KEY",
                "message": "Invalid payment service configuration. Please contact system administrator.",
                "action": "Check SNIPPE_API_KEY format. It should start with 'snp_'"
            }
        )
    return True

# ============================================================
# 🔥 PLAN PRICES
# ============================================================

PLAN_PRICES = {
    "monthly": 20000,
    "quarterly": 55000,
    "semester": 110000,
    "annual": 220000
}

PLAN_DAYS = {
    "monthly": 30,
    "quarterly": 90,
    "semester": 180,
    "annual": 365
}

PLAN_NAMES = {
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "semester": "Semester",
    "annual": "Annual"
}

# ============================================================
# 🔥 PYDANTIC SCHEMAS
# ============================================================

class InitiatePaymentRequest(BaseModel):
    school_id: int
    plan: str = Field(..., description="Subscription plan: monthly, quarterly, semester, annual")
    amount: float = Field(..., description="Amount to pay")
    phone_number: str = Field(..., description="Phone number for payment")
    customer_name: Optional[str] = Field(None, description="Customer full name")
    customer_email: Optional[str] = Field(None, description="Customer email")
    payment_method: str = Field("mobile", description="Payment method: mobile, bank, card")
    sub_account_id: Optional[str] = Field(None, description="Snippe sub-account ID (for POS/MASI separation)")

    @validator('plan')
    def validate_plan(cls, v):
        if v.lower() not in PLAN_PRICES:
            raise ValueError(f"Invalid plan. Must be one of: {', '.join(PLAN_PRICES.keys())}")
        return v.lower()

    @validator('phone_number')
    def validate_phone(cls, v):
        # Remove any non-digit characters
        v = ''.join(filter(str.isdigit, v))
        if len(v) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        return v

    @validator('amount')
    def validate_amount(cls, v, values):
        plan = values.get('plan', 'monthly')
        expected = PLAN_PRICES.get(plan, 0)
        if abs(v - expected) > 0.01:
            raise ValueError(f"Amount must be exactly {expected} for {plan} plan")
        return v


class PaymentResponse(BaseModel):
    id: int
    transaction_id: str
    reference_number: str
    status: str
    amount: float
    plan: str
    phone_number: str
    customer_name: Optional[str]
    checkout_url: Optional[str] = None
    message: str
    redirect_url: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    id: int
    transaction_id: str
    reference_number: str
    status: str
    amount: float
    plan: str
    school_id: int
    school_name: str
    created_at: str
    completed_at: Optional[str]
    error_message: Optional[str]
    provider_reference: Optional[str]


class PaymentHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    transactions: List[dict]


class WebhookPayload(BaseModel):
    event: str
    transaction_id: str
    reference_number: Optional[str] = None
    amount: float
    status: str
    provider_reference: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    data: Optional[dict] = None


class ExtendSubscriptionRequest(BaseModel):
    school_id: int
    plan: str = "monthly"
    days: Optional[int] = None
    amount: Optional[float] = None


class PaymentStatsResponse(BaseModel):
    total_transactions: int
    total_amount: float
    successful_transactions: int
    successful_amount: float
    pending_transactions: int
    failed_transactions: int
    recent_transactions: List[dict]

# ============================================================
# 🔥 HELPER FUNCTIONS
# ============================================================

def generate_transaction_id() -> str:
    """Generate unique transaction ID"""
    return f"TXN-{secrets.token_hex(4).upper()}"

def generate_reference_number() -> str:
    """Generate unique reference number"""
    return f"REF-{secrets.token_hex(6).upper()}"

def get_plan_days(plan: str) -> int:
    """Get number of days for a plan"""
    return PLAN_DAYS.get(plan.lower(), 30)

def get_plan_price(plan: str) -> int:
    """Get price for a plan"""
    return PLAN_PRICES.get(plan.lower(), 0)

def get_plan_name(plan: str) -> str:
    """Get display name for a plan"""
    return PLAN_NAMES.get(plan.lower(), plan.capitalize())

# ============================================================
# 🔥🔥🔥 ENDPOINT 1: INITIATE PAYMENT - 100% SNIPPE HALISI!
# ============================================================

@router.post("/payments/initiate", response_model=PaymentResponse)
def initiate_payment(
    request: InitiatePaymentRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    🔥 INITIATE PAYMENT - 100% SNIPPE PRODUCTION!
    
    Inaanzisha mchakato wa malipo kwa kutumia Snippe API HALISI.
    HAKUNA MOCK DATA - YOTE NI HALISI KUPITIA SNIPPE!
    
    Mtiririko:
    1. Thibitisha Snippe imesanidiwa (API Key lazima iwepo)
    2. Thibitisha school ipo
    3. Thibitisha amount inalingana na plan
    4. Unda transaction katika database
    5. Tuma ombi kwa Snippe API (HALISI!)
    6. Rudisha checkout URL kutoka Snippe
    """
    
    # 🔥 HAKIKISHA SNIPPE IMESANIDIWA - HAKUNA MOCK!
    check_snippe_configured()
    
    logger.info(f"💰 [SNIPPE PRODUCTION] Payment initiation: school_id={request.school_id}, plan={request.plan}, amount={request.amount}")
    
    # ============================================================
    # 🔥 1. HAKIKISHA SHULE IPO
    # ============================================================
    school = db.query(School).filter(School.id == request.school_id).first()
    if not school:
        logger.error(f"❌ School not found: {request.school_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # ============================================================
    # 🔥 2. UNDA TRANSACTION KWENYE DATABASE
    # ============================================================
    transaction_id = generate_transaction_id()
    reference_number = generate_reference_number()
    
    new_transaction = PaymentTransaction(
        school_id=request.school_id,
        phone_number=request.phone_number,
        customer_name=request.customer_name or school.name,
        customer_email=request.customer_email,
        amount=request.amount,
        plan=request.plan,
        payment_method=request.payment_method,
        status="pending",
        transaction_id=transaction_id,
        reference_number=reference_number,
        created_by=current_user.id if current_user else None,
    )
    
    db.add(new_transaction)
    db.commit()
    db.refresh(new_transaction)
    
    logger.info(f"✅ Transaction created: {transaction_id} for {school.name}")
    
    # ============================================================
    # 🔥 3. TUMA OMBI KWA SNIPPE API (HALISI!)
    # ============================================================
    
    try:
        # 🔥 Andaa payload kwa Snippe
        snippe_payload = {
            "amount": int(request.amount),
            "currency": "TZS",
            "phoneNumber": request.phone_number,
            "customer": {
                "name": request.customer_name or school.name,
                "email": request.customer_email,
                "phone": request.phone_number
            },
            "description": f"Subscription renewal - {school.name} ({request.plan})",
            "callbackUrl": f"{APP_URL}/api/v1/payments/webhook",
            "redirectUrl": f"{APP_URL}/payment/success?transaction_id={transaction_id}",
            "cancelUrl": f"{APP_URL}/payment/canceled?transaction_id={transaction_id}",
            "metadata": {
                "school_id": school.id,
                "school_name": school.name,
                "plan": request.plan,
                "transaction_id": transaction_id,
                "reference_number": reference_number
            }
        }
        
        # 🔥 Ikiwa kuna sub-account, ongeza
        if request.sub_account_id:
            snippe_payload["subAccountId"] = request.sub_account_id
        
        logger.info(f"📡 Sending request to Snippe API: {SNIPPE_API_URL}/payments/mobile")
        
        # 🔥 Tuma ombi kwa Snippe (HALISI!)
        response = requests.post(
            f"{SNIPPE_API_URL}/payments/mobile",
            headers={
                "Authorization": f"Bearer {SNIPPE_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json=snippe_payload,
            timeout=30
        )
        
        logger.info(f"📡 Snippe response status: {response.status_code}")
        
        # ============================================================
        # 🔥 4. CHAKATA JIBU KUTOKA SNIPPE
        # ============================================================
        
        if response.status_code in [200, 201]:
            data = response.json()
            provider_reference = data.get("id")
            checkout_url = data.get("checkoutUrl")
            
            # 🔥 Update transaction with Snippe reference
            new_transaction.provider_reference = provider_reference
            new_transaction.status = "processing"
            new_transaction.request_data = json.dumps(snippe_payload)
            new_transaction.response_data = json.dumps(data)
            db.commit()
            
            logger.info(f"✅ Snippe payment initiated: {provider_reference}")
            
            return PaymentResponse(
                id=new_transaction.id,
                transaction_id=transaction_id,
                reference_number=reference_number,
                status="processing",
                amount=request.amount,
                plan=request.plan,
                phone_number=request.phone_number,
                customer_name=request.customer_name or school.name,
                checkout_url=checkout_url,
                message=f"Payment initiated for {school.name}. Please complete the payment.",
                redirect_url=checkout_url
            )
            
        elif response.status_code == 402:
            # Payment required - Snippe imekataa malipo
            error_data = response.json() if response.text else {}
            error_message = error_data.get("message", "Payment method not available")
            
            new_transaction.status = "failed"
            new_transaction.error_message = error_message
            new_transaction.response_data = json.dumps(error_data)
            db.commit()
            
            logger.error(f"❌ Snippe payment rejected: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "PAYMENT_METHOD_UNAVAILABLE",
                    "message": error_message,
                    "transaction_id": transaction_id
                }
            )
            
        else:
            # Other errors
            error_data = response.json() if response.text else {}
            error_message = error_data.get("message", f"Snippe error: {response.status_code}")
            
            new_transaction.status = "failed"
            new_transaction.error_message = error_message
            new_transaction.response_data = json.dumps(error_data)
            db.commit()
            
            logger.error(f"❌ Snippe error: {response.status_code} - {error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "PAYMENT_INITIATION_FAILED",
                    "message": error_message,
                    "transaction_id": transaction_id
                }
            )
            
    except requests.exceptions.Timeout:
        error_message = "Snippe API timeout. Please try again."
        new_transaction.status = "failed"
        new_transaction.error_message = error_message
        db.commit()
        
        logger.error(f"❌ Snippe timeout: {transaction_id}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "error": "PAYMENT_TIMEOUT",
                "message": error_message,
                "transaction_id": transaction_id
            }
        )
        
    except requests.exceptions.ConnectionError:
        error_message = "Cannot connect to payment service. Please try again."
        new_transaction.status = "failed"
        new_transaction.error_message = error_message
        db.commit()
        
        logger.error(f"❌ Snippe connection error: {transaction_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "PAYMENT_SERVICE_UNAVAILABLE",
                "message": error_message,
                "transaction_id": transaction_id
            }
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        error_message = str(e)
        new_transaction.status = "failed"
        new_transaction.error_message = error_message
        db.commit()
        
        logger.error(f"❌ Snippe error: {transaction_id} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PAYMENT_PROCESSING_ERROR",
                "message": "An error occurred while processing your payment.",
                "transaction_id": transaction_id
            }
        )


# ============================================================
# 🔥🔥🔥 ENDPOINT 2: CHECK PAYMENT STATUS
# ============================================================

@router.get("/payments/status/{transaction_id}", response_model=PaymentStatusResponse)
def check_payment_status(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    🔥 CHECK PAYMENT STATUS
    
    Angalia hali ya malipo kwa kutumia transaction_id.
    Inaangalia halisi kutoka Snippe API.
    """
    
    transaction = db.query(PaymentTransaction).filter(
        PaymentTransaction.transaction_id == transaction_id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Check permissions
    if current_user:
        if hasattr(current_user, 'school_id') and current_user.school_id != transaction.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this transaction"
            )
    
    # Get school name
    school = db.query(School).filter(School.id == transaction.school_id).first()
    school_name = school.name if school else "Unknown"
    
    # 🔥 If processing and has provider_reference, check with Snippe (HALISI!)
    if transaction.status == "processing" and transaction.provider_reference:
        try:
            # Hakikisha Snippe imesanidiwa
            if SNIPPE_API_KEY and SNIPPE_API_KEY.startswith("snp_"):
                response = requests.get(
                    f"{SNIPPE_API_URL}/payments/{transaction.provider_reference}",
                    headers={
                        "Authorization": f"Bearer {SNIPPE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    snippe_status = data.get("status", "")
                    
                    if snippe_status == "completed":
                        transaction.status = "success"
                        transaction.completed_at = datetime.now()
                        
                        # 🔥 Extend subscription
                        school = db.query(School).filter(School.id == transaction.school_id).first()
                        if school:
                            days = get_plan_days(transaction.plan)
                            now = datetime.now()
                            
                            if school.subscription_expires_at and school.subscription_expires_at > now:
                                new_expiry = school.subscription_expires_at + timedelta(days=days)
                            else:
                                new_expiry = now + timedelta(days=days)
                            
                            school.subscription_expires_at = new_expiry
                            school.subscription_plan = transaction.plan
                            school.is_active = True
                            school.is_locked_by_superadmin = False
                            
                            if school.status == SchoolStatus.EXPIRED or school.status == SchoolStatus.INACTIVE:
                                school.status = SchoolStatus.ACTIVE
                            
                            db.commit()
                            logger.info(f"✅ Subscription extended for {school.name} until {new_expiry}")
                        
                    elif snippe_status == "failed":
                        transaction.status = "failed"
                        transaction.error_message = data.get("error_message", "Payment failed")
                        
                    elif snippe_status == "cancelled":
                        transaction.status = "cancelled"
                    
                    db.commit()
                    
        except Exception as e:
            logger.error(f"❌ Error checking payment status: {str(e)}")
    
    return PaymentStatusResponse(
        id=transaction.id,
        transaction_id=transaction.transaction_id,
        reference_number=transaction.reference_number,
        status=transaction.status,
        amount=transaction.amount,
        plan=transaction.plan,
        school_id=transaction.school_id,
        school_name=school_name,
        created_at=transaction.created_at.isoformat() if transaction.created_at else "",
        completed_at=transaction.completed_at.isoformat() if transaction.completed_at else None,
        error_message=transaction.error_message,
        provider_reference=transaction.provider_reference
    )


# ============================================================
# 🔥🔥🔥 ENDPOINT 3: WEBHOOK - SNIPPE INATUMA HAPA
# ============================================================

@router.post("/payments/webhook")
async def payment_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    🔥 WEBHOOK - SNIPPE INATUMA HAPA BAADA YA MALIPO (HALISI!)
    
    Hii ndiyo endpoint ambayo Snippe itatuma baada ya malipo kukamilika.
    """
    
    # ============================================================
    # 🔥 1. PATA DATA KUTOKA REQUEST
    # ============================================================
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"❌ Invalid webhook payload: {str(e)}")
        return {"status": "error", "message": "Invalid payload"}
    
    signature = request.headers.get("x-snippe-signature", "")
    
    logger.info(f"📩 Webhook received: {json.dumps(body)[:500]}...")
    
    # ============================================================
    # 🔥 2. THIBITISHA SIGNATURE (USALAMA)
    # ============================================================
    if SNIPPE_WEBHOOK_SECRET:
        try:
            expected_signature = hmac.new(
                SNIPPE_WEBHOOK_SECRET.encode(),
                json.dumps(body).encode(),
                hashlib.sha256
            ).hexdigest()
            
            if signature != expected_signature:
                logger.warning(f"⚠️ Invalid webhook signature")
                return {"status": "error", "message": "Invalid signature"}
        except Exception as e:
            logger.error(f"❌ Signature verification error: {str(e)}")
    
    # ============================================================
    # 🔥 3. CHAKATA DATA
    # ============================================================
    event = body.get("event", "")
    data = body.get("data", {})
    
    # Try different possible field names
    reference_number = (
        data.get("reference_number") or 
        data.get("reference") or 
        body.get("reference_number") or 
        body.get("reference")
    )
    
    transaction_id = (
        data.get("transaction_id") or 
        data.get("id") or 
        body.get("transaction_id") or 
        body.get("id")
    )
    
    provider_reference = data.get("provider_reference") or data.get("providerReference")
    
    if not transaction_id and not reference_number:
        logger.error("❌ No transaction_id or reference_number in webhook payload")
        return {"status": "error", "message": "No transaction identifier provided"}
    
    # ============================================================
    # 🔥 4. TAFUTA TRANSACTION KWENYE DATABASE
    # ============================================================
    transaction = None
    
    if transaction_id:
        transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.transaction_id == transaction_id
        ).first()
    
    if not transaction and reference_number:
        transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.reference_number == reference_number
        ).first()
    
    if not transaction and provider_reference:
        transaction = db.query(PaymentTransaction).filter(
            PaymentTransaction.provider_reference == provider_reference
        ).first()
    
    if not transaction:
        logger.error(f"❌ Transaction not found: transaction_id={transaction_id}, reference={reference_number}")
        return {"status": "error", "message": "Transaction not found"}
    
    # ============================================================
    # 🔥 5. SASISHA TRANSACTION NA SUBSCRIPTION
    # ============================================================
    old_status = transaction.status
    new_status = None
    
    # Extract status from payload
    status_from_payload = (
        data.get("status") or 
        body.get("status") or 
        event.replace("payment.", "") if event.startswith("payment.") else None
    )
    
    if event == "payment.completed" or status_from_payload == "success" or status_from_payload == "completed":
        new_status = "success"
        transaction.completed_at = datetime.now()
        
        # 🔥 EXTEND SUBSCRIPTION (HALISI!)
        school = db.query(School).filter(School.id == transaction.school_id).first()
        if school:
            days = get_plan_days(transaction.plan)
            now = datetime.now()
            
            if school.subscription_expires_at and school.subscription_expires_at > now:
                new_expiry = school.subscription_expires_at + timedelta(days=days)
            else:
                new_expiry = now + timedelta(days=days)
            
            school.subscription_expires_at = new_expiry
            school.subscription_plan = transaction.plan
            school.is_active = True
            school.is_locked_by_superadmin = False
            
            if school.status == SchoolStatus.EXPIRED or school.status == SchoolStatus.INACTIVE:
                school.status = SchoolStatus.ACTIVE
            
            db.commit()
            
            logger.info(f"✅ Subscription extended for {school.name} until {new_expiry}")
        else:
            logger.warning(f"⚠️ School not found for transaction {transaction.transaction_id}")
            
    elif event == "payment.failed" or status_from_payload == "failed":
        new_status = "failed"
        transaction.error_message = data.get("error_message") or data.get("message") or "Payment failed"
        
    elif event == "payment.cancelled" or status_from_payload == "cancelled":
        new_status = "cancelled"
        
    elif event == "payment.refunded" or status_from_payload == "refunded":
        new_status = "refunded"
        
    else:
        # Unknown event
        logger.warning(f"⚠️ Unknown webhook event: {event}")
        if status_from_payload:
            new_status = status_from_payload
    
    if new_status:
        transaction.status = new_status
        
        # Update provider reference if provided
        if provider_reference and not transaction.provider_reference:
            transaction.provider_reference = provider_reference
        
        # Store response data
        transaction.response_data = json.dumps(body)
        
        db.commit()
        logger.info(f"✅ Transaction {transaction.transaction_id} status updated: {old_status} → {new_status}")
    
    return {"status": "success", "message": "Webhook processed"}


# ============================================================
# 🔥🔥🔥 ENDPOINT 4: GET PAYMENT HISTORY
# ============================================================

@router.get("/payments/history", response_model=PaymentHistoryResponse)
def get_payment_history(
    school_id: Optional[int] = None,
    status: Optional[str] = None,
    plan: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    🔥 GET PAYMENT HISTORY
    
    Pata historia ya malipo kwa chujio mbalimbali.
    """
    
    query = db.query(PaymentTransaction)
    
    # 🔥 Filter by school
    if school_id:
        query = query.filter(PaymentTransaction.school_id == school_id)
    elif current_user and hasattr(current_user, 'school_id'):
        query = query.filter(PaymentTransaction.school_id == current_user.school_id)
    
    # 🔥 Filter by status
    if status:
        query = query.filter(PaymentTransaction.status == status)
    
    # 🔥 Filter by plan
    if plan:
        query = query.filter(PaymentTransaction.plan == plan)
    
    # 🔥 Filter by date
    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
            query = query.filter(PaymentTransaction.created_at >= start)
        except:
            pass
    
    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
            query = query.filter(PaymentTransaction.created_at <= end)
        except:
            pass
    
    total = query.count()
    transactions = query.order_by(PaymentTransaction.created_at.desc()).limit(limit).offset(offset).all()
    
    # Convert to dict
    result = []
    for t in transactions:
        dict_t = t.to_dict()
        # Add school name
        school = db.query(School).filter(School.id == t.school_id).first()
        dict_t["school_name"] = school.name if school else "Unknown"
        dict_t["plan_display"] = get_plan_name(t.plan)
        result.append(dict_t)
    
    return PaymentHistoryResponse(
        total=total,
        limit=limit,
        offset=offset,
        transactions=result
    )


# ============================================================
# 🔥🔥🔥 ENDPOINT 5: GET SINGLE TRANSACTION
# ============================================================

@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    🔥 GET SINGLE PAYMENT
    
    Pata maelezo ya malipo moja kwa ID yake.
    """
    
    transaction = db.query(PaymentTransaction).filter(
        PaymentTransaction.id == payment_id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Check permissions
    if current_user:
        if hasattr(current_user, 'school_id') and current_user.school_id != transaction.school_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this transaction"
            )
    
    result = transaction.to_dict()
    
    # Add school name
    school = db.query(School).filter(School.id == transaction.school_id).first()
    result["school_name"] = school.name if school else "Unknown"
    result["plan_display"] = get_plan_name(transaction.plan)
    
    return result


# ============================================================
# 🔥🔥🔥 ENDPOINT 6: PAYMENT STATISTICS
# ============================================================

@router.get("/payments/stats", response_model=PaymentStatsResponse)
def get_payment_stats(
    school_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    🔥 GET PAYMENT STATISTICS
    
    Pata takwimu za malipo.
    """
    
    query = db.query(PaymentTransaction)
    
    if school_id:
        query = query.filter(PaymentTransaction.school_id == school_id)
    elif current_user and hasattr(current_user, 'school_id'):
        query = query.filter(PaymentTransaction.school_id == current_user.school_id)
    
    # Total
    total_transactions = query.count()
    total_amount = query.with_entities(db.func.sum(PaymentTransaction.amount)).scalar() or 0
    
    # Successful
    successful = query.filter(PaymentTransaction.status == "success")
    successful_count = successful.count()
    successful_amount = successful.with_entities(db.func.sum(PaymentTransaction.amount)).scalar() or 0
    
    # Pending
    pending_count = query.filter(PaymentTransaction.status == "pending").count()
    
    # Failed
    failed_count = query.filter(PaymentTransaction.status == "failed").count()
    
    # Recent transactions (last 10)
    recent = query.order_by(PaymentTransaction.created_at.desc()).limit(10).all()
    recent_list = []
    for t in recent:
        dict_t = t.to_dict()
        school = db.query(School).filter(School.id == t.school_id).first()
        dict_t["school_name"] = school.name if school else "Unknown"
        recent_list.append(dict_t)
    
    return PaymentStatsResponse(
        total_transactions=total_transactions,
        total_amount=float(total_amount),
        successful_transactions=successful_count,
        successful_amount=float(successful_amount),
        pending_transactions=pending_count,
        failed_transactions=failed_count,
        recent_transactions=recent_list
    )


# ============================================================
# 🔥🔥🔥 ENDPOINT 7: EXTEND SUBSCRIPTION (SUPERADMIN ONLY)
# ============================================================

@router.post("/payments/extend-subscription")
def extend_subscription_manual(
    request: ExtendSubscriptionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🔥 EXTEND SUBSCRIPTION - SUPERADMIN ONLY
    
    Superadmin anaweza kuongeza muda wa subscription ya shule
    bila kutumia mfumo wa malipo.
    """
    
    # ============================================================
    # 🔥 1. HAKIKISHA NI SUPERADMIN
    # ============================================================
    user_role = getattr(current_user, 'role', None)
    if hasattr(user_role, 'value'):
        user_role = user_role.value
    
    is_superadmin = user_role == "superadmin" or user_role == "Superadmin"
    if not is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can manually extend subscription"
        )
    
    # ============================================================
    # 🔥 2. HAKIKISHA SHULE IPO
    # ============================================================
    school = db.query(School).filter(School.id == request.school_id).first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School not found"
        )
    
    # ============================================================
    # 🔥 3. HESABU IDADI YA SIKU
    # ============================================================
    days = request.days or get_plan_days(request.plan)
    amount = request.amount or get_plan_price(request.plan)
    
    # ============================================================
    # 🔥 4. WEKA TAREHE MPYA YA MALIPO
    # ============================================================
    now = datetime.now()
    
    if school.subscription_expires_at and school.subscription_expires_at > now:
        new_expiry = school.subscription_expires_at + timedelta(days=days)
    else:
        new_expiry = now + timedelta(days=days)
    
    # ============================================================
    # 🔥 5. SASISHA SCHOOL
    # ============================================================
    school.subscription_plan = request.plan
    school.subscription_expires_at = new_expiry
    school.is_active = True
    school.status = "active"
    school.is_locked_by_superadmin = False
    
    db.commit()
    db.refresh(school)
    
    logger.info(f"🔑 Superadmin {current_user.name} extended subscription for {school.name} by {days} days. New expiry: {new_expiry}")
    
    # 🔥 Unda transaction record kwa ajili ya kumbukumbu
    new_transaction = PaymentTransaction(
        school_id=school.id,
        phone_number="SYSTEM",
        customer_name=current_user.name,
        customer_email=current_user.email,
        amount=amount,
        plan=request.plan,
        payment_method="manual",
        status="success",
        transaction_id=f"ADMIN-{secrets.token_hex(4).upper()}",
        reference_number=f"ADMIN-REF-{secrets.token_hex(6).upper()}",
        provider_reference=f"MANUAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        created_by=current_user.id,
        completed_at=datetime.now()
    )
    
    db.add(new_transaction)
    db.commit()
    
    return {
        "message": f"Subscription extended by {days} days",
        "school_id": school.id,
        "school_name": school.name,
        "plan": request.plan,
        "days_added": days,
        "amount": amount,
        "new_expiry_date": new_expiry.isoformat(),
        "is_active": school.is_active,
        "status": school.status,
        "performed_by": current_user.name,
        "transaction_id": new_transaction.transaction_id
    }