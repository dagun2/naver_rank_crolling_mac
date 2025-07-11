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
}

setup(
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
