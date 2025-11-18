import os
import io
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from pdf2image import convert_from_path
from PIL import Image, ImageChops

# ---------------- CONFIGURACIÓN ----------------
SHEET_ID = "1-9vXBU43YjU6LMdivpVwL2ysLHANShHzrCW6MmmGvoI"
OUTPUT_FOLDER = "output_images"
CREDENTIALS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "pu-tracker",
    "historical_data",
    "prun-profit-42c5889f620d.json"
)
print("Looking for credentials at:", CREDENTIALS_PATH)
DPI = 300  # resolución de las imágenes

# GIDs and tab names
DATA_AI1_GID = "0"
REPORT_AI1_GID = "1259860972"
DATA_AI1_TAB = "DATA AI1"
REPORT_AI1_TAB = "Report AI1"
DATA_AI1_COL = "Y"
REPORT_AI1_COL = "BC"

# ---------------- AUTENTICACIÓN ----------------
creds = service_account.Credentials.from_service_account_file(
    CREDENTIALS_PATH,
    scopes=["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets.readonly"]
)
service = build("drive", "v3", credentials=creds)
sheets_service = build("sheets", "v4", credentials=creds)

# ---------------- CREAR CARPETA DE SALIDA ----------------
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# ---------------- DETECTAR ÚLTIMA FILA CON DATOS ----------------
def get_last_row_with_data(tab_name, last_col, sheet_id):
    # Get values for the whole range (A:LASTCOL)
    range_notation = f"'{tab_name}'!A:{last_col}"
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_notation,
        majorDimension="ROWS"
    ).execute()
    values = result.get("values", [])
    # Find the last row that has any non-empty cell
    last_row = 0
    for idx, row in enumerate(values, 1):
        if any(cell.strip() for cell in row if isinstance(cell, str)) or any(cell for cell in row if not isinstance(cell, str)):
            last_row = idx
    return last_row

# ---------------- EXPORTAR GOOGLE SHEET A PDF (TODO EL DOCUMENTO) ----------------
def export_sheet_to_pdf(sheet_id, output_path):
    request = service.files().export_media(
        fileId=sheet_id,
        mimeType="application/pdf"
    )
    fh = io.FileIO(output_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Descargando PDF: {int(status.progress() * 100)}%")
    fh.close()
    print(f"PDF guardado en: {output_path}")

# ---------------- EXPORTAR SOLO UNA TAB COMO PDF (AJUSTADO) ----------------
def export_tab_to_pdf(sheet_id, gid, output_path, creds, range_str=None):
    export_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/export"
        f"?format=pdf&gid={gid}&size=A4&portrait=true&fitw=true"
        f"&sheetnames=false&printtitle=false&pagenumbers=false"
        f"&gridlines=false&fzr=false"
    )
    if range_str:
        export_url += f"&range={range_str}"

    headers = {}
    authed_session = creds.with_scopes(['https://www.googleapis.com/auth/drive.readonly'])
    import google.auth.transport.requests
    request_auth = google.auth.transport.requests.Request()
    authed_session.refresh(request_auth)
    headers['Authorization'] = f"Bearer {authed_session.token}"

    response = requests.get(export_url, headers=headers)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"PDF de la pestaña guardado en: {output_path}")
    else:
        print(f"Error exportando la pestaña (status {response.status_code}): {response.text}")

# ---------------- CONVERTIR PDF → PNG ----------------
def pdf_to_images(pdf_path, output_folder, prefix="sheet"):
    poppler_path = r"C:\Users\Usuario\Documents\poppler-25.07.0\Library\bin"
    images = convert_from_path(pdf_path, dpi=DPI, poppler_path=poppler_path)
    image_paths = []
    for i, img in enumerate(images):
        img_path = os.path.join(output_folder, f"{prefix}_page_{i+1}.png")
        img.save(img_path, "PNG")
        image_paths.append(img_path)
        print(f"Imagen guardada: {img_path}")
    return image_paths

def crop_whitespace(img, bg_color=(255, 255, 255)):
    """Crop all white (or bg_color) margins from a PIL image."""
    bg = Image.new(img.mode, img.size, bg_color)
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        return img.crop(bbox)
    else:
        return img  # No content found, return as is

# ---------------- FUSIONAR IMÁGENES EN UNA SOLA ----------------
def fuse_images(image_paths, output_path, direction="vertical"):
    """Fuse a list of images into one big image (vertical or horizontal), cropping margins."""
    images = [Image.open(p) for p in image_paths]
    # Crop whitespace from each image
    cropped_images = [crop_whitespace(img) for img in images]
    if not cropped_images:
        print("No images to fuse.")
        return
    if direction == "vertical":
        total_width = max(img.width for img in cropped_images)
        total_height = sum(img.height for img in cropped_images)
        fused = Image.new('RGB', (total_width, total_height), (255, 255, 255))
        y_offset = 0
        for img in cropped_images:
            fused.paste(img, (0, y_offset))
            y_offset += img.height
    else:
        total_width = sum(img.width for img in cropped_images)
        total_height = max(img.height for img in cropped_images)
        fused = Image.new('RGB', (total_width, total_height), (255, 255, 255))
        x_offset = 0
        for img in cropped_images:
            fused.paste(img, (x_offset, 0))
            x_offset += img.width
    fused.save(output_path)
    print(f"Imagen fusionada guardada: {output_path}")

# ---------------- PROCESO COMPLETO ----------------
def main():
    # 1. Export whole sheet
    pdf_path = os.path.join(OUTPUT_FOLDER, "full_sheet.pdf")
    export_sheet_to_pdf(SHEET_ID, pdf_path)
    pdf_to_images(pdf_path, OUTPUT_FOLDER, prefix="full_sheet")

    # 2. Export DATA AI1 tab (A1:Y[last])
    last_row_data = get_last_row_with_data(DATA_AI1_TAB, DATA_AI1_COL, SHEET_ID)
    data_ai1_range = f"A1:{DATA_AI1_COL}{last_row_data}"
    data_ai1_pdf = os.path.join(OUTPUT_FOLDER, "DATA_AI1.pdf")
    export_tab_to_pdf(SHEET_ID, DATA_AI1_GID, data_ai1_pdf, creds, range_str=data_ai1_range)
    data_ai1_imgs = pdf_to_images(data_ai1_pdf, OUTPUT_FOLDER, prefix="DATA_AI1")
    fuse_images(data_ai1_imgs, os.path.join(OUTPUT_FOLDER, "DATA_AI1_fused.png"), direction="vertical")

    # 3. Export Report AI1 tab (A1:BC[last])
    last_row_report = get_last_row_with_data(REPORT_AI1_TAB, REPORT_AI1_COL, SHEET_ID)
    report_ai1_range = f"A1:{REPORT_AI1_COL}{last_row_report}"
    report_ai1_pdf = os.path.join(OUTPUT_FOLDER, "REPORT_AI1.pdf")
    export_tab_to_pdf(SHEET_ID, REPORT_AI1_GID, report_ai1_pdf, creds, range_str=report_ai1_range)
    report_ai1_imgs = pdf_to_images(report_ai1_pdf, OUTPUT_FOLDER, prefix="REPORT_AI1")
    fuse_images(report_ai1_imgs, os.path.join(OUTPUT_FOLDER, "REPORT_AI1_fused.png"), direction="vertical")

    print("✅ Exportación completada. Todas las páginas convertidas a PNG y fusionadas.")

if __name__ == "__main__":
    main()
