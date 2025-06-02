# app/services/college_portal_scraper.py
import requests
from bs4 import BeautifulSoup
import re
import json # For parsing script data if it's clean JSON
import ast # For safely evaluating Python-like string literals
from urllib.parse import urljoin
from app.config import Config # Import Config to access URLs

# --- PARSING HELPER FUNCTIONS (Python equivalents) ---

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

            # Regex to find 'columns: [...]' array-like structures
            columns_content_regex = re.compile(r'columns:\s*(\[[\s\S]*?\])\s*,?\s*(?:type|padding|radius|bindto|gauge|size)', re.IGNORECASE)
            columns_match = columns_content_regex.search(script_content)

            if columns_match and columns_match.group(1):
                array_string = columns_match.group(1)
                try:
                    # Attempt to parse as JSON first (might fail if not strict JSON)
                    # More robustly, use ast.literal_eval for Python-like literals
                    # This part is tricky as JS array syntax can differ slightly
                    # For `new Function('return ' + arrayString)()` in JS, ast.literal_eval is a close Python equivalent
                    # Assuming the data is like [['CODE1', val], ['CODE2', val]]
                    data_array = ast.literal_eval(array_string) # Be cautious with eval if source is untrusted
                                                              # but here it's from a specific script pattern.
                                                              # For more complex JS objects, a JS interpreter might be needed (heavy)
                    
                    is_cie_script = 'bindto: "#barPadding"' in script_content and 'type: "bar"' in script_content
                    is_attendance_script = 'bindto: "#gaugeTypeMulti"' in script_content and 'type: "gauge"' in script_content

                    if is_cie_script or is_attendance_script:
                        for item in data_array:
                            if isinstance(item, list) and len(item) == 2:
                                course_code_from_script = str(item[0]).strip()
                                value = item[1]
                                if not course_code_from_script:
                                    continue
                                
                                if course_code_from_script not in results:
                                    results[course_code_from_script] = {
                                        "code": course_code_from_script,
                                        "name": course_name_map.get(course_code_from_script, course_code_from_script), # Use mapped name if available
                                        "cieTotal": None,
                                        "attendancePercentage": None
                                    }
                                
                                if is_cie_script:
                                    results[course_code_from_script]["cieTotal"] = value
                                elif is_attendance_script:
                                    results[course_code_from_script]["attendancePercentage"] = value
                except (SyntaxError, ValueError) as e:
                    error_messages.append(f"Chart data parse error from script (Code: {course_code_from_script if 'course_code_from_script' in locals() else 'Unknown'}): {str(e)}")
                    # Fallback or log this error
                    pass # Continue trying other scripts or methods

        # Ensure all courses from the map are included, even if no script data found
        for code, name in course_name_map.items():
            if code not in results:
                results[code] = {"code": code, "name": name, "cieTotal": None, "attendancePercentage": None}
            elif results[code]["name"] == code: # If script only had code, update with name from table
                 results[code]["name"] = name
        
        # Fallback for attendance if not found in scripts (less reliable than JS version's specific selector)
        # This part of your JS selector `table[caption="..."]` is very specific.
        # Replicating it precisely needs careful inspection of the HTML source if scripts fail.
        # For now, primary extraction is from scripts.

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
            # Handle potential "CGPA : CGPA : X.XX" or "CGPA : X.XX"
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


def scrape_and_parse_college_data(usn, dob_dd, dob_mm, dob_yyyy):
    """
    Main function to login to college portal, scrape dashboard and exam history,
    and parse the data.
    Returns a dictionary with structured data and any error messages.
    """
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

        # Step 1: POST to College Login URL
        login_payload = {
            "username": student_usn,
            "dd": str(dob_dd),
            "mm": str(dob_mm),
            "yyyy": str(dob_yyyy),
            "passwd": college_password,
            "remember": "No",
            "option": "com_user",
            "task": "login",
            "return": "",
            Config.JOOMLA_TOKEN_NAME: Config.JOOMLA_TOKEN_VALUE,
        }
        
        try:
            print(f"Attempting college login for USN: {student_usn}...")
            login_response = session.post(
                Config.COLLEGE_LOGIN_URL,
                data=login_payload,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f"{Config.COLLEGE_BASE_URL}/newparents/",
                    'Origin': Config.COLLEGE_BASE_URL,
                },
                allow_redirects=False # Handle redirects manually to get dashboard URL
            )
            login_response.raise_for_status() # Check for 4xx/5xx errors immediately

            # Successful login usually results in a 302 or 303 redirect
            if login_response.status_code not in (302, 303) or 'location' not in login_response.headers:
                all_errors.append(f"College login failed. Status: {login_response.status_code}. Expected redirect.")
                # You might want to inspect login_response.text here for error messages from the portal
                if "Invalid username or password" in login_response.text or "User Name and Password do not match" in login_response.text :
                     all_errors.append("Portal indicated: Invalid username or password.")
                scraped_data_output["errorMessages"] = all_errors
                return scraped_data_output, False # Indicate failure

            dashboard_url = urljoin(Config.COLLEGE_BASE_URL, login_response.headers['location'])
            print(f"Login successful, redirecting to dashboard: {dashboard_url}")

            # Step 2: GET Dashboard Page
            print(f"Fetching dashboard for USN: {student_usn}...")
            dashboard_response = session.get(
                dashboard_url,
                headers={'Referer': Config.COLLEGE_LOGIN_URL}
            )
            dashboard_response.raise_for_status()
            dashboard_html = dashboard_response.text
            
            # Parse Dashboard
            scraped_data_output["studentProfile"], profile_errors = _extract_basic_student_info(dashboard_html)
            all_errors.extend(profile_errors)
            
            # USN Check (important)
            if scraped_data_output["studentProfile"].get("usn") and \
               scraped_data_output["studentProfile"]["usn"].upper() != student_usn:
                all_errors.append(f"USN mismatch! Login USN: {student_usn}, Dashboard USN: {scraped_data_output['studentProfile']['usn']}.")
                # This is a critical error, might indicate scraping wrong page or login issue
                scraped_data_output["errorMessages"] = all_errors
                return scraped_data_output, False 

            scraped_data_output["dashboardSummaries"], summary_errors = _extract_dashboard_subject_summaries(dashboard_html)
            all_errors.extend(summary_errors)
            print("Dashboard data extracted.")

            # Step 3: GET Exam History Page
            exam_history_url = urljoin(Config.COLLEGE_BASE_URL, Config.COLLEGE_EXAM_HISTORY_PATH)
            print(f"Fetching exam history for USN: {student_usn} from {exam_history_url}...")
            exam_history_response = session.get(
                exam_history_url,
                headers={'Referer': dashboard_url} # Referer is the dashboard URL
            )
            # Exam history might not exist for all students (e.g., first sem) or might return non-200 if issues
            if exam_history_response.status_code == 200:
                exam_history_html = exam_history_response.text
                scraped_data_output["examHistory"], eh_errors = _extract_exam_history(exam_history_html)
                all_errors.extend(eh_errors)
                print("Exam history data extracted.")
            else:
                all_errors.append(f"Failed to fetch exam history. Status: {exam_history_response.status_code}. URL: {exam_history_url}")
                print(f"Warning: Exam history fetch failed with status {exam_history_response.status_code}")

        except requests.exceptions.RequestException as e:
            all_errors.append(f"Network or HTTP error during scraping: {str(e)}")
            print(f"Scraping Error: {str(e)}")
            scraped_data_output["errorMessages"] = all_errors
            return scraped_data_output, False # Indicate failure
        except Exception as e:
            all_errors.append(f"An unexpected error occurred during scraping/parsing: {str(e)}")
            import traceback
            traceback.print_exc() # For server logs
            scraped_data_output["errorMessages"] = all_errors
            return scraped_data_output, False # Indicate failure

        scraped_data_output["errorMessages"] = all_errors
        
        # If studentProfile.usn is still None after trying, it's a major parsing/login issue
        if not scraped_data_output["studentProfile"].get("usn"):
            all_errors.append("Failed to extract student USN from dashboard. Login might have been incomplete or page structure changed.")
            return scraped_data_output, False

        return scraped_data_output, True # Indicate success