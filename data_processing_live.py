from datetime import datetime
from dateutil import parser
import pandas as pd
import re
import email
import ast
from bs4 import BeautifulSoup
import imaplib
import math
import sys
import re

def fetchRequiredEmails(emailAddress, password, sender, receiver, start_date, end_date):
    login_successful = checkLogin(emailAddress, password)
    if not login_successful:
        print(f"Login failed for {emailAddress}")
        return None

    try:
        # Select Inbox folder
        imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
        imap_server.login(emailAddress, password)
        imap_server.select('Inbox') # receiving emails

        if emailAddress == sender:
            search_criteria_sender = [
                # f'(HEADER "From" "{receiver}" TEXT "CI")', 
                # f'(HEADER "To" "{sender}" TEXT "CI")',
                # f'(X-GM-RAW "FROM "{receiver}"")', 
                # f'(X-GM-RAW "TO "{sender}"")', 
                f'(FROM "{receiver}")', #john (working)
                f'(TO "{sender}")',# good luck (working)
                f'(SINCE "{start_date.strftime("%d-%b-%Y")}")',
                f'(BEFORE "{end_date.strftime("%d-%b-%Y")}")'
            ]
            search_query = ' '.join(search_criteria_sender)
            result_inbox, data_inbox = imap_server.search(None, search_query)

        else:
            search_criteria_receiver = [
                # f'(HEADER "FROM" "{sender}" TEXT "CI")', # john (not working)
                # f'(HEADER "TO" "{receiver}" TEXT "CI")', # goodluck
                # f'(X-GM-RAW "FROM "{sender}"")', 
                # f'(X-GM-RAW "TO "{receiver}"")', 
                f'(FROM "{sender}")', # john (not working)
                f'(TO "{receiver}")', # goodluck
                f'(SINCE "{start_date.strftime("%d-%b-%Y")}")',
                f'(BEFORE "{end_date.strftime("%d-%b-%Y")}")'
            ]     
            search_query = ' '.join(search_criteria_receiver)
            result_inbox, data_inbox = imap_server.search(None, search_query)

        email_data = {
            'email_id': [],
            'date': [],
            'from': [],
            'to': [],
            'subject': [],
            'content': [],
        }

        # Process emails from Inbox
        for email_id in data_inbox[0].split():
            try:
                result, email_info = imap_server.fetch(email_id, '(RFC822)')
                email_raw = email_info[0][1]

                # Decode the email message
                email_decoded = decode_email(email_raw)

                # Add the decoded email message to the data dictionary
                email_data['email_id'].append(email_id)
                email_data['date'].append(email_decoded['date'])
                email_data['from'].append(email_decoded['from'])
                email_data['to'].append(email_decoded['to'])
                email_data['subject'].append(email_decoded['subject'])
                email_data['content'].append(email_decoded['content'])

            except Exception as e:
                print(f"Error decoding email {email_id}: {e}")

        # Select Sent folder
        imap_server.select('"[Gmail]/Sent Mail"')

        if emailAddress == sender:
            search_criteria1 = [
                f'(FROM "{sender}")',#goodluck
                f'(TO "{receiver}")',# john
                # f'(X-GM-RAW "FROM "{sender}"")', 
                # f'(X-GM-RAW "TO "{receiver}"")', 
                # f'(HEADER "FROM" "{sender}")',#goodluck
                # f'(HEADER "TO" "{receiver}")',# john
                f'(SINCE "{start_date.strftime("%d-%b-%Y")}")',
                f'(BEFORE "{end_date.strftime("%d-%b-%Y")}")'
            ]
            search_query = ' '.join(search_criteria1)
            result_sent, data_sent = imap_server.search(None, search_query)
        else:
            search_criteria2 = [
                # f'(HEADER "FROM" "{receiver}" TEXT "CI")', 
                # f'(HEADER "TO" "{sender}" TEXT "CI")', 
                # f'(X-GM-RAW "FROM "{receiver}"")', 
                # f'(X-GM-RAW "TO "{sender}"")', 
                f'(FROM "{receiver}")', 
                f'(TO "{sender}")', 
                f'(SINCE "{start_date.strftime("%d-%b-%Y")}")',
                f'(BEFORE "{end_date.strftime("%d-%b-%Y")}")'
            ]
            search_query = ' '.join(search_criteria2)
            result_sent, data_sent = imap_server.search(None, search_query)

        # Process emails from Sent Mail
        for email_id in data_sent[0].split():
            try:
                result, email_info = imap_server.fetch(email_id, '(RFC822)')
                email_raw = email_info[0][1]

                # Decode the email message
                email_decoded = decode_email(email_raw)

                # Add the decoded email message to the data dictionary
                email_data['email_id'].append(email_id)
                email_data['date'].append(email_decoded['date'])
                email_data['from'].append(email_decoded['from'])
                email_data['to'].append(email_decoded['to'])
                email_data['subject'].append(email_decoded['subject'])
                email_data['content'].append(email_decoded['content'])

            except Exception as e:
                print(f"Error decoding email {email_id}: {e}")

        # Create a DataFrame from the collected data
        df = pd.DataFrame(email_data)

        print("EMAIL DATA = :")
        print(df)

        df.rename(columns={'date': 'Date'}, inplace=True)
        df.rename(columns={'from': 'From'}, inplace=True)
        df.rename(columns={'to': 'To'}, inplace=True)

        df['FromEmail'] = df['From'].apply(extract_from_emails)
        df['FromName'] = df['From'].apply(extract_from_names)
        df['ToEmail'] = df['To'].apply(extract_from_emails)
        #df['ToEmail'] = df['To'].apply(lambda x: extract_from_emails(x) if isinstance(x, list) else [x])
        df['ToName'] = df['To'].apply(extract_from_names)

        df.drop(["From", "To"], axis=1, inplace=True)
        df.rename(columns={'FromEmail': 'From'}, inplace=True)
        df.rename(columns={'ToEmail': 'To'}, inplace=True)
        ###########df['From'] = df['From'].apply(lambda x: str(list(x)[0]))
        df['From'] = df['From'].apply(lambda x: str(list(x)[0]) if x else '')
        #df['To'] = df['To'].apply(lambda x: x if x else [])

        #df['From'] = df['From'].apply(lambda x: str(x[0]) if x else '')
        #df['To'] = df['To'].apply(lambda x: ', '.join(map(str, x)) if x else '')

        print("HELLOOOOOOOO")
        print(df['From'])
        print(df['To'])

        return df
    finally:
        # Always close the connection after use
        imap_server.logout()




    
def checkLogin(emailAddress, password):
    try:
        imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
        imap_server.login(emailAddress, password)
        
        # # Close the connection after successful login
        #imap_server.logout()
        # Return a success status
        return True

    except imaplib.IMAP4.error as e:
        # Return an error message and a failure status
        return False




def decode_email(email_raw):
    msg = email.message_from_bytes(email_raw)

    email_info = {
        'date': msg.get('Date'),
        'from': msg.get('From'),
        'to': msg.get('To'),
        'subject': msg.get('Subject'),
        'content': '',
    }

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition"))
        if "attachment" not in content_disposition:
            charset = part.get_content_charset()
            if charset is None:
                charset = 'utf-8'
            if "text" in content_type:
                try:
                    payload = part.get_payload(decode=True)
                    email_info['content'] += payload.decode(charset, 'ignore')
                except Exception as e:
                    print("Error decoding part:", e)

    # Convert the date string to a datetime object using dateutil.parser
    if email_info['date']:
        try:
            email_info['date'] = parser.parse(email_info['date'])
        except ValueError:
            print("Error parsing date:", email_info['date'])

    return email_info


def extract_from_emails(column):
    try:
        if pd.isna(column):
            return []
        emails = re.findall(r'<([^>]+)>', column)
        cleaned_emails = [email.strip() for email in emails if email.strip()]
        if not cleaned_emails:
            cleaned_emails.append(column.strip())

        return cleaned_emails
    except TypeError:
        return []
 



def extract_from_names(column):
    try:
        if pd.isna(column):
            return []
        names = re.findall(r'([^<>,]+)\s*<[^>]+>', column)
        cleaned_names = [name.strip() for name in names if name.strip()]
        if not cleaned_names:
            cleaned_names.append(column.strip())

        return cleaned_names
    except TypeError:
        return []




# Select Inbox folder
    # login_successful = checkLogin(emailAddress, password)
    # if not login_successful:
    #     print(f"Login failed for {emailAddress}")
    #     return None

    # try:
    #     # Select Inbox folder
    #     imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
    #     imap_server.login(emailAddress, password)
    #     imap_server.select('Inbox')

    #     search_criteria = []
    #     search_criteria.append(f'(FROM "{receiver}")')
    #     search_criteria.append(f'(TO "{sender}")')
    #     search_criteria.append(f'(SINCE "{start_date.strftime("%d-%b-%Y")}")')
    #     search_criteria.append(f'(BEFORE "{end_date.strftime("%d-%b-%Y")}")')

    #     # # Build the search criteria based on the provided parameters
    #     # search_criteria = [
    #     #     f'(FROM "{receiver}")',
    #     #     f'(TO "{sender}")',
    #     #     f'(SINCE "{start_date.strftime("%d-%b-%Y")}")',
    #     #     f'(BEFORE "{end_date.strftime("%d-%b-%Y")}")'
    #     # ]

    #     search_query = ' '.join(search_criteria)
    #     result_inbox, data_inbox = imap_server.search(None, search_query)

    #     email_data = {
    #         'email_id': [],
    #         'date': [],
    #         'from': [],
    #         'to': [],
    #         'subject': [],
    #         'content': [],
    #     }

    #     # Process emails from Inbox
    #     for email_id in data_inbox[0].split():
    #         try:
    #             result, email_info = imap_server.fetch(email_id, '(RFC822)')
    #             email_raw = email_info[0][1]

    #             # Decode the email message
    #             email_decoded = decode_email(email_raw)

    #             # Add the decoded email message to the data dictionary
    #             email_data['email_id'].append(email_id)
    #             email_data['date'].append(email_decoded['date'])
    #             email_data['from'].append(email_decoded['from'])
    #             email_data['to'].append(email_decoded['to'])
    #             email_data['subject'].append(email_decoded['subject'])
    #             email_data['content'].append(email_decoded['content'])

    #         except Exception as e:
    #             print(f"Error decoding email {email_id}: {e}")

    #     # Select Sent folder
    #     imap_server.select('"[Gmail]/Sent Mail"')
    #     # Build the search criteria based on the provided parameters
    #     search_criteria = []
    #     search_criteria.append(f'(FROM "{sender}")')
    #     search_criteria.append(f'(TO "{receiver}")')
    #     search_criteria.append(f'(SINCE "{start_date.strftime("%d-%b-%Y")}")')
    #     search_criteria.append(f'(BEFORE "{end_date.strftime("%d-%b-%Y")}")')

    #     search_query = ' '.join(search_criteria)
    #     result_inbox, data_inbox = imap_server.search(None, search_query)

    #     email_data = {
    #         'email_id': [],
    #         'date': [],
    #         'from': [],
    #         'to': [],
    #         'subject': [],
    #         'content': [],
    #     }

    #     # Process emails from Inbox
    #     for email_id in data_inbox[0].split():
    #         try:
    #             result, email_info = imap_server.fetch(email_id, '(RFC822)')
    #             email_raw = email_info[0][1]

    #             # Decode the email message
    #             email_decoded = decode_email(email_raw)

    #             # Add the decoded email message to the data dictionary
    #             email_data['email_id'].append(email_id)
    #             email_data['date'].append(email_decoded['date'])
    #             email_data['from'].append(email_decoded['from'])
    #             email_data['to'].append(email_decoded['to'])
    #             email_data['subject'].append(email_decoded['subject'])
    #             email_data['content'].append(email_decoded['content'])

    #         except Exception as e:
    #             print(f"Error decoding email {email_id}: {e}")

    #     # Create a DataFrame from the collected data
    #     df = pd.DataFrame(email_data)