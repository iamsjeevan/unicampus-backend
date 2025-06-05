# app/services/college_portal_scraper.py
import requests
from bs4 import BeautifulSoup
import re
import json
import ast
from urllib.parse import urljoin
from app.config import Config # Import Config to access URLs
import warnings

# Suppress InsecureRequestWarning:
from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# --- PARSING HELPER FUNCTIONS (UNCHANGED, assumed to be working if HTML structure is consistent) ---
# _extract_basic_student_info, _extract_dashboard_subject_summaries, _extract_exam_history
# (Your existing parsing functions go here)
def _extract_basic_student_info(dashboard_html_content):
    soup = BeautifulSoup(dashboard_html_content, 'lxml')
    student_info = {
        "name": None, "usn": None, "semester": None,
        "section": None, "department": "Unknown"
    }
    error_messages = []

    try:
        name_tag = soup.select_one('.cn-stu-data1 h3')
        if name_tag:
            student_info["name"] = name_tag.text.strip()

        usn_tag = soup.select_one('.cn-stu-data1 h2')
        if usn_tag:
            student_info["usn"] = usn_tag.text.strip()

        sem_dept_sec_tag = soup.select_one('.cn-stu-data1 p')
        if sem_dept_sec_tag:
            sem_dept_sec_raw = sem_dept_sec_tag.text.strip()
            sem_match = re.search(r'SEM\s*(\d+)', sem_dept_sec_raw, re.IGNORECASE)
            if sem_match:
                student_info["semester"] = int(sem_match.group(1))
            
            sec_match = re.search(r'SEC\s*([A-Z])', sem_dept_sec_raw, re.IGNORECASE)
            if sec_match:
                student_info["section"] = sec_match.group(1)

            # Department mapping (simplified based on your JS)
            if "B.E-CS" in sem_dept_sec_raw.upper() or "COMPUTER SCIENCE" in sem_dept_sec_raw.upper():
                student_info["department"] = "Computer Science & Engineering"
            elif "B.E-IS" in sem_dept_sec_raw.upper() or "INFORMATION SCIENCE" in sem_dept_sec_raw.upper():
                student_info["department"] = "Information Science & Engineering"
            elif "B.E-EC" in sem_dept_sec_raw.upper() or "ELECTRONICS AND COMMUNICATION" in sem_dept_sec_raw.upper():
                student_info["department"] = "Electronics & Communication Engineering"
            # Add more department mappings if needed
    except Exception as e:
        error_messages.append(f"Error parsing basic student info: {str(e)}")
    
    return student_info, error_messages


def _extract_dashboard_subject_summaries(dashboard_html_content):
    soup = BeautifulSoup(dashboard_html_content, 'lxml')
    results = {}
    course_name_map = {}
    error_messages = []
    data_table_found = False

    try:
        # First, try to find the table with course codes and names
        for table_element in soup.find_all('table'):
            if data_table_found:
                break
            header_cells = table_element.select('thead tr th')
            is_correct_table = False
            if len(header_cells) >= 2:
                first_header_text = header_cells[0].text.strip().lower()
                second_header_text = header_cells[1].text.strip().lower()
                if 'course code' in first_header_text and 'course name' in second_header_text:
                    is_correct_table = True
            
            if is_correct_table:
                data_table_found = True
                for row in table_element.select('tbody tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        course_code = cells[0].text.strip()
                        course_name = cells[1].text.strip()
                        if course_code and course_name:
                            course_name_map[course_code] = course_name
        
        # Then, parse script tags for CIE and Attendance data
        for script_tag in soup.find_all('script'):
            script_content = script_tag.string
            if not script_content:
                continue

            columns_content_regex = re.compile(r'columns:\s*(\[[\s\S]*?\])\s*,?\s*(?:type|padding|radius|bindto|gauge|size)', re.IGNORECASE)
            columns_match = columns_content_regex.search(script_content)

            if columns_match and columns_match.group(1):
                array_string = columns_match.group(1)
                course_code_from_script_for_error = 'Unknown' # For error reporting
                try:
                    data_array = ast.literal_eval(array_string) 
                    
                    is_cie_script = 'bindto: "#barPadding"' in script_content and 'type: "bar"' in script_content
                    is_attendance_script = 'bindto: "#gaugeTypeMulti"' in script_content and 'type: "gauge"' in script_content

                    if is_cie_script or is_attendance_script:
                        for item in data_array:
                            if isinstance(item, list) and len(item) == 2:
                                course_code_from_script = str(item[0]).strip()
                                course_code_from_script_for_error = course_code_from_script # Update for error context
                                value = item[1]
                                if not course_code_from_script:
                                    continue
                                
                                if course_code_from_script not in results:
                                    results[course_code_from_script] = {
                                        "code": course_code_from_script,
                                        "name": course_name_map.get(course_code_from_script, course_code_from_script),
                                        "cieTotal": None,
                                        "attendancePercentage": None
                                    }
                                
                                if is_cie_script:
                                    results[course_code_from_script]["cieTotal"] = value
                                elif is_attendance_script:
                                    results[course_code_from_script]["attendancePercentage"] = value
                except (SyntaxError, ValueError) as e:
                    error_messages.append(f"Chart data parse error from script (Code: {course_code_from_script_for_error}): {str(e)}")
                    pass

        for code, name in course_name_map.items():
            if code not in results:
                results[code] = {"code": code, "name": name, "cieTotal": None, "attendancePercentage": None}
            elif results[code]["name"] == code:
                 results[code]["name"] = name
        
    except Exception as e:
        error_messages.append(f"Error parsing dashboard summaries: {str(e)}")

    return list(results.values()), error_messages


def _extract_exam_history(exam_history_html_content):
    soup = BeautifulSoup(exam_history_html_content, 'lxml')
    exam_history_data = {"semesters": [], "mostRecentCGPA": None}
    error_messages = []

    try:
        for table_div in soup.select('div.result-table'):
            caption_tag = table_div.select_one('table caption')
            if not caption_tag:
                continue
            
            caption_text = caption_tag.text.strip()
            
            sem_name_match = re.search(r'^(.*?)\s+Credits Registered', caption_text, re.IGNORECASE)
            semester_name = sem_name_match.group(1).strip() if sem_name_match else f"Semester (Unknown Name)"

            cr_match = re.search(r'Credits Registered\s*:\s*(\d+)', caption_text, re.IGNORECASE)
            ce_match = re.search(r'Credits Earned\s*:\s*(\d+)', caption_text, re.IGNORECASE)
            sgpa_match = re.search(r'SGPA\s*:\s*([\d.]+)', caption_text, re.IGNORECASE)
            cgpa_match = re.search(r'CGPA\s*:\s*(?:CGPA\s*:\s*)?([\d.]+)', caption_text, re.IGNORECASE)

            sem_result = {
                "semesterName": semester_name,
                "creditsRegistered": int(cr_match.group(1)) if cr_match else None,
                "creditsEarned": int(ce_match.group(1)) if ce_match else None,
                "sgpa": float(sgpa_match.group(1)) if sgpa_match else None,
                "cgpa": float(cgpa_match.group(1)) if cgpa_match else None,
            }
            exam_history_data["semesters"].append(sem_result)
            if sem_result["cgpa"] is not None:
                exam_history_data["mostRecentCGPA"] = sem_result["cgpa"]
    except Exception as e:
        error_messages.append(f"Error parsing exam history: {str(e)}")
        
    return exam_history_data, error_messages

# --- MAIN SCRAPING FUNCTION ---

def scrape_and_parse_college_data(usn, dob_dd, dob_mm, dob_yyyy):
    student_usn = usn.strip().upper()
    college_password = f"{dob_yyyy}-{str(dob_mm).zfill(2)}-{str(dob_dd).zfill(2)}"
    
    all_errors = []
    scraped_data_output = {
        "studentProfile": {},
        "dashboardSummaries": [],
        "examHistory": {"semesters": [], "mostRecentCGPA": None},
        "errorMessages": []
    }

    with requests.Session() as session:
        session.headers.update({'User-Agent': Config.SCRAPER_USER_AGENT})

        # --- Step 0: GET login page to extract Joomla token ---
        joomla_token_name = None
        try:
            print(f"Fetching login page to get Joomla token from: {Config.COLLEGE_LOGIN_URL}")
            # This initial GET also helps establish a session and get initial cookies if any are set.
            login_page_response = session.get(
                Config.COLLEGE_LOGIN_URL,
                verify=False, # Bypass SSL verification
                headers={ # Mimic browser headers from cURL
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-GB,en;q=0.9',
                }
            )
            login_page_response.raise_for_status()
            login_page_soup = BeautifulSoup(login_page_response.text, 'lxml')
            
            # Find the Joomla security token. It's usually a hidden input with a 32-char hex name and value "1".
            # <input type="hidden" name="abcdef1234567890abcdef1234567890" value="1">
            token_input = login_page_soup.find('input', {'type': 'hidden', 'value': '1', 'name': re.compile(r'^[a-f0-9]{32}$')})
            if token_input and token_input.get('name'):
                joomla_token_name = token_input['name']
                print(f"Found Joomla token name: {joomla_token_name}")
            else:
                # Fallback: sometimes it might be the only input with value "1" in the form
                form = login_page_soup.find('form', id='login-form') # Adjust if form ID is different
                if form:
                    token_input_alt = form.find('input', {'type': 'hidden', 'value': '1'})
                    if token_input_alt and token_input_alt.get('name') and len(token_input_alt.get('name')) > 20 : # Heuristic: token names are long
                         joomla_token_name = token_input_alt['name']
                         print(f"Found Joomla token name (fallback): {joomla_token_name}")

                if not joomla_token_name:
                    all_errors.append("Critical: Could not find Joomla token on the login page. Page structure might have changed.")
                    # For debugging, you might want to save login_page_response.text
                    scraped_data_output["errorMessages"] = all_errors
                    return scraped_data_output, False
        
        except requests.exceptions.RequestException as e:
            all_errors.append(f"Network or HTTP error fetching login page for token: {str(e)}")
            scraped_data_output["errorMessages"] = all_errors
            return scraped_data_output, False
        except Exception as e:
            all_errors.append(f"Unexpected error fetching/parsing login page for token: {str(e)}")
            scraped_data_output["errorMessages"] = all_errors
            return scraped_data_output, False

        # --- Step 1: POST to College Login URL ---
        login_payload = {
            "username": student_usn,
            "dd": str(dob_dd), # cURL has '13+' but '+' is usually for space, not part of day.
            "mm": str(dob_mm),
            "yyyy": str(dob_yyyy),
            "passwd": college_password,
            "remember": "No",
            "option": "com_user", # As per cURL (same as your old code)
            "task": "login",     # As per cURL (same as your old code)
            "return": "", # Keep it simple, relying on 302 redirect. cURL had messy value.
            # Dynamic Joomla token
            joomla_token_name: "1", 
            # g-recaptcha-response and captcha-response from cURL are ignored as per your instruction
            # "g-recaptcha-response": "YOUR_CAPTCHA_SOLUTION_IF_NEEDED",
            # "captcha-response": "" # As seen in cURL, if needed
        }
        
        login_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive', # requests handles this usually
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': Config.COLLEGE_BASE_URL, # From cURL
            'Referer': f"{Config.COLLEGE_BASE_URL}/newparents/", # From cURL, or Config.COLLEGE_LOGIN_URL
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            # sec-ch-* headers are less critical but can be added if issues persist
        }

        try:
            print(f"Attempting college login for USN: {student_usn}...")
            login_response = session.post(
                Config.COLLEGE_LOGIN_URL,
                data=login_payload,
                headers=login_headers,
                verify=False, # Bypass SSL verification
                allow_redirects=False # Handle redirects manually
            )
            # No need to call raise_for_status() here if we check status code manually
            # because a failed login might still be a 200 OK with an error message.

            # Check for login success (usually a redirect)
            if login_response.status_code not in (301, 302, 303) or 'location' not in login_response.headers:
                # Check for specific error messages in response body if not a redirect
                login_fail_msg = f"College login failed. Status: {login_response.status_code}."
                if "Invalid username or password" in login_response.text or \
                   "User Name and Password do not match" in login_response.text or \
                   "Username and password do not match" in login_response.text: # Common Joomla message
                    login_fail_msg += " Portal indicated: Invalid credentials."
                elif "Your session has expired" in login_response.text:
                    login_fail_msg += " Portal indicated: Session expired (possibly token issue)."
                else:
                    login_fail_msg += " No redirect received. Check credentials or portal status."
                    # print(f"DEBUG: Login response text: {login_response.text[:500]}") # For debugging
                all_errors.append(login_fail_msg)
                scraped_data_output["errorMessages"] = all_errors
                return scraped_data_output, False

            dashboard_url_path = login_response.headers['location']
            # Ensure the location is a full URL or join with base
            if dashboard_url_path.startswith(('http://', 'https://')):
                dashboard_url = dashboard_url_path
            else:
                dashboard_url = urljoin(Config.COLLEGE_BASE_URL, dashboard_url_path)
            
            print(f"Login successful, redirecting to dashboard: {dashboard_url}")

            # --- Step 2: GET Dashboard Page ---
            dashboard_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-GB,en;q=0.9',
                'Cache-Control': 'max-age=0',
                'Connection': 'keep-alive',
                'Referer': Config.COLLEGE_LOGIN_URL, # Referer from login page or previous redirect source
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin', # was same-origin in cURL
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            }
            print(f"Fetching dashboard for USN: {student_usn}...")
            dashboard_response = session.get(
                dashboard_url,
                headers=dashboard_headers,
                verify=False # Bypass SSL verification
            )
            dashboard_response.raise_for_status() # Now we expect 200
            dashboard_html = dashboard_response.text
            
            # Parse Dashboard
            scraped_data_output["studentProfile"], profile_errors = _extract_basic_student_info(dashboard_html)
            all_errors.extend(profile_errors)
            
            if not scraped_data_output["studentProfile"].get("usn"):
                all_errors.append("Failed to extract student USN from dashboard. Login might have been incomplete or page structure changed.")
                # print(f"DEBUG: Dashboard HTML (first 500 chars): {dashboard_html[:500]}")
                scraped_data_output["errorMessages"] = all_errors
                return scraped_data_output, False 

            if scraped_data_output["studentProfile"]["usn"].upper() != student_usn:
                all_errors.append(f"USN mismatch! Login USN: {student_usn}, Dashboard USN: {scraped_data_output['studentProfile']['usn']}.")
                scraped_data_output["errorMessages"] = all_errors
                return scraped_data_output, False 

            scraped_data_output["dashboardSummaries"], summary_errors = _extract_dashboard_subject_summaries(dashboard_html)
            all_errors.extend(summary_errors)
            print("Dashboard data extracted.")

            # --- Step 3: GET Exam History Page ---
            exam_history_full_url = urljoin(Config.COLLEGE_BASE_URL, Config.COLLEGE_EXAM_HISTORY_PATH)
            
            exam_history_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-GB,en;q=0.9',
                'Connection': 'keep-alive',
                'Referer': dashboard_url, # Referer is the dashboard URL
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            }
            print(f"Fetching exam history for USN: {student_usn} from {exam_history_full_url}...")
            exam_history_response = session.get(
                exam_history_full_url,
                headers=exam_history_headers,
                verify=False # Bypass SSL verification
            )
            
            if exam_history_response.status_code == 200:
                exam_history_html = exam_history_response.text
                scraped_data_output["examHistory"], eh_errors = _extract_exam_history(exam_history_html)
                all_errors.extend(eh_errors)
                print("Exam history data extracted.")
            else:
                all_errors.append(f"Failed to fetch exam history. Status: {exam_history_response.status_code}. URL: {exam_history_full_url}")
                print(f"Warning: Exam history fetch failed with status {exam_history_response.status_code}")

        except requests.exceptions.RequestException as e:
            all_errors.append(f"Network or HTTP error during scraping: {str(e)}")
            print(f"Scraping Error: {str(e)}")
            # The SSL error will now be caught here if verify=False is missed or if other network issues occur
        except Exception as e:
            all_errors.append(f"An unexpected error occurred during scraping/parsing: {str(e)}")
            import traceback
            traceback.print_exc() # For server logs
        
        scraped_data_output["errorMessages"].extend(all_errors) # Use extend if all_errors can have multiple items
        
        if not scraped_data_output["studentProfile"].get("usn") and not any("Critical" in err for err in scraped_data_output["errorMessages"]):
             # Only add this if not already failed due to token or other critical step
            scraped_data_output["errorMessages"].append("Failed to retrieve valid student data from the portal. The portal might be down or its structure changed.")
            return scraped_data_output, False

        # Success if we have a USN and no critical errors earlier
        is_success = bool(scraped_data_output["studentProfile"].get("usn"))
        return scraped_data_output, is_success
