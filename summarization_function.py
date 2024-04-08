
# E.G. Summarize all the emails between Jack and Jane from January 1st to February 1st into a 500 word output
import math
import sys
import re
import pandas as pd
import email
import openai
from bs4 import BeautifulSoup
import html2text
import urllib

import html

#pip install beautifulsoup4
#pip install openai
#pip install openai==0.28

def clean_email_content(content):
    soup = BeautifulSoup(content, 'html.parser')
    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]

    unwanted_tags = ['style', 'script', 'head', 'title', 'div', 'table', 'tbody', 'tr', 'td', 'th', 'ul', 'li', 'span', 'a', 'p', 'img', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    for tag in unwanted_tags:
        for match in soup.findAll(tag):
            match.replace_with('')
  
    text = soup.get_text(separator=' ', strip=True)

    # Clean out remaining HTML tags and extract text
    text = soup.get_text(separator='\n')

    # Further clean up text
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    if text.startswith("---------- Forwarded message ---------"):
        return text  # Return the entire content without modifications if its a forwarded message. That means there is no
        # repeated emails from the conversation and hence we dont want to remove messages that start with 
        # "On Oct 16, 2023, at 12:19 PM, Sean Kelly wrote:" like we do below. 
    
    pattern1 = r"On\s+\w{3},\s+\d{1,2}\s+\w{3}\s+\d{4}\s+at\s+\d{1,2}:\d{2},\s+.*?\s+wrote:"
    # Split the text at the first pattern and keep only the first part
    parts = re.split(pattern1, text, flags=re.DOTALL, maxsplit=1)
    text1 = parts[0].strip() if parts else text    

    # Second, more comprehensive pattern
    pattern2 = r"On\s+\w{3},\s+(?:\d{1,2}\s+\w{3}|\w{3}\s+\d{1,2}),\s+\d{4}\s+at\s+\d{1,2}:\d{2}\s*(?:AM|PM)?,?\s+.*?\s+wrote:"
    # Split the text at the second pattern and keep only the first part
    parts1 = re.split(pattern2, text1, flags=re.DOTALL | re.IGNORECASE, maxsplit=1)
    finalOutput = parts1[0].strip() if parts1 else text1
    # finalOutput =text

    return finalOutput





# Function to count words in a text
def count_words(text):
    return len(text.split())


def calculate_words_per_chunk():
    return math.floor(4096 / 2.2)

def extract_chunks(text, words_per_summary):
    words_per_chunk = calculate_words_per_chunk()
    chunk_size=words_per_chunk-math.ceil(words_per_summary)
    words = text.split()
    total_words = len(words)
    for i in range(0, total_words, chunk_size):
        chunk = ' '.join(words[i:i+chunk_size])
        yield chunk

# Function to get emails and summarize
def get_emails_and_summarize(df, sender, recipient, start_date, end_date, total_words_in_output):
    words_per_chunk = calculate_words_per_chunk()
    # Step 1: Filter emails based on sender, recipient, and date range
    df['Date'] = pd.to_datetime(df['Date'], utc=True, errors='coerce') 
    start_date = pd.to_datetime(start_date, utc=True)
    end_date = pd.to_datetime(end_date, utc=True)
    filtered_emails = df[
    (
        ((df['From'] == sender) & (df['To'].apply(lambda x: recipient in x if isinstance(x, list) else False))) |
        ((df['To'] == sender) & (df['From'].apply(lambda x: recipient in x if isinstance(x, list) else False))) |
        ((df['From'] == recipient) & (df['To'].apply(lambda x: sender in x if isinstance(x, list) else False))) |
        ((df['To'] == recipient) & (df['From'].apply(lambda x: sender in x if isinstance(x, list) else False)))
    ) &
    ((df['Date'] >= start_date) & (df['Date'] <= end_date)) 
    ]

    # Check if there are any emails
    if filtered_emails.empty:
        print("No emails found between the specified sender and recipient.")
        error_message = "ERROR - NO EMAILS FOUND BETWEEN THE SPECIFIED ADDRESSES"
        return error_message
        sys.exit()  # Exit the function
        
    # Step 2: Sort emails by date
    filtered_emails = filtered_emails.sort_values(by='Date')
    filtered_emails['WordCount'] = filtered_emails['content'].apply(count_words)
    total_words_in_the_emails = filtered_emails['WordCount'].sum()
    print("TOTAL WORDS IN THE EMAILS: ", total_words_in_the_emails)
    
    concatenated_content = '\n'.join(filtered_emails['content'].astype(str).tolist())
    #print("TOTAL WORDS IN THE EMAILS together concatenated should be same: ", count_words(concatenated_content))
    cleaned_content = clean_email_content(concatenated_content)
    total_cleaned_content_count_words = count_words(cleaned_content)
    print("TOTAL WORDS cleaned content: ", total_cleaned_content_count_words)
    
    # Initialize variables
    chunks = []
    number_outputs=[]
    size_chunk=[]
    current_chunk = ""
    current_chunk_words = 0
    # Split the email content into chunks
    #words_per_chunk = math.floor(4096 / 2)  # model's maximum context length (INCLUDING THE GENERATED SUMMARY)
    # Iterate through each email
    #counter=0
    original_emails_info = []
    large_email_repeated = False

    for i, email_content in enumerate(filtered_emails['content'].astype(str).tolist()):
        # Clean the email content
        cleaned_content = clean_email_content(email_content)
        cleaned_content_count_words = count_words(cleaned_content)
        print("FROM:", filtered_emails.iloc[i]['From'])
        print("To:", filtered_emails.iloc[i]['To'])
        print("DATE: ", filtered_emails.iloc[i]['Date'])
        original_email_info = {
            "From": filtered_emails.iloc[i]['From'],
            "To": filtered_emails.iloc[i]['To'],
            "Date": filtered_emails.iloc[i]['Date'],
            "Email": cleaned_content
        }
        original_emails_info.append(original_email_info)
        
        if (cleaned_content_count_words > words_per_chunk):#&& counter == 0:
            print("NOTE HERE IS A LARGE SIZED EMAIL/!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
            print("current_chunk_words before appending (previous EMAIL)", current_chunk_words, "\n")
            print("cleaned_content_count_words LARGE EMAIL CURRENT= ", cleaned_content_count_words, "\n") 
            if (i != 0) and not large_email_repeated: #There was a bug here. I was not catching the case where there were two "larged sized" emails one after the other. THe problem was if two large emails came one after the other, in between them i would append an empty chunk. And this was a bug in (if i != 0:)
                chunks.append(current_chunk)
                size_chunk.append(current_chunk_words)    
                print("I HAVE JUST APPENDED ", current_chunk_words)       
                current_chunk_words = 0#1800
                current_chunk=""
            ##NOW WE BREAK UP THIS LARGE EMAIL HERE:
            #number_of_chunks_IN_LARGE_EMAIL = cleaned_content_count_words/words_per_chunk
            #for j in range Math.ceil(number_of_chunks_IN_LARGE_EMAIL):
            for word in cleaned_content.split():
                if current_chunk_words + 1 > words_per_chunk:
                    chunks.append(current_chunk)
                    print("JUST APPENDED core of email: ", current_chunk_words)
                    size_chunk.append(current_chunk_words)
                    current_chunk = word
                    current_chunk_words = 1
                else:
                    current_chunk += " " + word
                    current_chunk_words += 1
            chunks.append(current_chunk)
            size_chunk.append(current_chunk_words)
            print("JUST APPENDED last bit of large email: ", current_chunk_words)
            current_chunk = ""
            current_chunk_words = 0
            large_email_repeated = True
                   
        else:
            #######
            # Access the next email content to calculate the current_output_words_in_chunk
            if i + 1 < len(filtered_emails['content'].astype(str).tolist()):
                next_email_content = filtered_emails['content'].astype(str).tolist()[i + 1]
                cleaned_next_content = clean_email_content(next_email_content)
                cleaned_next_content_count_words = count_words(cleaned_next_content)
                if (current_chunk_words + cleaned_content_count_words + cleaned_next_content_count_words) > (words_per_chunk):
                    current_output_words_in_chunk = ((current_chunk_words + cleaned_content_count_words)/total_words_in_the_emails)*total_words_in_output
                else:
                    current_output_words_in_chunk=0
            #######
            if (current_chunk_words + cleaned_content_count_words) > (words_per_chunk):#-current_output_words_in_chunk
                print("Content current num words = ", cleaned_content_count_words) #1800
                chunks.append(current_chunk)
                size_chunk.append(current_chunk_words)           
                current_chunk_words = cleaned_content_count_words#1800
                current_chunk=cleaned_content###WHAT IF THE LARGE EMAIL IS AFTER THIS ONE? WHAT WILL HAPEN...????
                #counter=0       
            else:
                current_chunk+= " " + cleaned_content
                print(cleaned_content)
                #print("\nCurrent CHUNK:\n ", current_chunk)
                print("\n\n")
                current_chunk_words+=cleaned_content_count_words
                print(cleaned_content_count_words)
                print("\n\n")
                print("currCHUNK WORDS", current_chunk_words)
                print("\n\n")
                #counter+=1
            large_email_repeated = False

    #first we need to append the last chunks. but this is only if the "last chunk" has not already been appended.
    # it would have already been appended if the last email was a "large email", as after its added each word one 
    # by one, it appends the chunks when the email has been completed. 
    if not large_email_repeated:
        chunks.append(current_chunk)
        size_chunk.append(current_chunk_words) 

    
    #print(number_outputs)
    total_sum = sum(size_chunk)
    print("NEW TOTAL_SUM = ", total_sum)
    for element in size_chunk:
        percentage_of_chunk_words = element / total_sum
        current_output_words_per_chunk = math.floor(total_words_in_output * percentage_of_chunk_words)
        number_outputs.append(current_output_words_per_chunk)
    print(size_chunk)
    print(number_outputs)
    print(len(size_chunk))
    print(len(number_outputs))

    
    
    # Now, proceed with summarization for each chunk as before
    concatenated_summary = ""
    chunk_counter=0
    output_words_used = 0
    # Iterate through each chunk
    for i, chunk in enumerate(chunks):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Summarize the below email conversation in about {number_outputs[i]} words. Include important details and context:\n{chunk}.\nUse full sentances!"},
            ],
            #max_tokens=math.floor(number_outputs[i] * 1.5),
        )

        #chunk_summary = response['choices'][0]['text']
        chunk_summary = response['choices'][0]['message']['content']
        print(f"Mini Summarized Chunk:\n{chunk_summary}\nWord Count: {len(chunk_summary.split())}\n")
        concatenated_summary += f"\n{chunk_summary}"  # Add the mini summary to the concatenated summary
        print("\n")
    
    print("Final summarized version: \n", concatenated_summary)
    print(count_words(concatenated_summary))
    
    # Perform summarization for the entire concatenated summary
    input_NUMBER = count_words(concatenated_summary)
    #THIS IS only if the summarized chunks put together add up to more words than 1.5 times the specified output. THis means 
    # too long of a summary has been generated and we need to now summarize the summary. 
    if (input_NUMBER > 1.5*total_words_in_output):
        # Perform summarization for the entire concatenated summary
        remaining_words = total_words_in_output
        total_WORDS = input_NUMBER + remaining_words
        number_of_summaries = total_WORDS/words_per_chunk
        last_summary = number_of_summaries - int(number_of_summaries)
        number_of_words_in_last_summary = (last_summary/number_of_summaries) * remaining_words
        words_per_summary = remaining_words/number_of_summaries 

        final_final_summary = ""
        for i, chunk in enumerate(extract_chunks(concatenated_summary, words_per_summary)):
            summary_words = words_per_summary if i < (math.ceil(number_of_summaries) - 1) else number_of_words_in_last_summary
            #print(chunk)
            print("i=", i)
            print("CHUNK WORDS NUM: ", count_words(chunk))
            print("number_of_words_in_last_summary ", number_of_words_in_last_summary)
            print("SUMMARY WORDS: ", summary_words)
            print("number of summaries CEILING= ", math.ceil(number_of_summaries))
            #for i in Math.ceil(number_of_summaries):
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Take out the most important points and summarize this summary into {math.floor(summary_words)} words. Include important details and context:\n{chunk}.\nUse full sentences! NB! The summary must not be more than {math.floor(summary_words) + math.floor(summary_words) * 0.1} words!"},
                ],
                #max_tokens=math.floor(summary_words * 1.4),
            )
            final_portion = response['choices'][0]['message']['content']
            print(f"Summarized Chunk:\n{final_portion}\nWord Count: {len(final_portion.split())}\n")
            final_final_summary+= final_portion

        print("Process completed.")
        print(final_final_summary)
        print(count_words(final_final_summary))
        return final_final_summary, original_emails_info
    else:
        return concatenated_summary, original_emails_info


# def clean_email_content(content):
#     soup = BeautifulSoup(content, 'html.parser')
#     # Convert to text
#     [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]

#     unwanted_tags = ['style', 'script', 'head', 'title', 'div', 'table', 'tbody', 'tr', 'td', 'th', 'ul', 'li', 'span', 'a', 'p', 'img', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
#     for tag in unwanted_tags:
#         for match in soup.findAll(tag):
#             match.replace_with('')

#     text = soup.get_text(separator=' ', strip=True)

#     # # Remove style elements
#     # for tag in soup(['style']):
#     #     tag.decompose()

#     # Clean out remaining HTML tags and extract text
#     text = soup.get_text(separator='\n')

#     # Further clean up text
#     lines = (line.strip() for line in text.splitlines())
#     chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
#     text = '\n'.join(chunk for chunk in chunks if chunk)

#     return text


    