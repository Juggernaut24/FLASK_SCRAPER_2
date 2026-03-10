from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, Any
from datetime import datetime
import requests
import time
import os
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def handle_cookies(driver):
    """
    Attempts to find and close the cookie consent banner on Tjekbil.dk.
    It looks for common accept/allow buttons.
    """
    print("Checking for cookie banner...")
    try:
        # We use a combined XPath to look for buttons that say "Accepter", "Tillad", or "OK"
        # The translate function makes the search case-insensitive (e.g., matches "Accepter", "ACCEPTER", "accepter")
        xpath_cookie_btn = """
            //button[
                contains(translate(text(), 'ACCEPTER', 'accepter'), 'accepter') or 
                contains(translate(text(), 'TILLAD', 'tillad'), 'tillad') or 
                contains(translate(text(), 'OK', 'ok'), 'ok')
            ]
        """
        
        # Wait up to 5 seconds for the button to become clickable
        cookie_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, xpath_cookie_btn))
        )
        
        # Scroll the button into view just in case it is off-screen
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cookie_btn)
        
        # Click the button
        cookie_btn.click()
        print("Cookie banner accepted and closed.")
        
        # Give the website a brief moment to process the click and remove the banner from the screen
        driver.implicitly_wait(1)

    except Exception:
        # If the wait times out (no banner appeared within 5 seconds), we assume there is no banner and move on.
        print("No cookie banner found (or it disappeared). Continuing...")

def km_dato_graph(data_liste, plate, timestamp):
        
    parsed_data = []

    # 1. Behandl rå tekstdata til brugbare tal og datoer
    for entry in data_liste:
        km_match = re.search(r'([\d.]+)\s+km', entry)
        date_match = re.search(r'(\d{2}-\d{2}-\d{4})', entry)
        
        if km_match and date_match:
            km_tal = int(km_match.group(1).replace('.', ''))
            dato_objekt = datetime.strptime(date_match.group(1), '%d-%m-%Y')
            parsed_data.append((dato_objekt, km_tal))

    if not parsed_data:
        print("Ingen km-data fundet til grafen.")
        return

    # 2. Sortér kronologisk
    parsed_data.sort(key=lambda x: x[0])
    datoer = [d[0] for d in parsed_data]
    kilometer = [d[1] for d in parsed_data]

    # 3. Design grafen
    plt.figure(figsize=(10, 6))
    plt.plot(datoer, kilometer, marker='o', linestyle='-', color='#1f77b4')
    plt.title(f'Kilometerhistorik for {plate}')
    plt.xlabel('Dato')
    plt.ylabel('Kilometer (km)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 4. Konstruér filnavnet præcis som ønsket
    # Gemmes i 'outputs' mappen sammen med JSON filen
    filename = f"{plate}_{timestamp}_graph.png"
    save_path = os.path.join("outputs", filename)
    
    plt.savefig(save_path)
    plt.close("all")
    print(f"Graf gemt som: {save_path}")

def scrape_tjekbil_data(license_plate: str) -> Dict[str, Any]:
    edge_options = Options()
    edge_options.add_argument("--headless")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_argument("--log-level=3")
    edge_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    service = Service(executable_path="msedgedriver.exe")
    driver = webdriver.Edge(service=service, options=edge_options)

    handle_cookies(driver)

    scraped_data = {
        "Oversigt":{
            "Plate":None,
            "stel nr.":None,
            "Bil navn":None,
            "Model":None,
            "1.Reg dato":None,
            "alder":None,
            "Brændstof":None,
            "Hestekræfter":None,
        },
        "Overblik": {
            "Kviktjek": {
                "Status":None,
                "Seneste syn":None,
                "Næste syn":None,
                "km-tal ved seneste syn":None,
                "km fusk advarsel":None,
                "Nuværende ejer":None,
                "Tidligere ejere":None,
                "Efterlysninger":None,
                "Efterlysninger sidst opdateret":None,
            },
            "Forsikring": {
                "Nuværende forsikringsselskab":None,
                "Forsikring status":None,
                "Oprettet dato":None,
            },
            "Økonomi":{
                "Gæld":None,
                "Sidst opdateret":None,
                "Estimerede omkostninger":None,
                "Afgifter":None,
            }
        },
        "Teknisk info":{
            "Stamdata":{
                "Model årgang":None,
                "Indregistreret":None,
                "Type":None,
                "Farve":None,
                "Anvendelse":None,
                "Registreringsnummer":None,
                "Stelnummer":None,
                "Stelnummer findes her":None,
                "Produktionsland":None,
                "Tilladelser":None,
            },
            "Teknik":{
                "Motor":None,
                "Effekt":None,
                "Topfart":None,
                "Automatgear":None,
                "Motorkode":None,
            },
            "Miljø":{
                "Miljøzoner":None,
                "CO2 udslip":None,
                "Partikelfilter":None,
                "Euronorm":None,
            },
            "Vægt":{
                "Køreklar min. vægt":None,
                "Totalvægt":None,
                "Teknisk totalvægt":None,
                "Vogntogsvægt":None,
                "Anhængertræk":None,
                "Maksimal vægt af påhængskøretøj":None,
            },
            "Drivmiddel":{
                "Drivkraft":None,
                "Opgivet forbrug":None,
                "Plugin hybrid":None,
            },
            "Kilometerstand": {
                "Seneste km registreringer(liste)": []
            },
            "Udstyr":{
                "Sikkerhed":None,
                "NCAP test med 5 stjerner":None,
                "Udstyr":None,
            },
        },
        "Tidslinje": [],
        "Synsrapporter": [],
        "Registreringsafgift": {
            "vurderingstype": None,
            "beregningstype": None,
            "Biltype": None,
            "Nypris": None,
            "Handelspris": None,
            "værdi uden afgift": None,
            "Afgift": None,
            "Betalt afgift": None,
            "Dato": None,
        },
        "Afgifter": {}
    }

    def get_text_safe(xpath, context=driver):
        try:
            elem = context.find_element(By.XPATH, xpath)
            return elem.text.strip()
        except:
            return None
        
    
    
    # -- WHERE THE MAGIC HAPPENS --
    try:

        url = f"https://www.tjekbil.dk/nummerplade/{license_plate}/Overblik"

        driver.get(url)

        # kan Tilføje cookie håndtering

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h3"))
        )

        ####################
        # --- oversigt --- #
        ####################
        try:
            scraped_data["Oversigt"]["Plate"] = get_text_safe("//*[@id='optimize-vin-box']/parent::div/preceding-sibling::h6")
            scraped_data["Oversigt"]["Bil navn"] = get_text_safe("//h3")
            scraped_data["Oversigt"]["Model"] = get_text_safe("//h5")
            scraped_data["Oversigt"]["stel nr."] = get_text_safe("//*[@id='optimize-vin-box']")
            scraped_data["Oversigt"]["1.Reg dato"] = get_text_safe("//div[@aria-label='1. REG. DATO']//span[contains(@class, 'MuiChip-label')]")
            scraped_data["Oversigt"]["alder"] = get_text_safe("//div[@aria-label='ALDER']//span[contains(@class, 'MuiChip-label')]")
            scraped_data["Oversigt"]["Brændstof"] = get_text_safe("//img[contains(@src, 'fuel-icon')]/ancestor::div[contains(@class, 'MuiChip-root')]//span[contains(@class, 'MuiChip-label')]")
            scraped_data["Oversigt"]["Hestekræfter"] = get_text_safe("//img[contains(@src, 'engine-power-icon')]/ancestor::div[contains(@class, 'MuiChip-root')]//span[contains(@class, 'MuiChip-label')]")

        except Exception as e:
            print(f"Fejl i Oversigt: {e}")
        
        ####################
        # --- Overblik --- #
        ####################

        # --Overblik -> KVIKTJEK--
        try:
            KVIKTJEK_card = driver.find_element(By.XPATH, "//h5[text()='Kviktjek']/ancestor::div[2]")
        
            # status
            status_xpath = ".//span[contains(text(), 'Status')]/parent::div/following-sibling::div//span"
            scraped_data["Overblik"]["Kviktjek"]["Status"] = get_text_safe(status_xpath, context=KVIKTJEK_card)

            # seneste syn
            xpath_seneste = ".//span[text()='Seneste syn']/following::p[1]"
            scraped_data["Overblik"]["Kviktjek"]["Seneste syn"] = get_text_safe(xpath_seneste, context=KVIKTJEK_card)
            # næste syn
            xpath_naeste = ".//p[contains(text(), 'Næste syn')]"
            scraped_data["Overblik"]["Kviktjek"]["Næste syn"] = get_text_safe(xpath_naeste, context=KVIKTJEK_card)

            # lave næste syn dato til kun dato og ikke text
            naeste_syn_date = scraped_data["Overblik"]["Kviktjek"]["Næste syn"]
            if naeste_syn_date:
                clean_date = naeste_syn_date.split()[-1]
                scraped_data["Overblik"]["Kviktjek"]["Næste syn"] = clean_date

            # Km-tal ved seneste syn
            xpath_seneste_km = ".//span[contains(text(),'Km-tal ved seneste syn')]/following::span[1]"
            scraped_data["Overblik"]["Kviktjek"]["km-tal ved seneste syn"] = get_text_safe(xpath_seneste_km, context=KVIKTJEK_card)

            # fusk
            scraped_data["Overblik"]["Kviktjek"]["km fusk advarsel"] = get_text_safe(".//h6[contains(text(), 'Mistænkeligt') or contains(text(), 'Ingen tegn')]")

            # Nuværende ejer
            xpath_nuvaerende_ejer = ".//span[text()='Nuværende ejer']/following::p[1]"
            scraped_data["Overblik"]["Kviktjek"]["Nuværende ejer"] = get_text_safe(xpath_nuvaerende_ejer, context=KVIKTJEK_card)
            # Tidligere ejer
            xpath_tidligere = ".//p[contains(., 'tidligere ejer')]"
            scraped_data["Overblik"]["Kviktjek"]["Tidligere ejere"] = get_text_safe(xpath_tidligere, context=KVIKTJEK_card)
            tidligere = scraped_data["Overblik"]["Kviktjek"]["Tidligere ejere"]
            if tidligere == None:
                tidligere = "Ingen tidligere ejer fundet."
                scraped_data["Overblik"]["Kviktjek"]["Tidligere ejere"] = tidligere

            # Efterlysninger
            try:
                xpath_content = ".//span[text()='Efterlysninger']/parent::div/following-sibling::div[1]"
                content_div = KVIKTJEK_card.find_element(By.XPATH, xpath_content)

                xpath_status = ".//p[not(contains(text(), 'Sidst opdateret')) and string-length(text()) > 5]"
                status_tekst = get_text_safe(xpath_status, context=content_div)

                xpath_dato = ".//p[contains(text(), 'Sidst opdateret')]"
                dato_raw = get_text_safe(xpath_dato, context=content_div)

                if status_tekst:
                    scraped_data["Overblik"]["Kviktjek"]["Efterlysninger"] = status_tekst
                else:
                    scraped_data["Overblik"]["Kviktjek"]["Efterlysninger"] = "Ingen Efterlysninger"

                if dato_raw:
                    clean_dato = dato_raw.replace("Sidst opdateret:", "").strip()
                    scraped_data["Overblik"]["Kviktjek"]["Efterlysninger sidst opdateret"] = clean_dato
                else:
                    scraped_data["Overblik"]["Kviktjek"]["Efterlysninger sidst opdateret"] = None

            except Exception as e:
                print(f"Kunne ikke læse Efterlysninger: {e}")
                scraped_data["Overblik"]["Kviktjek"]["Efterlysninger"] = None

        except Exception as e:
            print(f"Error finding Kviktjek card: {e}")

        # --Overblik -> FORSIKRING--

        forsikring_fields = {
            "Nuværende forsikringsselskab": ".//span[text()='Nuværende forsikringsselskab']/following::p[1]",
            "Forsikring status": ".//span[text()='Status']/following::p[1]",
            "Oprettet dato": ".//span[text()='Oprettet']/following::p[1]"
        }
        try:
            FORSIKRING_card = driver.find_element(By.XPATH, "//h5[text()='Forsikring']/ancestor::div[2]")

            for key, xpath in forsikring_fields.items():
                try:
                    value = get_text_safe(xpath, context=FORSIKRING_card)

                    scraped_data["Overblik"]["Forsikring"][key] = value

                except Exception as field_error:
                    print(f"Error scraping field '{key}': {field_error}")
                    scraped_data["Overblik"]["Forsikring"][key] = None
                    continue

        except Exception as card_error:
            print(f"Could not find the main Forsikring card: {card_error}")

        # --Overblik -> ØKONOMI--
        oekonomi_fields = {
            "Gæld": ".//span[text()='Gæld']/following::p[1]",
            "Sidst opdateret": ".//p[contains(text(), 'Sidst opdateret')]",
            "Estimerede omkostninger": ".//span[text()='Estimerede omkostninger']/following::p[1]",
            "Afgifter": ".//span[text()='Afgifter']/following::p[1]",
        }

        # finding and clicking opdate button
        try:
            OEKONOMI_card = driver.find_element(By.XPATH, "//h5[text()='Økonomi']/ancestor::div[2]")
            xpath_opdaterknap = ".//span[text()='Opdater nu']"

            try:
                opdater_knap = OEKONOMI_card.find_element(By.XPATH, xpath_opdaterknap)
                opdater_knap.click()
                WebDriverWait(driver, 10).until(EC.staleness_of(OEKONOMI_card))
                OEKONOMI_card = driver.find_element(By.XPATH, "//h5[text()='Økonomi']/ancestor::div[2]")

            except Exception as e:
                # No button
                pass

            for key, xpath in oekonomi_fields.items():
                try:
                    value = get_text_safe(xpath, context=OEKONOMI_card)

                    if key == "sidst_opdatering" and value:
                        value = value.removeprefix('Sidst opdateret: ')

                    if key == "estimerede_omkostninger":
                        if not value or value.split() == "":
                            fallback_xpath = ".//span[text()='Estimerede omkostninger']/following::p[2]"
                            value = get_text_safe(fallback_xpath, context=OEKONOMI_card)

                    scraped_data["Overblik"]["Økonomi"][key] = value

                except Exception as field_error:
                    print(f"Error scraping field '{key}': {field_error}")
                    scraped_data["Overblik"]["Økonomi"][key] = None
                    continue
            
        except Exception as card_error:
            print(f"Could not find Økonomi card: {card_error}")

        ########################
        # --- TEKNISK INFO --- #
        ########################

        teknisk_info_fields = {
            "Stamdata": {
                "Model årgang": ".//span[text()='Model årgang']/following::p[1]",
                "Indregistreret": ".//span[text()='Indregistreret']/following::p[1]",
                "Type": ".//span[text()='Type']/following::p[1]",
                "Farve": ".//span[text()='Farve']/following::p[1]",
                "Anvendelse": ".//span[text()='Anvendelse']/following::p[1]",
                "Registreringsnummer": ".//span[text()='Registreringsnummer']/following::p[1]",
                "Stelnummer": ".//span[text()='Stelnummer']/following::p[1]",
                "Stelnummer findes her": ".//p[contains(text(), 'Findes her:')]",
                "Produktionsland": ".//span[text()='Produktionsland']/following::p[1]",
                "Tilladelser": ".//span[text()='Tilladelser']/following::p[1]"
            },
            "Teknik": {
                "Motor": ".//span[text()='Motor']/following::p[1]",
                "Effekt": ".//span[text()='Effekt']/following::p[1]",
                "Topfart": ".//span[text()='Topfart']/following::p[1]",
                "Automatgear": ".//span[text()='Automatgear']/following::p[1]",
                "Motorkode": ".//span[text()='Motorkode']/following::p[1]"
            },
            "Miljø": {
                "Miljøzoner": ".//span[text()='Miljøzoner']/following::p[1]",
                "CO2 udslip": ".//span[text()='CO2-UDSLIP']/following::p[1]",
                "Partikelfilter": ".//span[text()='Partikelfilter']/following::p[1]",
                "Euronorm": ".//span[text()='EURONORM']/following::p[1]"
            },
            "Vægt": {
                "Køreklar min. vægt": ".//span[text()='Køreklar min. vægt']/following::p[1]",
                "Totalvægt": ".//span[text()='Totalvægt']/following::p[1]",
                "Teknisk totalvægt": ".//span[text()='Teknisk totalvægt']/following::p[1]",
                "Vogntogsvægt": ".//span[text()='Vogntogsvægt']/following::p[1]",
                "Anhængertræk": ".//span[text()='Anhængertræk']/following::p[1]",
                "Maksimal vægt af påhængskøretøj": ".//span[text()='Maksimal vægt af påhængskøretøj']/following::p[1]"
            },
            "Drivmiddel": {
                "Drivkraft": ".//span[text()='Drivkraft']/following::p[1]",
                "Opgivet forbrug": ".//span[text()='Opgivet forbrug']/following::p[1]",
                "Plugin hybrid": ".//span[text()='Plugin hybrid']/following::p[1]"
            },
            # Left empty to perfectly match your provided data structure
            "Kilometerstand": [],
            "Udstyr": {
                "Sikkerhed": ".//span[text()='Sikkerhed']/following::p[1]",
                "NCAP test med 5 stjerner": ".//span[text()='NCAP test med 5 stjerner']/following::p[1]",
                "Udstyr": ".//span[text()='Udstyr']/following::p[1]"
            }
        }

        try:
            # -- teknisk info loop --
            TEKNISK_INFO_card = driver.find_element(By.XPATH, "//h5[text()='Teknisk info']/ancestor::div[2]")

            for category, fields in teknisk_info_fields.items():

                if category == "Kilometerstand":
                    xpath_km_data = ".//span[text()='Seneste km-registreringer']/following::p[contains(text(), 'km (')]"

                    try: # KM stand "Vis flere" knap
                        km_elements_initial = TEKNISK_INFO_card.find_elements(By.XPATH, xpath_km_data)
                        initial_count = len(km_elements_initial)

                        xpath_knap = ".//p[text()='Se alle' or text()='Vis flere']"
                        udvid_knap = TEKNISK_INFO_card.find_element(By.XPATH, xpath_knap)

                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", udvid_knap)
                        udvid_knap.click()

                        WebDriverWait(driver, 5).until(
                            lambda d: len(TEKNISK_INFO_card.find_elements(By.XPATH, xpath_km_data)) > initial_count
                        )
                    except Exception:
                        pass

                    try:
                        km_elements_final = TEKNISK_INFO_card.find_elements(By.XPATH, xpath_km_data)
                        km_list_raw = []

                        for element in km_elements_final:
                            text_val = element.text.strip()

                            if text_val:
                                km_list_raw.append(text_val)

                        scraped_data["Teknisk info"]["Kilometerstand"]["Seneste km registreringer(liste)"] = km_list_raw

                        ### LATER USE ##############################################################################
                        scraped_data["Teknisk info"]["Kilometerstand"]["seneste_km_registreringer_structured"] = []
                        ############################################################################################

                    except Exception as e:
                        print(f"Error scraping kilometer data: {e}")
                        scraped_data["Teknisk info"]["Kilometerstand"]["Seneste km registreringer(liste)"] = []
                        scraped_data["Teknisk info"]["Kilometerstand"]["seneste_km_registreringer_structured"] = []
                    continue

                for key, xpath in fields.items():
                    try:
                        value = get_text_safe(xpath, context=TEKNISK_INFO_card)
                        scraped_data["Teknisk info"][category][key] = value

                    except Exception as field_error:
                        print(f"Error scraping '{category}' -> '{key}': {field_error}")
                        scraped_data["Teknisk info"][category][key] = None
                        continue

        except Exception as card_error:
            print(f"Could not find Teknisk info card: {card_error}")

        #####################
        # --- Tidslinje --- #
        #####################
        try:
            TIDSLINJE_card = driver.find_element(By.ID, "timeline")

            # KM stand "Vis mere" BUTTON
            try:
                vis_mere_btn = TIDSLINJE_card.find_element(By.XPATH, ".//button[contains(text(), 'Vis mere')]")
                current_count = len(TIDSLINJE_card.find_elements(By.XPATH, ".//li"))
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", vis_mere_btn)
                vis_mere_btn.click()

                WebDriverWait(driver, 5).until(
                    lambda d: len(TIDSLINJE_card.find_elements(By.XPATH, ".//li")) > current_count
                )
            except Exception:
                # No button
                pass

            timeline_items = TIDSLINJE_card.find_elements(By.XPATH, ".//li")
            tidslinje_data= []

            for item in timeline_items:
                try:
                    dato = item.find_element(By.XPATH, ".//p[1]").text.strip()
                    titel = item.find_element(By.XPATH, ".//h6").text.strip()

                    event = {
                        "Dato": dato,
                        "Titel": titel,
                        "Detaljer": {},
                    }

                    if titel == "Annonceret til salg":
                        event["Detaljer"]["Oprettet"] = get_text_safe(".//p[text()='Oprettet:']/following-sibling::p", context=item)
                        event["Detaljer"]["Fjernet"] = get_text_safe(".//p[text()='Fjernet:']/following-sibling::p", context=item)
                        event["Detaljer"]["Pris"] = get_text_safe(".//p[text()='Pris:']/following-sibling::p", context=item)
                        event["Detaljer"]["Kilometer"] = get_text_safe(".//p[text()='Kilometer:']/following-sibling::p", context=item)
                        event["Detaljer"]["Sælger"] = get_text_safe(".//p[text()='Sælger:']/following-sibling::p", context=item)
                        event["Detaljer"]["Kilde"] = get_text_safe(".//p[text()='Kilde:']/following-sibling::p", context=item)

                    elif titel in ["Periodisk syn", "Registreringssyn uden ændring"]:
                        event["Detaljer"]["Beskrivelse"] ="Mere info i 'Synsrapporter'"

                    else:
                        paragraphs = item.find_elements(By.XPATH, ".//h6/following-sibling::p")
                        beskrivelse = " | ".join([p.text.strip() for p in paragraphs if p.text.strip()])
                        event["Detaljer"]["Beskrivelse"] = beskrivelse if beskrivelse else None

                    tidslinje_data.append(event)

                except Exception as event_error:
                    print(f"Error parsing a timeline item: {event_error}")
                    continue
            scraped_data["Tidslinje"] = tidslinje_data

        except Exception as card_error:
            print(f"Could not find Tidslinje info card: {card_error}")

        #########################
        # --- Synsrapporter --- #
        #########################
        try:
            
            print("Starter synsrapporter...")
            inspection_container = driver.find_element(By.ID, "inspection")
            row_count = len(inspection_container.find_elements(By.XPATH, ".//table/tbody/tr"))
            print(f"Fandt {row_count} synsrapporter.")
            
            synsrapporter_data = []

            # 2. Use an index (i) loop instead of an element loop to avoid Stale Elements
            for i in range(row_count):
                try:
                    print(f"\n--- Behandler række {i+1} af {row_count} ---")
                    # 3. RE-FIND the container and the specific row fresh on every single iteration
                    inspection_container = driver.find_element(By.ID, "inspection")
                    row = inspection_container.find_elements(By.XPATH, ".//table/tbody/tr")[i]
                    
                    # EXTRACT ONLY 'REG NR' FROM SURFACE DATA
                    cols = row.find_elements(By.XPATH, ".//td")
                    
                    if len(cols) == 6:
                        reg_nr = cols[5].text.strip()
                        report = {"reg_nr": reg_nr}

                        # 4. CLICK THE FIRST CELL (instead of the row) TO OPEN THE MODAL
                        first_cell = cols[0]
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_cell)
                        print("Klikker for at åbne synsrapport...")
                        driver.execute_script("arguments[0].click();", first_cell)
                        
                        # WAIT FOR MODAL AND DATA TO APPEAR
                        modal_xpath = "//div[@role='dialog']"
                        print("Venter på at pop-up vinduet (modal) åbner...")
                        
                        modal_element = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, modal_xpath))
                        )
                        
                        WebDriverWait(driver, 5).until(
                            lambda d: len(modal_element.find_elements(By.XPATH, ".//table/tbody/tr")) > 0
                        )
                        print("Modal er åben og data er indlæst.")
                        # SCRAPE THE DETAILED MODAL DATA
                        try:
                            detail_rows = modal_element.find_elements(By.XPATH, ".//table/tbody/tr")
                            for d_row in detail_rows:
                                d_cols = d_row.find_elements(By.XPATH, ".//td")
                                
                                if len(d_cols) == 2:
                                    key = d_cols[0].text.strip().lower()
                                    value = d_cols[1].text.strip()
                                    report[key] = value

                            # Extract the "Fejlliste"
                            try:
                                fejlliste_xpath = ".//span[text()='Fejlliste:']/following-sibling::div//p"
                                fejl_elements = modal_element.find_elements(By.XPATH, fejlliste_xpath)
                                fejlliste = [f.text.strip() for f in fejl_elements if f.text.strip()]
                                report["fejlliste"] = fejlliste
                            except Exception:
                                report["fejlliste"] = []

                            # Bil Billede save
                            print("Leder efter billede i synsrapporten...")

                            try:
                                # Find the image element inside the modal
                                image_elements = modal_element.find_elements(By.XPATH, ".//img")
                                
                                if image_elements:
                                    img_element = image_elements[0]
                                    
                                    # Scroll the image into the center of the view to ensure it renders fully
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", img_element)
                                    
                                    # Give it a tiny fraction of a second to render cleanly
                                    driver.implicitly_wait(0.5)

                                    # Set up the file path
                                    os.makedirs("outputs", exist_ok=True)                              
                                    now = datetime.now()
                                    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
                                    filename = f"{reg_nr}_{timestamp}.jpg"
                                    save_path = os.path.join("outputs", filename)
                                    
                                    # Use Selenium to capture exactly what the browser sees for this specific element
                                    img_element.screenshot(save_path)
                                    
                                    report["photo_path"] = save_path
                                    print("Image saved successfully using browser screenshot.")

                                else:
                                    report["photo_path"] = None
                                    print("No image found.")

                            except Exception as img_error:
                                print(f"Error saving image: {img_error}")
                                report["photo_path"] = None
                            

                        except Exception as scrape_error:
                            print(f"Error scraping modal details for row {i}: {scrape_error}")

                        # CLOSE THE MODAL
                        print("Forsøger at lukke modal...")
                        try:
                            close_btn = modal_element.find_element(By.XPATH, ".//button[text()='Luk rapport' or @title='Luk rapport']")
                            driver.execute_script("arguments[0].click();", close_btn)
                            
                            WebDriverWait(driver, 5).until(
                                EC.invisibility_of_element_located((By.XPATH, modal_xpath))
                            )
                            print("Modal lukket via knap.")

                        except Exception as close_error:
                            print(f"Failed to close modal on row {i}, using Escape: {close_error}")
                            
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            
                            WebDriverWait(driver, 5).until(
                                EC.invisibility_of_element_located((By.XPATH, modal_xpath))
                            )
                            print("Modal lukket via ESCAPE.")

                        synsrapporter_data.append(report)
                        print(f"Række {i+1} afsluttet med succes.")

                except Exception as row_error:
                    # The traceback will now tell you exactly which row number failed
                    print(f"Error scraping inspection row index {i}: {row_error}")
                    continue
                    
            scraped_data["Synsrapporter"] = synsrapporter_data

        except Exception as container_error:
            print(f"Could not find the Synsrapporter container: {container_error}")
            scraped_data["Synsrapporter"] = []

        ###############################
        # --- Registreringsafgift --- #
        ###############################
        try:
            REGISTRERINGSAFGIFT_card = driver.find_element(By.ID, "registrationTax")
            first_row = REGISTRERINGSAFGIFT_card.find_element(By.XPATH, ".//tbody/tr[1]")
            cols = first_row.find_elements(By.XPATH, ".//td")

            if len(cols) >= 9:
                scraped_data["Registreringsafgift"]["vurderingstype"] = cols[0].text.strip() or "Ingen værdi"
                scraped_data["Registreringsafgift"]["beregningstype"] = cols[1].text.strip() or "Ingen værdi"
                scraped_data["Registreringsafgift"]["Biltype"] = cols[2].text.strip() or "Ingen værdi"
                scraped_data["Registreringsafgift"]["Nypris"] = cols[3].text.strip() or "Ingen værdi"
                scraped_data["Registreringsafgift"]["Handelspris"] = cols[4].text.strip() or "Ingen værdi"
                scraped_data["Registreringsafgift"]["værdi uden afgift"] = cols[5].text.strip() or "Ingen værdi"
                scraped_data["Registreringsafgift"]["Afgift"] = cols[6].text.strip() or "Ingen værdi"
                scraped_data["Registreringsafgift"]["Betalt afgift"] = cols[7].text.strip() or "Ingen værdi"
                scraped_data["Registreringsafgift"]["Dato"] = cols[8].text.strip() or "Ingen værdi"

        except Exception as container_error:
            print(f"Could not find the Registreringsafgift container: {container_error}")
            scraped_data["Registreringsafgift"] = []

        ################
        # --- Pant --- #
        ################

        # pant kode her

        ####################
        # --- Afgifter --- #
        ####################
        try:
            AFGIFTER_card = driver.find_element(By.ID, "taxes")

            rows = AFGIFTER_card.find_elements(By.XPATH, ".//tbody/tr")

            for row in rows:
                cells = row.find_elements(By.XPATH, ".//td")
                if len(cells) >= 3:
                    tax_type = cells[0].text.strip()
                    interval = cells[1].text.strip()
                    amount = cells[2].text.strip()

                    scraped_data["Afgifter"][tax_type] = {
                        "Interval": interval,
                        "Beløb": amount,
                    }

        except Exception as container_error:
            print(f"Could not find the Afgifter container: {container_error}")
            scraped_data["Afgifter"] = {}



    except Exception as e:

        error_name = type(e).__name__
        print(f"Kritisk fejl: {error_name}")
        scraped_data["Oversigt"]["Bil navn"] = "Fejl under hentning"
    finally:
        driver.quit()
    return scraped_data

def scrape_tjekbil_for_flask(query=None):
    """
    Wrapper til Flask-appen. Sørger for tidsmåling og 
    at dataen returneres i det rigtige format til Elasticsearch.
    """
    start_time = time.time()
    results = []
    errors = []
    
    # Generer tidsstempel til brug i grafer og billednavne
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        if not query:
            raise ValueError("Ingen nummerplade angivet.")

        # Vi kalder din store funktion
        raw_data = scrape_tjekbil_data(query)
        
        if raw_data:
            # Vi tilføjer den rå data til vores result-liste
            # Selvom det kun er én bil, skal det være en liste pga. vores loop i app.py
            results.append(raw_data)
            
            # Her kan vi også kalde din graf-funktion, så den bliver genereret
            km_liste = raw_data["Teknisk info"]["Kilometerstand"].get("Seneste km registreringer(liste)", [])
            if km_liste:
                km_dato_graph(km_liste, query, timestamp)
        else:
            errors.append("Ingen data blev fundet på denne nummerplade.")

    except Exception as e:
        errors.append(f"Tjekbil Scraper Fejl: {str(e)}")

    runtime_ms = int((time.time() - start_time) * 1000)

    return {
        "source": "Tjekbil Scraper (Selenium)",
        "query": query,
        "runtime_ms": runtime_ms,
        "results": results,
        "errors": errors
    }

if __name__ == "__main__":
    import pprint
    import os
    import json
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Scrape vehicle data from Tjekbil.dk")
    parser.add_argument(
        "plate",
        type=str,
        help="The license plate or stel number to scrape (e.g., AB12345)"
    )

    args = parser.parse_args()

    pp = pprint.PrettyPrinter(indent=4, sort_dicts=False)
    result = scrape_tjekbil_data(args.plate)

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")

    actual_plate = result.get("Oversigt", {}).get("Plate")

    if not actual_plate:
        actual_plate = args.plate

    os.makedirs("outputs", exist_ok=True)
    filename = os.path.join("outputs", f"{actual_plate}_{timestamp}_data.json")

    with open (filename, "w", encoding="utf-8") as json_file:
        json.dump(result, json_file, indent=4, ensure_ascii=False)

    km_liste = result["Teknisk info"]["Kilometerstand"].get("Seneste km registreringer(liste)", [])
    km_dato_graph(km_liste, actual_plate, timestamp)

    print(f"Data successfully saved to: {filename}")
    # pp.pprint(result)

"""
AB12345
CK57480
DB49723
DZ87565
HD3522 = Påhængsvogn
"""