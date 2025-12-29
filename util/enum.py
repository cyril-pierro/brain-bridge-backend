import enum


class SubjectType(enum.Enum):
    CORE = "core"
    ELECTIVE = "elective"


class Gender(enum.Enum):
    male = "male"
    female = "female"


# Enum for OAuth providers


class Provider(enum.Enum):
    STANDARD = "standard"
    GOOGLE = "google"
    APPLE = "apple"


class SubscriptionType(enum.Enum):
    free = "free"
    premium = "premium"


class UserRole(str, enum.Enum):
    """Defines the role of a user in the system."""

    student = "student"
    admin = "admin"
    instructor = "instructor"


class BookingType(str, enum.Enum):
    """Defines whether the session is online or in-person."""

    online = "online"
    in_person = "in_person"


class BookingStatus(str, enum.Enum):
    """Defines the status of the booking."""

    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
