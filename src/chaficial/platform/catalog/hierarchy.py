"""정확한 차종 및 트림 선택을 위한 계층형 차량 카탈로그 서비스 (DIRECTIVE 050 3항).

선택 흐름:
제조사(Manufacturer) -> 차종(Model) -> 세대(Generation) -> 연식(Year) -> 세부 트림(Trim) -> 엔진/제원 기본값
"""

from __future__ import annotations
from typing import Any


class VehicleCatalogService:
    """국내외 주요 중고차 차종/세대/트림/제원 표준 카탈로그."""

    CATALOG_DATA: dict[str, dict[str, Any]] = {
        "현대": {
            "그랜저": {
                "body_type": "대형 세단",
                "generations": {
                    "디 올 뉴 그랜저 (GN7)": {
                        "years": [2023, 2024, 2025, 2026],
                        "trims": {
                            "2.5 가솔린 프리미엄": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 가솔린 익스클루시브": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 가솔린 캘리그래피": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "3.5 가솔린 캘리그래피 AWD": {"displacement_cc": 3470, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                            "1.6 하이브리드 캘리그래피": {"displacement_cc": 1598, "fuel_type": "하이브리드", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                    "더 뉴 그랜저 IG": {
                        "years": [2019, 2020, 2021, 2022],
                        "trims": {
                            "2.5 가솔린 프리미엄": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 가솔린 르블랑": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 가솔린 익스클루시브": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 가솔린 캘리그래피": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "3.3 가솔린 캘리그래피": {"displacement_cc": 3342, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                },
            },
            "쏘나타": {
                "body_type": "중형 세단",
                "generations": {
                    "쏘나타 디 엣지 (DN8)": {
                        "years": [2023, 2024, 2025, 2026],
                        "trims": {
                            "2.0 가솔린 프리미엄": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 가솔린 익스클루시브": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 가솔린 인스퍼레이션": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 터보 인스퍼레이션": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 하이브리드 인스퍼레이션": {"displacement_cc": 1999, "fuel_type": "하이브리드", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                    "쏘나타 (DN8)": {
                        "years": [2019, 2020, 2021, 2022],
                        "trims": {
                            "2.0 스마트": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 프리미엄 패밀리": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 인스퍼레이션": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                },
            },
            "아반떼": {
                "body_type": "준중형 세단",
                "generations": {
                    "더 뉴 아반떼 (CN7)": {
                        "years": [2023, 2024, 2025, 2026],
                        "trims": {
                            "1.6 가솔린 스마트": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 가솔린 모던": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 가솔린 인스퍼레이션": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 하이브리드 인스퍼레이션": {"displacement_cc": 1580, "fuel_type": "하이브리드", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                    "아반떼 (CN7)": {
                        "years": [2020, 2021, 2022],
                        "trims": {
                            "1.6 가솔린 스마트": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 가솔린 모던": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 가솔린 인스퍼레이션": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                },
            },
            "싼타페": {
                "body_type": "중형 SUV",
                "generations": {
                    "디 올 뉴 싼타페 (MX5)": {
                        "years": [2023, 2024, 2025, 2026],
                        "trims": {
                            "2.5 터보 익스클루시브": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 터보 프레스티지": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 터보 캘리그래피": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6T 하이브리드 캘리그래피 4WD": {"displacement_cc": 1598, "fuel_type": "하이브리드", "transmission": "오토", "drive_type": "4WD"},
                        },
                    },
                },
            },
            "팰리세이드": {
                "body_type": "대형 SUV",
                "generations": {
                    "더 뉴 팰리세이드 (LX2)": {
                        "years": [2022, 2023, 2024, 2025],
                        "trims": {
                            "3.8 가솔린 익스클루시브": {"displacement_cc": 3778, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "3.8 가솔린 프레스티지": {"displacement_cc": 3778, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "3.8 가솔린 캘리그래피": {"displacement_cc": 3778, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.2 디젤 캘리그래피 4WD": {"displacement_cc": 2199, "fuel_type": "디젤", "transmission": "오토", "drive_type": "4WD"},
                        },
                    },
                },
            },
        },
        "기아": {
            "K5": {
                "body_type": "중형 세단",
                "generations": {
                    "더 뉴 K5 3세대 (DL3)": {
                        "years": [2023, 2024, 2025, 2026],
                        "trims": {
                            "2.0 가솔린 프레스티지": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 가솔린 노블레스": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 가솔린 시그니처": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 터보 시그니처": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                    "K5 3세대 (DL3)": {
                        "years": [2019, 2020, 2021, 2022],
                        "trims": {
                            "2.0 트렌디": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 프레스티지": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 노블레스": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.0 시그니처": {"displacement_cc": 1999, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                },
            },
            "K8": {
                "body_type": "준대형 세단",
                "generations": {
                    "더 뉴 K8 (GL3)": {
                        "years": [2024, 2025, 2026],
                        "trims": {
                            "2.5 가솔린 노블레스": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 가솔린 시그니처": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 터보 하이브리드 시그니처": {"displacement_cc": 1598, "fuel_type": "하이브리드", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                    "K8 (GL3)": {
                        "years": [2021, 2022, 2023],
                        "trims": {
                            "2.5 가솔린 노블레스": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 가솔린 시그니처": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "3.5 가솔린 플래티넘 AWD": {"displacement_cc": 3470, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                        },
                    },
                },
            },
            "스포티지": {
                "body_type": "준중형 SUV",
                "generations": {
                    "스포티지 5세대 (NQ5)": {
                        "years": [2021, 2022, 2023, 2024, 2025, 2026],
                        "trims": {
                            "1.6 터보 2WD 프레스티지": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 터보 2WD 노블레스": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 터보 2WD 시그니처": {"displacement_cc": 1598, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 하이브리드 시그니처": {"displacement_cc": 1598, "fuel_type": "하이브리드", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                },
            },
            "쏘렌토": {
                "body_type": "중형 SUV",
                "generations": {
                    "더 뉴 쏘렌토 4세대 (MQ4)": {
                        "years": [2023, 2024, 2025, 2026],
                        "trims": {
                            "2.5 터보 프레스티지": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 터보 노블레스": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5 터보 시그니처": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 터보 하이브리드 시그니처 4WD": {"displacement_cc": 1598, "fuel_type": "하이브리드", "transmission": "오토", "drive_type": "4WD"},
                        },
                    },
                },
            },
            "카니발": {
                "body_type": "대형 RV",
                "generations": {
                    "더 뉴 카니발 4세대 (KA4)": {
                        "years": [2023, 2024, 2025, 2026],
                        "trims": {
                            "3.5 가솔린 9인승 프레스티지": {"displacement_cc": 3470, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "3.5 가솔린 9인승 노블레스": {"displacement_cc": 3470, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "3.5 가솔린 9인승 시그니처": {"displacement_cc": 3470, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "1.6 터보 하이브리드 9인승 시그니처": {"displacement_cc": 1598, "fuel_type": "하이브리드", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                },
            },
        },
        "제네시스": {
            "G80": {
                "body_type": "준대형 세단",
                "generations": {
                    "더 뉴 G80 (RG3)": {
                        "years": [2024, 2025, 2026],
                        "trims": {
                            "2.5T 가솔린 2WD": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5T 가솔린 AWD": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                            "3.5T 가솔린 AWD": {"displacement_cc": 3470, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                        },
                    },
                    "G80 (RG3)": {
                        "years": [2020, 2021, 2022, 2023],
                        "trims": {
                            "2.5T 가솔린 2WD": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5T 가솔린 AWD": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                            "3.5T 가솔린 AWD": {"displacement_cc": 3470, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                        },
                    },
                },
            },
            "GV70": {
                "body_type": "중형 SUV",
                "generations": {
                    "GV70 (JK1)": {
                        "years": [2021, 2022, 2023, 2024, 2025],
                        "trims": {
                            "2.5T 가솔린 2WD": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "2.5T 가솔린 AWD": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                            "3.5T 가솔린 AWD": {"displacement_cc": 3470, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                        },
                    },
                },
            },
            "GV80": {
                "body_type": "준대형 SUV",
                "generations": {
                    "GV80 (JX1)": {
                        "years": [2020, 2021, 2022, 2023, 2024, 2025],
                        "trims": {
                            "2.5T 가솔린 AWD": {"displacement_cc": 2497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                            "3.5T 가솔린 AWD": {"displacement_cc": 3470, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "AWD"},
                            "3.0 디젤 AWD": {"displacement_cc": 2996, "fuel_type": "디젤", "transmission": "오토", "drive_type": "AWD"},
                        },
                    },
                },
            },
        },
        "KG모빌리티": {
            "토레스": {
                "body_type": "중형 SUV",
                "generations": {
                    "토레스 (J100)": {
                        "years": [2022, 2023, 2024, 2025, 2026],
                        "trims": {
                            "T5 2WD": {"displacement_cc": 1497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "T7 2WD": {"displacement_cc": 1497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "T7 4WD": {"displacement_cc": 1497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "4WD"},
                        },
                    },
                },
            },
            "티볼리": {
                "body_type": "소형 SUV",
                "generations": {
                    "더 뉴 티볼리": {
                        "years": [2019, 2020, 2021, 2022, 2023, 2024],
                        "trims": {
                            "V1 2WD": {"displacement_cc": 1497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "V3 2WD": {"displacement_cc": 1497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                            "V5 2WD": {"displacement_cc": 1497, "fuel_type": "가솔린", "transmission": "오토", "drive_type": "2WD"},
                        },
                    },
                },
            },
        },
    }

    @classmethod
    def get_manufacturers(cls) -> list[str]:
        """제조사 목록 조회."""
        return list(cls.CATALOG_DATA.keys())

    @classmethod
    def get_models(cls, manufacturer: str) -> list[str]:
        """제조사별 모델 목록 조회."""
        return list(cls.CATALOG_DATA.get(manufacturer, {}).keys())

    @classmethod
    def get_generations(cls, manufacturer: str, model: str) -> list[str]:
        """모델별 세대 목록 조회."""
        m_data = cls.CATALOG_DATA.get(manufacturer, {}).get(model, {})
        return list(m_data.get("generations", {}).keys())

    @classmethod
    def get_years(cls, manufacturer: str, model: str, generation: str) -> list[int]:
        """세대별 연식 목록 조회."""
        gen_data = (
            cls.CATALOG_DATA.get(manufacturer, {})
            .get(model, {})
            .get("generations", {})
            .get(generation, {})
        )
        return gen_data.get("years", [])

    @classmethod
    def get_trims(cls, manufacturer: str, model: str, generation: str) -> list[str]:
        """세대별 세부 트림 목록 조회."""
        gen_data = (
            cls.CATALOG_DATA.get(manufacturer, {})
            .get(model, {})
            .get("generations", {})
            .get(generation, {})
        )
        return list(gen_data.get("trims", {}).keys())

    @classmethod
    def get_spec_defaults(
        cls, manufacturer: str, model: str, generation: str, trim: str
    ) -> dict[str, Any]:
        """트림 선택 시 표준 제원 기본값 반환."""
        m_info = cls.CATALOG_DATA.get(manufacturer, {}).get(model, {})
        body_type = m_info.get("body_type", "세단")
        gen_data = m_info.get("generations", {}).get(generation, {})
        trim_info = gen_data.get("trims", {}).get(trim, {})

        return {
            "manufacturer": manufacturer,
            "model": model,
            "generation": generation,
            "trim": trim,
            "body_type": body_type,
            "displacement_cc": trim_info.get("displacement_cc"),
            "fuel_type": trim_info.get("fuel_type", "가솔린"),
            "transmission": trim_info.get("transmission", "오토"),
            "drive_type": trim_info.get("drive_type", "2WD"),
        }

    @classmethod
    def get_full_catalog_tree(cls) -> dict[str, Any]:
        """프론트엔드 캐시용 전체 카탈로그 구조 트리."""
        return cls.CATALOG_DATA
