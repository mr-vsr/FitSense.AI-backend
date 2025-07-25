from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, unique=True, nullable=False)  # PK is now a string
    username = Column(String, unique=True, nullable=False)
    height_cm = Column(Float)
    weight_kg = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    meals = relationship("MealLog", back_populates="user")
    tips = relationship("HealthTip", back_populates="user")


class MealLog(Base):
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"))  # FK updated to match string PK
    image_path = Column(String)
    meal_time = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text)

    user = relationship("User", back_populates="meals")
    nutrition = relationship("NutritionalData", back_populates="meal", uselist=False)


class NutritionalData(Base):
    __tablename__ = "nutritional_data"

    id = Column(Integer, primary_key=True, index=True)
    meal_id = Column(Integer, ForeignKey("meal_logs.id"))
    calories = Column(Float)
    protein = Column(Float)
    fat = Column(Float)
    carbohydrates = Column(Float)

    meal = relationship("MealLog", back_populates="nutrition")


class HealthTip(Base):
    __tablename__ = "health_tips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"))  # FK updated to match string PK
    tip_text = Column(Text)
    generated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="tips")