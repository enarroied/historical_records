import csv
import time
from pathlib import Path
from typing import Dict, List, Tuple

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class PavillonBleuScraper:
    def __init__(self, headless=False):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.wait = WebDriverWait(self.driver, 10)

    def scroll_to_element(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
            element,
        )
        time.sleep(0.5)

    def extract_table_from_iframe(self, iframe_element, table_type: str) -> List[Dict]:
        results = []
        self.driver.switch_to.frame(iframe_element)
        time.sleep(2)

        page_num = 1
        while True:
            print(f"  Extracting {table_type} - Page {page_num}")

            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#table"))
                )
            except TimeoutException:
                print(f"  Table not found in {table_type} iframe")
                break

            rows = self.driver.find_elements(By.CSS_SELECTOR, "#table .tr.body-row")
            if not rows:
                print(f"  No rows found for {table_type}")
                break

            page_results = []
            for row in rows:
                try:
                    tds = row.find_elements(By.CSS_SELECTOR, ".td")
                    num_cols = len(tds)
                    if num_cols >= 4:
                        commune = tds[0].find_element(By.TAG_NAME, "font").text.strip()
                        places = tds[1].find_element(By.TAG_NAME, "p").text.strip()
                        department = tds[2].find_element(By.TAG_NAME, "p").text.strip()
                        region = tds[3].find_element(By.TAG_NAME, "p").text.strip()
                    elif num_cols == 3:
                        commune = tds[0].text.strip()
                        places = tds[0].find_element(By.TAG_NAME, "p").text.strip()
                        department = tds[1].find_element(By.TAG_NAME, "p").text.strip()
                        region = tds[2].find_element(By.TAG_NAME, "p").text.strip()
                    else:
                        print(f"  Skipping row with {num_cols} columns")
                        continue

                    item = {
                        "commune": commune,
                        "department": department,
                        "region": region,
                        "type_of_flag": "beach"
                        if "plage" in table_type.lower()
                        else "port",
                        "places": places,
                        "year": None,
                    }
                    page_results.append(item)
                except Exception as e:
                    print(f"  Error extracting row: {e}")
                    continue

            results.extend(page_results)
            print(
                f"  Page {page_num}: Found {len(page_results)} items (Total: {len(results)})"
            )

            try:
                pagination = self.driver.find_element(By.CSS_SELECTOR, "#pagination")
                self.scroll_to_element(pagination)
                next_button = self.driver.find_element(
                    By.CSS_SELECTOR, "#pagination .pagination-btn.next"
                )
                if "disabled" in next_button.get_attribute("class"):
                    print(f"  Reached last page of {table_type} (page {page_num})")
                    break
                self.driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)
                page_num += 1
                self.wait.until(
                    lambda driver: (
                        len(
                            driver.find_elements(By.CSS_SELECTOR, "#table .tr.body-row")
                        )
                        > 0
                    )
                )
            except NoSuchElementException:
                print(f"  No pagination found for {table_type}")
                break
            except Exception as e:
                print(f"  Error on page {page_num}: {e}")
                time.sleep(3)
                if page_num > 1:
                    break

        self.driver.switch_to.default_content()
        return results

    def scrape_year_data(self, url: str, year: int) -> Dict[str, List[Dict]]:
        print(f"\n{'=' * 60}")
        print(f"📅 Scraping data for {year}")
        print(f"🔗 URL: {url}")
        print(f"{'=' * 60}\n")

        print("Loading page...")
        self.driver.get(url)
        time.sleep(5)

        print("Scrolling to load content...")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(3)

        all_data = {"beaches": [], "ports": []}
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        print(f"\nFound {len(iframes)} iframes on the page")

        for idx, iframe in enumerate(iframes):
            try:
                self.driver.switch_to.frame(iframe)
                try:
                    table = self.driver.find_element(By.CSS_SELECTOR, "#table")
                    page_text = self.driver.find_element(
                        By.TAG_NAME, "body"
                    ).text.lower()

                    if "plage" in page_text or "beach" in page_text:
                        print(f"\n📊 Iframe {idx + 1} contains BEACHES data")
                        self.driver.switch_to.default_content()
                        beaches = self.extract_table_from_iframe(iframe, "plages")
                        for beach in beaches:
                            beach["year"] = year
                        all_data["beaches"] = beaches
                        print(f"✓ Extracted {len(all_data['beaches'])} beaches total")

                    elif "port" in page_text and "plage" not in page_text:
                        print(f"\n⚓ Iframe {idx + 1} contains PORTS data")
                        self.driver.switch_to.default_content()
                        ports = self.extract_table_from_iframe(iframe, "ports")
                        for port in ports:
                            port["year"] = year
                        all_data["ports"] = ports
                        print(f"✓ Extracted {len(all_data['ports'])} ports total")
                    else:
                        self.driver.switch_to.default_content()

                except NoSuchElementException:
                    self.driver.switch_to.default_content()
                    continue

            except Exception as e:
                self.driver.switch_to.default_content()
                print(f"Error processing iframe {idx + 1}: {e}")
                continue

        return all_data

    def save_to_csv(self, data: Dict[str, List[Dict]], year: int):
        all_records = data["beaches"] + data["ports"]
        if not all_records:
            print(f"No data to save for {year}")
            return

        output_dir = Path("output") / str(year)
        output_dir.mkdir(parents=True, exist_ok=True)

        combined_path = output_dir / f"pavillon_bleu_{year}.csv"
        with open(combined_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "year",
                "commune",
                "department",
                "region",
                "type_of_flag",
                "places",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_records)
        print(f"\n✓ Saved {len(all_records)} total records to {combined_path}")

        if data["beaches"]:
            beaches_path = output_dir / f"beaches_{year}.csv"
            with open(beaches_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data["beaches"])
            print(f"✓ Saved {len(data['beaches'])} beaches to {beaches_path}")

        if data["ports"]:
            ports_path = output_dir / f"ports_{year}.csv"
            with open(ports_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data["ports"])
            print(f"✓ Saved {len(data['ports'])} ports to {ports_path}")

        return output_dir

    def close(self):
        self.driver.quit()


def scrape_pavillon_bleu(year, url, headless=False):
    scraper = PavillonBleuScraper(headless=headless)
    try:
        data = scraper.scrape_year_data(url, year)
        output_dir = scraper.save_to_csv(data, year)
        print("\n" + "=" * 50)
        print(f"SUMMARY FOR {year}")
        print("=" * 50)
        print(f"Total beaches: {len(data['beaches'])}")
        print(f"Total ports: {len(data['ports'])}")
        print(f"Grand total: {len(data['beaches']) + len(data['ports'])}")
        print(f"Output saved to: {output_dir}")
        return data, output_dir
    except Exception as e:
        print(f"An error occurred for {year}: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        scraper.close()


if __name__ == "__main__":
    years_data = {
        2020: "https://www.bfmtv.com/societe/carte-decouvrez-les-500-plages-et-ports-de-plaisance-labellises-pavillon-bleu-en-2020_AN-202006090268.html",
        2021: "https://www.bfmtv.com/environnement/carte-decouvrez-les-525-plages-et-ports-labellises-pavillon-bleu-en-2021_AN-202106050002.html",
        2022: "https://www.bfmtv.com/societe/carte-decouvrez-toutes-les-plages-et-ports-labellises-pavillon-bleu-en-2022_AN-202205180333.html",
        2023: "https://www.bfmtv.com/environnement/carte-decouvrez-les-511-plages-et-ports-de-plaisance-labellises-pavillon-bleu-en-2023_AN-202305260213.html",
    }

    all_results = {}
    for year, url in years_data.items():
        print(f"\n{'#' * 60}")
        print(f"# Starting scrape for {year}")
        print(f"{'#' * 60}")

        data, output_dir = scrape_pavillon_bleu(year=year, url=url, headless=True)

        if data:
            all_results[year] = data

        if year != list(years_data.keys())[-1]:
            print("\nWaiting 5 seconds before next year...")
            time.sleep(5)

    print("\n" + "=" * 60)
    print("FINAL SUMMARY ACROSS ALL YEARS")
    print("=" * 60)
    for year, data in all_results.items():
        total = len(data["beaches"]) + len(data["ports"])
        print(f"{year}: {len(data['beaches'])} beaches + {len(data['ports'])} ports = {total} total")
