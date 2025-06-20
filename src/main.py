from fastapi import FastAPI, File, UploadFile, Depends, Response, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
import os  
import gigaam
import gigaam.vad_utils
from pyannote.audio import Pipeline
import re
import uuid
import asyncio
import aiofiles
import uvicorn

PATH = os.getcwd()

if not os.environ.get("HF_TOKEN"):
    print("run offline")
    gigaam.vad_utils._PIPELINE = Pipeline.from_pretrained(PATH + "/config/vad/config.yaml")

app = FastAPI()

res = {}
files_list = {}

templates = Jinja2Templates(directory = PATH + '/src/templates')

SESSIONS_DIR = f"{PATH}/tmp/user_sessions"
os.makedirs(SESSIONS_DIR, exist_ok=True)

def get_session_id(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(key="session_id", value=session_id)
    return session_id

def get_user_dir(session_id: str) -> str:
    user_dir = os.path.join(SESSIONS_DIR, session_id)
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(f"{user_dir}/output", exist_ok=True)
    return user_dir


@app.post("/uploadfile")
async def create_upload_file(file: UploadFile | None = None, session_id: str = Depends(get_session_id)):
    global files_list

    if file is None:
        return PlainTextResponse("Файл не передан", status_code=400)

    file_location = f"{SESSIONS_DIR}/{session_id}/buffer"
    output_name = re.sub(r'(.webm|.mp4|.m4a)', '', file.filename)
    safe_output = output_name.replace(" ", "_")
    wav_path = f"{SESSIONS_DIR}/{session_id}/{safe_output}.wav"

    # Асинхронное чтение файла
    file_data = await file.read()

    # Сохраняем файл асинхронно
    async with aiofiles.open(file_location, "wb") as f:
        await f.write(file_data)

    # Асинхронный вызов ffmpeg
    command = f'ffmpeg -i "{file_location}" -ab 160k -ac 2 -ar 44100 -vn "{wav_path}" -y'
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    await process.communicate()

    # Обновляем список файлов
    files_list[session_id] = {
        "wav": wav_path,
        "name": output_name
    }

    return PlainTextResponse("Файл успешно загружен.",status_code=200)

@app.post("/process")
async def process_file(session_id: str = Depends(get_session_id)):
    from time import time
    import datetime
    # Загрузка модели (лучше делать один раз и кэшировать!)
    start_time = time()
    print(f"[{datetime.datetime.now()}] Обработка началась")
    
    model = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: gigaam.load_model("v2_ctc", device="cpu", download_root=f"{PATH}/models/")
    )
    wav_path = files_list[session_id]["wav"]
    output_txt_path = f"{SESSIONS_DIR}/{session_id}/output/{files_list[session_id]['name']}.txt"

    # Распознавание — тоже блокирующая операция
    recognition_result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: model.transcribe_longform(wav_path)
    )

    # Асинхронная запись результата
    async with aiofiles.open(output_txt_path, 'a') as f:
        for utterance in recognition_result:
            transcription = utterance["transcription"]
            start, end = utterance["boundaries"]
            line = f"[{gigaam.format_time(start)} - {gigaam.format_time(end)}]: {transcription}\n"
            res[session_id] += line
            await f.write(line)

    # Асинхронное удаление временных файлов (через run_in_executor)
    async def remove_if_exists(path):
        if os.path.exists(path):
            await asyncio.get_event_loop().run_in_executor(None, os.remove, path)

    await remove_if_exists(f"{SESSIONS_DIR}/{session_id}/buffer")
    await remove_if_exists(files_list[session_id]["wav"])
    files_list.pop(session_id)
    print(f"[{datetime.datetime.now()}] Обработка закончилась общее время работы ({time() - start_time})")
    return Response(status_code=200)
    
@app.get("/result", response_class=PlainTextResponse)
async def result(session_id: str = Depends(get_session_id)):
    global res
    return res[session_id]

@app.get("/files")
async def listfiles(session_id: str = Depends(get_session_id)):
    return os.listdir(f"{SESSIONS_DIR}/{session_id}/output")

@app.get('/files/{filename}')
async def download_file(filename: str, session_id: str = Depends(get_session_id)):
    return FileResponse(path=f'{SESSIONS_DIR}/{session_id}/output/{filename}', filename=filename, media_type='multipart/form-data')

@app.delete("/files/{filename}")
def delete_file(filename: str, session_id: str = Depends(get_session_id)):
    global res
    file_path = os.path.join(f'{SESSIONS_DIR}/{session_id}/output/', filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        res[session_id] = ""
        return {"status": "ok"}
    return {"status": "not found"}, 404

@app.post("/cookie")
def create_cookie(
    request: Request,
    response: Response,
    session_id: str = Depends(get_session_id)
):
    global res
    get_user_dir(session_id)
    res[session_id] = ""
    return {'message':'SetUp cookie'}


@app.get("/")
def main_page(
    request: Request,
    session_id: str = Depends(get_session_id)
):
    global res
    get_user_dir(session_id)
    res[session_id] = ""
    return templates.TemplateResponse(name='index.html', context={'request': request})





def start():
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()