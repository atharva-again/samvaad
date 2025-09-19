from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List
from pipeline.ingestion import parse_file, chunk_text


app = FastAPI(title="Samvaad RAG Backend")


@app.get("/health")
def health_check():
	"""Health check endpoint to verify the server is running."""
	return JSONResponse(content={"status": "ok"})


# Ingest endpoint for uploading PDF or text files
@app.post("/ingest")
async def ingest_file(file: UploadFile = File(...)):
	"""
	Accept a PDF or text file upload, parse, chunk, and return a preview.
	"""
	filename = file.filename
	content_type = file.content_type
	contents = await file.read()
	text, error = parse_file(filename, content_type, contents)
	if not error and text:
		chunks = chunk_text(text)
		preview = chunks[:3]  # Show first 3 chunks as a preview
	else:
		chunks = []
		preview = []
	return {
		"filename": filename,
		"content_type": content_type,
		"size_bytes": len(contents),
		"num_chunks": len(chunks),
		"chunk_preview": preview,
		"error": error,
	}
