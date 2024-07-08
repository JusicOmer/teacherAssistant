from fastapi import FastAPI, HTTPException

from excelsave import save_drive_files_to_excel

app = FastAPI()

@app.get("/save_drive_files")
async def save_drive_files():
    try:
        save_drive_files_to_excel()
        return {"message": "File list saved to google_drive_files.xlsx"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=4000)
