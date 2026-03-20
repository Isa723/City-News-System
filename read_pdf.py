import pypdf
import sys

def extract_text(pdf_path):
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    pdf_path = r"c:\Users\PISHTAAZ SOFTWARE\Desktop\Project\Yazlab 2- Proje 1.pdf"
    content = extract_text(pdf_path)
    with open("pdf_content.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("Content written to pdf_content.txt")
