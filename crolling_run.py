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
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_base_dir():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        return os.path.abspath(os.path.join(exe_dir, "../../../"))
    return os.path.dirname(os.path.abspath(__file__))

def normalize_url(url: str) -> str:
    return url.replace("http://", "").replace("https://", "").rstrip("/")

def main():
    try:
        # ─── 기본 디렉토리 & 로그 ───────────────────────────────────
        base_dir = get_base_dir()
        print(f"[경로] base_dir: {base_dir}")

        # ─── 엑셀 파일 탐색 ─────────────────────────────────────────
        target_fname = unicodedata.normalize("NFC", "네이버_검색어.xlsx")
        excel_path = os.path.join(base_dir, target_fname)
        print(f"🔍 검사 중: {excel_path}")
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"{excel_path} 을(를) 찾을 수 없습니다.")
        print("✅ 파일 발견!")

        # ─── 엑셀 로딩 ─────────────────────────────────────────────
        df = pd.read_excel(excel_path)
        if "키워드" not in df.columns or "링크" not in df.columns:
            raise ValueError("엑셀에 '키워드', '링크' 컬럼이 필요합니다.")

        # ─── 셀레니움 & 크롤링 설정 ─────────────────────────────────
        target_classes = {
            "info_title",
            "link_tit",
            "link_question",
            "title_link",
            "fds-comps-right-image-text-title",
        }
        anchor_selector = ",".join(f"a[class*='{c}']" for c in target_classes)

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )
        wait = WebDriverWait(driver, 10)

        results = []
        for idx, row in enumerate(df.itertuples(index=False), start=1):
            keyword = str(row.키워드).strip()
            target_url = str(row.링크).strip()
            print(f"\n[{idx:>2}] ✅ 키워드 '{keyword}' 검색 중…")

            driver.get("https://www.naver.com")
            wait.until(EC.presence_of_element_located((By.NAME, "query")))
            box = driver.find_element(By.NAME, "query")
            box.clear()
            box.send_keys(keyword)
            box.send_keys(Keys.RETURN)

            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.api_subject_bx")))
            blocks = driver.find_elements(By.CSS_SELECTOR, "div.api_subject_bx")
            found = False

            for block in blocks:
                # 그룹명 추출
                try:
                    group_title = block.find_element(By.CSS_SELECTOR, "h2.title").text.strip()
                except:
                    try:
                        group_title = block.find_element(
                            By.CSS_SELECTOR, "span.fds-comps-header-headline"
                        ).text.strip()
                    except:
                        group_title = "그룹명 없음"

                anchors = block.find_elements(By.CSS_SELECTOR, anchor_selector)
                for rank, a in enumerate(anchors, start=1):
                    href = a.get_attribute("href") or ""
                    text = a.text.strip()
                    if normalize_url(target_url) in normalize_url(href):
                        # 등록일 추출
                        date_candidates = []
                        for sel in [
                            "div.profile_bx span.etc.date",
                            "div.user_info span.sub",
                            "span.etc.date",
                            "span.fds-info-sub-inner-text",
                        ]:
                            try:
                                date_candidates.append(
                                    block.find_element(By.CSS_SELECTOR, sel).text.strip()
                                )
                            except:
                                pass
                        date_text = date_candidates[-1].rstrip(".") if date_candidates else "등록일 없음"

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

            if not found:
                results.append({
                    "키워드": keyword,
                    "링크": target_url,
                    "그룹명": "순위에 없음",
                    "글제목": "순위에 없음",
                    "등록일": "순위에 없음",
                    "금일 순위": "순위에 없음",
                })

        driver.quit()

        # ─── 결과 저장 ─────────────────────────────────────────────
        out_dir = os.path.join(base_dir, "outputs")
        os.makedirs(out_dir, exist_ok=True)
        now = datetime.now().strftime("%Y%m%d_%H%M")
        out_path = os.path.join(out_dir, f"네이버_순위체크_크롤링_{now}.xlsx")

        out_df = pd.DataFrame(
            results,
            columns=["키워드", "링크", "그룹명", "글제목", "등록일", "금일 순위"],
        )
        out_df.to_excel(out_path, index=False)
        print(f"\n✅ 결과 저장 완료: {out_path}")

    except Exception:
        print("❌ 오류 발생:")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
