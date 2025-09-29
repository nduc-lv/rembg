from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
from rembg import remove

app = FastAPI(title="RemBG API", description="Background removal API using rembg")


@app.post("/remove-background")
async def remove_background(file: UploadFile = File(...)):
    """
    Remove background from uploaded image file.

    Args:
        file: Image file to process (JPEG, PNG, etc.)

    Returns:
        PNG image with background removed
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        # Read the uploaded file
        input_data = await file.read()

        # Remove background using rembg
        output_data = remove(input_data)

        # Return the processed image as PNG
        return Response(
            content=output_data,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=removed_background.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.get("/")
def read_root():
    """Health check endpoint"""
    return {"message": "RemBG API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)