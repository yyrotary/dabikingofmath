# AI 서비스 (Gemini API 연동)
import asyncio
import json
import re
import logging
from typing import List, Optional, Dict, Any
import google.generativeai as genai

from app.config import get_settings
from app.models import Problem, Answer, AIScoreResult

logger = logging.getLogger(__name__)
settings = get_settings()

class AIService:
    """AI 기반 수학 답안 처리 서비스"""
    
    def __init__(self):
        # Gemini API 설정
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        
        # 프롬프트 템플릿
        self.extraction_prompt = """
        다음 이미지는 학생이 작성한 수학 문제의 답안입니다.
        이미지에서 텍스트와 수학 기호를 정확히 추출하여 마크다운 형식으로 변환해주세요.

        추출 규칙:
        1. 수학 기호는 LaTeX 형식으로 표현 ($...$)
        2. 분수는 \\frac{분자}{분모} 형식
        3. 제곱근은 \\sqrt{} 형식
        4. 그리스 문자, 첨자, 위첨자 포함
        5. 계산 과정의 단계를 명확히 구분

        출력 형식:
        ```markdown
        [추출된 답안 내용]
        ```
        """
        
        self.scoring_prompt = """
        다음은 수학 문제와 학생의 답안입니다.

        **문제:**
        {problem_content}

        **정답:**
        {solution}

        **학생 답안:**
        {student_answer}

        다음 기준으로 답안을 채점하고 분석해주세요:

        1. **정답 여부**: 최종 답이 정확한지 확인
        2. **풀이 과정**: 각 단계가 논리적이고 올바른지 검증
        3. **개념 이해**: 사용된 수학적 개념과 공식의 정확성
        4. **실수 분석**: 발견된 오류와 그 원인
        5. **부분 점수**: 맞는 부분에 대한 인정

        응답 형식 (JSON):
        {{
            "score": 점수 (0-100),
            "is_correct": true/false,
            "step_analysis": [
                {{
                    "step": "단계 설명",
                    "is_correct": true/false,
                    "points": 부분점수,
                    "comment": "평가 내용"
                }}
            ],
            "concept_understanding": [
                "이해한 개념1",
                "이해한 개념2"
            ],
            "mistakes_detected": [
                "실수1",
                "실수2"
            ],
            "feedback": "종합 피드백",
            "suggestions": [
                "개선 제안1",
                "개선 제안2"
            ]
        }}
        """
        
        self.feedback_prompt = """
        다음은 학생의 수학 답안 채점 결과입니다.

        **점수:** {score}/100
        **문제 주제:** {topic}
        **난이도:** {difficulty}/10

        **채점 분석:**
        {score_analysis}

        다음 관점에서 학습자에게 도움이 되는 개인화된 피드백을 작성해주세요:

        1. **긍정적 부분**: 잘한 점과 이해한 개념
        2. **개선 영역**: 부족한 부분과 실수 분석
        3. **학습 방향**: 다음에 연습해야 할 내용
        4. **격려 메시지**: 동기부여가 되는 응원

        피드백은 친근하고 격려적인 톤으로 작성하되, 구체적이고 실용적인 조언을 포함해주세요.
        """
    
    async def extract_text_from_images(self, image_paths: List[str]) -> str:
        """이미지에서 수학 답안 텍스트 추출"""
        try:
            extracted_texts = []
            
            for image_path in image_paths:
                logger.info(f"이미지 텍스트 추출 시작: {image_path}")
                
                # 이미지 로드
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                
                # Gemini API 호출
                response = await self._call_gemini_with_image(
                    self.extraction_prompt,
                    image_data
                )
                
                if response:
                    # 마크다운 코드 블록에서 내용 추출
                    text = self._extract_markdown_content(response)
                    extracted_texts.append(text)
                    logger.info(f"텍스트 추출 완료: {len(text)} 문자")
                
            return "\n\n---\n\n".join(extracted_texts)
            
        except Exception as e:
            logger.error(f"이미지 텍스트 추출 실패: {e}")
            return ""
    
    async def score_answer(self, problem: Problem, student_answer: str) -> Dict[str, Any]:
        """답안 채점 및 분석"""
        try:
            logger.info(f"답안 채점 시작: 문제 ID {problem.id}")
            
            # 채점 프롬프트 준비
            prompt = self.scoring_prompt.format(
                problem_content=problem.content,
                solution=problem.solution or "정답이 제공되지 않음",
                student_answer=student_answer
            )
            
            # Gemini API 호출
            response = await self._call_gemini_text(prompt)
            
            # JSON 형식으로 파싱
            try:
                # JSON 부분만 추출
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    # JSON 형식이 아닌 경우 기본값 반환
                    result = {
                        "score": 0,
                        "is_correct": False,
                        "step_analysis": [],
                        "concept_understanding": [],
                        "mistakes_detected": [],
                        "feedback": "채점 중 오류가 발생했습니다.",
                        "suggestions": []
                    }
                
                logger.info(f"답안 채점 완료: {result['score']}점")
                return result
                
            except json.JSONDecodeError:
                logger.error("채점 결과 JSON 파싱 실패")
                return {
                    "score": 0,
                    "is_correct": False,
                    "step_analysis": [],
                    "concept_understanding": [],
                    "mistakes_detected": [],
                    "feedback": "채점 결과를 해석할 수 없습니다.",
                    "suggestions": []
                }
                
        except Exception as e:
            logger.error(f"답안 채점 실패: {e}")
            return {
                "score": 0,
                "is_correct": False,
                "step_analysis": [],
                "concept_understanding": [],
                "mistakes_detected": [str(e)],
                "feedback": "채점 중 오류가 발생했습니다.",
                "suggestions": []
            }
    
    async def generate_feedback(self, score_result: Dict[str, Any], problem: Problem) -> str:
        """개인화된 학습 피드백 생성"""
        try:
            logger.info("개인화된 피드백 생성 시작")
            
            # 피드백 프롬프트 준비
            prompt = self.feedback_prompt.format(
                score=score_result['score'],
                topic=problem.topic,
                difficulty=problem.difficulty_level,
                score_analysis=json.dumps(score_result, ensure_ascii=False, indent=2)
            )
            
            # Gemini API 호출
            feedback = await self._call_gemini_text(prompt)
            
            logger.info("피드백 생성 완료")
            return feedback
            
        except Exception as e:
            logger.error(f"피드백 생성 실패: {e}")
            return "죄송합니다. 피드백 생성 중 오류가 발생했습니다."
    
    async def analyze_learning_pattern(self, user_id: int, recent_answers: List[Answer]) -> Dict[str, Any]:
        """학습 패턴 분석"""
        try:
            logger.info(f"사용자 {user_id}의 학습 패턴 분석 시작")
            
            if not recent_answers:
                return {
                    "pattern_analysis": "분석할 데이터가 부족합니다.",
                    "recommendations": ["더 많은 문제를 풀어보세요."]
                }
            
            # 최근 답안들의 패턴 분석
            analysis_data = {
                "scores": [ans.score for ans in recent_answers if ans.score is not None],
                "topics": [ans.problem_id for ans in recent_answers],  # 실제로는 문제의 주제를 가져와야 함
                "mistakes": []
            }
            
            # 실수 패턴 수집
            for answer in recent_answers:
                if answer.mistakes_detected:
                    analysis_data["mistakes"].extend(answer.mistakes_detected)
            
            # AI 분석 요청
            prompt = f"""
            다음은 학습자의 최근 수학 답안 데이터입니다:

            점수 분포: {analysis_data['scores']}
            주요 실수: {analysis_data['mistakes'][:10]}

            이 데이터를 바탕으로 다음을 분석해주세요:
            1. 학습 패턴과 강약점
            2. 반복되는 실수 유형
            3. 개선을 위한 구체적 제안
            4. 다음 학습 방향

            JSON 형식으로 응답해주세요:
            {{
                "pattern_analysis": "패턴 분석 내용",
                "strengths": ["강점1", "강점2"],
                "weaknesses": ["약점1", "약점2"],
                "recommendations": ["제안1", "제안2"],
                "next_focus_areas": ["영역1", "영역2"]
            }}
            """
            
            response = await self._call_gemini_text(prompt)
            
            # JSON 파싱
            try:
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    logger.info("학습 패턴 분석 완료")
                    return result
            except:
                pass
            
            # 파싱 실패시 기본 응답
            return {
                "pattern_analysis": "분석을 완료했습니다.",
                "strengths": [],
                "weaknesses": [],
                "recommendations": ["꾸준한 연습을 계속하세요."],
                "next_focus_areas": []
            }
            
        except Exception as e:
            logger.error(f"학습 패턴 분석 실패: {e}")
            return {
                "pattern_analysis": "분석 중 오류가 발생했습니다.",
                "recommendations": ["나중에 다시 시도해주세요."]
            }
    
    async def _call_gemini_with_image(self, prompt: str, image_data: bytes) -> str:
        """Gemini API에 이미지와 함께 요청"""
        try:
            # 이미지 프롬프트 생성
            response = self.model.generate_content([
                prompt,
                {'mime_type': 'image/jpeg', 'data': image_data}
            ])
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API (이미지) 호출 실패: {e}")
            return ""
    
    async def _call_gemini_text(self, prompt: str) -> str:
        """Gemini API에 텍스트만 요청"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API (텍스트) 호출 실패: {e}")
            return ""
    
    def _extract_markdown_content(self, text: str) -> str:
        """마크다운 코드 블록에서 내용 추출"""
        # ```markdown ... ``` 형식에서 내용 추출
        pattern = r'```markdown\s*(.*?)\s*```'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        else:
            # 코드 블록이 없으면 전체 텍스트 반환
            return text.strip()

# 싱글톤 AI 서비스 인스턴스
ai_service = AIService()