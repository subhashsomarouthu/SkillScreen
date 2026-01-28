"""
Migration script to add interview_settings column to job_positions table
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import DBFactory

def add_interview_settings_column():
    """Add interview_settings JSONB column to job_positions table"""

    sql = """
    -- Add interview_settings column to job_positions table
    ALTER TABLE job_positions
    ADD COLUMN IF NOT EXISTS interview_settings JSONB DEFAULT '{}';

    -- Add comment explaining the column
    COMMENT ON COLUMN job_positions.interview_settings IS
    'Interview configuration including coding round settings: {has_coding_round, coding_question_ids, coding_time_limit, allowed_languages, qa_question_count, etc.}';
    """

    session = DBFactory.get_session()
    try:
        session.execute(sql)
        session.commit()
        print("Successfully added interview_settings column to job_positions table")
    except Exception as e:
        session.rollback()
        print(f"Error adding column: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    DBFactory.init()
    add_interview_settings_column()
