from setuptools import setup

APP = ['crolling_run.py']
DATA_FILES = []

OPTIONS = {
    'argv_emulation': False,
    'emulate_shell_environment': True,
    'redirect_stdout_to_asl': True,
    'includes': [
        'datetime',
        'pytz',
        'unicodedata',
        'cmath',                            # C-확장 모듈
        'pandas._libs.testing',            # pandas 테스트용 C-모듈
        'pandas._libs.tslibs.timezones',    # pandas 시간대 처리용 C-모듈
    ],
    'packages': [
        'pandas',
        'openpyxl',
        'numpy',
        'dateutil',
    ],
    'excludes': [
        'tkinter',        # GUI 미사용 시 제외
        'pandas._testing' # 순위 체크엔 불필요한 테스트 코드
    ],
    'plist': {
        'CFBundleName': 'NaverRankChecker',
        'CFBundleDisplayName': 'NaverRankChecker',
        'CFBundleIdentifier': 'com.midnightaxi.NaverRankChecker',
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
)
