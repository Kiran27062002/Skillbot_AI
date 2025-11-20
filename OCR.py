!pip install paddlepaddle -i https://pypi.tuna.tsinghua.edu.cn/simple
!pip install paddleocr opencv-python pandas

import cv2
import numpy as np
import pandas as pd
from paddleocr import PaddleOCR
import re

# ------------------------------------------------------------
# 1) Load & preprocess image to fix blur/noise/lighting
# ------------------------------------------------------------
def preprocess_image(path):
    img = cv2.imread(path)

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Remove noise
    gray = cv2.bilateralFilter(gray, 9, 75, 75)

    # Adaptive threshold (works for colored/noisy marksheets)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31, 10
    )

    return img, thresh

# ------------------------------------------------------------
# 2) OCR detection using PaddleOCR (much more accurate)
# ------------------------------------------------------------
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def extract_text(img):
    result = ocr.ocr(img)
    text_data = []
    if result and result[0]: # Check if result is not empty and has detections for the first image
        # PaddleOCR can return a list of dictionaries with results per image, or a list of detection tuples.
        # The 'Warning: Unrecognized item format' suggests result[0] is a dictionary.
        if isinstance(result[0], dict) and 'rec_texts' in result[0]:
            # If result[0] is a dictionary and contains 'rec_texts' (a list of text strings)
            text_data = result[0]['rec_texts']
        elif isinstance(result[0], list):
            # Fallback for older PaddleOCR versions or different output formats
            # where result[0] is directly a list of detection items
            for item in result[0]:
                # Handle potential variations in PaddleOCR output format
                if isinstance(item, (list, tuple)) and len(item) == 3: # Format: (bbox, text_str, confidence_float)
                    box_coords, text_str, confidence = item
                    text_data.append(text_str)
                elif isinstance(item, (list, tuple)) and len(item) == 2: # Format: (bbox, (text_str, confidence_float))
                    box_coords, text_info = item
                    if isinstance(text_info, (list, tuple)) and len(text_info) == 2:
                        text_data.append(text_info[0])
                    else:
                        # Fallback if text_info is not a (text, confidence) tuple
                        text_data.append(str(text_info))
                else:
                    print(f"Warning: Unrecognized item format from PaddleOCR: {item}")
        else:
            print(f"Warning: Unrecognized top-level item format from PaddleOCR: {result[0]}")
    return text_data

# ------------------------------------------------------------
# Helper for robust number extraction
# ------------------------------------------------------------
def extract_number_robust(s):
    s = str(s).strip()
    # Find the first sequence of digits, optionally with a decimal point
    match = re.search(r'\d+\.?\d*', s)
    if match:
        try:
            return float(match.group(0)) if '.' in match.group(0) else int(match.group(0))
        except ValueError:
            return None
    return None

# ------------------------------------------------------------
# 3) Convert extracted text into "Subject | Max | Obtained"
# ------------------------------------------------------------
def parse_marks(text_list):
    subjects = []
    maximum = []
    obtained = []

    # Find the starting point of the actual marks table
    start_parsing_from_index = -1
    for idx, text in enumerate(text_list):
        if 'SUBJECT - WISE STATEMENT OF MARKS' in text.upper():
            start_parsing_from_index = idx
            break

    if start_parsing_from_index != -1:
        i = start_parsing_from_index + 1 # Start from the item after the header
    else:
        i = 0 # Fallback to start from beginning if header not found

    # Keywords to ignore when identifying subjects or as noise
    forbidden_subject_keywords = {'SR.NO.', 'SR.NO', 'SUBJECTS', 'MARKS', 'MAXIMUM', 'OBTAINED', 'ANNUAL', 'NO CERTIFICATE'}
    # Single-letter/short strings often misidentified by OCR or irrelevant from the provided raw OCR
    noise_words = {'L', 'E', 'a', 'b', 'c', 'd', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '1', '2', '3', '4', '5', '6', '7', '8', '9', '100', 'FIRST'}

    while i < len(text_list):
        t1_raw = text_list[i].strip()
        t1_upper = t1_raw.upper()

        # Skip empty strings or known noise words/forbidden keywords
        if not t1_raw or t1_upper in forbidden_subject_keywords or t1_raw.lower() in [nw.lower() for nw in noise_words] or len(t1_raw) < 2 and not t1_upper == 'TOTAL':
            i += 1
            continue

        # Check if t1 is a plausible subject
        is_plausible_subject = False
        # A subject should contain at least two alphabetic characters and not be a forbidden/noise word
        if re.search(r'[a-zA-Z]{2,}', t1_raw) and \
           t1_upper not in forbidden_subject_keywords and \
           t1_raw.lower() not in [nw.lower() for nw in noise_words]:
            is_plausible_subject = True

        # Allow specific subjects regardless of strict alpha check or length if they are explicitly known
        specific_subjects_keywords = ["URDU", "ENGLISH", "ISLAMIYAT", "PAKISTAN STUDIES", "MATHEMATICS", "PHYSICS", "CHEMISTRY", "BIOLOGY", "TOTAL"]
        if any(ss in t1_upper for ss in specific_subjects_keywords):
             is_plausible_subject = True

        if is_plausible_subject:
            subject_name = t1_raw

            # Special handling for 'TOTAL' as its numbers are sometimes out of immediate sequence
            if t1_upper == 'TOTAL':
                potential_total_nums = []
                scan_idx = i + 1
                while scan_idx < len(text_list) and len(potential_total_nums) < 3: # Scan up to 3 numbers for safety
                    num = extract_number_robust(text_list[scan_idx])
                    if num is not None:
                        potential_total_nums.append((num, scan_idx)) # Store number and its original index
                    scan_idx += 1

                if len(potential_total_nums) >= 2:
                    # For 'TOTAL', we want the largest two numbers (Total Max and Total Obtained)
                    # Example: 'TOTAL', '49', '850', '426'. We want 850 and 426.
                    # Sort by value to easily pick the max and obtained
                    potential_total_nums.sort(key=lambda x: x[0], reverse=True)

                    subjects.append(subject_name)
                    maximum.append(int(potential_total_nums[0][0])) # Largest number
                    obtained.append(int(potential_total_nums[1][0])) # Second largest number

                    # Advance 'i' past the highest index of the numbers used
                    max_k_used = max(item[1] for item in potential_total_nums[:2])
                    i = max_k_used + 1
                else:
                    i += 1 # Not enough numbers for total, skip
                continue

            # For regular subjects, look for two numbers immediately after the subject name
            found_nums = []
            last_num_idx = i
            scan_idx = i + 1
            num_search_count = 0 # To limit how far we scan for numbers
            while scan_idx < len(text_list) and len(found_nums) < 2 and num_search_count < 4: # Scan up to 4 items ahead
                num = extract_number_robust(text_list[scan_idx])
                if num is not None and num >= 0:
                    # Heuristic to skip potential serial numbers (small number after Max and before another mark)
                    if len(found_nums) == 1 and num < 10 and (scan_idx + 1 < len(text_list)) and extract_number_robust(text_list[scan_idx+1]) is not None:
                        print(f"Skipping potential serial number: {num} for subject {subject_name}") # For debugging
                        # Don't append, just advance scan_idx
                    else:
                        found_nums.append(num)
                    last_num_idx = scan_idx
                scan_idx += 1
                num_search_count += 1

            if len(found_nums) >= 2: # Ensure at least two numbers are found
                subjects.append(subject_name)
                maximum.append(int(found_nums[0]))
                obtained.append(int(found_nums[1]))
                i = last_num_idx + 1 # Advance index past the last number used
            else:
                i += 1 # Not enough numbers for subject marks, advance one position
        else:
            i += 1 # Not a subject candidate, move to next item.

    df = pd.DataFrame({
        "Subject": subjects,
        "Maximum": maximum,
        "Obtained": obtained
    })

    return df

# ------------------------------------------------------------
# 4) MAIN FUNCTION
# ------------------------------------------------------------
def extract_marks_from_marksheet(image_path, output_csv=None):
    img, thresh = preprocess_image(image_path)

    print("🔍 Running OCR...")
    text_list = extract_text(img)

    print("📄 Raw OCR Text:")
    print(text_list)

    df = parse_marks(text_list)

    print("\n📊 Extracted Marks:")
    print(df)

    if output_csv:
        df.to_csv(output_csv, index=False)
        print(f"\n💾 Marks saved to {output_csv}")

    return df


# ------------------------------------------------------------
# 5) Run on your marksheet
# ------------------------------------------------------------
extract_marks_from_marksheet("/content/IMG_20210617_120733.jpg", output_csv='marksheet_marks.csv')