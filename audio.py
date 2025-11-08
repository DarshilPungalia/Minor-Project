from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import logging
from typing import Optional
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, filename=r'./logs/ingestion.log', filemode='w')
logger = logging.getLogger(__name__)

app = FastAPI(title="Audio Ingestion API", version="1.0.0")

UPLOAD_DIR = "./uploaded_audio"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus'}


class UploadResponse(BaseModel):
    status: str
    filename: str
    file_size_mb: float
    file_path: str
    audio_format: str
    message: str


class StatusResponse(BaseModel):
    status: str
    message: str
    total_files: Optional[int] = None

def parse_audio(file_content: bytes, file_name: str) -> str:
    """
    Save uploaded audio file
    
    Args:
        file_content: Bytes content of the uploaded audio
        file_name: Original filename 
                    
    Returns:
        Path to saved file
    """
    try:
        output_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(output_path, 'wb') as f:
            f.write(file_content)
 
        logger.info(f"Successfully saved audio file: {output_path}")

        return output_path
        
    except Exception as e:
        logger.error(f"Failed to save uploaded file {file_name}: {e}")
        raise Exception(f"Failed to save uploaded Audio: {e}")


@app.post("/upload", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload and store an audio file
    
    Args:
        file: Audio file to upload
        
    Returns:
        Success message with file information
    """
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension not in SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported audio format. Supported formats: {', '.join(SUPPORTED_AUDIO_FORMATS)}"
        )
    
    MAX_FILE_SIZE = 100 * 1024 * 1024 
    file_content = await file.read()
    
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024)}MB"
        )
    
    if len(file_content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )
    
    file_size_bytes = len(file_content)
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    try:
        logger.info(f"Processing audio file: {file.filename}, size: {file_size_mb:.2f}MB")
        
        file_path = parse_audio(file_content, file.filename)
        
        logger.info(f"Successfully saved audio file to {file_path}")
        
        return UploadResponse(
            status="success",
            filename=os.path.basename(file_path),
            file_size_mb=round(file_size_mb, 2),
            file_path=file_path,
            audio_format=file_extension.lstrip('.'),
            message=f"Successfully uploaded audio file: {os.path.basename(file_path)}"
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error processing {file.filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/health", response_model=StatusResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check if upload directory exists
        if not os.path.exists(UPLOAD_DIR):
            Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        
        # Count total uploaded files
        total_files = len([f for f in os.listdir(UPLOAD_DIR) if os.path.isfile(os.path.join(UPLOAD_DIR, f))])
        
        return StatusResponse(
            status="healthy", 
            message="Audio Ingestion API is running",
            total_files=total_files
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unhealthy"
        )


@app.get("/files", response_model=dict)
async def list_files():
    """List all uploaded audio files"""
    try:
        files = []
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                files.append({
                    "filename": filename,
                    "size_mb": round(file_size, 2),
                    "path": file_path
                })
        
        return {
            "total_files": len(files),
            "files": files
        }
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list files: {str(e)}"
        )


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Audio Ingestion API",
        "version": "1.0.0",
        "description": "Upload and store audio files",
        "endpoints": {
            "POST /upload": "Upload an audio file",
            "GET /health": "Health check",
            "GET /files": "List all uploaded files",
            "GET /": "API information"
        },
        "supported_formats": list(SUPPORTED_AUDIO_FORMATS),
        "max_file_size": "100MB",
        "upload_directory": UPLOAD_DIR
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8069, log_level="info")