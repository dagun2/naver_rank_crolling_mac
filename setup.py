from setuptools import setup

APP = ["crolling_run.py"]
OPTIONS = {
    "argv_emulation": True,      # 디버깅 시 콘솔 로그 보기 위해 켜 두셔도 좋습니다
    "plist": {
        "CFBundleName": "NaverRankChecker",
        "CFBundleDisplayName": "NaverRankChecker",
        "CFBundleIdentifier": "com.yourname.naver-rank-checker",
        "CFBundleVersion": "1.0.0",
    },
    'packages': [
        # pandas 내부 C 확장도 통째로 묶어 줍니다
        'pandas', 'numpy',
        # 기타 엑셀 입출력용 패키지
        'openpyxl', 'xlsxwriter'
    ],
    'includes': [
        # 표준 라이브러리 cmath를 강제로 포함
        'cmath',
        # pandas._libs.testing 같은 숨은 확장 모듈도 포함
        'pandas._libs.testing',
    ],
    # 필요하다면 excludes / optimize 등 추가 설정
}

setup(
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
