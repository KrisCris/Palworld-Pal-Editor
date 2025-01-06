import re
import base64
import requests
import sys

def convert_images_to_base64(markdown_file, output_file):
    with open(markdown_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Find Markdown image syntax: ![alt-text](image-url)
    markdown_pattern = r"!\[(.*?)\]\((.*?)\)"
    markdown_matches = re.findall(markdown_pattern, content)

    # Find HTML <img> tags
    img_tag_pattern = r'<img[^>]+src=["\'](.*?)["\']'
    img_tag_matches = re.findall(img_tag_pattern, content)

    # Combine all matches with their types
    matches = [{'type': 'markdown', 'alt': alt, 'url': url} for alt, url in markdown_matches]
    matches += [{'type': 'html', 'url': url} for url in img_tag_matches]

    for match in matches:
        try:
            img_url = match['url']
            # Download the image
            response = requests.get(img_url)
            response.raise_for_status()
            img_data = response.content

            # Get the image MIME type
            mime_type = response.headers.get('Content-Type', 'image/png')  # Default to PNG

            # Convert to base64
            base64_data = base64.b64encode(img_data).decode('utf-8')
            base64_string = f"data:{mime_type};base64,{base64_data}"

            # Replace the URL with base64 data
            if match['type'] == 'markdown':
                alt_text = match['alt']
                original = f"![{alt_text}]({img_url})"
                replacement = f"![{alt_text}]({base64_string})"
                content = content.replace(original, replacement)
            elif match['type'] == 'html':
                original = f'src="{img_url}"'
                replacement = f'src="{base64_string}"'
                content = content.replace(original, replacement)
        except Exception as e:
            print(f"Failed to process image {img_url}: {e}")

    # Write the updated content to a new file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f"Updated markdown saved to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python md_convert.py input.md")
        sys.exit(1)
    in_file = sys.argv[1]
    convert_images_to_base64(in_file, f"{in_file}_output.md")