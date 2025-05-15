# 이미지 처리 유틸리티
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
import logging
from PIL import Image, ImageOps
import io

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class ImageProcessor:
    """이미지 처리 클래스"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # 지원되는 이미지 형식
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.webp'}
        
        # 최대 이미지 크기 설정
        self.max_dimension = 2048  # 최대 가로/세로 크기
        self.compression_quality = 85  # JPEG 압축 품질
    
    def validate_image(self, file_data: bytes, filename: str) -> bool:
        """이미지 파일 검증"""
        try:
            # 파일 확장자 검증
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.supported_formats:
                logger.warning(f"지원하지 않는 이미지 형식: {file_ext}")
                return False
            
            # 이미지 데이터 검증
            image = Image.open(io.BytesIO(file_data))
            image.verify()
            
            return True
            
        except Exception as e:
            logger.error(f"이미지 검증 실패: {e}")
            return False
    
    def process_image(self, file_data: bytes, filename: str) -> Tuple[str, str]:
        """
        이미지 처리 및 저장
        Returns: (저장된 파일 경로, 파일명)
        """
        try:
            # 이미지 로드
            image = Image.open(io.BytesIO(file_data))
            
            # EXIF 정보에 따른 회전 보정
            image = ImageOps.exif_transpose(image)
            
            # RGB 변환 (RGBA나 다른 모드인 경우)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 크기 조정 (필요한 경우)
            image = self._resize_image(image)
            
            # 파일명 생성
            unique_filename = self._generate_unique_filename(filename)
            file_path = self.upload_dir / unique_filename
            
            # 이미지 저장
            image.save(
                file_path,
                'JPEG',
                quality=self.compression_quality,
                optimize=True
            )
            
            logger.info(f"이미지 처리 완료: {unique_filename}")
            return str(file_path), unique_filename
            
        except Exception as e:
            logger.error(f"이미지 처리 실패: {e}")
            raise
    
    def _resize_image(self, image: Image.Image) -> Image.Image:
        """이미지 크기 조정"""
        width, height = image.size
        
        # 최대 크기를 넘지 않는 경우 그대로 반환
        if width <= self.max_dimension and height <= self.max_dimension:
            return image
        
        # 비율을 유지하면서 크기 조정
        ratio = min(self.max_dimension / width, self.max_dimension / height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        logger.info(f"이미지 크기 조정: {width}x{height} -> {new_width}x{new_height}")
        return resized_image
    
    def _generate_unique_filename(self, original_filename: str) -> str:
        """고유한 파일명 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_ext = Path(original_filename).suffix.lower()
        
        # 원본 파일명에서 안전하지 않은 문자 제거
        safe_name = "".join(c for c in Path(original_filename).stem if c.isalnum() or c in '_-')[:20]
        
        return f"{timestamp}_{unique_id}_{safe_name}{file_ext}"
    
    def delete_image(self, file_path: str) -> bool:
        """이미지 파일 삭제"""
        try:
            file_path_obj = Path(file_path)
            if file_path_obj.exists():
                file_path_obj.unlink()
                logger.info(f"이미지 삭제 완료: {file_path}")
                return True
            else:
                logger.warning(f"삭제할 파일이 없습니다: {file_path}")
                return False
        except Exception as e:
            logger.error(f"이미지 삭제 실패: {e}")
            return False
    
    def get_image_info(self, file_path: str) -> Optional[dict]:
        """이미지 정보 조회"""
        try:
            with Image.open(file_path) as image:
                return {
                    'width': image.width,
                    'height': image.height,
                    'format': image.format,
                    'mode': image.mode,
                    'size_bytes': os.path.getsize(file_path)
                }
        except Exception as e:
            logger.error(f"이미지 정보 조회 실패: {e}")
            return None

# 이미지 처리 함수들
def save_uploaded_images(files: List, upload_dir: str = "uploads") -> List[str]:
    """업로드된 이미지들을 처리하고 저장"""
    processor = ImageProcessor(upload_dir)
    saved_paths = []
    
    for file in files:
        try:
            # 파일 내용 읽기
            file_data = file.file.read()
            file.file.seek(0)  # 파일 포인터 초기화
            
            # 이미지 검증
            if not processor.validate_image(file_data, file.filename):
                logger.warning(f"유효하지 않은 이미지: {file.filename}")
                continue
            
            # 파일 크기 검증
            if len(file_data) > settings.MAX_FILE_SIZE:
                logger.warning(f"파일 크기 초과: {file.filename} ({len(file_data)} bytes)")
                continue
            
            # 이미지 처리 및 저장
            file_path, filename = processor.process_image(file_data, file.filename)
            saved_paths.append(file_path)
            
        except Exception as e:
            logger.error(f"이미지 저장 실패: {file.filename}, {e}")
            continue
    
    return saved_paths

def create_thumbnail(image_path: str, thumbnail_size: Tuple[int, int] = (200, 200)) -> str:
    """썸네일 생성"""
    try:
        with Image.open(image_path) as image:
            # 썸네일 생성
            image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            # 썸네일 파일명 생성
            path_obj = Path(image_path)
            thumbnail_path = path_obj.parent / f"{path_obj.stem}_thumb{path_obj.suffix}"
            
            # 썸네일 저장
            image.save(thumbnail_path, 'JPEG', quality=80)
            
            return str(thumbnail_path)
            
    except Exception as e:
        logger.error(f"썸네일 생성 실패: {e}")
        return image_path

def validate_uploaded_file(file, max_size_mb: int = 5) -> Tuple[bool, str]:
    """업로드된 파일 검증"""
    # 파일 크기 검증
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # 파일 내용 읽기
    file_content = file.file.read()
    file.file.seek(0)  # 파일 포인터 초기화
    
    if len(file_content) > max_size_bytes:
        return False, f"파일 크기가 {max_size_mb}MB를 초과합니다"
    
    # 파일 형식 검증
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        return False, f"지원하지 않는 파일 형식입니다. 허용 형식: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
    
    # 이미지 파일 검증
    try:
        image = Image.open(io.BytesIO(file_content))
        image.verify()
    except Exception:
        return False, "유효하지 않은 이미지 파일입니다"
    
    return True, "검증 완료"

def cleanup_old_images(upload_dir: str = "uploads", days: int = 30):
    """오래된 이미지 파일 정리"""
    upload_path = Path(upload_dir)
    cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
    
    deleted_count = 0
    for file_path in upload_path.glob("*.jpg"):
        try:
            if file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1
        except Exception as e:
            logger.error(f"파일 삭제 실패: {file_path}, {e}")
    
    logger.info(f"{deleted_count}개의 오래된 이미지 파일 삭제 완료")

# 전역 이미지 처리기 인스턴스
image_processor = ImageProcessor()