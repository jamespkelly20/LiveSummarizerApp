import streamlit as st
import pandas as pd
import openai  
from summarization_function import get_emails_and_summarize
import imaplib
from data_processing_live import checkLogin
from data_processing_live import fetchRequiredEmails
import math
import sys
import re
# Have to enable IMAP server \n",
    # May need to enable less secure apps in order to login using IMAP.\n",
    # To do this, go to the Security settings in your Gmail account and enable the \"Allow less secure apps\" option.\n",
    #imap_server = imaplib.IMAP4_SSL('imap.gmail.com')\n",
    ## IN order to get this security key password you ahve to go into gmail settings and allow IMAP settings and then create\n",
    ## an app password. This will generate a 16 digit key for you to use. \n",

    # Follow the instructions at https://streamlit.io/ to install streamlit locally. (pip install streamlit)


#sender_email = richard.shapiro@enron.com jeff.dasovich@enron.com
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Streamlit UI
st.set_page_config(page_title="Email Summarization", page_icon=":tada:", layout="wide")

if "df" not in st.session_state:
    st.session_state.df = None

if "live_summaries" not in st.session_state:
    st.session_state.live_summaries = {}

if "login_successful" not in st.session_state:
    st.session_state.login_successful = False

with st.container():
    st.title("Large Language Model (LLM) Email Summarizer")

with st.container():
    st.write("---")
    left_column, right_column = st.columns(2)
    original_emails_info = []

    with left_column:
        st.header("Summarize live personal data")
        imap_server = imaplib.IMAP4_SSL('imap.gmail.com')
        emailAddress = st.text_input("Enter your email:")
        password = st.text_input("Enter your security key:", type="password")
        if st.button("Login"):
            with st.spinner("Logging in..."):
                # Only set login_successful to True upon successful login
                login_successful = checkLogin(emailAddress, password)
                if login_successful:
                    st.success("Login successful!")
                    st.session_state.login_successful = True
                    
                else:
                    st.error(f"Login failed...")
                # if fetchEmailDetails(emailAddress, password) is not None:
                #     st.session_state.login_successful = True
                #     st.text("Logged in successfully!")

        if st.session_state.login_successful:
            email1 = st.text_input("Enter the Sender's Email Address:")
            email2 = st.text_input("Enter the Recipient's Email Address:")
            startDate = st.date_input("Enter Start Date:", min_value=pd.to_datetime('2000-01-01'))
            endDate = st.date_input("Enter End Date:", min_value=pd.to_datetime('2000-01-01'))
            totalWordsInOutput = st.number_input("Enter Number of Words in Output:", min_value=20, value=250, step=25)

            # Button to trigger summarization
            if st.button("Summarize Live Emails"):
                # Fetch emails only when the "Summarize Live Emails" button is pressed
                with st.spinner("Fetching and summarizing emails..."):
                    st.session_state.df = fetchRequiredEmails(emailAddress, password, email1, email2, startDate, endDate)
                    print("st.session_state.df: = ", st.session_state.df)
                    if st.session_state.df is not None:
                        try:
                            summary, original_emails_info = get_emails_and_summarize(st.session_state.df, email1, email2, startDate, endDate, totalWordsInOutput)
                            st.session_state.live_summaries["live_emails"] = {
                                "summary": summary,
                                "original_emails_info": original_emails_info
                            }
                            st.session_state.live_summaries["live_emails"] = summary
                            st.markdown("### Summarized Output:")
                            st.markdown(summary, unsafe_allow_html=True)
                            st.text("Summarization completed!")
                        except ValueError:
                            st.warning("Error occurred during summarization. \n\nEither one or more email addresses have not been found, or there is no existing emails!")
                        except openai.error.InvalidRequestError as e:
                            st.warning(f"The total words in the emails exceeded the models capacity. \nPlease reduce the input and try again")
                        except openai.error.RateLimitError:
                            # This block catches the RateLimitError specifically
                            st.error("OPENAI has reached its limit. Try again soon or shorten the amount of emails you want summarized.")
                        except Exception as e:
                            # Generic exception handler for any other exceptions
                            st.error(f"An unexpected error occurred: {e}")
                    else:
                        st.warning("No emails found for the specified criteria.")

            if st.button("Clear Live Emails Output"):
                if "live_emails" in st.session_state.live_summaries:
                    del st.session_state.live_summaries["live_emails"]

    
    with right_column:
        st.header("Original Emails:")
        for info in original_emails_info:
            # Convert newlines in email content to HTML line breaks while escaping other HTML
            formatted_email = info['Email'].replace("\n", "<br>")
            
            email_content = f"""
            <div style="font-size: 16px;">
                <strong><br>From:</strong> {info['From']}<br>
                <strong>To:</strong> {info['To']}<br>
                <strong>Date:</strong> {info['Date']}<br>
                <strong>Email:</strong><br><br>{formatted_email}<br>
            </div>
            """
            st.markdown(email_content, unsafe_allow_html=True) 

    # with right_column:
    #     st.header("Original Emails:")
    #     for info in original_emails_info:
    #         st.markdown(f"**From:** {info['From']}  \n**To:** {info['To']}  \n**Date:** {info['Date']}  \n**Email:** \n\n {info['Email']}  \n")
