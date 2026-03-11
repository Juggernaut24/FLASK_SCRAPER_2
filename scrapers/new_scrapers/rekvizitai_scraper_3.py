from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException
from datetime import datetime
import urllib.parse
import requests
import time
import json
import os
import re
import argparse


def get_text_safe(driver, by, locator, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((by, locator))
        )
        return element.text.strip()
    except Exception:
        return None

def company_side_scrape(driver, wait, timestamp):
    base_url = driver.current_url
    data = {}

    month_translation = {
    "sausis": "January", 
    "vasaris": "February", 
    "kovas": "March",
    "balandis": "April", 
    "gegužė": "May", 
    "birželis": "June",
    "liepa": "July", 
    "rugpjūtis": "August", 
    "rugsėjis": "September",
    "spalis": "October", 
    "lapkritis": "November", 
    "gruodis": "December"
    }

    # waiting for the title
    try:
        h1_element = get_text_safe(driver, By.CSS_SELECTOR, "h1.title")
        data["Company name"] = h1_element
    except:
        data["Company name"] = "N/A"

    #######################
    # -- Comapany info -- #
    #######################

    name_elements = driver.find_elements(By.CSS_SELECTOR, ".name")
    
    for name_elem in name_elements:
        try:
            key = name_elem.get_attribute("textContent").strip()
            key = key.replace("New", "").strip()

            if not key or key == "Report":
                continue

            value_elem = name_elem.find_element(By.XPATH, "following-sibling::*[contains(@class, 'value')]")
            raw_value = value_elem.get_attribute("textContent").strip()

            lines = [line.strip() for line in raw_value.split("\n") if line.strip()]

            if lines:
                clean_value = lines[0]

                if len(lines) > 1 and lines[1] == '€':
                    clean_value += ' €'

                clean_value = clean_value.replace('\xa0', ' ')

                try:
                    extra_elem = value_elem.find_element(By.CSS_SELECTOR, ".extra-info")
                    extra_text = extra_elem.get_attribute("textContent").strip()

                    for lt_month, en_month in month_translation.items():
                        if lt_month in extra_text.lower():
                            extra_text = extra_text.lower().replace(lt_month, en_month)

                    if extra_text and extra_text not in clean_value:
                        clean_value += f" {extra_text}"
                except:
                    pass

            else:
                clean_value = ""

            if clean_value.startswith("New"):
                clean_value = clean_value.replace("New", "", 1).strip()

            if key in data:
                if isinstance(data[key], list):
                    data[key].append(clean_value)
                else:
                    data[key] = [data[key], clean_value]
            else:
                data[key] = clean_value
            
        except Exception:
            continue
    # -- Branches --
    try:
        branches_list = []
        branch_container = driver.find_element(By.CSS_SELECTOR, "div.companyBranches")

        branch_links = branch_container.find_elements(By.CSS_SELECTOR, "a.href")

        for link_elem in branch_links:
            branch_name = link_elem.text.strip()
            branch_url = link_elem.get_attribute("href")
            raw_address = driver.execute_script("return arguments[0].nextSibling.textContent;", link_elem).strip()
            clean_address = raw_address.replace("(", "").replace(")", "").strip()
            
            branches_list.append({
                "Branch Name": branch_name,
                "Link": branch_url,
                "Address": clean_address,
            })

        data["Branches"] = branches_list if branches_list else []

    except Exception:
        data["Branches"] = []


    # --- Categories ---
    try:
        category_elements = driver.find_elements(By.CSS_SELECTOR, ".activities .activity")
        categories = []

        for cat in category_elements:
            cat_text = cat.get_attribute("textContent").strip()
            if cat_text:
                categories.append(cat_text)

        data["Categories"] = categories if categories else ["N/A"]

    except Exception:
        data["Categories"] = ["N/A"]

    # --- EMAIL ---
    try:
        script_element = driver.find_element(By.XPATH, "//script[@type='application/ld+json']")
        script_text = script_element.get_attribute("innerHTML")
        json_data = json.loads(script_text)

        if "email" in json_data:
            data["Email address"] = json_data["email"]
    except Exception:
        pass

    # --- Description ---
    try:
        desc_elements = driver.find_elements(By.CSS_SELECTOR, "div.description p")
        description_lines = []

        for p in desc_elements:
            clean_text = p.text.strip()
            if clean_text:
                description_lines.append(clean_text)

        final_description = "\n\n".join(description_lines)

        data['description'] = final_description

    except Exception as e:
        print(f"Couldnt find DESCRIPTION: {e}")

    #############
    # -- CEO -- #
    #############
    try:
        manager_url = base_url + "manager/"
        driver.get(manager_url)
        try:
            manager_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1[itemprop='name']")))
            data["CEO Name"] = manager_elem.text.strip()
        except Exception:
            data["CEO Name"] = "N/A"

        try:
            photos_local_paths = []
            os.makedirs("outputs", exist_ok=True)
            photo_links = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.about.photos div.d-flex a[data-fslightbox='managerPhotos']")
            ))

            for index, img in enumerate(photo_links):
                high_res_url = img.get_attribute("href")

                if high_res_url:
                    try:
                        response = requests.get(high_res_url, stream=True)
                        response.raise_for_status()

                        filename = f"ceo_photo_{timestamp}_{index}.jpg"
                        file_path = os.path.join("outputs", filename)

                        with open(file_path, "wb") as file:
                            for chunk in response.iter_content(1024):
                                file.write(chunk)

                        photos_local_paths.append(file_path)
                    
                    except Exception as e:
                        print(f"Failed to download image {high_res_url}: {e}")

            data["CEO Photos"] = photos_local_paths if photos_local_paths else ["N/A"]

        except Exception as e:
            data["CEO Photos"] = ["N/A"]
            # print(f"Error processing CEO photos: {e}")

    except Exception as e:
        data["CEO Description"] = "N/A"
        data["CEO Photos"] = ["N/A"]
        print(f"Could not load manager page: {e}")


    ##############################
    # -- Legal entity history -- #
    ##############################
    try:
        legal_entity_url = base_url + "legal-entity/"
        driver.get(legal_entity_url)

        # -- first table loop --
        general_info_rows = driver.find_elements(By.CSS_SELECTOR, "div[class^='details-block__'] tr")
        
        for row in general_info_rows:
            try:
                name_elem = row.find_element(By.CSS_SELECTOR, "td.name")
                value_elem = row.find_element(By.CSS_SELECTOR, "td.value")
                key = name_elem.text.strip()
                raw_value = value_elem.text.strip()
                if not key:
                    continue
                if "EVRK" in key:
                    clean_value = " ".join(raw_value.split())
                else:
                    clean_value = raw_value.split('\n')[0].strip()
                if key not in data:
                    data[key] = clean_value
            except Exception:
                continue

        # -- second table loop --
        history_events = []
        history_rows = driver.find_elements(By.CSS_SELECTOR, "table.legal-data-history-table tr")

        for row in history_rows:
            try:
                columns = row.find_elements(By.TAG_NAME, "td")

                if len(columns) == 2:
                    event_date = columns[0].text.strip()
                    event_desc = columns[1].text.strip()

                    history_events.append({
                        "Date": event_date,
                        "Description" : event_desc,
                    })
            except Exception:
                continue
            
        data["History of legal entity data changes"] = history_events

    except Exception as e:
        print(f"No Legal-entity side: {e}")

    ########################
    # -- Public Tenders -- #
    ########################

    try:
        tenders_url = base_url + "tenders/"
        driver.get(tenders_url)

        if "There is no information about the company's participation in public tenders" in driver.page_source:
            data["Public Tenders Chart Path"] = "N/A"
            data["Public Tenders Description"] = "N/A"
            print("No public tenders information available for this company.")
        else:
        # -- Graph --
            try:
                tender_graph_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.tendersStatsChart")))
                chart_img_url = tender_graph_elem.get_attribute("href")

                if chart_img_url:
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
                    response = requests.get(chart_img_url, headers=headers, stream=True, timeout=10)
                    response.raise_for_status()

                    tenders_filename = f"tenders_chart_{timestamp}.png"
                    file_path = os.path.join("outputs", tenders_filename)

                    with open(file_path, "wb") as file:
                        for chunk in response.iter_content(1024):
                            file.write(chunk)
                    data["Public Tenders Chart Path"] = file_path
                else:
                    data["Public Tenders Chart Path"] = "N/A"
            except Exception as e:
                data["Public Tenders Chart Path"] = "N/A"
                print(f"Chart element not found or timed out: {e}")

            # -- Public tenders desc --
            try:
                info_container = driver.find_element(By.CSS_SELECTOR, "div.info-content.pb-0")
                
                full_text = info_container.text
                
                child_elements = info_container.find_elements(By.XPATH, "./*")
                
                for child in child_elements:
                    child_text = child.text
                    if child_text:
                        full_text = full_text.replace(child_text, "")
            
                clean_text = " ".join(full_text.split())
                
                data["Public Tenders Description"] = clean_text if clean_text else "N/A"
                
            except Exception as e:
                data["Public Tenders Description"] = "N/A"
                print(f"Could not scrape tenders description: {e}")

            # -- tenders partners, competitors, buyers --
            try:
                tender_tables = driver.find_elements(By.CSS_SELECTOR, "table.tenders-table")
                tables_data = {}

                for table in tender_tables:
                    try:
                        title_elem = table.find_element(By.CSS_SELECTOR, "td.tender-title")
                        table_title = title_elem.text.strip().replace("\n", " ")

                        rows = table.find_elements(By.CSS_SELECTOR, "tr.tender-list-item")
                        row_data = []

                        for row in rows:
                            cells = row.find_elements(By.TAG_NAME, "td")

                            if len(cells) == 1:
                                org_name = cells[0].text.strip()
                                row_data.append({"Name": org_name})

                            elif len(cells) == 2:
                                org_name = cells[0].text.strip()
                                value = cells[1].text.strip()

                                row_data.append({"Name": org_name,"Value": value})

                        tables_data[table_title] = row_data

                    except Exception as e:
                        print(f"Error parsing individual tender table: {e}")
                        continue
                data["Public Tenders Tables"] = tables_data if tables_data else "N/A"

            except Exception as e:
                data["Public Tenders Tables"] = "N/A"
                print(f"Could not scrape tenders tables: {e}")
            
            # -- Public tenders desc 2 --
            try:
                tenders_desc_2_elem = driver.find_elements(By.CSS_SELECTOR, "div.info-content")
                second_text = tenders_desc_2_elem[1].text.strip()
                third_text = tenders_desc_2_elem[2].text.strip()

                data["Public Tenders 2. Descriptions"] = second_text
                data["Public Tenders 3. Descriptions"] = third_text

            except Exception as e:
                data["Public Tenders 2. Descriptions"] = "N/A"
                data["Public Tenders 3. Descriptions"] = "N/A"
                print(f"Could not scrape 2. tenders description: {e}")
                
    except Exception as e:
        print(f"No Public Tenders side: {e}")

    ###################
    # -- Transport -- #
    ###################
    try:
        transport_url = base_url + "transport/"
        driver.get(transport_url)

        # --- Transport Graph ---

        chart_link_elem = driver.find_element(By.ID, "transportChart")
        chart_url = chart_link_elem.get_attribute("href")

        if chart_url:
            response = requests.get(chart_url, stream=True)
            response.raise_for_status()

            filename = f"transport_chart_{timestamp}.png"
            file_path = os.path.join("outputs", filename)

            with open(file_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            data["Transport Chart Path"] = file_path
        else:
            data["Transport Chart Path"] = "N/A"

        # --- Transport Description ---
        try:
            transport_text_elem = driver.find_element(By.ID, "transport-text")
            raw_transport_value = transport_text_elem.text
            clean_transport_text = " ".join(raw_transport_value.split())
            data["Transport Description"] = clean_transport_text
        except Exception:
            data["Transport Description"] = "N/A"

        # --- Tranport Table ---
        try:
            vehicles_list = []
            header_elements = driver.find_elements(By.CSS_SELECTOR, "div.transport-table thead th")
            headers = [th.text.strip() for th in header_elements]
            body_rows = driver.find_elements(By.CSS_SELECTOR, "div.transport-table tbody tr")

            for row in body_rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) == len(headers):
                    vehicle_data = {}

                    for i in range(len(cells)):
                        column_name = headers[i]
                        cell_value = cells[i].text.strip()

                        vehicle_data[column_name] = cell_value

                    vehicles_list.append(vehicle_data)

            data["Transport Fleet"] = vehicles_list if vehicles_list else "N/A"

            try:
                source_elem = driver.find_element(By.ID, "source")
                data["Transport Source"] = source_elem.text.strip()
            except Exception:
                data["Transport Source"] = "N/A"

        except Exception as e:
            data["Transport Fleet"] = "N/A"
            print(f"Could not scrape transport table: {e}")

    except Exception:
        print(f"No Transport side")

    ####################
    # -- Trademarks -- #
    ####################
    """
    try:
        trademark_url = base_url + "trademarks/"
        driver.get(trademark_url)
        try:
            desc_top = driver.find_element(By.ID, "description-top").text.strip()
            data["Trademark description"] = desc_top
        except Exception:
            data["Trademark description"] = "N/A"
        
        
        trademark_translation_da = {
            "grafinis": "Grafisk",
            "žodinis": "Ordmærke",

            "Registruotas": "Registreret",
            "Neregistruotinas ženklas 1": "Ikke-registrerbart mærke",
            "Atšaukta paraiška": "Tilbagetrukket ansøgning",
            "Pasibaigęs ženklo galiojimo terminas, su galimybe pratęsti": "Udløbet, med mulighed for forlængelse",
            "Išregistruotas, nepratęsus galiojimo termino": "Afregistreret, ikke forlænget",
            "Panaikinta registracija": "Annulleret registrering",
            "Išregistruotas": "Afregistreret",
            "--": "N/A",
            "----": "N/A"
            }
        try:
            trademark_list = []
            trademark_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

            
        except Exception:
            data["Varemærke liste"] = "N/A"
        

        try:
            source = driver.find_element(By.ID, "source").text.strip()
            data["Trademark source"] = source
        except Exception:
            data["Trademark source"] = "N/A"

    except Exception as e:
        print(f"No Tradermarks side: {e}")
    """
    ####################
    # -- Financials -- #
    ####################
    try:
        turnover_url = base_url + "turnover/"
        driver.get(turnover_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.finances-block")))
        
        finance_blocks = driver.find_elements(By.CSS_SELECTOR, "div.finances-block")
        all_financial_data = {}

        for block in finance_blocks:
            try:
                title_elements = block.find_elements(By.CSS_SELECTOR, "h2.title")
                if not title_elements:
                    continue

                block_title = title_elements[0].get_attribute("textContent").strip()
                title_lower = block_title.lower()

                if "annual financial" in title_lower or "consolidated" in title_lower:
                    financial_data = {}

                    # --- 1. Tabel Scraping (inkl. display:none) ---
                    table = block.find_element(By.CSS_SELECTOR, "table.finances-table")
                    header_elements = table.find_elements(By.CSS_SELECTOR, "thead th.years")
                    years = [th.get_attribute("textContent").strip() for th in header_elements]
                    
                    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) > 1:
                            metric_name = cells[0].get_attribute("textContent").strip()
                            values = [cell.get_attribute("textContent").strip() for cell in cells[1:]]
                            metric_data = {}
                            for i, year in enumerate(years):
                                if i < len(values):
                                    clean_val = " ".join(values[i].split())
                                    metric_data[year] = clean_val
                            financial_data[metric_name] = metric_data

                    # --- 2. Koncernstruktur (group members) - NU INDE I LOOPET ---
                    try:
                        block_titles = block.find_elements(By.CSS_SELECTOR, ".finances-summary__graph-title")
                        for i, title_el in enumerate(block_titles):
                            text = title_el.get_attribute("textContent").strip()

                            if "consolidated group consisted of" in text.lower():
                                koncern_data = {"Erklæring": text}

                                if i + 1 < len(block_titles):
                                    koncern_data["Moderselskab"] = block_titles[i+1].get_attribute("textContent").strip()

                                datterselskaber = []
                                ul_liste = block.find_elements(By.CSS_SELECTOR, "ul.mb-0 li")
                                for li in ul_liste:
                                    navn = " ".join(li.get_attribute("textContent").split())
                                    if navn:
                                        datterselskaber.append(navn)
                                
                                koncern_data["Datterselskaber"] = datterselskaber
                                financial_data["Koncernstruktur"] = koncern_data
                                break 
                    except Exception as e:
                        print(f"Fejl ved koncernstruktur i denne blok: {e}")

                    clean_title = block_title.split(" for ")[0].strip()
                    all_financial_data[clean_title] = financial_data

            except Exception as e:
                print(f"Error parsing a finance block: {e}")
                continue

        data["Financials"] = all_financial_data if all_financial_data else "N/A"
        
        data["Finansielle definitioner"] = {
            "Anlægsaktiver (Non-current assets)": "Aktiver, der skal bruges af virksomheden i mere end et år.",
            "Omsætningsaktiver (Current assets)": "Omfatter tilgodehavender, kortfristede materielle aktiver, varebeholdninger, forudbetalte omkostninger, andre tilgodehavender og likvider.",
            "Egenkapital (Equity)": "Dette er, hvad der er tilbage af de samlede aktiver efter fradrag af de samlede forpligtelser.",
            "Forpligtelser (Liabilities)": "Dette er virksomhedens langfristede og kortfristede gæld til leverandører, medarbejdere, kreditorer, staten osv.",
            "Salgsindtægter (Sales revenue)": "Stigningen i økonomiske fordele i regnskabsperioden som følge af salg af varer og tjenesteydelser.",
            "Resultat før skat (Profit before taxes)": "Alle virksomhedens indtægter minus alle virksomhedens udgifter.",
            "Overskudsgrad før skat (Profit before taxes margin)": "Forholdet mellem resultat før skat og salgsindtægter.",
            "Nettooverskud (Net profit)": "Dette er virksomhedens indtjening efter fradrag af alle udgifter og skatter.",
            "Nettomargin (Net profit margin)": "Forholdet mellem nettooverskud og salgsindtægter."
            }

    except Exception as e:
        data["Financials"] = "N/A"
        print(f"No financials side: {e}")

    ####################
    # -- Paid Taxes -- #
    ####################
    try:
        taxes_url = base_url + "paid-taxes/"
        driver.get(taxes_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.finances-block")))

        tax_blocks = driver.find_elements(By.CSS_SELECTOR, "div.finances-block")
        all_tax_data = {}

        for block in tax_blocks:
            try:
                title_el = block.find_elements(By.CSS_SELECTOR, "h2.title")
                if not title_el:
                    continue

                block_title = title_el[0].get_attribute("textContent").strip()
                table_elements = block.find_elements(By.CSS_SELECTOR, "table.finances-table")

                if not table_elements:
                    continue

                table = table_elements[0]
                table_results = {}

                header_elements = table.find_elements(By.CSS_SELECTOR, "thead th.years")
                years = [" ".join(th.get_attribute("textContent").split()) for th in header_elements]

                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")

                    if len(cells) > 1:
                        metric_name = cells[0].get_attribute("textContent").strip()
                        values = [c.get_attribute("textContent").strip() for c in cells[1:]]

                        metric_years = {}

                        for i, year in enumerate(years):
                            if i < len(values):
                                clean_val = " ".join(values[i].split())
                                metric_years[year] = clean_val
                        if metric_name:
                            table_results[metric_name] = metric_years

                all_tax_data[block_title] = table_results

            except Exception as e:
                print(f"Fejl ved behandling af skatte-blok: {e}")
                continue
        data["Skatter og Bidrag"] = all_tax_data if all_tax_data else "N/A"

    except Exception as e:
        data["Skatter og Bidrag"] = "N/A"
        print(f"No paid-taxes side: {e}")

    #############################
    # -- Number of employees -- #
    #############################
    try:
        employee_url = base_url + "number-of-employees/"
        driver.get(employee_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.description")))
        employee_history = []

        try:
            employee_desc_elem = driver.find_element(By.CSS_SELECTOR, "p.description").text.strip()
            data["Medarbejder beskrivelse"] = employee_desc_elem

        except Exception:
            data["Medarbejder beskrivelse"] = "N/A"

        employee_list_elem = driver.find_elements(By.CSS_SELECTOR, "ul.employees-list li.employee-item")
        for line in employee_list_elem:
            try:
                raw_text = line.get_attribute("textContent").strip()
                clean_text = " ".join(raw_text.split())

                if clean_text:
                    employee_history.append(clean_text)
            except Exception as e:
                continue

        data["Historiske data om antallet af forsikrede medarbejdere"] = employee_history if employee_history else "N/A"

    except Exception as e:
        data["Historiske data om antallet af forsikrede medarbejdere"] = "N/A"
        print(f"No employer page: {e}")

    ################
    # -- Salary -- #
    ################

    try:
        salary_url = base_url + "salary/"
        driver.get(salary_url)

        # -- CHARTS --
        try:
            os.makedirs("outputs", exist_ok=True)
            chart_containers = driver.find_elements(By.CSS_SELECTOR, "div.charts")
            
            for container in chart_containers:
                try:
                    link_el = container.find_elements(By.CSS_SELECTOR, ".highcharts-download a.basic-link")

                    if link_el:
                        chart_url = link_el[0].get_attribute("href")

                        if chart_url:
                            
                            url_filename = chart_url.split("/")[-1]
                            
                            file_name_base = url_filename.replace(".png", "").replace(".jpg", "")
                            
                            if not file_name_base:
                                file_name_base = container.get_attribute("id") or "unnamed_graph"

                            response = requests.get(chart_url, stream=True, timeout=10)
                            response.raise_for_status()

                            final_filename = f"{file_name_base}_{timestamp}.png"
                            file_path = os.path.join("outputs", final_filename)

                            with open(file_path, "wb") as f:
                                for chunk in response.iter_content(1024):
                                    f.write(chunk)
                                    
                            print(f"Graph gemt: {final_filename}")

                except Exception as e:
                    print(f"Kunne ikke downloade en specifik graf: {e}")
                    continue

        except Exception as e:
            print(f"fejl i graph loopet")

        # -- salary table --
        try:
            salary_table_data = {}
            salary_table = driver.find_elements(By.CSS_SELECTOR, "table.currency-table")
            if salary_table:
                table = salary_table[0]
                headers = []

                th_elements = table.find_elements(By.CSS_SELECTOR, "thead th")

                for th in th_elements[1:]:
                    raw_month_text = th.get_attribute("textContent").strip()
                    for lt_month, en_month in month_translation.items():
                        if lt_month in raw_month_text.lower():
                            raw_month_text = raw_month_text.replace(lt_month, en_month)

                    headers.append(raw_month_text)

                tbodies = table.find_elements(By.TAG_NAME, "tbody")
                current_category = "General Data"

                for tbody in tbodies:
                    rows = tbody.find_elements(By.TAG_NAME, "tr")

                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")

                        if len(cells) == 1 and cells[0].get_attribute("colspan"):
                            raw_category = cells[0].get_attribute("textContent").strip()
                            current_category = " ".join(raw_category.split())

                            if current_category not in salary_table_data:
                                salary_table_data[current_category] = {}

                        elif len(cells) > 1:
                            metric_name = cells[0].get_attribute("textContent").strip()
                            metric_name = " ".join(metric_name.split())
                            
                            values = [c.get_attribute("textContent").strip() for c in cells[1:]]
                            
                            metric_data = {}

                            for i, month in enumerate(headers):
                                if i < len(values):
                                    # Clean the number string to remove invisible HTML line breaks
                                    clean_val = " ".join(values[i].split())
                                    metric_data[month] = clean_val

                            if current_category not in salary_table_data:
                                salary_table_data[current_category] = {}
                                
                            # Save the metric data under the current active category
                            if metric_name:
                                salary_table_data[current_category][metric_name] = metric_data
                                
                data["Løn og Forsikring Data"] = salary_table_data if salary_table_data else "N/A"

        except Exception as e:
            data["Løn og Forsikring Data"] = "N/A"
            print(f"Fejl ved Løn og Forsikring Tabel: {e}")

    except Exception as e:
        print(f"No salary side: {e}")

    '''
    ###############
    # -- DEBTS -- #
    ###############
    try:
        debts_url = base_url + "debts/"
        driver.get(debts_url)

        try:

    except Exception as e:
        print(f"No debts side: {e}")
    '''


    # -- sidts payload --
    # time.sleep(3) # Test sleep ##########################################
    return data

def rekvizitai_scrape(query, timestamp, mode="name"):

    firefox_options = Options()
    firefox_options.add_argument("--headless")
    firefox_options.add_argument("--width=1920")
    firefox_options.add_argument("--height=1080")
    
    service = Service()
    driver = webdriver.Firefox(service=service, options=firefox_options)

    safe_query = urllib.parse.quote(query)

    base_url = "https://rekvizitai.vz.lt/en/companies/1/?scrollTo=searchForm"

    if mode == "code":
        url = f"{base_url}&name=&company_code={safe_query}&search_word=&industry=&search_terms=&location=&catUrlKey=&resetFilter=0&order=1&redirected=1"
    elif mode == "name":
        url = f"{base_url}&name={safe_query}&company_code=&search_word=&industry=&search_terms=&location=&catUrlKey=&resetFilter=0&order=1&redirected=1"
    elif mode == "manager":
        url = f"{base_url}&name=&company_code=&search_word={safe_query}&industry=&search_terms=&location=&catUrlKey=&resetFilter=0&order=1&redirected=1"
    else:
        print("Ugyldig mode valgt")
        driver.quit()
        return
    
    # -- main logic --
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 15)

        # -- 1. Cookie håndtering --
        try:
            cookie_btn = wait.until(
                EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"))
            )
            cookie_btn.click()
        except:
            print("No cookie dialog appeared")
            pass
        
        # -- 2. Search button click --
        try:
            search_button = wait.until(EC.element_to_be_clickable((By.ID, "ok")))
            search_button.click()
        except Exception as e:
            print(f"Search button error: {e}")

        # -- 3. First result click --
        click_success = False
        for attempt in range(3):
            try:
                first_result = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".list-item .company-title")))
                first_result.click()
                click_success = True
                break
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", first_result)
                click_success = True
                break
            except StaleElementReferenceException:
                print(f"Forsøg {attempt + 1}: Elementet blev forældet (Stale). Prøver igen...")

        if not click_success and "/company/" not in driver.current_url:
            return {"error": "Kunne ikke klikke på resultatet, eller ingen resultater fundet."}
        
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title")))
        print(f"Succes! Landet på: {driver.current_url}")

        return company_side_scrape(driver, wait, timestamp)

    except Exception as e:
        print(f"Fejl: {e}")
    finally:
        driver.quit()

def scrape_rekvizitai_for_flask(query=None):
    start_time = time.time()
    results = []
    errors = []

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        if not query:
            raise ValueError("Der blev ikke angivet et søgeord (query) til rekvizitai.vz.lt.")

        raw_data = rekvizitai_scrape(query, timestamp, mode="name")
        
        if raw_data and "error" in raw_data:
            errors.append(raw_data["error"])
        elif raw_data:
            results.append(raw_data)
        else:
            errors.append("Scraperen kørte, men returnerede ingen data.")

    except Exception as e:
        errors.append(str(e))

    runtime_ms = int((time.time() - start_time) * 1000)

    # 5. Returnér det format, som `app.py` forventer for at kunne lave JSON-log og sende til Elasticsearch
    return {
        "source": "Rekvizitai Scraper (Selenium)",
        "query": query if query else "Ingen",
        "runtime_ms": runtime_ms,
        "results": results,
        "errors": errors
    }

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Scrape company data from Rekvizitai.")
    parser.add_argument("query", help="The search term (Company name, code, or manager)")
    parser.add_argument(
        "-m", "--mode","--m", "-mode",
        choices=["name", "code", "manager"],
        default="name",
        help="Search mode (default: name)"
    )

    args = parser.parse_args()

    global_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # global_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    result = rekvizitai_scrape(args.query, global_timestamp, mode=args.mode)

    if result:
        # --- JSON file saving ---

        os.makedirs("outputs", exist_ok=True)
        
        scraped_name = result.get("Company name", "Unknown_Company")
        clean_name = re.sub(r'[^a-zA-Z0-9 ]', '', scraped_name)
        safe_company_name = clean_name.strip().replace(" ", "_").lower()

        filename = f"{safe_company_name}_{global_timestamp}.json"
        file_path = os.path.join("outputs", filename)

        with open(file_path, "w", encoding="utf-8") as json_file:
            json.dump(result, json_file, indent=4, ensure_ascii=False)

        print(f"Data saved to: {file_path}")
    else:
        print("Scraping failed or returned no data. Nothing was saved.")