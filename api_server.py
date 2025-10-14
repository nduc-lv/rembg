from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
from rembg import remove
from PIL import Image
import io
import os
from typing import Optional

app = FastAPI(title="RemBG API", description="Background removal API using rembg")


def apply_background_image(foreground_img: Image.Image, background_path: str) -> Image.Image:
    """
    Apply a background image to a foreground image with transparent background.

    Args:
        foreground_img: PIL Image with transparent background (RGBA mode)
        background_path: Path to the background image file

    Returns:
        PIL Image with background applied
    """
    try:
        # Open and prepare background image
        background_img = Image.open(background_path)

        # Convert foreground to RGBA if not already
        if foreground_img.mode != 'RGBA':
            foreground_img = foreground_img.convert('RGBA')

        # Resize background to match foreground dimensions
        background_img = background_img.resize(foreground_img.size, Image.Resampling.LANCZOS)

        # Convert background to RGBA
        if background_img.mode != 'RGBA':
            background_img = background_img.convert('RGBA')

        # Composite foreground over background
        result = Image.alpha_composite(background_img, foreground_img)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying background: {str(e)}")


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


@app.post("/remove-and-add-background")
async def remove_and_add_background(
    image_file: UploadFile = File(...),
    background_file: Optional[UploadFile] = File(None)
):
    """
    Remove background from image and add a new background in one step.
    If no background file is provided, uses the default background.jpg.

    Args:
        image_file: Image file to process (JPEG, PNG, etc.)
        background_file: Background image file to apply (optional, uses default if not provided)

    Returns:
        PNG image with background removed and new background added
    """
    # Validate file types
    if not image_file.content_type or not image_file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Image file must be an image")

    if background_file and not background_file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Background file must be an image")

    try:
        # Read the uploaded image file
        input_data = await image_file.read()

        # Remove background using rembg
        removed_bg_data = remove(input_data)

        # Convert removed background image to PIL Image
        foreground_img = Image.open(io.BytesIO(removed_bg_data))

        # Determine background path
        if background_file:
            # Use uploaded background
            background_data = await background_file.read()
            temp_bg_path = "/tmp/temp_background.jpg"
            with open(temp_bg_path, "wb") as f:
                f.write(background_data)
            bg_path = temp_bg_path
        else:
            # Use default background
            bg_path = "background.jpg"
            if not os.path.exists(bg_path):
                raise HTTPException(status_code=500, detail="Default background.jpg not found")

        # Apply background
        result_img = apply_background_image(foreground_img, bg_path)

        # Keep the original image format
        original_format = image_file.content_type.split('/')[-1].upper()
        if original_format == 'JPEG':
            result_img = result_img.convert('RGB')

        bio = io.BytesIO()
        result_img.save(bio, original_format)
        bio.seek(0)
        output_data = bio.read()

        return Response(
            content=output_data,
            media_type=image_file.content_type,
            headers={"Content-Disposition": f"attachment; filename=with_background.{original_format.lower()}"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/add-background")
async def add_background_only(
    foreground_file: UploadFile = File(...),
    background_file: Optional[UploadFile] = File(None)
):
    """
    Add a background to an existing image with transparent background.
    If no background file is provided, uses the default background.jpg.

    Args:
        foreground_file: Image with transparent background (PNG with alpha channel)
        background_file: Background image file (optional, uses default if not provided)

    Returns:
        PNG image with new background applied
    """
    # Validate file types
    if not foreground_file.content_type or not foreground_file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Foreground file must be an image")

    if background_file and not background_file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Background file must be an image")

    try:
        # Read foreground file
        foreground_data = await foreground_file.read()
        foreground_img = Image.open(io.BytesIO(foreground_data))

        # Determine background path
        if background_file:
            # Use uploaded background
            background_data = await background_file.read()
            temp_bg_path = "/tmp/temp_background.jpg"
            with open(temp_bg_path, "wb") as f:
                f.write(background_data)
            bg_path = temp_bg_path
        else:
            # Use default background
            bg_path = "background.jpg"
            if not os.path.exists(bg_path):
                raise HTTPException(status_code=500, detail="Default background.jpg not found")

        # Apply background
        result_img = apply_background_image(foreground_img, bg_path)

        # Convert to bytes
        bio = io.BytesIO()
        result_img.save(bio, "PNG")
        bio.seek(0)
        output_data = bio.read()

        return Response(
            content=output_data,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=with_background.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding background: {str(e)}")


@app.get("/")
def read_root():
    """Health check endpoint"""
    default_bg_exists = os.path.exists("background.jpg")
    return {
        "message": "RemBG API is running with background addition support",
        "default_background_available": default_bg_exists
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)