# app/models/subject.py

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Subject(Base):
    """
    🔥 SUBJECT MODEL - SALAMA KWA ALAMA ZA WANAFUNZI!
    
    KANUNI MUHIMU ZA USALAMA:
    - ✅ Somo likifutwa → Alama za wanafunzi ZINABAKI (subject_id = NULL)
    - ✅ Somo likifutwa → Assignments za walimu ZINAONDOKA (hazina maana)
    - ✅ School ikifutwa → Subjects zinafutika (CASCADE ni sawa)
    
    ⚠️ MUHIMU: Haturuhusu cascade delete kwenye `marks`!
    Tunaacha ForeignKey (SET NULL) ifanye kazi yake.
    """
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(
        Integer, 
        ForeignKey("schools.id", ondelete="CASCADE"), 
        nullable=False
    )
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=True, index=True)
    
    # ============================================================
    # 🔥 COLUMNS - ZIMEBORESHA!
    # ============================================================
    
    # 🔥 Aina ya somo (Core, Optional, Extra)
    subject_type = Column(String(20), nullable=True, default="Core")
    
    # 🔥 Daraja la somo (Primary, Secondary, Advanced)
    level = Column(String(20), nullable=False, default="secondary")
    
    # 🔥 Ikiwa somo linahesabiwa kwenye average
    is_calculated = Column(Boolean, default=True)
    
    # 🔥 Ikiwa somo ni la lazima
    is_required = Column(Boolean, default=True)
    
    # 🔥 Mpangilio wa somo (kwa ajili ya UI)
    display_order = Column(Integer, nullable=True, default=0)

    # ============================================================
    # 🔥 RELATIONSHIPS - ZOTE SALAMA!
    # ============================================================
    
    # 🔥 School (Shule)
    school = relationship("School", back_populates="subjects")
    
    # ============================================================
    # 🔥 MARKS - MUHIMU SANA!
    # ============================================================
    # ⚠️ HATUWEKI cascade="all, delete-orphan"!
    # 
    # Kwa nini? Kwa sababu:
    # 1. Mark.subject_id ina ondelete="SET NULL"
    # 2. Tunaacha Database ifanye kazi yake
    # 3. Somo likifutwa, subject_id inakuwa NULL kwenye marks
    # 4. Alama za wanafunzi ZINABAKI salama!
    #
    # passive_deletes=True inasema: "Usifute marks, acha DB ifanye"
    marks = relationship(
        "Mark", 
        back_populates="subject",
        passive_deletes=True  # ✅ Acha DB ifanye kazi (SET NULL)
    )
    
    # ============================================================
    # 🔥 TEACHER_SUBJECTS - SAWA KUFUTA
    # ============================================================
    # Somo likifutwa, assignments za walimu hazina maana
    # Kwa hiyo cascade delete ni SAHIHI hapa
    teacher_subjects = relationship(
        "TeacherSubject", 
        back_populates="subject", 
        cascade="all, delete-orphan"  # ✅ Sawa - haina alama za wanafunzi
    )

    def __repr__(self):
        return f"<Subject {self.name} ({self.code}) - {self.level}>"