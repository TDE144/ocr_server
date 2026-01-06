from fastapi import FastAPI, UploadFile
from pix2text import Pix2Text
from PIL import Image
from fastapi.responses import PlainTextResponse


app = FastAPI()

latex_formula = None

@app.post("/get_latex")
async def recognize_latex(file: UploadFile):
    img = Image.open(file.file).convert("RGB").resize((224, 224))
    p2t = Pix2Text().from_config()
    latex = p2t.recognize(img, file_type='formula')
    global latex_formula
    latex_formula = latex
    return PlainTextResponse(latex)



