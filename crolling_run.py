import os
import re
import time
import random
import shutil
import pandas as pd
import sys
import logging
import platform
import subprocess
import tempfile
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    UnexpectedAlertPresentException,
    NoAlertPresentException,
    TimeoutException,
    NoSuchWindowException,
    InvalidSessionIdException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from pandas import ExcelWriter

# =========================
# 경로 유틸 (입력 엑셀은 절대 변경 X)
# =========================
def get_executable_dir():
    if getattr(sys, 'frozen', False):
        return os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../../../"))
    else:
        return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    # .app 실행 시 base path는 Contents/MacOS가 됨
    if getattr(sys, 'frozen', False):
        base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../Resources"))
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


# =========================
# 기본 경로/파일 (입력/출력 경로는 기존 유지)
# =========================
BASE_DIR = get_executable_dir()

URL_FILE_PATH = os.path.join(BASE_DIR, "네이버_검색어.xlsx")  # 입력 엑셀: 위치 그대로 유지
FILES_DIR = os.path.join(BASE_DIR, "files")                  # 출력 폴더
os.makedirs(FILES_DIR, exist_ok=True)

LOGS_DIR = os.path.join(BASE_DIR, "logs")                    # 로그 폴더
os.makedirs(LOGS_DIR, exist_ok=True)

current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
today_prefix = datetime.now().strftime("%Y%m%d")

# 출력 엑셀 파일명(요청: "_수집" 제거) - 기존 규칙 유지
OUTPUT_XLSX = os.path.join(FILES_DIR, f"카페글_조회수_{current_time}.xlsx")

# =========================
# 로깅 설정 (파일 + 콘솔)
# =========================
LOG_FILE = os.path.join(LOGS_DIR, f"run_{current_time}.txt")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("crawler")

log.info(f"BASE_DIR: {BASE_DIR}")
log.info(f"INPUT  : {URL_FILE_PATH}")
log.info(f"OUTPUT : {OUTPUT_XLSX}")
log.info(f"LOG    : {LOG_FILE}")

# =========================
# Selenium (크롬 버전 독립 실행: Selenium Manager 사용)
# =========================
# 임시 사용자 데이터 디렉터리로 세션/캐시 격리 (매 실행 독립, 로그인 유지 X)
TMP_PROFILE_DIR = tempfile.mkdtemp(prefix="nrk_chrome_")

chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1280,900")
chrome_options.add_argument(f"--user-data-dir={TMP_PROFILE_DIR}")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
chrome_options.add_experimental_option("useAutomationExtension", False)
# DOM 로드까지만(이미지/서브리소스 기다리지 않음)
chrome_options.page_load_strategy = "eager"
# 필요 시 헤드리스: chrome_options.add_argument("--headless=new")

# ✅ 핵심: Service(executable_path=...) 미지정 → Selenium Manager 자동 매칭
# (동봉된 chromedriver를 절대 강제 사용하지 않음)
driver = webdriver.Chrome(options=chrome_options)
driver.set_page_load_timeout(25)
wait = WebDriverWait(driver, 15)

# =========================
# 보조 함수
# =========================
def safe_int_from_text(t: str) -> int:
    nums = re.findall(r"\d+", t or "")
    return int(nums[0]) if nums else 0

def open_log_after_finish(path: str):
    """작업 후 OS에서 로그 파일 열기"""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", path], check=False)
        elif platform.system() == "Windows":
            os.startfile(path)  # type: ignore
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception as e:
        log.warning(f"로그 자동 열기 실패(무시 가능): {e}")

def human_delay(min_s=0.6, max_s=1.4):
    time.sleep(random.uniform(min_s, max_s))

def pause_between_pages():
    sec = random.uniform(3.0, 5.0)
    log.info(f"다음 페이지로 넘어가기 전 대기: {sec:.2f}s")
    time.sleep(sec)

def switch_to_last_window(drv: webdriver.Chrome):
    try:
        handles = drv.window_handles
        if handles:
            drv.switch_to.window(handles[-1])
    except Exception as e:
        log.debug(f"윈도우 전환 실패(무시): {e}")


def close_and_cleanup_driver():
    try:
        try:
            driver.quit()
        except Exception:
            pass
    finally:
        # 임시 프로필 정리
        try:
            shutil.rmtree(TMP_PROFILE_DIR, ignore_errors=True)
        except Exception:
            pass

# =========================
# 로그인 (매 실행 새 로그인 OK)
# =========================
try:
    driver.get("https://www.naver.com")
    log.info("네이버 접속. 로그인 대기 최대 60초(세션 재사용 안 함, 수동 로그인).")
    # 수동 로그인 대기 (고정 슬립 + 조기 통과 조건 병행)
    start = time.time()
    while True:
        # 로그인 완료 힌트: 메인 바디 존재 && 로그인 버튼이 사라졌거나, 내정보/프로필 요소가 보이는 경우 등
        try:
            body_ok = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            if body_ok:
                # 조기 통과 조건(보수적으로 2초 쉰 뒤 종료)
                time.sleep(2)
                break
        except TimeoutException:
            pass
        if time.time() - start > 60:
            break
        time.sleep(1)
except TimeoutException:
    log.warning("네이버 첫 페이지 로드 타임아웃. 계속 진행합니다.")

human_delay(1.0, 2.0)

# =========================
# 입력 엑셀 읽기 (경로/포맷 고정)
# =========================
if not os.path.exists(URL_FILE_PATH):
    log.error("입력 엑셀(네이버_검색어.xlsx)이 존재하지 않습니다. 작업을 종료합니다.")
    close_and_cleanup_driver()
    sys.exit(1)

try:
    cafe_df = pd.read_excel(URL_FILE_PATH)
except Exception as e:
    log.error(f"입력 엑셀 로드 실패: {e}")
    close_and_cleanup_driver()
    sys.exit(1)

# 필수 컬럼 점검
if not set(["키워드", "링크"]).issubset(set(cafe_df.columns)):
    log.error("입력 엑셀에 '키워드', '링크' 컬럼이 필요합니다.")
    close_and_cleanup_driver()
    sys.exit(1)

# =========================
# 크롤링
# =========================
CAFE_VIEW_LIST = []
total = len(cafe_df)
log.info(f"총 {total}건 수집 시작")

try:
    for idx, row in cafe_df.iterrows():
        keyword = str(row.get("키워드", "")).strip()
        visit_cafe_url = str(row["링크"]).strip()

        log.info(f"[{idx+1}/{total}] 방문: {visit_cafe_url}")

        # 페이지 열기
        try:
            driver.get(visit_cafe_url)
        except (TimeoutException,) as e:
            log.warning(f"페이지 로드 타임아웃 → 0으로 기록하고 다음으로 진행: {e}")
            CAFE_VIEW_LIST.append([keyword, visit_cafe_url, 0])
            pause_between_pages()
            continue
        except (NoSuchWindowException, InvalidSessionIdException, WebDriverException) as e:
            # 창/세션 이슈: 마지막 창으로 재전환 시도 후 한번 더 시도
            log.warning(f"창/세션 이슈 감지(재시도): {e}")
            try:
                switch_to_last_window(driver)
                driver.get(visit_cafe_url)
            except Exception as e2:
                log.warning(f"재시도 실패 → 0으로 기록: {e2}")
                CAFE_VIEW_LIST.append([keyword, visit_cafe_url, 0])
                pause_between_pages()
                continue

        # iframe 진입 및 조회수 파싱
        count = 0
        try:
            iframe = wait.until(EC.presence_of_element_located((By.ID, "cafe_main")))
            driver.switch_to.frame(iframe)

            # 조회수 요소 탐색(텍스트/클래스 모두 대응)
            xpath_candidates = [
                "//span[contains(., '조회')]",
                "//*[contains(@class,'view') and (self::span or self::em or self::div)]",
                "//*[contains(@class,'count') and (self::span or self::em or self::div)]",
            ]

            elem = None
            for xp in xpath_candidates:
                try:
                    elem = WebDriverWait(driver, 6).until(
                        EC.presence_of_element_located((By.XPATH, xp))
                    )
                    text = (elem.text or "").strip()
                    val = safe_int_from_text(text)
                    if val > 0:
                        count = val
                        break
                except TimeoutException:
                    continue
                except StaleElementReferenceException:
                    # 프레임 내 재탐색
                    try:
                        driver.switch_to.default_content()
                        iframe = wait.until(EC.presence_of_element_located((By.ID, "cafe_main")))
                        driver.switch_to.frame(iframe)
                    except Exception:
                        pass

            # 백업 XPath 한 번 더
            if count == 0:
                try:
                    backup = driver.find_element(By.XPATH, "/html/body/div/div/div/div[2]/div[1]/div[2]/div[2]/div[2]/span[2]")
                    count = safe_int_from_text((backup.text or "").strip())
                except Exception:
                    pass

            if count == 0:
                log.warning(f"조회수 추출 실패(0으로 기록) URL: {visit_cafe_url}")
            else:
                log.info(f"▶ 조회수: {count}")

        except UnexpectedAlertPresentException:
            try:
                alert = driver.switch_to.alert
                log.warning(f"Alert 감지: {alert.text}")
                alert.accept()
            except NoAlertPresentException:
                pass
        except (NoSuchWindowException, InvalidSessionIdException) as e:
            log.warning(f"프레임/파싱 중 세션 이슈 → 0 기록: {e}")
            count = 0
        except Exception as e:
            log.warning(f"iframe/파싱 실패: {e}")
        finally:
            # 프레임 상태 복구
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

        CAFE_VIEW_LIST.append([keyword, visit_cafe_url, count])

        # 페이지 전환 사이 필수 대기(3~5초)
        pause_between_pages()

finally:
    close_and_cleanup_driver()

# =========================
# 오늘자 결과 엑셀 저장 (누적 관련 전부 제거)
# =========================
if CAFE_VIEW_LIST:
    df_today = pd.DataFrame(CAFE_VIEW_LIST, columns=["키워드", "링크", today_prefix])
    try:
        with ExcelWriter(OUTPUT_XLSX, engine="xlsxwriter") as writer:
            df_today.to_excel(writer, index=False, sheet_name="조회수기록")
        log.info(f"✅ 결과 저장 완료: {OUTPUT_XLSX}")
    except Exception as e:
        log.error(f"엑셀 저장 실패: {e}")
else:
    log.warning("⚠️ 저장할 데이터가 없습니다(수집 결과 0건).")

log.info("모든 작업 완료. 로그 파일을 열겠습니다.")
open_log_after_finish(LOG_FILE)
