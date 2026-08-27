"""Add new columns to marks, teacher_subjects, student_reports, subjects, payment_transactions

Revision ID: 3265a44592cb
Revises: 
Create Date: 2026-08-16 01:03:32.832552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3265a44592cb'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # ============================================================
    # 🔥 1. MARKS TABLE
    # ============================================================
    op.add_column('marks', sa.Column('class_id', sa.Integer(), nullable=True))
    op.add_column('marks', sa.Column('year', sa.Integer(), nullable=True))
    op.add_column('marks', sa.Column('stream_id', sa.Integer(), nullable=True))
    
    op.alter_column('marks', 'teacher_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    
    op.drop_constraint('unique_mark_per_exam', 'marks', type_='unique')
    op.create_unique_constraint(
        'unique_mark_per_exam_year_class', 
        'marks', 
        ['student_id', 'subject_id', 'teacher_id', 'exam_type', 'year', 'class_id']
    )
    
    op.drop_constraint('marks_teacher_id_fkey', 'marks', type_='foreignkey')
    op.create_foreign_key('fk_marks_teacher_id', 'marks', 'teachers', ['teacher_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_marks_stream_id', 'marks', 'streams', ['stream_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_marks_class_id', 'marks', 'classes', ['class_id'], ['id'], ondelete='CASCADE')

    # ============================================================
    # 🔥 2. PAYMENT_TRANSACTIONS TABLE
    # ============================================================
    op.add_column('payment_transactions', sa.Column('customer_name', sa.String(length=200), nullable=True))
    op.add_column('payment_transactions', sa.Column('customer_email', sa.String(length=200), nullable=True))
    op.add_column('payment_transactions', sa.Column('payment_method', sa.String(length=50), nullable=True, server_default='mobile'))
    op.add_column('payment_transactions', sa.Column('reference_number', sa.String(length=100), nullable=True))
    op.add_column('payment_transactions', sa.Column('provider_reference', sa.String(length=100), nullable=True))
    op.add_column('payment_transactions', sa.Column('request_data', sa.Text(), nullable=True))
    op.add_column('payment_transactions', sa.Column('response_data', sa.Text(), nullable=True))
    op.add_column('payment_transactions', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('payment_transactions', sa.Column('subscription_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('payment_transactions', sa.Column('subscription_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('payment_transactions', sa.Column('created_by', sa.Integer(), nullable=True))
    op.add_column('payment_transactions', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    
    op.create_unique_constraint('uq_payment_reference', 'payment_transactions', ['reference_number'])
    op.create_index('ix_payment_transactions_reference_number', 'payment_transactions', ['reference_number'], unique=True)
    
    op.drop_constraint('payment_transactions_school_id_fkey', 'payment_transactions', type_='foreignkey')
    op.create_foreign_key('fk_payment_school_id', 'payment_transactions', 'schools', ['school_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_payment_created_by', 'payment_transactions', 'teachers', ['created_by'], ['id'], ondelete='SET NULL')

    # ============================================================
    # 🔥 3. SCHOOLS TABLE - SKIP (HAIBADILISHI)
    # ============================================================
    # SKIP - Usibadilishe school_level

    # ============================================================
    # 🔥 4. STUDENT_REPORTS TABLE
    # ============================================================
    op.add_column('student_reports', sa.Column('class_id', sa.Integer(), nullable=True))
    op.add_column('student_reports', sa.Column('stream_id', sa.Integer(), nullable=True))
    op.add_column('student_reports', sa.Column('exam_type', sa.String(length=50), nullable=True))
    op.add_column('student_reports', sa.Column('total_students', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('student_reports', sa.Column('teacher_remarks', sa.Text(), nullable=True))
    op.add_column('student_reports', sa.Column('headmaster_remarks', sa.Text(), nullable=True))
    op.add_column('student_reports', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    
    op.alter_column('student_reports', 'points',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    op.alter_column('student_reports', 'division',
                    existing_type=sa.VARCHAR(length=5),
                    nullable=True)
    
    op.create_index('ix_class_term_year', 'student_reports', ['class_id', 'term', 'year'])
    op.create_index('ix_report_exam_type', 'student_reports', ['exam_type'])
    op.create_index('ix_report_year', 'student_reports', ['year'])
    
    op.create_foreign_key('fk_reports_stream_id', 'student_reports', 'streams', ['stream_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_reports_class_id', 'student_reports', 'classes', ['class_id'], ['id'], ondelete='SET NULL')
    
    op.drop_column('student_reports', 'remarks')

    # ============================================================
    # 🔥 5. STUDENTS TABLE
    # ============================================================
    op.drop_constraint('unique_roll_number_per_class', 'students', type_='unique')

    # ============================================================
    # 🔥 6. SUBJECTS TABLE
    # ============================================================
    op.add_column('subjects', sa.Column('subject_type', sa.String(length=20), nullable=True, server_default='Core'))
    op.add_column('subjects', sa.Column('level', sa.String(length=20), nullable=True))
    op.add_column('subjects', sa.Column('is_calculated', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('subjects', sa.Column('is_required', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('subjects', sa.Column('display_order', sa.Integer(), nullable=True, server_default='0'))

    # ============================================================
    # 🔥 7. TEACHER_SUBJECTS TABLE
    # ============================================================
    op.add_column('teacher_subjects', sa.Column('is_main_teacher', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('teacher_subjects', sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('teacher_subjects', sa.Column('start_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))
    op.add_column('teacher_subjects', sa.Column('end_date', sa.DateTime(timezone=True), nullable=True))

    # ============================================================
    # 🔥 8. TEACHERS TABLE
    # ============================================================
    op.alter_column('teachers', 'role',
                    existing_type=sa.TEXT(),
                    type_=sa.String(length=50),
                    existing_nullable=False)
    
    op.alter_column('teachers', 'status',
                    existing_type=sa.VARCHAR(length=20),
                    nullable=False,
                    existing_server_default=sa.text("'pending'::character varying"))
    
    op.alter_column('teachers', 'approved_at',
                    existing_type=postgresql.TIMESTAMP(),
                    type_=sa.DateTime(timezone=True),
                    existing_nullable=True)
    
    op.alter_column('teachers', 'updated_at',
                    existing_type=postgresql.TIMESTAMP(),
                    type_=sa.DateTime(timezone=True),
                    existing_nullable=True,
                    existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    
    op.alter_column('teachers', 'transferred_at',
                    existing_type=postgresql.TIMESTAMP(),
                    type_=sa.DateTime(timezone=True),
                    existing_nullable=True)
    
    #op.add_column('teachers', sa.Column('previous_school_id', sa.Integer(), nullable=True))
    
    op.create_foreign_key('fk_teachers_approved_by', 'teachers', 'teachers', ['approved_by'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_teachers_previous_school', 'teachers', 'schools', ['previous_school_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    
    # ============================================================
    # 🔥 REVERT TEACHERS TABLE
    # ============================================================
    op.drop_constraint('fk_teachers_previous_school', 'teachers', type_='foreignkey')
    op.drop_constraint('fk_teachers_approved_by', 'teachers', type_='foreignkey')
    op.drop_column('teachers', 'previous_school_id')
    
    op.alter_column('teachers', 'transferred_at',
                    existing_type=sa.DateTime(timezone=True),
                    type_=postgresql.TIMESTAMP(),
                    existing_nullable=True)
    op.alter_column('teachers', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    type_=postgresql.TIMESTAMP(),
                    existing_nullable=True,
                    existing_server_default=sa.text('CURRENT_TIMESTAMP'))
    op.alter_column('teachers', 'approved_at',
                    existing_type=sa.DateTime(timezone=True),
                    type_=postgresql.TIMESTAMP(),
                    existing_nullable=True)
    op.alter_column('teachers', 'status',
                    existing_type=sa.VARCHAR(length=20),
                    nullable=True,
                    existing_server_default=sa.text("'pending'::character varying"))
    op.alter_column('teachers', 'role',
                    existing_type=sa.String(length=50),
                    type_=sa.TEXT(),
                    existing_nullable=False)

    # ============================================================
    # 🔥 REVERT TEACHER_SUBJECTS TABLE
    # ============================================================
    op.drop_column('teacher_subjects', 'end_date')
    op.drop_column('teacher_subjects', 'start_date')
    op.drop_column('teacher_subjects', 'is_active')
    op.drop_column('teacher_subjects', 'is_main_teacher')

    # ============================================================
    # 🔥 REVERT SUBJECTS TABLE
    # ============================================================
    op.drop_column('subjects', 'display_order')
    op.drop_column('subjects', 'is_required')
    op.drop_column('subjects', 'is_calculated')
    op.drop_column('subjects', 'level')
    op.drop_column('subjects', 'subject_type')

    # ============================================================
    # 🔥 REVERT STUDENTS TABLE
    # ============================================================
    op.create_unique_constraint(
        'unique_roll_number_per_class', 
        'students', 
        ['roll_number', 'class_id', 'school_id']
    )

    # ============================================================
    # 🔥 REVERT STUDENT_REPORTS TABLE
    # ============================================================
    op.add_column('student_reports', sa.Column('remarks', sa.VARCHAR(length=255), nullable=True))
    op.drop_constraint('fk_reports_class_id', 'student_reports', type_='foreignkey')
    op.drop_constraint('fk_reports_stream_id', 'student_reports', type_='foreignkey')
    op.drop_index('ix_report_year', table_name='student_reports')
    op.drop_index('ix_report_exam_type', table_name='student_reports')
    op.drop_index('ix_class_term_year', table_name='student_reports')
    op.alter_column('student_reports', 'division',
                    existing_type=sa.VARCHAR(length=5),
                    nullable=False)
    op.alter_column('student_reports', 'points',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.drop_column('student_reports', 'updated_at')
    op.drop_column('student_reports', 'headmaster_remarks')
    op.drop_column('student_reports', 'teacher_remarks')
    op.drop_column('student_reports', 'total_students')
    op.drop_column('student_reports', 'exam_type')
    op.drop_column('student_reports', 'stream_id')
    op.drop_column('student_reports', 'class_id')

    # ============================================================
    # 🔥 REVERT PAYMENT_TRANSACTIONS TABLE
    # ============================================================
    op.drop_constraint('fk_payment_created_by', 'payment_transactions', type_='foreignkey')
    op.drop_constraint('fk_payment_school_id', 'payment_transactions', type_='foreignkey')
    op.create_foreign_key('payment_transactions_school_id_fkey', 'payment_transactions', 'schools', ['school_id'], ['id'])
    op.drop_constraint('uq_payment_reference', 'payment_transactions', type_='unique')
    op.drop_index('ix_payment_transactions_reference_number', table_name='payment_transactions')
    op.drop_column('payment_transactions', 'completed_at')
    op.drop_column('payment_transactions', 'created_by')
    op.drop_column('payment_transactions', 'subscription_end')
    op.drop_column('payment_transactions', 'subscription_start')
    op.drop_column('payment_transactions', 'error_message')
    op.drop_column('payment_transactions', 'response_data')
    op.drop_column('payment_transactions', 'request_data')
    op.drop_column('payment_transactions', 'provider_reference')
    op.drop_column('payment_transactions', 'reference_number')
    op.drop_column('payment_transactions', 'payment_method')
    op.drop_column('payment_transactions', 'customer_email')
    op.drop_column('payment_transactions', 'customer_name')

    # ============================================================
    # 🔥 REVERT MARKS TABLE
    # ============================================================
    op.drop_constraint('fk_marks_class_id', 'marks', type_='foreignkey')
    op.drop_constraint('fk_marks_stream_id', 'marks', type_='foreignkey')
    op.drop_constraint('fk_marks_teacher_id', 'marks', type_='foreignkey')
    op.create_foreign_key('marks_teacher_id_fkey', 'marks', 'teachers', ['teacher_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('unique_mark_per_exam_year_class', 'marks', type_='unique')
    op.create_unique_constraint('unique_mark_per_exam', 'marks', ['student_id', 'subject_id', 'teacher_id', 'exam_type'])
    op.alter_column('marks', 'teacher_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.drop_column('marks', 'stream_id')
    op.drop_column('marks', 'year')
    op.drop_column('marks', 'class_id')