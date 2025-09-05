import cv2
import pytesseract
import os
import numpy as np
from tkinter import *
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
from datetime import datetime
from fpdf import FPDF
import tempfile

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Global variables
extracted_text = ""
current_image = None

def preprocess_image(img, mode='printed'):
    """Enhanced image preprocessing for different text types"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if mode == 'handwritten':
        # Special processing for handwritten text
        gray = cv2.medianBlur(gray, 3)
        gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 11, 2)
    else:
        # Processing for printed text
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # Optional: dilation and erosion to remove noise
    kernel = np.ones((1, 1), np.uint8)
    gray = cv2.dilate(gray, kernel, iterations=1)
    gray = cv2.erode(gray, kernel, iterations=1)
    
    return gray

def extract_text_from_image(img, text_type='auto'):
    """Extract text with automatic detection or specified type"""
    global current_image
    
    # Save the current image for later use
    current_image = img.copy()
    
    if text_type == 'auto':
        # First try printed text mode
        processed = preprocess_image(img, 'printed')
        text = pytesseract.image_to_string(processed)
        
        # If little text detected, try handwritten mode
        if len(text.strip()) < 10:
            processed = preprocess_image(img, 'handwritten')
            text = pytesseract.image_to_string(processed, config='--psm 6')
    else:
        processed = preprocess_image(img, text_type)
        config = '--psm 6' if text_type == 'handwritten' else ''
        text = pytesseract.image_to_string(processed, config=config)
    
    return text

def upload_image():
    global extracted_text
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp")])
    if file_path:
        image = cv2.imread(file_path)
        if image is None:
            messagebox.showerror("Error", "Could not read the image file")
            return
        
        # Show processing options
        choice = messagebox.askquestion("Processing Mode", 
                                      "Is this handwritten text?\n(Yes for Handwritten, No for Printed)")
        text_type = 'handwritten' if choice == 'yes' else 'printed'
        
        extracted_text = extract_text_from_image(image, text_type)
        display_text(extracted_text)
        
        # Show the processed image
        show_processed_image(image, text_type)

def live_scan():
    global extracted_text
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        messagebox.showerror("Error", "Could not open webcam")
        return

    messagebox.showinfo("Live Scan", "Press 's' to scan, 'h' for handwritten mode, 'p' for printed mode, 'q' to quit.")
    
    text_type = 'auto'  # Default to auto detection
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Display instructions on the frame
        cv2.putText(frame, "Press 's' to scan", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "'h': handwritten, 'p': printed", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Current mode: {text_type}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, "'q' to quit", (10, 120), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        cv2.imshow("Live Scan", frame)
        key = cv2.waitKey(1)
        
        if key == ord('s'):
            extracted_text = extract_text_from_image(frame, text_type)
            display_text(extracted_text)
            show_processed_image(frame, text_type)
            break
        elif key == ord('h'):
            text_type = 'handwritten'
        elif key == ord('p'):
            text_type = 'printed'
        elif key == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

def show_processed_image(img, text_type):
    """Show the processed image in a new window"""
    processed = preprocess_image(img, text_type)
    processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
    
    # Resize for display if too large
    height, width = processed_rgb.shape[:2]
    max_height = 600
    if height > max_height:
        ratio = max_height / height
        processed_rgb = cv2.resize(processed_rgb, (int(width * ratio), max_height))
    
    cv2.imshow("Processed Image (What OCR sees)", processed_rgb)
    cv2.waitKey(1)

def display_text(text):
    text_area.config(state=NORMAL)
    text_area.delete(1.0, END)
    text_area.insert(END, text)
    text_area.config(state=DISABLED)

def save_text_to_file():
    global extracted_text
    if not extracted_text.strip():
        messagebox.showwarning("⚠️ Warning", "No text to save!")
        return
    
    # Ask for format
    format_choice = messagebox.askquestion("Save Format", 
                                         "Save as PDF?\n(No for TXT format)")
    
    filename = f"extracted_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if format_choice == 'yes':
        # Save as PDF
        filename += ".pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Split text into lines and add to PDF
        for line in extracted_text.split('\n'):
            pdf.cell(200, 10, txt=line, ln=1)
        
        pdf.output(filename)
    else:
        # Save as TXT
        filename += ".txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(extracted_text)
    
    messagebox.showinfo("✅ Saved", f"Text saved to:\n{filename}")

def save_as_pdf_with_image():
    """Save both text and image as PDF"""
    global extracted_text, current_image
    
    if not extracted_text.strip() or current_image is None:
        messagebox.showwarning("⚠️ Warning", "No text or image to save!")
        return
    
    filename = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Save image to temp file
    temp_img_path = os.path.join(tempfile.gettempdir(), "temp_ocr_img.jpg")
    cv2.imwrite(temp_img_path, current_image)
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Add image to PDF (scaled to fit)
    pdf.image(temp_img_path, x=10, y=10, w=180)
    
    # Add text below image
    pdf.set_y(100)  # Position below image
    for line in extracted_text.split('\n'):
        pdf.cell(200, 10, txt=line, ln=1)
    
    pdf.output(filename)
    
    # Clean up temp file
    os.remove(temp_img_path)
    
    messagebox.showinfo("✅ Saved", f"Document saved to:\n{filename}")

# Create main window
root = Tk()
root.title("📄 Advanced Document OCR Scanner")
root.geometry("900x700")
root.config(bg="#e8f0f2")

# Header
header = Frame(root, bg="#2c3e50", height=80)
header.pack(fill=X)

title = Label(header, text="📄 Advanced Document OCR Scanner", font=("Helvetica", 20, "bold"),
              bg="#2c3e50", fg="white")
title.pack(pady=20)

# Button frame
button_frame = Frame(root, bg="#e8f0f2")
button_frame.pack(pady=20)

style_btn = {"font": ("Arial", 12, "bold"), "width": 20, "height": 2}

upload_btn = Button(button_frame, text="📂 Upload Image", bg="#3498db", fg="white", **style_btn, command=upload_image)
upload_btn.grid(row=0, column=0, padx=10, pady=5)

live_btn = Button(button_frame, text="📷 Live Camera Scan", bg="#27ae60", fg="white", **style_btn, command=live_scan)
live_btn.grid(row=0, column=1, padx=10, pady=5)

save_btn = Button(button_frame, text="💾 Save as Text", bg="#e67e22", fg="white", **style_btn, command=save_text_to_file)
save_btn.grid(row=1, column=0, padx=10, pady=5)

pdf_btn = Button(button_frame, text="🖨️ Save as PDF with Image", bg="#9b59b6", fg="white", 
                **style_btn, command=save_as_pdf_with_image)
pdf_btn.grid(row=1, column=1, padx=10, pady=5)

# Text frame
text_frame = Frame(root, bg="#ffffff", padx=15, pady=15, bd=2, relief=GROOVE)
text_frame.pack(fill=BOTH, expand=True, padx=30, pady=(0, 20))

Label(text_frame, text="📝 Extracted Text", font=("Arial", 14, "bold"), bg="#ffffff", anchor="w").pack(anchor="w")

text_area = scrolledtext.ScrolledText(text_frame, wrap=WORD, font=("Courier New", 11), state=DISABLED,
                                    bg="#fefefe", relief=SOLID, bd=1)
text_area.pack(fill=BOTH, expand=True, pady=10)

# Run the application
root.mainloop()