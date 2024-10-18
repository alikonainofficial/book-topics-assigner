import argparse
import pandas as pd
import openai
from openai import OpenAI
from dotenv import load_dotenv
import os
import time
import logging
import csv
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Set your OpenAI API key
open_ai_api= os.getenv("OPENAI_API_KEY")

# Set up OpenAI API key
client = OpenAI(api_key=open_ai_api)

# Function to load topics from a file
def load_topics_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            topics = [line.strip() for line in file if line.strip()]  # Remove empty lines or spaces
        return topics
    except FileNotFoundError:
        logging.error(f"Topics file {file_path} not found.")
        return []
    
# Function to clean HTML tags from the description
def clean_html(raw_html):
    if pd.isna(raw_html):
        return ""
    
    # Parse HTML and extract text
    soup = BeautifulSoup(raw_html, "html.parser")
    cleaned_text = soup.get_text(separator=" ", strip=True)
    
    # Decode HTML entities like &#10; (newline) and others
    cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')
    
    # Remove excessive whitespace, including encoded HTML spaces
    cleaned_text = ' '.join(cleaned_text.split())
        
    # Explicitly remove all occurrences of "\n"
    cleaned_text = cleaned_text.replace("\\n", "").strip()
    
    # Return an empty string if the cleaned text is effectively empty
    if not cleaned_text:
        return ""
    
    return cleaned_text

            
# Function to get the topic list from OpenAI API
def get_topics_for_book(description, topics):

    prompt = (
        f"Based on the following book description, choose the most relevant topics from the provided topic list."
        f"Select between 3 and 10 topics that best match the book's description. Make sure to only pick topics from the provided list "
        f"that are clearly applicable, and avoid including irrelevant ones.\n\n"
        f"Description: {description}\n\n"
        f"Topics List: {', '.join(topics)}\n\n"
        f"Return the chosen topics as a comma-separated list without any additional text."
    )
    delay = 2  # Initial delay in seconds
    max_delay = 60  # Maximum delay in seconds
    max_retries = 5  # Maximum number of retry attempts
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100
            )
            
            # Extract the text response
            topics_response = response.choices[0].message.content.strip()
            
            # Convert the comma-separated response to a list
            topics_list = [topic.strip() for topic in topics_response.split(',') if topic.strip() in topics]
            
            return topics_list
        except openai.RateLimitError as e:
            logging.warning(f'Rate limit exceeded. Attempt {attempt + 1}/{max_retries}. Retrying in {delay} seconds.')
            time.sleep(delay)
            delay = min(max_delay, delay * 2)  # Exponential backoff
        
        except openai.OpenAIError as e:
            logging.error(f'OpenAI API error: {e}')
            return "No description available"
        
    # If all attempts fail
    logging.error("All retry attempts failed. Returning 'No description available'.")
    return "No description available"

# Validate and preprocess descriptions
def preprocess_description(ai_description, description, title):
    # Prefer ai_description if available
    combined_description = ai_description if pd.notna(ai_description) else description
    
    # Clean HTML from the description
    combined_description = clean_html(combined_description)
        
    # Check if the cleaned description is empty
    if not combined_description.strip() or len(combined_description) < 5:
        logging.warning(f"No valid description found for title '{title}'")
        return ""
    
    # Truncate the description if it's too long (let's say we limit it to 1000 characters)
    max_desc_length = 1000
    return f"{title}: {combined_description[:max_desc_length]}"


# Main function to process the input CSV and generate topics
def assign_topics(input_file, output_file, topics_file):
    # Load the topics from the provided file
    topics = load_topics_from_file(topics_file)
    if not topics:
        logging.error("No topics loaded. Exiting.")
        return
    
    df = pd.read_csv(input_file)
    
    # Check if the output file already exists
    last_processed_id = None
    if os.path.exists(output_file):
        with open(output_file, mode='r') as output_csv:
            reader = csv.DictReader(output_csv)
            rows = list(reader)
            if rows:
                last_processed_id = rows[-1]['id']
                logging.info(f"Resuming from last processed ID: {last_processed_id}")
    
    # Filter dataframe to start from the next unprocessed row
    if last_processed_id:
        start_index = df[df['id'] == last_processed_id].index[0] + 1
        df = df.iloc[start_index:]
        logging.info(f"Resuming processing from row index {start_index}")
    
    with open(output_file, mode='a', newline='') as output_csv:
        writer = csv.DictWriter(output_csv, fieldnames=['id', 'topics_list'])
        
        # Write header only if the file is empty
        if output_csv.tell() == 0:
            writer.writeheader()

        for index, row in df.iterrows():
            book_id = row['id']
            title = row['title'] if pd.notna(row['title']) else ""
            description = row['description'] if pd.notna(row['description']) else ""
            ai_description = row['ai_description'] if pd.notna(row['ai_description']) else ""

            logging.info(f"Processing ID {book_id}")
            combined_description = preprocess_description(ai_description, description, title)

            if not combined_description:
                logging.warning(f"Skipping ID {book_id} due to empty description.")
                continue

            topics_list = get_topics_for_book(combined_description, topics)
            writer.writerow({"id": book_id, "topics_list": str(topics_list)})
            output_csv.flush()

    logging.info(f"Processing completed. Results saved to {output_file}")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Assign topics to books based on descriptions using OpenAI API")
    parser.add_argument("input_file", help="Path to the input CSV file containing book descriptions")
    parser.add_argument("output_file", help="Path to the output CSV file where topics will be saved")
    parser.add_argument("topics_file", help="Path to the text file containing the list of topics")

    args = parser.parse_args()

    # Call the main function with parsed arguments
    assign_topics(args.input_file, args.output_file, args.topics_file)