from setuptools import setup

APP = ['crolling_run.py']

# ✅ chromedriver 동봉하지 않음 (Selenium Manager 사용)
DATA_FILES = [
    # ('resources', ['resources/anything_else_needed'])  # 필요시 다른 리소스만 남기세요
]

OPTIONS = {
    'argv_emulation': False,
    'emulate_shell_environment': True,
    # 'redirect_stdout_to_asl': True,
    'includes': [
        'datetime', 'pytz', 'unicodedata', 'cmath'
    ],
    # ✅ 런타임에 실제 임포트되는 패키지들
    'packages': ['pandas', 'openpyxl', 'numpy', 'dateutil', 'selenium', 'xlsxwriter'],
    'excludes': ['tkinter'],  # 충돌 방지용
    'plist': {
        'CFBundleName': 'NaverRankChecker',
        'CFBundleDisplayName': 'NaverRankChecker',
        'CFBundleIdentifier': 'com.midnightaxi.naver_rank_checker',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSEnvironment': {
            'PYTHONIOENCODING': 'utf-8',
            'LANG': 'en_US.UTF-8',
            'LC_ALL': 'en_US.UTF-8'
        }
    }
}

setup(
    app=APP,
    name='NaverRankChecker',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'selenium>=4.25',   # ✅ Selenium Manager 사용을 위해 상향
        'pandas',
        'openpyxl',
        'numpy',
        'python-dateutil',
        'xlsxwriter',       # ✅ ExcelWriter(engine="xlsxwriter") 사용
    ]
)
