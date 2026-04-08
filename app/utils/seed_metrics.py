import uuid
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.tts_request import TTSRequest
from app.models.audio_quality_metric import AudioQualityMetric
from app.models.user import User

def seed_mock_data(user_id: uuid.UUID):
    db: Session = SessionLocal()
    try:
        # 1. Ensure user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"User {user_id} not found. Skipping.")
            return

        print(f"Seeding data for user: {user.email}")

        emotions = ["happy", "sad", "neutral", "angry", "surprised"]
        
        # 2. Generate requests for the last 10 days
        for i in range(10):
            day = datetime.utcnow() - timedelta(days=i)
            # 5-15 requests per day
            for _ in range(random.randint(5, 15)):
                request_id = uuid.uuid4()
                latency = random.randint(800, 5000)
                emotion = random.choice(emotions)
                
                # Mock TTS Request
                req = TTSRequest(
                    id=request_id,
                    user_id=user_id,
                    input_text="This is mock text for performance testing.",
                    detected_emotion=emotion,
                    confidence_score=random.uniform(0.6, 0.99),
                    audio_path=f"app/media/tts/{request_id}.wav",
                    latency_ms=latency,
                    created_at=day
                )
                db.add(req)
                
                # Mock Quality Metric (for about 70% of requests)
                if random.random() > 0.3:
                    quality = AudioQualityMetric(
                        tts_request_id=request_id,
                        mos_score=random.randint(3, 5),
                        intelligibility=random.randint(3, 5),
                        created_at=day
                    )
                    db.add(quality)
        
        db.commit()
        print("Mock data seeded successfully!")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # You can pass a real user_id here. 
    # For now, let's find the first user in the DB.
    db = SessionLocal()
    first_user = db.query(User).first()
    db.close()
    
    if first_user:
        seed_mock_data(first_user.id)
    else:
        print("No users found in database. Create a user first.")
