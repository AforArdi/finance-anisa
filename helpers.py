import os
import json
import uuid # New import
from PIL import Image, ImageDraw, ImageFont

def generate_certificate(participant, template_data, output_dir="static/certs"):
    """
    Generates a certificate image for a given participant and template.

    Args:
        participant (dict): A dictionary containing participant details (e.g., name, event, date, position).
        template_data (dict): A dictionary containing template details
                              (e.g., 'file_path', 'fields_config').
        output_dir (str): The directory where the generated certificate will be saved.

    Returns:
        str: The path to the generated certificate image, or None if an error occurs.
    """
    try:
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Load the template image
        template_path = template_data["file_path"]
        if not os.path.exists(template_path):
            print(f"Error in generate_certificate: Template image not found at {template_path}")
            print(f"Participant data: {participant}")
            print(f"Template data: {template_data}")
            return None
        
        img = Image.open(template_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Parse fields_config
        fields_config = json.loads(template_data["fields_config"])

        # Iterate through fields and draw text
        for field_name, config in fields_config.items():
            text_to_draw = ""
            # First, check standard participant fields (name, email, event, position, date)
            if field_name in participant and participant[field_name] is not None:
                text_to_draw = str(participant[field_name])
            # If not found in standard fields, check custom_fields JSON
            elif "custom_fields" in participant and participant["custom_fields"]:
                try:
                    custom_fields_dict = json.loads(participant["custom_fields"])
                    if field_name in custom_fields_dict and custom_fields_dict[field_name] is not None:
                        text_to_draw = str(custom_fields_dict[field_name])
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode custom_fields for participant ID {participant.get('id')}. Skipping custom field lookup for '{field_name}'.")
            
            if text_to_draw: # Only proceed if we actually have text
                x = config.get("x")
                y = config.get("y")
                font_size = config.get("font_size", 40)
                font_color = config.get("color", "#000000") # Default to black
                font_path = config.get("font_path") # Removed default 'arial.ttf'

                if x is None or y is None:
                    print(f"Warning: Missing x or y coordinate for field '{field_name}'. Skipping text drawing.")
                    continue

                # Load font
                font = None
                if font_path:
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                    except IOError:
                        print(f"Warning: Font {font_path} not found. Using default Pillow font with specified size.")
                    except Exception as font_e:
                        print(f"Error loading custom font {font_path}: {font_e}. Using default Pillow font with specified size.")
                
                # If custom font failed or not specified, use default Pillow font with specified size
                if font is None:
                    font = ImageFont.load_default(size=font_size)

                # Calculate text position
                draw_x = x
                if config.get("align") == "center":
                    try:
                        # Get text bounding box to calculate width
                        bbox = draw.textbbox((0,0), text_to_draw, font=font)
                        text_width = bbox[2] - bbox[0]
                        draw_x = x - (text_width / 2)
                    except Exception as align_e:
                        print(f"Could not calculate text width for alignment: {align_e}. Using original x coordinate.")
                
                draw.text((draw_x, y), text_to_draw, font=font, fill=font_color)
        
        # Generate a unique filename for the certificate
        unique_id = uuid.uuid4().hex
        safe_name = "".join(c for c in participant.get("name", "unknown").replace(" ", "_") if c.isalnum() or c == "_")
        safe_event = "".join(c for c in participant.get("event", "event").replace(" ", "_") if c.isalnum() or c == "_")
        
        # Use a more robust filename, potentially including participant ID for debugging
        filename = f"{safe_name}_{safe_event}_{participant.get('id', 'no_id')}_{unique_id}.png"
        output_path = os.path.join(output_dir, filename)

        img.save(output_path)
        # Return a URL-friendly path
        return output_path.replace("\\", "/")

    except Exception as e:
        print(f"An error occurred during certificate generation: {e}")
        print(f"Participant data causing error: {participant}")
        print(f"Template data causing error: {template_data}")
        return None

