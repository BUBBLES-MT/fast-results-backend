from app.core.database import SessionLocal
from app.models.school import School
from app.models.school_class import SchoolClass
from app.models.stream import Stream

def add_sample_data():
    db = SessionLocal()
    
    # Unda shule
    school = School(
        name="BUOYANT SECONDARY SCHOOL",
        school_type="secondary",
        status="active",
        is_active=True
    )
    db.add(school)
    db.commit()
    db.refresh(school)
    print(f"✅ Shule imeundwa: ID={school.id}, Name={school.name}")
    
    # Unda darasa
    class_obj = SchoolClass(
        name="Form 1",
        school_id=school.id
    )
    db.add(class_obj)
    db.commit()
    db.refresh(class_obj)
    print(f"✅ Darasa limeundwa: ID={class_obj.id}, Name={class_obj.name}")
    
    # Unda stream
    stream = Stream(
        name="A",
        class_id=class_obj.id,
        school_id=school.id
    )
    db.add(stream)
    db.commit()
    db.refresh(stream)
    print(f"✅ Stream imeundwa: ID={stream.id}, Name={stream.name}")
    
    db.close()
    print("\n🎉 Data ya mfano imeongezwa! Sasa unaweza kuunda student.")

if __name__ == "__main__":
    add_sample_data()