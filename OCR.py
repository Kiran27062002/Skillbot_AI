
# Install Required Libraries

!pip install easyocr opencv-python pandas matplotlib 


# Import Libraries

import cv2
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import easyocr


#  Load Image
img = cv2.imread("/content/IMG-20250707-WA0018.jpg")

#  Convert to Grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# Binarize (Black Background, White Text)
thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)[1]
plt.imshow(thresh, cmap='gray')
plt.axis("off")
plt.show()

#  Find Contours (Identify Table Area)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=cv2.contourArea, reverse=True)

#  Extract Largest Rectangle (Marks Table)
x, y, w, h = cv2.boundingRect(contours[0])
table_img = img[y:y+h, x:x+w]
plt.imshow(cv2.cvtColor(table_img, cv2.COLOR_BGR2RGB))
plt.axis("off")
plt.show()

# Read Text from Table using EasyOCR
reader = easyocr.Reader(['en'])
results = reader.readtext(table_img)

# Print all detected text chunks
for bbox, text, prob in results:
    print(text)

#  Organize Extracted Text into Lines
data = [(bbox[0][1], text) for bbox, text, _ in results]
data.sort(key=lambda x: x[0])
lines = []
current_line = []
prev_y = None
threshold = 10   # Adjust if spacing is too much

for y, text in data:
    if prev_y is None or abs(y - prev_y) < threshold:
        current_line.append(text)
    else:
        lines.append(" ".join(current_line))
        current_line = [text]
    prev_y = y
lines.append(" ".join(current_line))


#  Extract Subject, Maximum Marks, Obtained Marks
subjects, maximum, obtained = [], [], []

for line in lines:
    parts = line.split()
    if len(parts) >= 3:
        subjects.append(" ".join(parts[:-2]))
        maximum.append(parts[-2])
        obtained.append(parts[-1])


#  Create DataFrame
df = pd.DataFrame({
    "Subject": subjects,
    "Maximum": maximum,
    "Obtained": obtained
})

print(df)

# Save as CSV

df.to_csv("marks_only.csv", index=False)


# Download CSV (Colab)
from google.colab import files
files.download("marks_only.csv")