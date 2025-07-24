import os
import sys
import unicodedata
import traceback

import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException


def get_executable_dir():
    if getattr(sys, 'frozen', False):
        return os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../../../"))
    else:
        return os.path.dirname(os.path.abspath(__file__))

def resource_path(relative_path):
    # .app 실행 시 base path는 Contents/MacOS
    if getattr(sys, 'frozen', False):
        base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "../Resources"))
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

# 이 경로에 chromedriver가 위치해야 합니다
CHROMEDRIVER_PATH = resource_path("resources/chromedriver")


def normalize_url(url: str) -> str:
    return url.replace("http://", "").replace("https://", "").rstrip("/")


log = ""
error_log = ""

try:

    exe_dir = get_executable_dir()
    base_dir = exe_dir
    files_dir = os.path.join(base_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(files_dir, exist_ok=True)
    
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(logs_dir, f"log_{now_str}.txt")
    err_path = os.path.join(logs_dir, "error_log.txt")

    log += f"[경로] base_dir: {base_dir}\n"

    target_fname = unicodedata.normalize("NFC", "네이버_검색어.xlsx")
    excel_path = os.path.join(base_dir, target_fname)
    log += f"🔍 검사 중: {excel_path}\n"
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"{excel_path} 을(를) 찾을 수 없습니다.")
    log += "✅ 파일 발견!\n"

    df = pd.read_excel(excel_path)
    log += f"📁 엑셀 로딩 완료: {len(df)}개 레코드\n"
    if "키워드" not in df.columns or "링크" not in df.columns:
        raise ValueError("엑셀에 '키워드', '링크' 컬럼이 필요합니다.")

    target_classes = {
        "info_title", "link_tit", "link_question",
        "title_link", "fds-comps-right-image-text-title"
    }
    anchor_selector = ",".join(f"a[class*='{c}']" for c in target_classes)

    #chrome_path = "/Users/david/.wdm/drivers/chromedriver/mac64/138.0.7204.94/chromedriver-mac-arm64/chromedriver"
    options = webdriver.ChromeOptions()
    #options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
 
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 20)

    results = []
    for idx, row in enumerate(df.itertuples(index=False), start=1):
        keyword = str(row.키워드).strip()
        target_url = str(row.링크).strip()
        log += f"\n[{idx:>2}] ✅ 키워드 '{keyword}' 검색 중…\n"

        driver.get("https://www.naver.com")
        wait.until(EC.presence_of_element_located((By.NAME, "query")))
        box = driver.find_element(By.NAME, "query")
        box.clear()
        box.send_keys(keyword)
        box.send_keys(Keys.RETURN)
        time.sleep(random.uniform(10, 12))

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.api_subject_bx")))
        found = False

        blocks = driver.find_elements(By.CSS_SELECTOR, "div.api_subject_bx")
        log += f"   ▶ 그룹 블록 {len(blocks)}개 확인\n"

        for b_idx in range(len(blocks)):
            try:
                blocks = driver.find_elements(By.CSS_SELECTOR, "div.api_subject_bx")  # 재탐색
                block = blocks[b_idx]

                try:
                    group_title = block.find_element(By.CSS_SELECTOR, "h2.title").text.strip()
                except:
                    try:
                        group_title = block.find_element(By.CSS_SELECTOR, "span.fds-comps-header-headline").text.strip()
                    except:
                        group_title = "그룹명 없음"
                log += f"   [그룹{b_idx + 1}] {group_title}\n"

                try:
                    anchors = block.find_elements(By.CSS_SELECTOR, anchor_selector)
                except StaleElementReferenceException:
                    log += f"      · StaleElement 발생 → 앵커 재탐색 시도\n"
                    blocks = driver.find_elements(By.CSS_SELECTOR, "div.api_subject_bx")
                    block = blocks[b_idx]
                    anchors = block.find_elements(By.CSS_SELECTOR, anchor_selector)

                log += f"      · 앵커 {len(anchors)}개 추출\n"

                for rank, a in enumerate(anchors, start=1):
                    href = a.get_attribute("href") or ""
                    text = a.text.strip()
                    log += f"        {rank:>2}. {text} → {href}\n"

                    if normalize_url(target_url) in normalize_url(href):
                        date_candidates = []
                        for sel in [
                            "div.profile_bx span.etc.date",
                            "div.user_info span.sub",
                            "span.etc.date",
                            "span.fds-info-sub-inner-text",
                        ]:
                            try:
                                val = block.find_element(By.CSS_SELECTOR, sel).text.strip()
                                date_candidates.append(val)
                            except:
                                pass
                        date_text = date_candidates[-1].rstrip(".") if date_candidates else "등록일 없음"
                        log += f"        → 매칭! 순위={rank}, 등록일={date_text}\n"

                        results.append({
                            "키워드": keyword,
                            "링크": href,
                            "그룹명": group_title,
                            "글제목": text,
                            "등록일": date_text,
                            "금일 순위": rank,
                        })
                        found = True
                        break

                if found:
                    break

            except Exception as e:
                log += f"   [그룹{b_idx + 1}] 오류 발생: {e}\n"
                continue

        if not found:
            log += "        → 매칭된 글 없음\n"
            results.append({
                "키워드": keyword,
                "링크": target_url,
                "그룹명": "순위에 없음",
                "글제목": "순위에 없음",
                "등록일": "순위에 없음",
                "금일 순위": "순위에 없음",
            })

    driver.quit()

    now = datetime.now().strftime("%Y%m%d_%H%M")

    out_path = os.path.join(files_dir, f"네이버_순위체크_크롤링_{now}.xlsx")
    pd.DataFrame(results, columns=["키워드", "링크", "그룹명", "글제목", "등록일", "금일 순위"]) \
        .to_excel(out_path, index=False)
    log += f"\n✅ 결과 저장 완료: {out_path}\n"

    #with open(log_path, "w", encoding="utf-8") as f:
    #    f.write(log)
    #print(f"\n📝 로그 저장: {log_path}")

except Exception as e:
    error_log += f"\n❌ 오류 발생: {e}\n"
    error_log += traceback.format_exc() + "\n"

    files_dir = os.path.join(get_executable_dir(), "files")
    os.makedirs(files_dir, exist_ok=True)

    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    err_path = os.path.join(logs_dir, "error_log.txt")
    with open(err_path, "a", encoding="utf-8") as f:
        f.write(f"\n[{now_str}]\n")
        f.write(error_log)
    print(f"⚠️ 에러 로그 기록: {err_path}")

    if sys.platform == "darwin":
        os.system(f"open '{err_path}'")

    sys.exit(1)
