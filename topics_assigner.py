"""
This module assigns topics to books based on their descriptions using the OpenAI API.
It reads input from a CSV file, processes the descriptions, 
and writes the topics to an output CSV file.
"""

import os
import time
import logging
import csv
import argparse
import pandas as pd
import openai
from openai import OpenAI
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

# Set your OpenAI API key
open_ai_api = os.getenv("OPENAI_API_KEY")

# Set up OpenAI API key
client = OpenAI(api_key=open_ai_api)


# Function to load topics from a file
def load_topics_from_file(file_path):
    """
    Loads topics from the specified file and returns them as a list.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            topics = [
                line.strip() for line in file if line.strip()
            ]  # Remove empty lines or spaces
        return topics
    except FileNotFoundError:
        logging.error("Topics file %s not found.", file_path)
        return []


# Function to clean HTML tags from the description
def clean_html(raw_html):
    """
    Cleans HTML tags from the provided string and returns plain text.
    """
    if pd.isna(raw_html):
        return ""

    # Parse HTML and extract text
    soup = BeautifulSoup(raw_html, "html.parser")
    cleaned_text = soup.get_text(separator=" ", strip=True)

    # Decode HTML entities like &#10; (newline) and others
    cleaned_text = cleaned_text.replace("\n", " ").replace("\r", " ")

    # Remove excessive whitespace, including encoded HTML spaces
    cleaned_text = " ".join(cleaned_text.split())

    # Explicitly remove all occurrences of "\n"
    cleaned_text = cleaned_text.replace("\\n", "").strip()

    # Return an empty string if the cleaned text is effectively empty
    if not cleaned_text:
        return ""

    return cleaned_text


# Function to get the topic list from OpenAI API
def get_topics_for_book(description, topics):
    """
    Uses the OpenAI API to extract relevant topics based on a book description.
    """
    prompt = (
        f"Based on the following book description, choose the most relevant topics from the "
        f"provided topic list. Select between 3 and 10 topics that best match the book's "
        f"description. Make sure to only pick topics from the provided list that are "
        f"clearly applicable, and avoid including irrelevant ones.\n\n"
        f"Description: {description}\n\n"
        f"Topics List: {', '.join(topics)}\n\n"
        f"Return the chosen topics as a comma-separated list without any additional text."
    )
    delay = 2  # Initial delay in seconds

    for attempt in range(5):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
            )

            # Convert the comma-separated response to a list
            return [
                topic.strip()
                for topic in response.choices[0].message.content.split(",")
                if topic.strip() in topics
            ]
        except openai.RateLimitError:
            delay = min(60, 2 * (attempt + 1))
            logging.warning("Rate limit exceeded. Retrying in %s seconds.", delay)
            time.sleep(delay)
        except openai.OpenAIError as e:
            logging.error("OpenAI API error: %s", e)
            break

    # If all attempts fail
    logging.error("Failed to retrieve topics after multiple attempts.")
    return []


# Validate and preprocess descriptions
def preprocess_description(ai_description, description, title):
    """
    Preprocesses and combines AI-generated and regular descriptions with the book title.

    :param ai_description: The description generated by an AI model
    :param description: The book's original description
    :param title: The book's title
    :return: A cleaned and truncated description string
    """
    # Prefer ai_description if available
    combined_description = ai_description if pd.notna(ai_description) else description

    # Clean HTML from the description
    combined_description = clean_html(combined_description)

    # Check if the cleaned description is empty
    if not combined_description.strip() or len(combined_description) < 5:
        logging.warning("No valid description found for title '%s'", title)
        return ""

    # Truncate the description if it's too long (let's say we limit it to 1000 characters)
    max_desc_length = 1000
    return f"{title}: {combined_description[:max_desc_length]}"


def get_last_processed_id(output_file):
    """
    Retrieves the last processed ID from the output file to enable resuming.

    :param output_file: Path to the output CSV file
    :return: The ID of the last processed row, or None if the file` is empty
    """
    if os.path.exists(output_file):
        with open(output_file, mode="r", encoding="utf-8") as output_csv:
            reader = csv.DictReader(output_csv)
            rows = list(reader)
            if rows:
                return rows[-1]["id"]
    return None


def resume_from_last_processed(df, last_processed_id):
    """
    Filters the dataframe to start processing from the next unprocessed row.

    :param df: The original dataframe
    :param last_processed_id: The last processed ID from the output file
    :return: A filtered dataframe starting from the next row
    """
    try:
        start_index = df[df["id"] == last_processed_id].index[0] + 1
        return df.iloc[start_index:]
    except IndexError:
        logging.warning(
            "Could not find last processed ID in input file. Processing all rows."
        )
        return df


def process_and_write_row(row, topics, writer, output_csv):
    """
    Processes a single row and writes the result to the output CSV.

    :param row: The dataframe row representing a book
    :param topics: List of topics to match with
    :param writer: The CSV DictWriter object to write the result
    """
    book_id = row["id"]
    title = row.get("title", "")
    description = row.get("description", "")
    ai_description = row.get("ai_description", "")

    logging.info("Processing ID %s", book_id)
    combined_description = preprocess_description(ai_description, description, title)

    if not combined_description:
        logging.warning("Skipping ID %s due to empty description.", book_id)
        return

    topics_list = get_topics_for_book(combined_description, topics)
    writer.writerow({"id": book_id, "topics_list": str(topics_list)})
    output_csv.flush()


# Main function to process the input CSV and generate topics
def assign_topics(input_file, output_file, topics_file):
    """
    Processes the input CSV, assigns topics to books using OpenAI API,
    and writes the results to the output CSV.

    :param input_file: Path to the input CSV file containing book descriptions
    :param output_file: Path to the output CSV file where the results will be saved
    :param topics_file: Path to the file containing the list of topics
    """
    # Load the topics from the provided file
    topics = load_topics_from_file(topics_file)
    if not topics:
        logging.error("No topics loaded. Exiting.")
        return

    df = pd.read_csv(input_file)

    # Check if the output file already exists
    last_processed_id = get_last_processed_id(output_file)

    # Filter dataframe to start from the next unprocessed row
    if last_processed_id:
        df = resume_from_last_processed(df, last_processed_id)
        logging.info("Resuming from last processed ID: %s", last_processed_id)

    with open(output_file, mode="a", newline="", encoding="utf-8") as output_csv:
        writer = csv.DictWriter(output_csv, fieldnames=["id", "topics_list"])

        # Write header only if the file is empty
        if output_csv.tell() == 0:
            writer.writeheader()

        for _, row in df.iterrows():
            process_and_write_row(row, topics, writer, output_csv)

    logging.info("Processing completed. Results saved to %s", output_file)


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Assign topics to books based on descriptions using OpenAI API"
    )
    parser.add_argument(
        "input_file", help="Path to the input CSV file containing book descriptions"
    )
    parser.add_argument(
        "output_file", help="Path to the output CSV file where topics will be saved"
    )
    parser.add_argument(
        "topics_file", help="Path to the text file containing the list of topics"
    )

    args = parser.parse_args()

    # Call the main function with parsed arguments
    assign_topics(args.input_file, args.output_file, args.topics_file)
