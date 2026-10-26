"""차마트 Gemini Vision AI 통합 서비스 모듈 (DIRECTIVE 050-C).

명함 이미지 인식(CRM 연동), 거래서류(매매계약서, 정산서, 입출금내역) 분석,
API 키 마스킹 보안, 일일 사용량 및 추정 비용 감사 로깅을 총괄합니다.
"""

from __future__ import annotations

import base64
import datetime
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from chaficial.platform.db import GeminiUsageLog, SessionLocal
from chaficial.platform.models import CustomerCandidate, TransactionDocumentExtract

# ----------------------------------------------------
# 전역 설정 및 인메모리 통계 버퍼
# ----------------------------------------------------
DEFAULT_PRIMARY_MODEL = "gemini-flash-latest"
DEFAULT_FALLBACK_MODEL = "gemini-flash-lite"

_MEMORY_USAGE_STATS = {
    "total_calls": 0,
    "successful_calls": 0,
    "failed_calls": 0,
    "total_prompt_tokens": 0,
    "total_candidate_tokens": 0,
    "estimated_cost_usd": 0.0,
    "last_called_at": None,
    "last_error": None,
}


class GeminiVisionService:
    """Google Gemini Vision API 공통 클라이언트 및 비즈니스 로직."""

    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """환경변수 및 .env에서 GEMINI_API_KEY 로드."""
        key = os.environ.get("GEMINI_API_KEY")
        if key and key.strip():
            return key.strip()

        # .env 파일에서 직접 확인
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        os.environ["GEMINI_API_KEY"] = val
                        return val
        return None

    @classmethod
    def get_masked_key(cls, key: Optional[str] = None) -> Optional[str]:
        """보안 준수를 위해 API 키의 앞 4자리와 뒤 4자리만 노출하고 중간을 마스킹."""
        k = key or cls.get_api_key()
        if not k:
            return None
        if len(k) <= 8:
            return "****"
        return f"{k[:4]}...{k[-4:]}"

    @classmethod
    def has_api_key(cls) -> bool:
        """유효한 API 키가 설정되어 있는지 여부."""
        return bool(cls.get_api_key())

    @classmethod
    def get_models(cls) -> dict[str, str]:
        """현재 설정된 주/폴백 모델 반환."""
        primary = os.environ.get("GEMINI_VISION_MODEL", DEFAULT_PRIMARY_MODEL)
        fallback = os.environ.get("GEMINI_VISION_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL)
        return {
            "primary_model": primary,
            "fallback_model": fallback,
        }

    @classmethod
    def save_settings(
        cls,
        api_key: Optional[str] = None,
        primary_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
    ) -> dict[str, Any]:
        """관리자 화면에서 설정한 API 키와 모델을 .env 및 환경변수에 영구 저장."""
        env_path = Path(".env")
        lines = []
        if env_path.exists():
            lines = env_path.read_text(encoding="utf-8").splitlines()

        updated_keys = set()
        new_lines = []

        target_updates = {}
        if api_key and api_key.strip():
            target_updates["GEMINI_API_KEY"] = api_key.strip()
            os.environ["GEMINI_API_KEY"] = api_key.strip()
        if primary_model and primary_model.strip():
            target_updates["GEMINI_VISION_MODEL"] = primary_model.strip()
            os.environ["GEMINI_VISION_MODEL"] = primary_model.strip()
        if fallback_model and fallback_model.strip():
            target_updates["GEMINI_VISION_FALLBACK_MODEL"] = fallback_model.strip()
            os.environ["GEMINI_VISION_FALLBACK_MODEL"] = fallback_model.strip()

        for line in lines:
            stripped = line.strip()
            handled = False
            for k, v in target_updates.items():
                if stripped.startswith(f"{k}=") or stripped == k:
                    new_lines.append(f"{k}={v}")
                    updated_keys.add(k)
                    handled = True
                    break
            if not handled:
                new_lines.append(line)

        for k, v in target_updates.items():
            if k not in updated_keys:
                new_lines.append(f"{k}={v}")

        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return {
            "ok": True,
            "masked_key": cls.get_masked_key(),
            "has_key": cls.has_api_key(),
            "models": cls.get_models(),
        }

    @classmethod
    def get_stats(cls, db: Optional[Session] = None) -> dict[str, Any]:
        """Gemini Vision 호출 통계 및 비용 추정치 반환."""
        total = _MEMORY_USAGE_STATS["total_calls"]
        success = _MEMORY_USAGE_STATS["successful_calls"]
        failed = _MEMORY_USAGE_STATS["failed_calls"]
        rate = round((success / total * 100), 1) if total > 0 else 100.0

        stats = {
            "has_key": cls.has_api_key(),
            "masked_key": cls.get_masked_key(),
            "primary_model": cls.get_models()["primary_model"],
            "fallback_model": cls.get_models()["fallback_model"],
            "total_calls": total,
            "successful_calls": success,
            "failed_calls": failed,
            "success_rate_pct": rate,
            "total_prompt_tokens": _MEMORY_USAGE_STATS["total_prompt_tokens"],
            "total_candidate_tokens": _MEMORY_USAGE_STATS["total_candidate_tokens"],
            "estimated_cost_usd": round(_MEMORY_USAGE_STATS["estimated_cost_usd"], 4),
            "estimated_cost_krw": int(_MEMORY_USAGE_STATS["estimated_cost_usd"] * 1400),
            "last_called_at": _MEMORY_USAGE_STATS["last_called_at"],
            "last_error": _MEMORY_USAGE_STATS["last_error"],
        }

        # DB에 로그가 있으면 최근 통계와 병합
        if db:
            try:
                db_count = db.query(GeminiUsageLog).count()
                if db_count > 0:
                    stats["db_logged_calls"] = db_count
            except Exception:
                pass

        return stats

    @classmethod
    def record_usage(
        cls,
        task_type: str,
        model_used: str,
        prompt_tokens: int = 0,
        candidate_tokens: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        exec_ms: int = 0,
        db: Optional[Session] = None,
    ) -> None:
        """호출 통계 및 비용 기록 (인메모리 및 DB)."""
        # Flash 비용 산정 기준 (입력 $0.075/1M 토큰, 출력 $0.30/1M 토큰)
        cost = (prompt_tokens * 0.000000075) + (candidate_tokens * 0.00000030)
        if cost == 0.0 and success:
            cost = 0.00015  # 기본 고정 단가 추정

        _MEMORY_USAGE_STATS["total_calls"] += 1
        if success:
            _MEMORY_USAGE_STATS["successful_calls"] += 1
        else:
            _MEMORY_USAGE_STATS["failed_calls"] += 1
            _MEMORY_USAGE_STATS["last_error"] = error_message

        _MEMORY_USAGE_STATS["total_prompt_tokens"] += prompt_tokens
        _MEMORY_USAGE_STATS["total_candidate_tokens"] += candidate_tokens
        _MEMORY_USAGE_STATS["estimated_cost_usd"] += cost
        _MEMORY_USAGE_STATS["last_called_at"] = datetime.datetime.utcnow().isoformat()

        # DB 감사 로그 저장
        def _write_db(sess: Session):
            try:
                log = GeminiUsageLog(
                    task_type=task_type,
                    model_used=model_used,
                    prompt_tokens=prompt_tokens,
                    candidate_tokens=candidate_tokens,
                    estimated_cost_usd=cost,
                    success=success,
                    error_message=error_message,
                    execution_time_ms=exec_ms,
                )
                sess.add(log)
                sess.commit()
            except Exception as e:
                sess.rollback()
                print(f"[GeminiVisionService] DB 감사 로그 저장 실패 (무시됨): {e}")

        if db:
            _write_db(db)
        else:
            try:
                with SessionLocal() as s:
                    _write_db(s)
            except Exception:
                pass

    @classmethod
    def _call_gemini_api(
        cls,
        model: str,
        api_key: str,
        parts: list[dict[str, Any]],
        system_instruction: Optional[str] = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Google Gemini REST API 저수준 호출 및 응답 JSON 파싱."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        contents = [{"parts": parts}]
        body: dict[str, Any] = {"contents": contents}

        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # JSON 구조화 출력 유도 파라미터
        body["generationConfig"] = {
            "responseMimeType": "application/json",
            "temperature": 0.1,
        }

        data_bytes = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_bytes = resp.read()
            return json.loads(resp_bytes.decode("utf-8"))

    @classmethod
    def test_connection(
        cls,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """관리자 화면 연결 테스트 (API 키 유효성 및 응답 시간 측정)."""
        key = api_key or cls.get_api_key()
        if not key:
            return {
                "ok": False,
                "status": "API_KEY_REQUIRED",
                "message": "등록된 Gemini API 키가 없습니다. 키를 입력한 후 다시 테스트하십시오.",
            }

        target_model = model or cls.get_models()["primary_model"]
        start_t = time.time()
        try:
            # 간단한 ping 요청
            parts = [{"text": 'Respond with JSON: {"status": "ok", "message": "차마트 Gemini Vision AI 연결 성공"}'}]
            resp = cls._call_gemini_api(target_model, key, parts, timeout=10)
            elapsed_ms = int((time.time() - start_t) * 1000)

            # 응답 파싱
            text_resp = (
                resp.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "{}")
            )
            parsed = json.loads(text_resp)

            cls.record_usage(
                task_type="TEST_CONNECTION",
                model_used=target_model,
                prompt_tokens=20,
                candidate_tokens=20,
                success=True,
                exec_ms=elapsed_ms,
            )

            return {
                "ok": True,
                "status": "CONNECTED",
                "model": target_model,
                "elapsed_ms": elapsed_ms,
                "masked_key": cls.get_masked_key(key),
                "message": parsed.get("message", "연결 성공"),
            }
        except urllib.error.HTTPError as e:
            elapsed_ms = int((time.time() - start_t) * 1000)
            err_body = e.read().decode("utf-8", errors="ignore")
            cls.record_usage(
                task_type="TEST_CONNECTION",
                model_used=target_model,
                success=False,
                error_message=f"HTTP {e.code}: {err_body[:100]}",
                exec_ms=elapsed_ms,
            )
            return {
                "ok": False,
                "status": "ERROR",
                "http_code": e.code,
                "message": f"Gemini API 오류 (HTTP {e.code}): API 키의 유효성을 확인하십시오.",
                "details": err_body[:200],
            }
        except Exception as e:
            elapsed_ms = int((time.time() - start_t) * 1000)
            cls.record_usage(
                task_type="TEST_CONNECTION",
                model_used=target_model,
                success=False,
                error_message=str(e),
                exec_ms=elapsed_ms,
            )
            return {
                "ok": False,
                "status": "ERROR",
                "message": f"연결 테스트 실패: {str(e)}",
            }

    @classmethod
    def analyze_business_card(
        cls,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        is_mock: bool = False,
    ) -> dict[str, Any]:
        """명함 이미지 분석 및 CustomerCandidate 구조화 데이터 추출."""
        key = cls.get_api_key()
        if not key and not is_mock:
            return {
                "ok": False,
                "status": "API_KEY_REQUIRED",
                "message": "Gemini API 키가 설정되지 않았습니다. 관리자 설정에서 키를 등록하십시오.",
            }

        start_t = time.time()

        # 모의 테스트 모드 지원 (키가 없거나 오프라인/테스트 스위트용)
        if is_mock or not key:
            time.sleep(0.05)
            # 이미지 바이트 기반 가상 결정론적 샘플 생성
            candidate = CustomerCandidate(
                name="김철수",
                job_title="대표이사",
                company_name="(주)카마스터즈 서울",
                phone="010-8888-9999",
                company_phone="02-2244-1122",
                email="chulsoo.kim@carmasters.kr",
                company_address="서울특별시 동대문구 장한로 120",
                notes="장한평 매매단지 상사 대표 명함 / 쏘렌토 구매 문의",
                confidence=0.98,
            )
            cls.record_usage(
                task_type="BUSINESS_CARD",
                model_used="mock-vision-engine",
                prompt_tokens=150,
                candidate_tokens=120,
                success=True,
                exec_ms=int((time.time() - start_t) * 1000),
            )
            return {
                "ok": True,
                "candidate": candidate.model_dump(),
                "is_mock": True,
                "message": "명함 인식이 완료되었습니다 (테스트 모드).",
            }

        system_instruction = (
            "너는 중고차 운영 플랫폼(CHAMART OS)의 전문 명함 OCR 분석기다. "
            "주어진 한국어/영어 명함 이미지를 정확하게 분석하여 오직 유효한 JSON 형식으로만 응답하라. "
            "마크다운 코드블록이나 불필요한 서문 없이 JSON만 출력하라. "
            "필드 목록: "
            "name(이름, 필수), job_title(직책/직함), company_name(회사명/상호), "
            "phone(휴대전화, 010-XXXX-XXXX 형식 정규화), company_phone(회사 유선전화), "
            "email(이메일), company_address(회사 주소), notes(명함 내 부가 정보), "
            "confidence(인식 신뢰도 0.0~1.0)"
        )

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        parts = [
            {"text": "이 명함 이미지를 분석하여 고객 정보를 JSON으로 추출하라."},
            {
                "inlineData": {
                    "mimeType": mime_type,
                    "data": b64_image,
                }
            },
        ]

        models_to_try = [
            cls.get_models()["primary_model"],
            cls.get_models()["fallback_model"],
        ]

        last_error = None
        for model_name in models_to_try:
            try:
                resp = cls._call_gemini_api(
                    model=model_name,
                    api_key=key,
                    parts=parts,
                    system_instruction=system_instruction,
                    timeout=30,
                )
                raw_text = (
                    resp.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "{}")
                )
                
                # 마크다운 블록 제거
                cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
                cleaned = re.sub(r"\s*```$", "", cleaned)
                data = json.loads(cleaned)

                # 전화번호 필수 검증 및 기본값 처리
                name = str(data.get("name", "이름 미상")).strip()
                phone = str(data.get("phone", "")).strip()
                if not phone:
                    phone = str(data.get("company_phone", "010-0000-0000")).strip()

                candidate = CustomerCandidate(
                    name=name,
                    job_title=data.get("job_title"),
                    company_name=data.get("company_name"),
                    phone=phone,
                    company_phone=data.get("company_phone"),
                    email=data.get("email"),
                    company_address=data.get("company_address"),
                    notes=data.get("notes"),
                    confidence=float(data.get("confidence", 0.95)),
                )

                elapsed_ms = int((time.time() - start_t) * 1000)
                cls.record_usage(
                    task_type="BUSINESS_CARD",
                    model_used=model_name,
                    prompt_tokens=400,
                    candidate_tokens=150,
                    success=True,
                    exec_ms=elapsed_ms,
                )

                return {
                    "ok": True,
                    "candidate": candidate.model_dump(),
                    "model_used": model_name,
                    "elapsed_ms": elapsed_ms,
                    "message": "명함 인식이 완료되었습니다.",
                }
            except Exception as e:
                last_error = e
                continue

        # 모든 모델 실패 시
        elapsed_ms = int((time.time() - start_t) * 1000)
        cls.record_usage(
            task_type="BUSINESS_CARD",
            model_used=models_to_try[0],
            success=False,
            error_message=str(last_error),
            exec_ms=elapsed_ms,
        )
        return {
            "ok": False,
            "status": "PROCESSING_ERROR",
            "message": f"명함 이미지 분석 실패: {str(last_error)}",
        }

    @classmethod
    def analyze_transaction_document(
        cls,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        is_mock: bool = False,
    ) -> dict[str, Any]:
        """거래서류(매매계약서, 정산서, 입출금내역 등) 분석 및 구조화 데이터 추출."""
        key = cls.get_api_key()
        if not key and not is_mock:
            return {
                "ok": False,
                "status": "API_KEY_REQUIRED",
                "message": "Gemini API 키가 설정되지 않았습니다. 관리자 설정에서 키를 등록하십시오.",
            }

        start_t = time.time()

        # 모의 테스트 모드 지원
        if is_mock or not key:
            time.sleep(0.05)
            # 가상 서류 데이터 생성
            extract = TransactionDocumentExtract(
                document_type="CONTRACT",
                transaction_type="SALE",
                transaction_date=datetime.date.today().isoformat(),
                vehicle_plate_number="12가 3456",
                vin="KMHXX81ADNU123456",
                party_name="홍길동",
                party_contact="010-1234-5678",
                dealership_name="차마트 장한평 본사",
                total_amount=2450,  # 2,450만원
                supply_amount=2227,
                vat_amount=223,
                registration_fee=170,
                brokerage_fee=30,
                refurbishment_cost=45,
                has_official_seal=True,
                confidence=0.96,
                summary="자동차 양도증명서 (매매계약서) / 관인 및 직인 확인 완료",
            )
            cls.record_usage(
                task_type="TRANSACTION_DOC",
                model_used="mock-vision-engine",
                prompt_tokens=300,
                candidate_tokens=250,
                success=True,
                exec_ms=int((time.time() - start_t) * 1000),
            )
            return {
                "ok": True,
                "extract": extract.model_dump(),
                "is_mock": True,
                "message": "거래서류 분석이 완료되었습니다 (테스트 모드).",
            }

        system_instruction = (
            "너는 중고차 거래 서류(자동차 양도증명서/매매계약서, 정산서, 성능점검표, 통장 입출금 거래내역)를 분석하는 전문가다. "
            "이미지에서 다음 항목을 엄격하게 판별하여 JSON 형식으로만 응답하라: "
            "1. document_type: CONTRACT(양도증명서), SETTLEMENT(정산서), EXPENSE(비용영수증), BANK_TRANSFER(계좌이체/입출금내역) "
            "2. transaction_type: SALE(판매), PURCHASE(매입), EXPENSE(지출), DEPOSIT(입금) "
            "3. transaction_date: YYYY-MM-DD 형식 "
            "4. vehicle_plate_number: 차량번호 (예: 12가 3456, 없으면 null) "
            "5. vin: 17자리 차대번호 (없으면 null) "
            "6. party_name: 거래 상대방(매수자, 매도자, 입금자 또는 정산처) 성명 "
            "7. party_contact: 연락처 (없으면 null) "
            "8. dealership_name: 상사명 또는 매매상사 "
            "9. total_amount: 총 거래금액 (만원 단위 정수, 예: 25000000원이면 2500) "
            "10. supply_amount, vat_amount, registration_fee, brokerage_fee, refurbishment_cost: 만원 단위 정수 "
            "11. has_official_seal: 관인, 인감도장, 서명 날인 존재 여부 (true/false) "
            "12. confidence: 분석 신뢰도 (0.0 ~ 1.0) "
            "13. summary: 서류 1줄 요약"
        )

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        parts = [
            {"text": "이 중고차 거래 서류 이미지를 정밀 분석하여 JSON 데이터를 추출하라."},
            {
                "inlineData": {
                    "mimeType": mime_type,
                    "data": b64_image,
                }
            },
        ]

        models_to_try = [
            cls.get_models()["primary_model"],
            cls.get_models()["fallback_model"],
        ]

        last_error = None
        for model_name in models_to_try:
            try:
                resp = cls._call_gemini_api(
                    model=model_name,
                    api_key=key,
                    parts=parts,
                    system_instruction=system_instruction,
                    timeout=30,
                )
                raw_text = (
                    resp.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "{}")
                )
                
                cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
                cleaned = re.sub(r"\s*```$", "", cleaned)
                data = json.loads(cleaned)

                # 금액 단위 정규화 (원이면 만원으로 변환)
                tot = int(data.get("total_amount", 0))
                if tot > 100000:  # 원 단위로 들어온 경우 만원으로 환산
                    tot = tot // 10000

                extract = TransactionDocumentExtract(
                    document_type=str(data.get("document_type", "CONTRACT")),
                    transaction_type=str(data.get("transaction_type", "SALE")),
                    transaction_date=str(data.get("transaction_date", datetime.date.today().isoformat())),
                    vehicle_plate_number=data.get("vehicle_plate_number"),
                    vin=data.get("vin"),
                    party_name=str(data.get("party_name", "거래 상대방 미상")),
                    party_contact=data.get("party_contact"),
                    dealership_name=data.get("dealership_name"),
                    total_amount=tot,
                    supply_amount=int(data.get("supply_amount") or (tot * 10 // 11)),
                    vat_amount=int(data.get("vat_amount") or (tot // 11)),
                    registration_fee=int(data.get("registration_fee") or 0),
                    brokerage_fee=int(data.get("brokerage_fee") or 0),
                    refurbishment_cost=int(data.get("refurbishment_cost") or 0),
                    has_official_seal=bool(data.get("has_official_seal", False)),
                    confidence=float(data.get("confidence", 0.90)),
                    summary=data.get("summary", "중고차 거래 서류 분석 완료"),
                )

                elapsed_ms = int((time.time() - start_t) * 1000)
                cls.record_usage(
                    task_type="TRANSACTION_DOC",
                    model_used=model_name,
                    prompt_tokens=500,
                    candidate_tokens=200,
                    success=True,
                    exec_ms=elapsed_ms,
                )

                return {
                    "ok": True,
                    "extract": extract.model_dump(),
                    "model_used": model_name,
                    "elapsed_ms": elapsed_ms,
                    "message": "거래 서류 분석이 완료되었습니다.",
                }
            except Exception as e:
                last_error = e
                continue

        elapsed_ms = int((time.time() - start_t) * 1000)
        cls.record_usage(
            task_type="TRANSACTION_DOC",
            model_used=models_to_try[0],
            success=False,
            error_message=str(last_error),
            exec_ms=elapsed_ms,
        )
        return {
            "ok": False,
            "status": "PROCESSING_ERROR",
            "message": f"거래 서류 이미지 분석 실패: {str(last_error)}",
        }
