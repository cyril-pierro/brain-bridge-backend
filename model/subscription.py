from sqlalchemy import Column, Integer, Enum, ForeignKey, UUID
from sqlalchemy.orm import relationship
from util.enum import SubscriptionType
from core.setup import Base
from core.db import CreateDBSession


class Subscription(Base):
    """
    Represents the user's current subscription status (1-to-1 with User).
    """

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id"), unique=True, nullable=False)
    type = Column(Enum(SubscriptionType), nullable=False,
                  default=SubscriptionType.free)

    # Relationships
    user = relationship("User", back_populates="subscription")

    def save(self) -> "Base":
        with CreateDBSession() as session:
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    def delete(self) -> bool:
        with CreateDBSession() as session:
            session.delete(self)
            session.commit()
            return True

    @staticmethod
    def get_subscription_by_user_id(user_id: int) -> "Subscription":
        with CreateDBSession() as session:
            return (
                session.query(Subscription)
                .filter(Subscription.user_id == user_id)
                .first()
            )

    @staticmethod
    def subscribe(user_id: int, subscription_type: SubscriptionType) -> "Subscription":
        subscription = Subscription(user_id=user_id, type=subscription_type)
        return subscription.save()
