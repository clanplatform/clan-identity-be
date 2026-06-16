"""
Login Attempt Schemas
Request and response schemas for login attempt tracking and monitoring
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class LoginAttemptCreate(BaseModel):
    """Schema for creating a login attempt record"""
    user_id: Optional[UUID] = Field(None, description="User ID if identified")
    email_or_username: str = Field(..., max_length=255, description="Email or username attempted")
    attempt_type: str = Field(default="password", max_length=50, description="Type of attempt (password, otp, 2fa, sso)")
    is_successful: bool = Field(default=False, description="Whether the attempt was successful")
    failure_reason: Optional[str] = Field(None, max_length=100, description="Reason for failure")
    ip_address: str = Field(..., max_length=45, description="IP address of the attempt")
    user_agent: Optional[str] = Field(None, description="User agent string")
    device_fingerprint: Optional[str] = Field(None, max_length=255, description="Device fingerprint")
    country: Optional[str] = Field(None, max_length=100, description="Country based on IP")
    city: Optional[str] = Field(None, max_length=100, description="City based on IP")
    risk_score: Optional[str] = Field(None, max_length=10, description="Risk score (0-100)")
    is_suspicious: bool = Field(default=False, description="Whether attempt is flagged as suspicious")
    suspicious_reason: Optional[str] = Field(None, max_length=255, description="Reason for suspicious flag")


class LoginAttemptResponse(BaseModel):
    """Schema for login attempt response"""
    id: UUID = Field(..., description="Login attempt ID")
    user_id: Optional[UUID] = Field(None, description="User ID if identified")
    email_or_username: str = Field(..., description="Email or username attempted")
    attempt_type: str = Field(..., description="Type of attempt")
    is_successful: bool = Field(..., description="Whether the attempt was successful")
    failure_reason: Optional[str] = Field(None, description="Reason for failure")
    ip_address: str = Field(..., description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    device_fingerprint: Optional[str] = Field(None, description="Device fingerprint")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")
    risk_score: Optional[str] = Field(None, description="Risk score")
    is_suspicious: bool = Field(..., description="Suspicious flag")
    suspicious_reason: Optional[str] = Field(None, description="Reason for suspicious flag")
    created_at: datetime = Field(..., description="Timestamp of the attempt")

    class Config:
        from_attributes = True


class LoginAttemptSummary(BaseModel):
    """Schema for login attempt summary"""
    total_attempts: int = Field(..., description="Total number of login attempts")
    successful_attempts: int = Field(..., description="Number of successful attempts")
    failed_attempts: int = Field(..., description="Number of failed attempts")
    suspicious_attempts: int = Field(..., description="Number of suspicious attempts")
    unique_ips: int = Field(..., description="Number of unique IP addresses")
    last_attempt: Optional[datetime] = Field(None, description="Timestamp of last attempt")


class LoginAttemptQueryParams(BaseModel):
    """Query parameters for filtering login attempts"""
    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    email_or_username: Optional[str] = Field(None, description="Filter by email or username")
    is_successful: Optional[bool] = Field(None, description="Filter by success status")
    is_suspicious: Optional[bool] = Field(None, description="Filter by suspicious flag")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    attempt_type: Optional[str] = Field(None, description="Filter by attempt type")
    from_date: Optional[datetime] = Field(None, description="Filter attempts from this date")
    to_date: Optional[datetime] = Field(None, description="Filter attempts until this date")
    limit: int = Field(default=100, ge=1, le=1000, description="Number of records to return")
    offset: int = Field(default=0, ge=0, description="Number of records to skip")


class LoginAttemptListResponse(BaseModel):
    """Schema for paginated login attempts list"""
    total: int = Field(..., description="Total number of login attempts matching criteria")
    limit: int = Field(..., description="Number of records per page")
    offset: int = Field(..., description="Number of records skipped")
    attempts: list[LoginAttemptResponse] = Field(..., description="List of login attempts")


class LoginAttemptStats(BaseModel):
    """Schema for login attempt statistics"""
    period: str = Field(..., description="Time period for statistics (e.g., '24h', '7d', '30d')")
    total_attempts: int = Field(..., description="Total attempts in period")
    successful_rate: float = Field(..., description="Success rate percentage")
    failed_rate: float = Field(..., description="Failure rate percentage")
    suspicious_rate: float = Field(..., description="Suspicious attempts rate percentage")
    top_failure_reasons: list[dict[str, int]] = Field(default=[], description="Top failure reasons with counts")
    top_countries: list[dict[str, int]] = Field(default=[], description="Top countries with counts")
    hourly_distribution: list[dict[str, int]] = Field(default=[], description="Hourly attempt distribution")


class RateLimitInfo(BaseModel):
    """Schema for rate limit information"""
    is_rate_limited: bool = Field(..., description="Whether the user/IP is rate limited")
    attempts_count: int = Field(..., description="Number of recent attempts")
    window_minutes: int = Field(..., description="Rate limit window in minutes")
    max_attempts: int = Field(..., description="Maximum allowed attempts")
    retry_after_seconds: Optional[int] = Field(None, description="Seconds until retry is allowed")
    lockout_until: Optional[datetime] = Field(None, description="Lockout expiration timestamp")


class SuspiciousActivityAlert(BaseModel):
    """Schema for suspicious activity alerts"""
    alert_id: UUID = Field(..., description="Alert ID")
    user_id: Optional[UUID] = Field(None, description="User ID if identified")
    email_or_username: str = Field(..., description="Email or username")
    alert_type: str = Field(..., description="Type of suspicious activity")
    severity: str = Field(..., description="Alert severity (low, medium, high, critical)")
    description: str = Field(..., description="Description of suspicious activity")
    ip_address: str = Field(..., description="IP address")
    attempts_count: int = Field(..., description="Number of attempts in suspicious pattern")
    first_attempt: datetime = Field(..., description="First attempt timestamp")
    last_attempt: datetime = Field(..., description="Last attempt timestamp")
    is_resolved: bool = Field(default=False, description="Whether alert is resolved")


