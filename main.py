import cv2
import pytesseract
import numpy as np
from tkinter import *
from tkinter import filedialog, messagebox, scrolledtext
from fpdf import FPDF, enums  # यहाँ बदलाव किया गया है
from datetime import datetime
import os
import tempfile

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Global variablespip 
extracted_text = ""
current_image = None

def enhance_handwriting_image(img):
    """Special preprocessing for handwritten text"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.8, beta=50)
    gray = cv2.medianBlur(gray, 3)
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY_INV, 31, 10)
    kernel = np.ones((2,2), np.uint8)
    gray = cv2.dilate(gray, kernel, iterations=1)
    return gray

def extract_text(image, is_handwritten=False):
    """Extract text from image"""
    global extracted_text, current_image
    current_image = image.copy()
    if is_handwritten:
        processed = enhance_handwriting_image(image)
        config = r'--oem 3 --psm 6 -l eng+script/Devanagari'
    else:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processed = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        config = r'--oem 3 --psm 3'
    
    extracted_text = pytesseract.image_to_string(processed, config=config)
    return extracted_text

def upload_image():
    global extracted_text  
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
    if file_path:
        img = cv2.imread(file_path)
        if img is None:
            messagebox.showerror("Error", "Could not read the image file")
            return
        
        is_handwritten = messagebox.askyesno("Text Type", "Is this handwritten text?")
        text = extract_text(img, is_handwritten)
        display_text(text)

def live_scan():
    global extracted_text  
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Could not open webcam")
        return

    messagebox.showinfo("Live Scan", "Press 'S' to scan\n'H' for Handwritten mode\n'P' for Printed mode\n'Q' to quit")
    
    mode = "Printed"
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Display instructions
        cv2.putText(frame, f"Mode: {mode}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        cv2.putText(frame, "Press 'S' to Scan", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        cv2.putText(frame, "'Q' to Quit", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
        
        cv2.imshow("Live Handwriting Scanner", frame)
        key = cv2.waitKey(1)
        
        if key == ord('s'):
            text = extract_text(frame, mode=="Handwritten")
            display_text(text)
            break
        elif key == ord('h'):
            mode = "Handwritten"
        elif key == ord('p'):
            mode = "Printed"
        elif key == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

def display_text(text):
    text_area.config(state=NORMAL)
    text_area.delete(1.0, END)
    text_area.insert(END, text)
    text_area.config(state=DISABLED)

def save_text_pdf():
    global extracted_text
    if not extracted_text.strip():
        messagebox.showwarning("Warning", "No text to save!")
        return
    
    filename = f"extracted_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Convert text to latin-1 compatible characters
        text = extracted_text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=text)
        pdf.output(filename)
        
        messagebox.showinfo("Success", f"PDF saved as:\n{filename}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save PDF: {str(e)}")

def save_image_pdf():
    global current_image, extracted_text
    if current_image is None:
        messagebox.showwarning("Warning", "No document to save!")
        return
    
    filename = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Save temp image
        temp_img = os.path.join(tempfile.gettempdir(), "temp_doc.jpg")
        cv2.imwrite(temp_img, current_image)
        
        # Add image to PDF
        pdf.image(temp_img, x=10, y=10, w=180)
        
        # Add extracted text below image if available
        if extracted_text.strip():
            pdf.set_y(100)
            pdf.set_font("Arial", size=12)
            # Convert text to latin-1 compatible characters
            text = extracted_text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, txt=text)
        
        pdf.output(filename)
        os.remove(temp_img)
        
        messagebox.showinfo("Success", f"Document saved as:\n{filename}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save PDF: {str(e)}")
        if os.path.exists(temp_img):
            os.remove(temp_img)

def save_as_text():
    global extracted_text  
    if not extracted_text.strip():
        messagebox.showwarning("Warning", "No text to save!")
        return
    
    filename = f"extracted_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(extracted_text)
    messagebox.showinfo("Success", f"Text saved as:\n{filename}")

def edit_text():
    text_area.config(state=NORMAL)
    messagebox.showinfo("Edit Mode", "You can now edit the extracted text")
    root.focus_set()

# Create main window
root = Tk()
root.title("Advanced Document Scanner")
root.geometry("1000x800")

# UI Components
header = Frame(root, bg="#2c3e50", height=90)
header.pack(fill=X)

title = Label(header, text="✍️ Advanced Document Scanner", 
             font=("Helvetica", 20, "bold"), bg="#2c3e50", fg="white")
title.pack(pady=20)

# Buttons
btn_frame = Frame(root)
btn_frame.pack(pady=20)

btn_style = {
    "font": ("Arial", 12, "bold"),
    "width": 20,
    "height": 2,
    "bd": 2
}

upload_btn = Button(btn_frame, text="📂 Upload Image", bg="#3498db", fg="white", 
                   command=upload_image, **btn_style)
upload_btn.grid(row=0, column=0, padx=5, pady=5)

live_btn = Button(btn_frame, text="📷 Live Scan", bg="#27ae60", fg="white", 
                 command=live_scan, **btn_style)
live_btn.grid(row=0, column=1, padx=5, pady=5)

save_pdf_btn = Button(btn_frame, text="💾 Save Text PDF", bg="#e67e22", fg="white", 
                     command=save_text_pdf, **btn_style)
save_pdf_btn.grid(row=1, column=0, padx=5, pady=5)

save_img_btn = Button(btn_frame, text="🖨️ Save Image PDF", bg="#9b59b6", fg="white", 
                     command=save_image_pdf, **btn_style)
save_img_btn.grid(row=1, column=1, padx=5, pady=5)

save_txt_btn = Button(btn_frame, text="📝 Save as Text", bg="#2ecc71", fg="white", 
                     command=save_as_text, **btn_style)
save_txt_btn.grid(row=2, column=0, padx=5, pady=5)

edit_btn = Button(btn_frame, text="✏️ Edit Text", bg="#f39c12", fg="white", 
                 command=edit_text, **btn_style)
edit_btn.grid(row=2, column=1, padx=5, pady=5)

# Text display
text_frame = Frame(root, bd=2, relief=GROOVE)
text_frame.pack(fill=BOTH, expand=True, padx=30, pady=20)

Label(text_frame, text="Extracted Text (Editable):", font=("Arial", 14, "bold")).pack(anchor="w")

text_area = scrolledtext.ScrolledText(text_frame, wrap=WORD, font=("Arial", 12), 
                                    height=20, state=DISABLED)
text_area.pack(fill=BOTH, expand=True)

root.mainloop()