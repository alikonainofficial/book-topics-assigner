# Book Topics Assigner

This script assigns topics to books based on their descriptions using the OpenAI API. It processes an input CSV file containing book information, selects the most relevant topics from a predefined list, and outputs the results to a CSV file.

## Prerequisites

1. **Python 3.7+**: Ensure Python is installed on your machine.
2. **OpenAI API Key**: You must have an OpenAI API key to use the GPT model for topic extraction.
3. **Environment Setup**: The script loads environment variables from a `.env` file to securely handle the API key.

## Dependencies

The script requires the following Python packages:

- `openai`: For interacting with the OpenAI GPT model.
- `pandas`: For handling CSV data.
- `python-dotenv`: For loading environment variables.
- `argparse`: For parsing command-line arguments.
- `BeautifulSoup4`: For cleaning HTML tags from descriptions.
- `csv`: For reading/writing CSV files.
- `logging`: For logging information and errors.

You can install these dependencies by running:

```bash
pip install openai pandas python-dotenv beautifulsoup4

Setup

	1.	Install Python Packages: Use the provided requirements.txt (if available) or install the packages manually using pip.
	2.	Create a .env file: The script uses a .env file to store the OpenAI API key. Create a file called .env in the root directory of the script with the following content:

OPENAI_API_KEY=your_openai_api_key_here


	3.	Prepare Files:
	•	Input CSV: The input file should contain a list of books with columns like id, title, description, and ai_description (optional).
	•	Topics File: A text file containing a list of topics (one per line) that the script will use to classify books.

Usage

Run the script from the command line with the following syntax:

python3 topics_assigner.py <input_file> <output_file> <topics_file>

Arguments

	•	<input_file>: Path to the input CSV file that contains book descriptions.
	•	<output_file>: Path to the output CSV file where the results will be saved.
	•	<topics_file>: Path to a text file containing a list of topics (one per line).

Example Command

python3 topics_assigner.py sample_input.csv output.csv topics.txt

This command processes the books.csv file, assigns topics to the books, and saves the output in output.csv.

Resuming from the Last Processed Book

If the script is interrupted, it will resume processing from where it left off, based on the last processed id in the output file.

How It Works

	1.	Input Parsing: The script reads the input CSV file and loads the book data.
	2.	Description Cleaning: It cleans up HTML tags from book descriptions using BeautifulSoup.
	3.	Topic Selection: It generates a prompt for OpenAI’s GPT model, asking it to select relevant topics from the provided list based on the book’s description.
	4.	CSV Output: The script appends the results (book id and topics) to the output CSV file.

Logging

The script logs useful information to the console, including:

	•	Progress of book processing.
	•	Errors, warnings, and retries for API requests.

Error Handling

	•	Rate Limiting: If the OpenAI API rate limit is exceeded, the script retries the request with exponential backoff.
	•	File Errors: If any required files are missing (e.g., the topics file), the script logs an error and exits.

License

This project is licensed under the MIT License. See the LICENSE file for details.