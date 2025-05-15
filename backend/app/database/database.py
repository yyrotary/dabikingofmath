# 데이터베이스 연결 및 초기화
import sqlite3
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 데이터베이스 파일 경로
DB_PATH = "mathapp.db"

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """데이터베이스 연결 컨텍스트 매니저"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 딕셔너리처럼 접근 가능
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    """데이터베이스 초기화 및 테이블 생성"""
    logger.info("데이터베이스 초기화 시작...")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 사용자 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL DEFAULT '다비',
            grade VARCHAR(10) DEFAULT '고2-1',
            password_hash VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 문제 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(200) NOT NULL,
            content TEXT NOT NULL,
            solution TEXT,
            difficulty_level INTEGER CHECK(difficulty_level BETWEEN 1 AND 10),
            topic VARCHAR(50) NOT NULL,
            subtopic VARCHAR(100),
            estimated_time INTEGER,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 미션 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            status VARCHAR(20) CHECK(status IN ('pending', 'in_progress', 'completed')) DEFAULT 'pending',
            total_problems INTEGER NOT NULL,
            completed_problems INTEGER DEFAULT 0,
            target_score INTEGER,
            actual_score INTEGER,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # 미션-문제 연결 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mission_problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id INTEGER NOT NULL,
            problem_id INTEGER NOT NULL,
            sequence_order INTEGER NOT NULL,
            is_completed BOOLEAN DEFAULT FALSE,
            completed_at TIMESTAMP,
            FOREIGN KEY (mission_id) REFERENCES missions(id),
            FOREIGN KEY (problem_id) REFERENCES problems(id),
            UNIQUE(mission_id, sequence_order)
        )
        ''')
        
        # 답안 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mission_id INTEGER NOT NULL,
            problem_id INTEGER NOT NULL,
            answer_images TEXT,
            extracted_text TEXT,
            extracted_markdown TEXT,
            score INTEGER CHECK(score BETWEEN 0 AND 100),
            ai_feedback TEXT,
            key_concepts_identified TEXT,
            mistakes_detected TEXT,
            time_spent INTEGER,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scored_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (mission_id) REFERENCES missions(id),
            FOREIGN KEY (problem_id) REFERENCES problems(id)
        )
        ''')
        
        # 학습 분석 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mission_id INTEGER,
            metric_type VARCHAR(50) NOT NULL,
            metric_value REAL NOT NULL,
            topic VARCHAR(50),
            subtopic VARCHAR(100),
            analysis_data TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (mission_id) REFERENCES missions(id)
        )
        ''')
        
        # 학습 히스토리 테이블
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            total_study_time INTEGER,
            problems_solved INTEGER,
            average_score REAL,
            topics_covered TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, date)
        )
        ''')
        
        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_problems_topic ON problems(topic)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_problems_difficulty ON problems(difficulty_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_missions_user_status ON missions(user_id, status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_answers_user_mission ON answers(user_id, mission_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_user_topic ON learning_analytics(user_id, topic)')
        
        conn.commit()
        logger.info("데이터베이스 테이블 생성 완료")
        
        # 초기 데이터 생성
        _create_initial_data(cursor, conn)

def _create_initial_data(cursor: sqlite3.Cursor, conn: sqlite3.Connection):
    """초기 데이터 생성"""
    # 기본 사용자 생성 (다비님)
    cursor.execute("SELECT COUNT(*) FROM users WHERE name = ?", (settings.DEFAULT_USER_NAME,))
    if cursor.fetchone()[0] == 0:
        from app.utils.security import get_password_hash
        password_hash = get_password_hash(settings.DEFAULT_USER_PASSWORD)
        
        cursor.execute(
            "INSERT INTO users (name, grade, password_hash) VALUES (?, ?, ?)",
            (settings.DEFAULT_USER_NAME, "고2-1", password_hash)
        )
        logger.info(f"기본 사용자 '{settings.DEFAULT_USER_NAME}' 생성 완료")
    
    # 문제 데이터 로드
    _load_problems_from_json(cursor)
    
    conn.commit()

def _load_problems_from_json(cursor: sqlite3.Cursor):
    """JSON 파일에서 문제 데이터 로드"""
    problems_file = Path("data/problems_sequences.json")
    
    if not problems_file.exists():
        logger.warning(f"문제 데이터 파일을 찾을 수 없습니다: {problems_file}")
        return
    
    # 기존 문제가 있는지 확인
    cursor.execute("SELECT COUNT(*) FROM problems")
    if cursor.fetchone()[0] > 0:
        logger.info("이미 문제 데이터가 존재합니다. 스킵...")
        return
    
    try:
        with open(problems_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        problems = data.get('problems', [])
        
        for problem in problems:
            cursor.execute('''
            INSERT INTO problems (
                title, content, solution, difficulty_level, 
                topic, subtopic, estimated_time, keywords
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                problem['title'],
                problem['content'],
                problem['solution'],
                problem['difficulty_level'],
                problem['topic'],
                problem.get('subtopic'),
                problem.get('estimated_time'),
                json.dumps(problem.get('keywords', []))
            ))
        
        logger.info(f"{len(problems)}개의 문제 데이터 로드 완료")
        
    except Exception as e:
        logger.error(f"문제 데이터 로드 실패: {e}")

def reset_db():
    """데이터베이스 초기화 (모든 데이터 삭제 후 재생성)"""
    logger.warning("데이터베이스 리셋 중...")
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        logger.info("기존 데이터베이스 파일 삭제됨")
    
    init_db()
    logger.info("데이터베이스 리셋 완료")

def backup_db(backup_path: str = None):
    """데이터베이스 백업"""
    if backup_path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"mathapp_backup_{timestamp}.db"
    
    if os.path.exists(DB_PATH):
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"데이터베이스 백업 완료: {backup_path}")
    else:
        logger.error("백업할 데이터베이스 파일이 없습니다")

# 데이터베이스 연결 테스트
def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            logger.info("데이터베이스 연결 테스트 성공")
            return True
    except Exception as e:
        logger.error(f"데이터베이스 연결 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    # 직접 실행시 데이터베이스 초기화
    init_db()
    test_connection()